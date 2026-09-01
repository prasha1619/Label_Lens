import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.core.config import settings
from app.core.logging import logger
from app.database.base import Base

db_uri = settings.SQLALCHEMY_DATABASE_URI
is_sqlite = db_uri.startswith("sqlite")

engine_kwargs = {
    "echo": False,
    "pool_pre_ping": True,
}

if is_sqlite:
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    # PostgreSQL / Supabase cloud connection pooling configuration
    engine_kwargs["pool_size"] = settings.DB_POOL_SIZE
    engine_kwargs["max_overflow"] = settings.DB_MAX_OVERFLOW
    engine_kwargs["pool_recycle"] = settings.DB_POOL_RECYCLE

engine = create_engine(db_uri, **engine_kwargs)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """Create all database tables on application startup and apply migrations if needed."""
    try:
        import app.models.inspection  # noqa
        import app.models.rule        # noqa
        import app.models.audit       # noqa
        import app.models.user        # noqa
        Base.metadata.create_all(bind=engine)

        # Apply schema updates for SQLite if columns are missing
        if is_sqlite:
            from sqlalchemy import text
            with engine.connect() as conn:
                existing_cols = [row[1] for row in conn.execute(text("PRAGMA table_info(image_records);")).fetchall()]
                if "panel_type" not in existing_cols:
                    conn.execute(text("ALTER TABLE image_records ADD COLUMN panel_type VARCHAR(50) DEFAULT 'front';"))
                if "image_index" not in existing_cols:
                    conn.execute(text("ALTER TABLE image_records ADD COLUMN image_index INTEGER DEFAULT 0;"))
                inspection_cols = [row[1] for row in conn.execute(text("PRAGMA table_info(inspections); ")).fetchall()]
                if 'user_id' not in inspection_cols:
                    conn.execute(text("ALTER TABLE inspections ADD COLUMN user_id VARCHAR(36);"))
                    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_inspections_user_id ON inspections (user_id);"))
                audit_cols = [row[1] for row in conn.execute(text("PRAGMA table_info(audit_logs); ")).fetchall()]
                if 'user_id' not in audit_cols:
                    conn.execute(text("ALTER TABLE audit_logs ADD COLUMN user_id VARCHAR(36);"))
                user_cols = [row[1] for row in conn.execute(text("PRAGMA table_info(users); ")).fetchall()]
                if 'profile_photo_path' not in user_cols:
                    conn.execute(text("ALTER TABLE users ADD COLUMN profile_photo_path VARCHAR(500);"))
                
                # Drop legacy unique index if present and create standard index
                try:
                    conn.execute(text("DROP INDEX IF EXISTS ix_image_records_inspection_id;"))
                    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_image_records_inspection_id ON image_records (inspection_id);"))
                except Exception as idx_e:
                    logger.debug(f"Index migration notice: {idx_e}")
                conn.commit()

        db_type = "SQLite" if is_sqlite else ("Supabase PostgreSQL" if "supabase" in db_uri.lower() else "PostgreSQL")
        logger.info(f"Database tables initialized successfully on {db_type}.")
    except Exception as e:
        logger.error(f"Database initialization error: {e}")
        raise

# Auto-initialize tables for immediate database readiness
init_db()

def get_db():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
