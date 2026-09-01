from datetime import datetime
import uuid
from sqlalchemy import Column, String, DateTime, Text, JSON, ForeignKey
from app.database.base import Base

def generate_uuid():
    return str(uuid.uuid4())

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    inspection_id = Column(String(36), nullable=True, index=True)
    user_id = Column(String(36), ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True)
    action = Column(String(100), nullable=False)  # INSPECTION_CREATED, PIPELINE_EXECUTED, REPORT_GENERATED
    actor = Column(String(100), default="SYSTEM_INSPECTOR")
    details = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

class ModelVersionRecord(Base):
    __tablename__ = "model_version_records"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    module_name = Column(String(100), nullable=False)  # CV_DETECTOR, OCR_ENGINE, RULE_ENGINE
    version_string = Column(String(100), nullable=False)
    weights_path = Column(String(500), nullable=True)
    is_available = Column(String(50), default="ACTIVE")
    loaded_at = Column(DateTime, default=datetime.utcnow)
