from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from app.schemas.rule import RuleCheckResult, ViolationSummary, OverallComplianceStatus, LegalStatusEnum
from app.schemas.cv import QualityAssessment
from app.schemas.ocr import OCRResultSchema
from app.schemas.extraction import ExtractedField

class ImageRecordSchema(BaseModel):
    id: str
    original_filename: str
    file_path: str
    annotated_file_path: Optional[str] = None
    file_size_bytes: int
    panel_type: str = "front"
    image_index: int = 0
    width: Optional[int] = None
    height: Optional[int] = None
    mime_type: str
    quality_status: str
    blur_score: Optional[float] = None
    brightness_score: Optional[float] = None
    contrast_score: Optional[float] = None
    glare_score: Optional[float] = None
    quality_reasons: List[str] = Field(default_factory=list)

class InspectionCreate(BaseModel):
    product_category: str = "packaged_commodity"
    is_demo: bool = False
    demo_key: Optional[str] = None

class InspectionResponse(BaseModel):
    id: str
    product_name: Optional[str] = None
    product_category: str
    overall_status: str
    compliance_score: Optional[float] = None
    is_demo: bool
    execution_mode: str
    
    total_checks: int
    passed_checks: int
    failed_checks: int
    warning_checks: int
    undetected_checks: int
    uncertain_checks: int
    
    cv_model_version: Optional[str] = None
    ocr_version: Optional[str] = None
    rule_set_version: Optional[str] = None
    processing_time_ms: Optional[float] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    image: Optional[ImageRecordSchema] = None
    images: List[ImageRecordSchema] = Field(default_factory=list)
    ocr_summary: Optional[Dict[str, Any]] = None
    detected_fields: List[ExtractedField] = Field(default_factory=list)
    compliance_checks: List[RuleCheckResult] = Field(default_factory=list)
    violations: List[ViolationSummary] = Field(default_factory=list)

class InspectionListItem(BaseModel):
    id: str
    product_name: Optional[str] = None
    product_category: str
    overall_status: str
    compliance_score: Optional[float] = None
    quality_status: Optional[str] = "PASS"
    total_checks: int
    passed_checks: int
    failed_checks: int
    created_at: datetime
    original_filename: Optional[str] = None
    annotated_image_available: bool = False
    image_count: int = 1

class InspectionListResponse(BaseModel):
    total: int
    page: int
    limit: int
    items: List[InspectionListItem]

class DashboardMetrics(BaseModel):
    total_inspections: int
    compliant_count: int
    non_compliant_count: int
    needs_review_count: int
    unable_to_verify_count: int
    average_compliance_score: float
    category_distribution: Dict[str, int]
    recent_inspections: List[InspectionListItem]

class FieldOverrideRequest(BaseModel):
    field_name: str
    value: str
    unit: Optional[str] = None
    note: Optional[str] = "Manually verified by inspector"

