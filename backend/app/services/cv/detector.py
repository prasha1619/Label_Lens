import os
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from pathlib import Path
from app.core.config import settings
from app.core.logging import logger
from app.schemas.cv import DetectionRegion, CVDetectionResult

class BaseDetector(ABC):
    """Abstract Base Class for Object/Region Detectors."""
    
    @abstractmethod
    def is_available(self) -> bool:
        pass

    @abstractmethod
    def detect(self, image_path: str) -> CVDetectionResult:
        pass

class YOLODetector(BaseDetector):
    """
    YOLO-compatible legal label region detector.
    Loads custom fine-tuned Legal Metrology weights from MODEL_PATH.
    If weights are not found, reports unconfigured status truthfully without fabricating detections.
    """

    def __init__(self, model_path: Optional[str] = None):
        self.model_path = model_path or settings.MODEL_PATH
        self.model = None
        self._is_loaded = False
        self._load_model()

    def _load_model(self):
        if not self.model_path or not Path(self.model_path).exists():
            logger.info(
                f"YOLO detector model not found at '{self.model_path}'. "
                "Inference detector will report unconfigured status."
            )
            self._is_loaded = False
            return

        try:
            # Attempt to load using ultralytics YOLO if installed
            from ultralytics import YOLO
            self.model = YOLO(self.model_path)
            self._is_loaded = True
            logger.info(f"Loaded custom YOLO model from {self.model_path}")
        except ImportError:
            logger.warning("ultralytics package is not installed. YOLO model cannot be loaded.")
            self._is_loaded = False
        except Exception as e:
            logger.error(f"Failed to load YOLO model from {self.model_path}: {e}")
            self._is_loaded = False

    def is_available(self) -> bool:
        return self._is_loaded

    def detect(self, image_path: str) -> CVDetectionResult:
        if not self._is_loaded or self.model is None:
            return CVDetectionResult(
                model_status="AI detection model not configured — demo/inference mode unavailable.",
                model_version="custom-yolo-unconfigured",
                regions=[]
            )

        try:
            results = self.model.predict(
                source=image_path,
                conf=settings.CONFIDENCE_THRESHOLD,
                verbose=False
            )
            
            regions: List[DetectionRegion] = []
            for result in results:
                boxes = result.boxes
                for box in boxes:
                    cls_id = int(box.cls[0].item())
                    cls_name = result.names.get(cls_id, f"class_{cls_id}").lower()
                    conf = float(box.conf[0].item())
                    xyxy = [int(v) for v in box.xyxy[0].tolist()]

                    regions.append(
                        DetectionRegion(
                            label_class=cls_name,
                            bbox=xyxy,
                            confidence=round(conf, 4),
                            detection_method="YOLO"
                        )
                    )

            return CVDetectionResult(
                model_status="ACTIVE",
                model_version=f"YOLO-{Path(self.model_path).name}",
                regions=regions
            )
        except Exception as e:
            logger.error(f"YOLO inference error on {image_path}: {e}")
            return CVDetectionResult(
                model_status=f"Inference error: {str(e)}",
                model_version="error",
                regions=[]
            )

# Singleton Detector instance
detector_service = YOLODetector()
