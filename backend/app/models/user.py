from datetime import datetime, timedelta
import hashlib
import uuid
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String
from sqlalchemy.orm import relationship
from app.database.base import Base

def uuid4(): return str(uuid.uuid4())

class User(Base):
    __tablename__ = 'users'
    id = Column(String(36), primary_key=True, default=uuid4)
    full_name = Column(String(120), nullable=False)
    email = Column(String(254), nullable=False, unique=True, index=True)
    password_hash = Column(String(512), nullable=False)
    organization = Column(String(160))
    profile_photo_path = Column(String(500))
    role = Column(String(20), nullable=False, default='inspector', index=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login_at = Column(DateTime)
    inspections = relationship('Inspection', back_populates='owner')
    sessions = relationship('AuthSession', back_populates='user', cascade='all, delete-orphan')

class AuthSession(Base):
    __tablename__ = 'auth_sessions'
    id = Column(String(36), primary_key=True, default=uuid4)
    user_id = Column(String(36), ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    token_hash = Column(String(64), nullable=False, unique=True, index=True)
    expires_at = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    revoked_at = Column(DateTime)
    user = relationship('User', back_populates='sessions')
