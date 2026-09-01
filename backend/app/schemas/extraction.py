from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class ExtractedField(BaseModel):
    field_name: str  # e.g., mrp, net_quantity, manufacturer, mfg_date, expiry_date, consumer_care, country_of_origin
    display_name: str  # e.g., Maximum Retail Price (MRP)
    raw_value: Optional[str] = None
    normalized_value: Optional[str] = None
    unit: Optional[str] = None
    confidence: float = Field(..., ge=0.0, le=1.0)
    detection_method: str = "OCR_REGEX"
    bbox: Optional[List[int]] = None
    is_detected: bool = True
    metadata: Dict[str, Any] = Field(default_factory=dict)

class FieldNormalizationResult(BaseModel):
    category_id: str
    fields: Dict[str, ExtractedField] = Field(default_factory=dict)
    raw_to_normalized_map: Dict[str, str] = Field(default_factory=dict)
    extracted_count: int
