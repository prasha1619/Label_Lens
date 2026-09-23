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

        from sqlalchemy import text
        with engine.connect() as conn:
            if is_sqlite:
                # SQLite PRAGMA migrations
                img_cols = [row[1] for row in conn.execute(text("PRAGMA table_info(image_records);")).fetchall()]
                if "panel_type" not in img_cols:
                    conn.execute(text("ALTER TABLE image_records ADD COLUMN panel_type VARCHAR(50) DEFAULT 'front';"))
                if "image_index" not in img_cols:
                    conn.execute(text("ALTER TABLE image_records ADD COLUMN image_index INTEGER DEFAULT 0;"))
                if "package_id" not in img_cols:
                    conn.execute(text("ALTER TABLE image_records ADD COLUMN package_id VARCHAR(100);"))
                if "bbox" not in img_cols:
                    conn.execute(text("ALTER TABLE image_records ADD COLUMN bbox JSON;"))

                insp_cols = [row[1] for row in conn.execute(text("PRAGMA table_info(inspections);")).fetchall()]
                if 'user_id' not in insp_cols:
                    conn.execute(text("ALTER TABLE inspections ADD COLUMN user_id VARCHAR(36);"))
                if 'package_id' not in insp_cols:
                    conn.execute(text("ALTER TABLE inspections ADD COLUMN package_id VARCHAR(100) DEFAULT 'Package #1';"))
                if 'parent_scan_id' not in insp_cols:
                    conn.execute(text("ALTER TABLE inspections ADD COLUMN parent_scan_id VARCHAR(36);"))
                if 'conflicts' not in insp_cols:
                    conn.execute(text("ALTER TABLE inspections ADD COLUMN conflicts JSON DEFAULT '[]';"))
                if 'review_decisions' not in insp_cols:
                    conn.execute(text("ALTER TABLE inspections ADD COLUMN review_decisions JSON DEFAULT '[]';"))
                if 'anomaly_signals' not in insp_cols:
                    conn.execute(text("ALTER TABLE inspections ADD COLUMN anomaly_signals JSON DEFAULT '[]';"))
                if 'is_offline_synced' not in insp_cols:
                    conn.execute(text("ALTER TABLE inspections ADD COLUMN is_offline_synced BOOLEAN DEFAULT 0;"))

                det_cols = [row[1] for row in conn.execute(text("PRAGMA table_info(detected_fields);")).fetchall()]
                if 'source_panel' not in det_cols:
                    conn.execute(text("ALTER TABLE detected_fields ADD COLUMN source_panel VARCHAR(100);"))
                if 'has_conflict' not in det_cols:
                    conn.execute(text("ALTER TABLE detected_fields ADD COLUMN has_conflict BOOLEAN DEFAULT 0;"))

                audit_cols = [row[1] for row in conn.execute(text("PRAGMA table_info(audit_logs);")).fetchall()]
                if 'user_id' not in audit_cols:
                    conn.execute(text("ALTER TABLE audit_logs ADD COLUMN user_id VARCHAR(36);"))

                user_cols = [row[1] for row in conn.execute(text("PRAGMA table_info(users);")).fetchall()]
                if 'profile_photo_path' not in user_cols:
                    conn.execute(text("ALTER TABLE users ADD COLUMN profile_photo_path VARCHAR(500);"))
            else:
                # PostgreSQL / Supabase ALTER TABLE IF NOT EXISTS migrations
                postgres_migrations = [
                    "ALTER TABLE inspections ADD COLUMN IF NOT EXISTS user_id VARCHAR(36);",
                    "ALTER TABLE inspections ADD COLUMN IF NOT EXISTS package_id VARCHAR(100) DEFAULT 'Package #1';",
                    "ALTER TABLE inspections ADD COLUMN IF NOT EXISTS parent_scan_id VARCHAR(36);",
                    "ALTER TABLE inspections ADD COLUMN IF NOT EXISTS conflicts JSON DEFAULT '[]';",
                    "ALTER TABLE inspections ADD COLUMN IF NOT EXISTS review_decisions JSON DEFAULT '[]';",
                    "ALTER TABLE inspections ADD COLUMN IF NOT EXISTS anomaly_signals JSON DEFAULT '[]';",
                    "ALTER TABLE inspections ADD COLUMN IF NOT EXISTS is_offline_synced BOOLEAN DEFAULT FALSE;",
                    "ALTER TABLE image_records ADD COLUMN IF NOT EXISTS panel_type VARCHAR(50) DEFAULT 'front';",
                    "ALTER TABLE image_records ADD COLUMN IF NOT EXISTS image_index INTEGER DEFAULT 0;",
                    "ALTER TABLE image_records ADD COLUMN IF NOT EXISTS package_id VARCHAR(100);",
                    "ALTER TABLE image_records ADD COLUMN IF NOT EXISTS bbox JSON;",
                    "ALTER TABLE detected_fields ADD COLUMN IF NOT EXISTS source_panel VARCHAR(100);",
                    "ALTER TABLE detected_fields ADD COLUMN IF NOT EXISTS has_conflict BOOLEAN DEFAULT FALSE;",
                    "ALTER TABLE compliance_checks ADD COLUMN IF NOT EXISTS source_panel VARCHAR(100);",
                    "ALTER TABLE compliance_checks ADD COLUMN IF NOT EXISTS conflict_detected BOOLEAN DEFAULT FALSE;",
                    "ALTER TABLE compliance_checks ADD COLUMN IF NOT EXISTS is_applicable BOOLEAN DEFAULT TRUE;",
                    "ALTER TABLE compliance_checks ADD COLUMN IF NOT EXISTS applicability_reason VARCHAR(255);",
                    "ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS user_id VARCHAR(36);",
                    "ALTER TABLE users ADD COLUMN IF NOT EXISTS profile_photo_path VARCHAR(500);",
                ]
                for stmt in postgres_migrations:
                    try:
                        conn.execute(text(stmt))
                    except Exception as col_e:
                        logger.debug(f"Migration note for statement '{stmt}': {col_e}")

            conn.commit()

        db_type = "SQLite" if is_sqlite else ("Supabase PostgreSQL" if "supabase" in db_uri.lower() else "PostgreSQL")
        logger.info(f"Database schema migrations initialized successfully on {db_type}.")
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
