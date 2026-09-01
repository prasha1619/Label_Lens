from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class LegalStatusEnum(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    WARNING = "WARNING"
    NOT_DETECTED = "NOT_DETECTED"
    UNCERTAIN = "UNCERTAIN"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    UNABLE_TO_VERIFY = "UNABLE_TO_VERIFY"

class OverallComplianceStatus(str, Enum):
    COMPLIANT = "COMPLIANT"
    NON_COMPLIANT = "NON_COMPLIANT"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    UNABLE_TO_VERIFY = "UNABLE_TO_VERIFY"

class RuleRequirementSchema(BaseModel):
    rule_id: str
    field_name: str
    title: str
    legal_reference: str
    description: str
    is_mandatory: bool = True
    min_confidence_pass: int = 70
    min_confidence_warning: int = 50
    validation_regex: Optional[str] = None
    severity_if_missing: str = "HIGH"  # HIGH, MEDIUM, LOW
    recommendation_template: str

class ProductCategorySchema(BaseModel):
    category_id: str
    display_name: str
    description: str
    rules: List[RuleRequirementSchema] = Field(default_factory=list)

class RuleCheckResult(BaseModel):
    rule_id: str
    rule_title: str
    legal_reference: str
    field_name: str
    display_name: str
    is_mandatory: bool
    status: LegalStatusEnum
    detected_value: Optional[str] = None
    raw_ocr_value: Optional[str] = None
    confidence: Optional[float] = None
    explanation: str
    inspector_recommendation: Optional[str] = None
    bbox: Optional[List[int]] = None
    evidence_available: bool = False

class ViolationSummary(BaseModel):
    field_name: str
    severity: str  # HIGH, MEDIUM, LOW, ADVISORY
    rule_id: str
    legal_reference: Optional[str] = None
    reason: str
    recommendation: str

class ComplianceEvaluationResult(BaseModel):
    product_category: str
    rule_set_version: str
    overall_status: OverallComplianceStatus
    compliance_score: float  # Secondary coverage metric 0-100
    rule_checks: List[RuleCheckResult] = Field(default_factory=list)
    violations: List[ViolationSummary] = Field(default_factory=list)
    disclaimer: str = (
        "AI-assisted screening result. Final legal determination requires verification "
        "by an authorized inspector/competent authority and depends on the applicable "
        "rules and the quality/completeness of the submitted evidence."
    )
