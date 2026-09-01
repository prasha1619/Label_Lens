from typing import List, Optional
from pydantic import BaseModel, Field

class OCRWord(BaseModel):
    text: str
    confidence: float
    bbox: List[int]  # [x1, y1, x2, y2]

class OCRLine(BaseModel):
    line_number: int
    text: str
    confidence: float
    bbox: List[int]  # [x1, y1, x2, y2]
    words: List[OCRWord] = Field(default_factory=list)

class OCRResultSchema(BaseModel):
    engine: str = "PaddleOCR"
    total_lines: int
    mean_confidence: float
    raw_full_text: str
    lines: List[OCRLine] = Field(default_factory=list)
    processing_time_ms: float
