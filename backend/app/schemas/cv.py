from typing import List, Optional, Tuple
from pydantic import BaseModel, Field

class BoundingBox(BaseModel):
    x1: int = Field(..., description="Top-left X coordinate")
    y1: int = Field(..., description="Top-left Y coordinate")
    x2: int = Field(..., description="Bottom-right X coordinate")
    y2: int = Field(..., description="Bottom-right Y coordinate")

    def to_list(self) -> List[int]:
        return [self.x1, self.y1, self.x2, self.y2]

class QualityAssessment(BaseModel):
    status: str = Field(..., description="PASS, WARNING, or FAIL")
    is_acceptable: bool = Field(..., description="True if pipeline can reliably evaluate label")
    blur_score: float = Field(..., description="Laplacian variance sharpness metric")
    brightness_score: float = Field(..., description="Mean pixel intensity 0-255")
    contrast_score: float = Field(..., description="Pixel standard deviation 0-128")
    glare_score: float = Field(..., description="Percentage of oversaturated highlight pixels")
    skew_angle: float = Field(0.0, description="Estimated skew angle in degrees")
    width: int
    height: int
    reasons: List[str] = Field(default_factory=list, description="Explanations if image quality is degraded")

class DetectionRegion(BaseModel):
    label_class: str = Field(..., description="Field/Region class, e.g., mrp, net_quantity, manufacturer")
    bbox: List[int] = Field(..., description="[x1, y1, x2, y2]")
    confidence: float = Field(..., ge=0.0, le=1.0)
    detection_method: str = Field("YOLO", description="YOLO, HEURISTIC, or ANCHOR")

class CVDetectionResult(BaseModel):
    model_status: str = Field(..., description="ACTIVE, UNCONFIGURED, or FALLBACK")
    model_version: str
    regions: List[DetectionRegion] = Field(default_factory=list)
    annotated_image_url: Optional[str] = None

class DetectedPackage(BaseModel):
    package_id: str = Field(..., description="Unique package identifier, e.g., Package #1")
    package_index: int = Field(..., description="0-indexed package sequence")
    bbox: List[int] = Field(..., description="[x1, y1, x2, y2] in full frame")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    label_class: str = Field(default="packaged_commodity")
    cropped_image_path: Optional[str] = Field(None, description="Path to isolated package crop image")
    crop_width: Optional[int] = None
    crop_height: Optional[int] = None

class MultiPackageDetectionResult(BaseModel):
    total_detected: int = Field(default=1)
    packages: List[DetectedPackage] = Field(default_factory=list)
    annotated_frame_path: Optional[str] = None

