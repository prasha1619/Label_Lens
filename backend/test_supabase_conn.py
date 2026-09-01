"""
LabelLens Supabase PostgreSQL Connection & Health Diagnostic Tool
Usage:
    python backend/test_supabase_conn.py [OPTIONAL_SUPABASE_DATABASE_URL]
"""

import sys
import os
import time
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.core.config import settings
from sqlalchemy import create_engine, text, inspect
from app.database.base import Base
import app.models.inspection  # noqa
import app.models.rule        # noqa
import app.models.audit       # noqa
import app.models.user        # noqa

def test_connection(target_url: str = None):
    url = target_url or settings.DATABASE_URL
    print("\n=======================================================")
    print("      LabelLens Supabase / Database Connection Test    ")
    print("=======================================================\n")

    # Normalize url
    if url.startswith("postgres://"):
        norm_url = url.replace("postgres://", "postgresql+psycopg2://", 1)
    elif url.startswith("postgresql://") and not url.startswith("postgresql+"):
        norm_url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
    else:
        norm_url = url

    # Mask credentials for display
    masked_url = norm_url
    if "@" in masked_url:
        prefix, rest = masked_url.split("@", 1)
        if ":" in prefix:
            scheme_user = prefix.rsplit(":", 1)[0]
            masked_url = f"{scheme_user}:****@{rest}"

    print(f"Target Database URL : {masked_url}")
    is_supabase = "supabase" in norm_url.lower()
    print(f"Detected Target     : {'Supabase PostgreSQL (Cloud)' if is_supabase else ('PostgreSQL' if 'postgres' in norm_url else 'SQLite')}")

    try:
        t0 = time.time()
        print("\n[1/4] Initializing SQLAlchemy engine...")
        engine_kwargs = {"echo": False, "pool_pre_ping": True}
        if norm_url.startswith("sqlite"):
            engine_kwargs["connect_args"] = {"check_same_thread": False}
        else:
            engine_kwargs["pool_size"] = 5
            engine_kwargs["pool_recycle"] = 300

        engine = create_engine(norm_url, **engine_kwargs)
        print("  -> Engine created successfully.")

        print("\n[2/4] Testing basic query connectivity (SELECT 1)...")
        with engine.connect() as conn:
            res = conn.execute(text("SELECT 1")).scalar()
            latency = (time.time() - t0) * 1000
            print(f"  -> Connection SUCCESS! Query returned {res} (Latency: {latency:.1f}ms)")

            # Check database version
            if not norm_url.startswith("sqlite"):
                version = conn.execute(text("SELECT version()")).scalar()
                print(f"  -> Remote Version: {version.split(',')[0] if version else 'N/A'}")

        print("\n[3/4] Creating all tables & schema from metadata...")
        Base.metadata.create_all(bind=engine)
        print("  -> Tables provisioned successfully.")

        print("\n[4/4] Inspecting existing tables in database:")
        inspector = inspect(engine)
        table_names = inspector.get_table_names()
        for idx, tbl in enumerate(table_names, 1):
            cols = [c['name'] for c in inspector.get_columns(tbl)]
            print(f"  {idx}. {tbl:<25} ({len(cols)} columns)")

        print("\n-------------------------------------------------------")
        print(" SUCCESS: Database is fully operational and ready for use!")
        print("-------------------------------------------------------\n")
        return True

    except Exception as e:
        print(f"\n[ERROR] Failed to connect to database: {e}")
        print("\nTroubleshooting tips for Supabase:")
        print(" 1. Check if the project is active in your Supabase dashboard.")
        print(" 2. If using the Connection Pooler, make sure port 6543 (Transaction) or 5432 (Session) is specified.")
        print(" 3. Ensure your password is correct and URL-encoded if it contains special characters.")
        print(" 4. Append ?sslmode=require to your connection string.")
        return False

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else None
    success = test_connection(target)
    sys.exit(0 if success else 1)
