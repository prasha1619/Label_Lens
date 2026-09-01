import os
import sys
import time
from pathlib import Path
from typing import Dict, Any
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.config import settings
from app.database.session import get_db
from app.services.cv.detector import detector_service
from app.services.ocr.ocr_manager import ocr_manager
from app.services.rules.rule_loader import RuleLoader

router = APIRouter()

START_TIME = time.time()

@router.get("", response_model=Dict[str, Any])
def health_check(db: Session = Depends(get_db)):
    """
    Returns system status, module versions, model availability, and database connectivity.
    """
    uptime_sec = time.time() - START_TIME
    
    # Check Database
    db_status = "HEALTHY"
    try:
        db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"ERROR: {str(e)}"

    # Determine DB Dialect & Provider
    db_url_lower = settings.SQLALCHEMY_DATABASE_URI.lower()
    if "supabase" in db_url_lower:
        db_type = "Supabase PostgreSQL"
    elif "postgresql" in db_url_lower or "postgres" in db_url_lower:
        db_type = "PostgreSQL"
    else:
        db_type = "SQLite"

    # Check YOLO Detector
    yolo_available = detector_service.is_available()
    yolo_status = (
        f"ACTIVE ({Path(detector_service.model_path).name})"
        if yolo_available
        else "UNCONFIGURED (Running heuristic & OCR region parser)"
    )

    # Check OCR Engine
    active_ocr = ocr_manager.get_active_engine_name()

    # Check Rules
    categories = RuleLoader.list_categories()

    return {
        "status": "ONLINE",
        "app_name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "uptime_seconds": round(uptime_sec, 1),
        "database": {
            "status": db_status,
            "url_type": db_type,
            "is_external": db_type != "SQLite"
        },
        "supabase_auth": {
            # Do not expose keys or make network calls from a health check. This
            # tells operators whether registration is configured to use auth.users.
            "configured": settings.supabase_auth_enabled,
            "provider": "Supabase Auth" if settings.supabase_auth_enabled else None,
        },
        "computer_vision": {
            "yolo_detector": yolo_status,
            "model_path": settings.MODEL_PATH,
            "is_yolo_loaded": yolo_available
        },
        "ocr_service": {
            "active_engine": active_ocr,
            "version": settings.OCR_VERSION
        },
        "rule_engine": {
            "version": settings.RULE_SET_VERSION,
            "active_categories": len(categories)
        }
    }
