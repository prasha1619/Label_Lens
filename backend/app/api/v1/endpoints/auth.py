"""Cookie-backed, database-persisted authentication routes."""
from datetime import datetime, timedelta
import hashlib, hmac, json, os, re, secrets
import mimetypes, time
from typing import Any
import httpx
from fastapi.responses import FileResponse
from fastapi import APIRouter, Depends, HTTPException, Request, Response, UploadFile, File, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session
from app.core.config import settings
from app.database.session import get_db
from app.models.user import User, AuthSession
from app.models.audit import AuditLog

router = APIRouter()
COOKIE = 'labellens_session'
LOGIN_ATTEMPTS: dict[str, list[datetime]] = {}


def supabase_auth_request(method: str, path: str, *, key: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Call Supabase Auth and turn its response into a safe API error."""
    if not settings.SUPABASE_URL:
        raise HTTPException(status_code=503, detail='Supabase Auth is not configured')
    try:
        response = httpx.request(
            method,
            f"{settings.SUPABASE_URL.rstrip('/')}/auth/v1{path}",
            headers={'apikey': key, 'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'},
            json=payload,
            timeout=15.0,
        )
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=503, detail='Could not reach Supabase Auth. Please try again.') from exc

    if response.is_error:
        try:
            message = response.json().get('msg') or response.json().get('message') or response.json().get('error_description')
        except (ValueError, AttributeError):
            message = None
        raise HTTPException(status_code=409 if response.status_code == 422 else response.status_code, detail=message or 'Supabase authentication request failed')
    return response.json() if response.content else {}


def create_supabase_user(payload: 'RegisterRequest') -> str:
    """Create the canonical auth.users record and return its UUID."""
    if not settings.supabase_auth_enabled:
        raise HTTPException(
            status_code=503,
            detail='Supabase Auth needs SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY, and SUPABASE_SECRET_KEY.',
        )
    result = supabase_auth_request(
        'POST', '/admin/users', key=settings.SUPABASE_SECRET_KEY,
        payload={
            'email': payload.email,
            'password': payload.password,
            'email_confirm': True,
            'user_metadata': {'full_name': payload.full_name.strip(), 'organization': payload.organization.strip() if payload.organization else None},
        },
    )
    user_id = result.get('id')
    if not user_id:
        raise HTTPException(status_code=502, detail='Supabase Auth did not return a user ID')
    return user_id


def delete_supabase_user(user_id: str) -> None:
    """Best-effort compensation if local profile creation fails."""
    if settings.supabase_auth_enabled:
        try:
            supabase_auth_request('DELETE', f'/admin/users/{user_id}', key=settings.SUPABASE_SECRET_KEY)
        except HTTPException:
            pass

def hash_password(password: str) -> str:
    salt = os.urandom(16); value = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
    return f'scrypt${salt.hex()}${value.hex()}'
def verify_password(password: str, encoded: str) -> bool:
    try:
        _, salt, expected = encoded.split('$'); result = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=2**14, r=8, p=1)
        return hmac.compare_digest(result.hex(), expected)
    except (ValueError, TypeError): return False
def token_hash(token: str) -> str: return hashlib.sha256(token.encode()).hexdigest()
def user_data(user: User):
    return {
        'id': user.id,
        'full_name': user.full_name,
        'email': user.email,
        'organization': user.organization,
        'role': user.role,
        'profile_photo_url': f'/api/v1/auth/photo/{user.id}' if user.profile_photo_path else None,
        'created_at': user.created_at,
        'last_login_at': user.last_login_at
    }
def record(db, user_id, event, metadata=None): db.add(AuditLog(user_id=user_id, action=event, actor='AUTHENTICATED_USER', details=metadata or {}))

class RegisterRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: str = Field(max_length=254)
    password: str
    confirm_password: str
    organization: str | None = Field(default=None, max_length=160)
    @field_validator('email')
    @classmethod
    def email_valid(cls, value):
        value = value.strip().lower()
        if not re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+', value): raise ValueError('Enter a valid email address')
        return value
    @field_validator('password')
    @classmethod
    def password_valid(cls, value):
        if len(value) < 8 or not re.search('[A-Za-z]', value) or not re.search('[0-9]', value): raise ValueError('Password must be at least 8 characters and include a letter and number')
        return value
class LoginRequest(BaseModel):
    email: str = Field(max_length=254); password: str = Field(min_length=1, max_length=512)
class ProfileUpdate(BaseModel):
    full_name: str = Field(min_length=2, max_length=120); organization: str | None = Field(default=None, max_length=160)
class PasswordChange(BaseModel):
    current_password: str; new_password: str; confirm_password: str

def create_session(response: Response, db: Session, user: User):
    raw = secrets.token_urlsafe(48); expiry = datetime.utcnow() + timedelta(days=settings.SESSION_EXPIRE_DAYS)
    db.add(AuthSession(user_id=user.id, token_hash=token_hash(raw), expires_at=expiry)); db.commit()
    response.set_cookie(COOKIE, raw, httponly=True, secure=settings.COOKIE_SECURE, samesite='lax', max_age=settings.SESSION_EXPIRE_DAYS * 86400, path='/')
def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    raw = request.cookies.get(COOKIE)
    if not raw: raise HTTPException(status_code=401, detail='Authentication required')
    session = db.query(AuthSession).filter(AuthSession.token_hash == token_hash(raw), AuthSession.revoked_at.is_(None), AuthSession.expires_at > datetime.utcnow()).first()
    if not session or not session.user.is_active: raise HTTPException(status_code=401, detail='Session expired. Please log in again.')
    return session.user
def require_admin(user: User = Depends(get_current_user)):
    if user.role != 'admin': raise HTTPException(status_code=403, detail='Administrator access required')
    return user

@router.post('/register', status_code=201)
def register(payload: RegisterRequest, response: Response, db: Session = Depends(get_db)):
    if payload.password != payload.confirm_password: raise HTTPException(status_code=422, detail='Passwords do not match')
    if db.query(User).filter(User.email == payload.email).first(): raise HTTPException(status_code=409, detail='An account with this email already exists')
    supabase_user_id = create_supabase_user(payload)
    try:
        # Keep the app profile in public.users and use the same UUID as auth.users.
        # This makes inspections, profiles, and Supabase Auth refer to one account.
        user = User(id=supabase_user_id, full_name=payload.full_name.strip(), email=payload.email, password_hash=hash_password(payload.password), organization=payload.organization.strip() if payload.organization else None)
        db.add(user); db.flush(); record(db, user.id, 'USER_REGISTERED'); db.commit(); db.refresh(user); create_session(response, db, user)
    except Exception:
        db.rollback()
        delete_supabase_user(supabase_user_id)
        raise
    return {'user': user_data(user)}
@router.post('/login')
def login(payload: LoginRequest, response: Response, request: Request, db: Session = Depends(get_db)):
    key = request.client.host if request.client else 'unknown'; now = datetime.utcnow(); attempts = [t for t in LOGIN_ATTEMPTS.get(key, []) if t > now - timedelta(minutes=15)]
    if len(attempts) >= 10: raise HTTPException(status_code=429, detail='Too many login attempts. Please try again later.')
    email = payload.email.strip().lower()
    if not settings.supabase_auth_enabled:
        raise HTTPException(status_code=503, detail='Supabase Auth is not configured')
    try:
        supabase_auth_request('POST', '/token?grant_type=password', key=settings.SUPABASE_PUBLISHABLE_KEY, payload={'email': email, 'password': payload.password})
    except HTTPException as exc:
        if exc.status_code in (400, 401, 422):
            LOGIN_ATTEMPTS[key] = attempts + [now]
            raise HTTPException(status_code=401, detail='Invalid email or password') from exc
        raise
    user = db.query(User).filter(User.email == email).first()
    if not user or not user.is_active:
        LOGIN_ATTEMPTS[key] = attempts + [now]
        raise HTTPException(status_code=401, detail='Your application profile could not be found')
    LOGIN_ATTEMPTS.pop(key, None); user.last_login_at = now; record(db, user.id, 'USER_LOGIN'); db.commit(); create_session(response, db, user)
    return {'user': user_data(user)}
@router.post('/logout')
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    raw = request.cookies.get(COOKIE)
    if raw:
        session = db.query(AuthSession).filter(AuthSession.token_hash == token_hash(raw), AuthSession.revoked_at.is_(None)).first()
        if session: session.revoked_at = datetime.utcnow(); record(db, session.user_id, 'USER_LOGOUT'); db.commit()
    response.delete_cookie(COOKIE, path='/'); return {'message': 'Logged out'}
@router.get('/me')
def me(user: User = Depends(get_current_user)): return user_data(user)
@router.patch('/me')
def update_me(payload: ProfileUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    user.full_name = payload.full_name.strip(); user.organization = payload.organization.strip() if payload.organization else None; db.commit(); db.refresh(user); return user_data(user)
@router.post('/photo')
async def upload_profile_photo(file: UploadFile = File(...), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    ext = file.filename.split('.')[-1].lower() if file.filename and '.' in file.filename else ''
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f'Invalid image format. Allowed formats: {", ".join(settings.ALLOWED_EXTENSIONS)}')
    
    contents = await file.read()
    max_bytes = settings.PROFILE_PHOTO_MAX_SIZE_MB * 1024 * 1024
    if len(contents) > max_bytes:
        raise HTTPException(status_code=400, detail=f'File exceeds maximum size of {settings.PROFILE_PHOTO_MAX_SIZE_MB}MB')
    
    # Fetch persistent user from DB if available
    db_user = db.query(User).filter(User.id == user.id).first() or user
    
    # Remove old avatar file if present
    if db_user.profile_photo_path:
        old_path = settings.UPLOAD_DIR / db_user.profile_photo_path
        if old_path.exists():
            try: old_path.unlink()
            except OSError: pass
            
    avatars_dir = settings.UPLOAD_DIR / 'avatars'
    avatars_dir.mkdir(parents=True, exist_ok=True)
    filename = f'avatars/avatar_{db_user.id}_{int(time.time())}.{ext}'
    file_path = settings.UPLOAD_DIR / filename
    with open(file_path, 'wb') as f:
        f.write(contents)
        
    db_user.profile_photo_path = filename
    db.add(db_user)
    db.commit()
    record(db, db_user.id, 'PROFILE_PHOTO_UPDATED')
    return {'user': user_data(db_user)}

@router.get('/photo/{user_id}')
def get_profile_photo(user_id: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.profile_photo_path:
        raise HTTPException(status_code=404, detail='Profile photo not found')
    photo_file = settings.UPLOAD_DIR / user.profile_photo_path
    if not photo_file.exists():
        raise HTTPException(status_code=404, detail='Profile photo file not found')
    mime, _ = mimetypes.guess_type(str(photo_file))
    return FileResponse(photo_file, media_type=mime or 'image/jpeg', headers={'Cache-Control': 'public, max-age=86400'})

@router.delete('/photo')
def delete_profile_photo(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    db_user = db.query(User).filter(User.id == user.id).first() or user
    if db_user.profile_photo_path:
        old_path = settings.UPLOAD_DIR / db_user.profile_photo_path
        if old_path.exists():
            try: old_path.unlink()
            except OSError: pass
        db_user.profile_photo_path = None
        db.add(db_user)
        db.commit()
        record(db, db_user.id, 'PROFILE_PHOTO_REMOVED')
    return {'user': user_data(db_user)}


@router.post('/change-password')
def change_password(payload: PasswordChange, response: Response, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if payload.new_password != payload.confirm_password: raise HTTPException(status_code=422, detail='Passwords do not match')
    if len(payload.new_password) < 8 or not re.search('[A-Za-z]', payload.new_password) or not re.search('[0-9]', payload.new_password): raise HTTPException(status_code=422, detail='Password must be at least 8 characters and include a letter and number')
    try:
        supabase_auth_request('POST', '/token?grant_type=password', key=settings.SUPABASE_PUBLISHABLE_KEY, payload={'email': user.email, 'password': payload.current_password})
    except HTTPException as exc:
        if exc.status_code in (400, 401, 422):
            raise HTTPException(status_code=400, detail='Current password is incorrect') from exc
        raise
    supabase_auth_request('PUT', f'/admin/users/{user.id}', key=settings.SUPABASE_SECRET_KEY, payload={'password': payload.new_password})
    user.password_hash = hash_password(payload.new_password); db.query(AuthSession).filter(AuthSession.user_id == user.id).update({'revoked_at': datetime.utcnow()}); record(db, user.id, 'PASSWORD_CHANGED'); db.commit(); response.delete_cookie(COOKIE, path='/'); return {'message': 'Password changed. Please log in again.'}
