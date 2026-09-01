from datetime import datetime
import uuid
from sqlalchemy import Column, String, Float, Integer, Boolean, DateTime, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship
from app.database.base import Base

def generate_uuid():
    return str(uuid.uuid4())

class Inspection(Base):
    __tablename__ = "inspections"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    user_id = Column(String(36), ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True)
    product_name = Column(String(255), nullable=True)
    product_category = Column(String(100), default="packaged_commodity", index=True)
    overall_status = Column(String(50), nullable=False, default="PENDING", index=True)  
    # Values: COMPLIANT, NON_COMPLIANT, NEEDS_REVIEW, UNABLE_TO_VERIFY, PENDING, PROCESSING, FAILED
    
    compliance_score = Column(Float, nullable=True)  # Secondary confidence/coverage metric (0-100)
    is_demo = Column(Boolean, default=False)
    execution_mode = Column(String(50), default="LIVE_PIPELINE")  # LIVE_PIPELINE, DEMO_SAMPLE, MODEL_UNCONFIGURED
    
    # Summary of findings
    total_checks = Column(Integer, default=0)
    passed_checks = Column(Integer, default=0)
    failed_checks = Column(Integer, default=0)
    warning_checks = Column(Integer, default=0)
    undetected_checks = Column(Integer, default=0)
    uncertain_checks = Column(Integer, default=0)
    
    # Audit & Version metadata
    cv_model_version = Column(String(100), nullable=True)
    ocr_version = Column(String(100), nullable=True)
    rule_set_version = Column(String(100), nullable=True)
    processing_time_ms = Column(Float, nullable=True)
    error_message = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    images = relationship("ImageRecord", back_populates="inspection", cascade="all, delete-orphan", order_by="ImageRecord.image_index")
    ocr_results = relationship("OCRResult", back_populates="inspection", cascade="all, delete-orphan")
    detected_fields = relationship("DetectedField", back_populates="inspection", cascade="all, delete-orphan")
    compliance_checks = relationship("ComplianceCheck", back_populates="inspection", cascade="all, delete-orphan")
    violations = relationship("Violation", back_populates="inspection", cascade="all, delete-orphan")
    owner = relationship('User', back_populates='inspections')

    @property
    def image(self):
        """Backward-compatible property returning the primary/first image record."""
        return self.images[0] if self.images else None

class ImageRecord(Base):
    __tablename__ = "image_records"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    inspection_id = Column(String(36), ForeignKey("inspections.id", ondelete="CASCADE"), index=True)
    panel_type = Column(String(50), default="front")  # front, back, side, top, general
    image_index = Column(Integer, default=0)
    
    original_filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    annotated_file_path = Column(String(500), nullable=True)
    file_size_bytes = Column(Integer, nullable=False)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    mime_type = Column(String(100), nullable=False)
    
    # Quality metrics
    quality_status = Column(String(50), default="PASS")  # PASS, WARNING, FAIL
    blur_score = Column(Float, nullable=True)
    brightness_score = Column(Float, nullable=True)
    contrast_score = Column(Float, nullable=True)
    glare_score = Column(Float, nullable=True)
    skew_angle = Column(Float, nullable=True)
    quality_reasons = Column(JSON, default=list)  # List of string reasons for degradation
    
    created_at = Column(DateTime, default=datetime.utcnow)

    inspection = relationship("Inspection", back_populates="images")

class OCRResult(Base):
    __tablename__ = "ocr_results"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    inspection_id = Column(String(36), ForeignKey("inspections.id", ondelete="CASCADE"), index=True)
    
    raw_text = Column(Text, nullable=False)
    confidence = Column(Float, nullable=False)
    bbox = Column(JSON, nullable=False)  # [x1, y1, x2, y2]
    line_number = Column(Integer, nullable=True)
    engine = Column(String(50), default="PaddleOCR")

    inspection = relationship("Inspection", back_populates="ocr_results")

class DetectedField(Base):
    __tablename__ = "detected_fields"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    inspection_id = Column(String(36), ForeignKey("inspections.id", ondelete="CASCADE"), index=True)
    
    field_name = Column(String(100), nullable=False, index=True)  # mrp, net_quantity, manufacturer, mfg_date, etc.
    display_name = Column(String(150), nullable=False)
    raw_value = Column(Text, nullable=True)
    normalized_value = Column(Text, nullable=True)
    unit = Column(String(50), nullable=True)  # g, ml, kg, INR, etc.
    confidence = Column(Float, nullable=False)
    detection_method = Column(String(50), default="OCR_REGEX")  # YOLO, OCR_REGEX, FUZZY, NLP
    bbox = Column(JSON, nullable=True)  # [x1, y1, x2, y2]
    metadata_info = Column(JSON, default=dict)
    
    inspection = relationship("Inspection", back_populates="detected_fields")

class ComplianceCheck(Base):
    __tablename__ = "compliance_checks"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    inspection_id = Column(String(36), ForeignKey("inspections.id", ondelete="CASCADE"), index=True)
    
    rule_id = Column(String(100), nullable=False, index=True)
    rule_title = Column(String(255), nullable=False)
    legal_reference = Column(String(255), nullable=True)  # e.g., "Rule 6(1)(e), Legal Metrology (PC) Rules 2011"
    field_name = Column(String(100), nullable=False)
    is_mandatory = Column(Boolean, default=True)
    
    status = Column(String(50), nullable=False)  
    # PASS, FAIL, WARNING, NOT_DETECTED, UNCERTAIN, NOT_APPLICABLE, UNABLE_TO_VERIFY
    
    detected_value = Column(Text, nullable=True)
    confidence = Column(Float, nullable=True)
    explanation = Column(Text, nullable=False)
    inspector_recommendation = Column(Text, nullable=True)
    bbox = Column(JSON, nullable=True)

    inspection = relationship("Inspection", back_populates="compliance_checks")

class Violation(Base):
    __tablename__ = "violations"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    inspection_id = Column(String(36), ForeignKey("inspections.id", ondelete="CASCADE"), index=True)
    
    field_name = Column(String(100), nullable=False)
    severity = Column(String(50), default="HIGH")  # HIGH, MEDIUM, LOW, ADVISORY
    rule_id = Column(String(100), nullable=False)
    reason = Column(Text, nullable=False)
    legal_provision = Column(String(255), nullable=True)
    recommendation = Column(Text, nullable=False)

    inspection = relationship("Inspection", back_populates="violations")
