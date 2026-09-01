from abc import ABC, abstractmethod
from typing import List, Optional
from app.schemas.ocr import OCRResultSchema

class BaseOCRService(ABC):
    """
    Standard interface for OCR engines.
    Ensures that switching OCR providers (PaddleOCR, EasyOCR, Tesseract, Cloud)
    does not affect the rest of the compliance pipeline.
    """

    @property
    @abstractmethod
    def engine_name(self) -> str:
        pass

    @abstractmethod
    def is_available(self) -> bool:
        pass

    @abstractmethod
    def extract_text(self, image_path: str) -> OCRResultSchema:
        """
        Processes image and returns structured line and word-level OCR output with bounding boxes.
        """
        pass
