import os
from pathlib import Path
from typing import List, Optional
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "LabelLens - AI Legal Metrology Compliance"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Environment & Debug
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = os.getenv("DEBUG", "True").lower() in ("true", "1", "yes")
    
    # Base Directories
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    ROOT_DIR: Path = BASE_DIR.parent
    UPLOAD_DIR: Path = BASE_DIR / "uploads"
    DEMO_DIR: Path = ROOT_DIR / "demo"
    REPORTS_DIR: Path = BASE_DIR / "reports"
    RULES_DIR: Path = BASE_DIR / "app" / "services" / "rules" / "definitions"
    
    # Database & Supabase
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        os.getenv("SUPABASE_DATABASE_URL", f"sqlite:///{BASE_DIR / 'labellens.db'}")
    )
    SUPABASE_URL: Optional[str] = os.getenv("SUPABASE_URL", None)
    # Supabase renamed its API keys.  Keep the legacy name working while
    # accepting the current dashboard variable names used in this project.
    SUPABASE_PUBLISHABLE_KEY: Optional[str] = os.getenv(
        "SUPABASE_PUBLISHABLE_KEY", os.getenv("SUPABASE_ANON_KEY", os.getenv("SUPABASE_KEY"))
    )
    SUPABASE_SECRET_KEY: Optional[str] = os.getenv(
        "SUPABASE_SECRET_KEY", os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    )
    DB_POOL_SIZE: int = int(os.getenv("DB_POOL_SIZE", "10"))
    DB_MAX_OVERFLOW: int = int(os.getenv("DB_MAX_OVERFLOW", "20"))
    DB_POOL_RECYCLE: int = int(os.getenv("DB_POOL_RECYCLE", "300"))

    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        """
        Normalize database URL for SQLAlchemy compatibility.
        Converts postgres:// or postgresql:// to postgresql+psycopg2:// when using PostgreSQL/Supabase.
        """
        url = self.DATABASE_URL
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+psycopg2://", 1)
        elif url.startswith("postgresql://") and not url.startswith("postgresql+"):
            url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
        return url

    @property
    def supabase_auth_enabled(self) -> bool:
        """Whether the API can create and manage Supabase Auth users."""
        return bool(self.SUPABASE_URL and self.SUPABASE_PUBLISHABLE_KEY and self.SUPABASE_SECRET_KEY)

    # CORS
    CORS_ORIGINS: List[str] = [
        orig.strip() for orig in os.getenv(
            "CORS_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000,http://localhost:8000,http://127.0.0.1:8000"
        ).split(",") if orig.strip()
    ]
    COOKIE_SECURE: bool = os.getenv('COOKIE_SECURE', 'false').lower() in ('true', '1', 'yes')
    SESSION_EXPIRE_DAYS: int = int(os.getenv('REFRESH_TOKEN_EXPIRE_DAYS', '7'))
    
    # Computer Vision & Model Config
    # Default path for custom trained YOLO Legal Metrology model
    MODEL_PATH: Optional[str] = os.getenv("MODEL_PATH", str(ROOT_DIR / "models" / "legal_label_detector.pt"))
    CONFIDENCE_THRESHOLD: float = 0.50
    
    # OCR Engine: "paddleocr", "easyocr", "tesseract", or "fallback"
    OCR_ENGINE: str = os.getenv("OCR_ENGINE", "paddleocr")
    
    # File Limits
    MAX_UPLOAD_SIZE_MB: int = 15
    PROFILE_PHOTO_MAX_SIZE_MB: int = int(os.getenv('PROFILE_PHOTO_MAX_SIZE_MB', '3'))
    ALLOWED_EXTENSIONS: List[str] = ["jpg", "jpeg", "png", "webp"]
    
    # Versioning
    CV_MODEL_VERSION: str = "yolo11-legal-v1"
    OCR_VERSION: str = "PaddleOCR-v4-std"
    RULE_SET_VERSION: str = "LM-Rules-2026.1"

    class Config:
        case_sensitive = True
        extra = "allow"
        env_file = (
            str(Path(__file__).resolve().parent.parent.parent.parent / ".env"),
            str(Path(__file__).resolve().parent.parent.parent / ".env"),
            ".env"
        )

settings = Settings()

# Ensure directories exist
settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
(settings.UPLOAD_DIR / "avatars").mkdir(parents=True, exist_ok=True)
settings.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
(settings.ROOT_DIR / "models").mkdir(parents=True, exist_ok=True)
(settings.DEMO_DIR / "images").mkdir(parents=True, exist_ok=True)
(settings.DEMO_DIR / "expected").mkdir(parents=True, exist_ok=True)
