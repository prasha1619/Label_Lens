import os
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from pathlib import Path
from app.core.config import settings
from app.core.logging import logger
import cv2
import numpy as np
from PIL import Image
from app.schemas.cv import DetectionRegion, CVDetectionResult, DetectedPackage, MultiPackageDetectionResult

class BaseDetector(ABC):
    """Abstract Base Class for Object/Region Detectors."""
    
    @abstractmethod
    def is_available(self) -> bool:
        pass

    @abstractmethod
    def detect(self, image_path: str) -> CVDetectionResult:
        pass

    @abstractmethod
    def detect_packages(self, image_path: str) -> MultiPackageDetectionResult:
        pass

class YOLODetector(BaseDetector):
    """
    YOLO-compatible legal label region and multi-package detector.
    Loads fine-tuned weights from MODEL_PATH.
    Provides robust multi-package segmentation and isolated cropping.
    """

    PACKAGE_CLASSES = {
        "package", "bottle", "box", "can", "packet", "product", "container",
        "carton", "bag", "pouch", "commodity", "item"
    }

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

    def detect_packages(self, image_path: str) -> MultiPackageDetectionResult:
        """
        Detects distinct packaged commodities in an image frame.
        Returns a list of DetectedPackage instances with isolated crop files.
        """
        if not os.path.exists(image_path):
            return MultiPackageDetectionResult(total_detected=0, packages=[])

        try:
            with Image.open(image_path) as img:
                img_w, img_h = img.size
        except Exception as e:
            logger.error(f"Failed to read image dimensions for {image_path}: {e}")
            return MultiPackageDetectionResult(total_detected=0, packages=[])

        package_boxes: List[Dict[str, Any]] = []

        # 1. Try YOLO detection first if active
        if self._is_loaded and self.model is not None:
            try:
                results = self.model.predict(
                    source=image_path,
                    conf=max(0.25, settings.CONFIDENCE_THRESHOLD),
                    verbose=False
                )
                for result in results:
                    for box in result.boxes:
                        cls_id = int(box.cls[0].item())
                        cls_name = result.names.get(cls_id, f"class_{cls_id}").lower()
                        conf = float(box.conf[0].item())
                        xyxy = [int(v) for v in box.xyxy[0].tolist()]
                        # Check if box covers a reasonable package area (>3% of frame)
                        box_area = (xyxy[2] - xyxy[0]) * (xyxy[3] - xyxy[1])
                        frame_area = img_w * img_h
                        if box_area >= 0.03 * frame_area:
                            package_boxes.append({
                                "bbox": xyxy,
                                "confidence": round(conf, 4),
                                "label_class": cls_name
                            })
            except Exception as e:
                logger.warning(f"YOLO multi-package detection failed: {e}")

        # 2. Heuristic multi-package contour detection if YOLO didn't find multiple packages
        if len(package_boxes) < 2:
            try:
                cv_img = cv2.imread(image_path)
                if cv_img is not None:
                    gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
                    blurred = cv2.GaussianBlur(gray, (7, 7), 0)
                    edged = cv2.Canny(blurred, 30, 120)
                    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 15))
                    closed = cv2.morphologyEx(edged, cv2.MORPH_CLOSE, kernel)
                    contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

                    detected_contours = []
                    frame_area = img_w * img_h
                    for c in contours:
                        x, y, w, h = cv2.boundingRect(c)
                        area = w * h
                        # Require package candidate to be between 8% and 92% of frame
                        if 0.08 * frame_area <= area <= 0.92 * frame_area and w >= 60 and h >= 60:
                            detected_contours.append({
                                "bbox": [max(0, x), max(0, y), min(img_w, x + w), min(img_h, y + h)],
                                "confidence": 0.88,
                                "label_class": "packaged_commodity"
                            })

                    # If multiple non-overlapping contours found, sort left-to-right
                    if len(detected_contours) >= 2:
                        # Sort by X position (reading order left-to-right)
                        detected_contours.sort(key=lambda item: item["bbox"][0])
                        package_boxes = detected_contours
            except Exception as e:
                logger.warning(f"Contour package segmentation error: {e}")

        # 3. Fallback to single full-frame package if none or single package
        if not package_boxes:
            package_boxes = [{
                "bbox": [0, 0, img_w, img_h],
                "confidence": 1.0,
                "label_class": "packaged_commodity"
            }]

        # 4. Generate isolated crop images for each package
        packages: List[DetectedPackage] = []
        base_name = Path(image_path).stem
        upload_dir = settings.UPLOAD_DIR

        for idx, pbox in enumerate(package_boxes):
            pkg_id = f"Package #{idx + 1}"
            bbox = pbox["bbox"]
            x1, y1, x2, y2 = bbox

            # Ensure valid bounds
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(img_w, max(x1 + 10, x2)), min(img_h, max(y1 + 10, y2))
            crop_w = x2 - x1
            crop_h = y2 - y1

            # Crop if sub-region of full image
            if crop_w < img_w or crop_h < img_h:
                try:
                    with Image.open(image_path) as full_img:
                        crop_img = full_img.crop((x1, y1, x2, y2))
                        crop_filename = f"{base_name}_pkg{idx + 1}.jpg"
                        crop_path = str(upload_dir / crop_filename)
                        crop_img.save(crop_path, "JPEG", quality=95)
                except Exception as e:
                    logger.error(f"Failed to create crop for {pkg_id}: {e}")
                    crop_path = image_path
            else:
                crop_path = image_path

            packages.append(
                DetectedPackage(
                    package_id=pkg_id,
                    package_index=idx,
                    bbox=[x1, y1, x2, y2],
                    confidence=pbox.get("confidence", 0.95),
                    label_class=pbox.get("label_class", "packaged_commodity"),
                    cropped_image_path=crop_path,
                    crop_width=crop_w,
                    crop_height=crop_h
                )
            )

        # 5. Draw visual multi-package overview annotation
        annotated_path = None
        if len(packages) > 1:
            try:
                annotated_path = self._draw_multi_package_annotation(image_path, packages)
            except Exception as e:
                logger.warning(f"Could not generate multi-package annotated overview: {e}")

        return MultiPackageDetectionResult(
            total_detected=len(packages),
            packages=packages,
            annotated_frame_path=annotated_path
        )

    @staticmethod
    def _draw_multi_package_annotation(image_path: str, packages: List[DetectedPackage]) -> str:
        """Annotates full frame with bounding boxes and badges for each detected package."""
        img = cv2.imread(image_path)
        if img is None:
            return image_path

        colors_list = [
            (255, 120, 0),  # Cyan-blue
            (0, 200, 100),  # Emerald
            (180, 50, 255),  # Violet
            (0, 165, 255),  # Orange
            (255, 200, 0),  # Sky blue
        ]

        for idx, pkg in enumerate(packages):
            x1, y1, x2, y2 = pkg.bbox
            color = colors_list[idx % len(colors_list)]

            # Draw outer rectangle
            cv2.rectangle(img, (x1, y1), (x2, y2), color, 3)

            # Draw top label badge
            label_text = f"{pkg.package_id} ({int(pkg.confidence * 100)}%)"
            (tw, th), _ = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
            cv2.rectangle(img, (x1, max(0, y1 - th - 12)), (x1 + tw + 16, y1), color, -1)
            cv2.putText(
                img,
                label_text,
                (x1 + 8, max(y1 - 6, th + 2)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (255, 255, 255),
                2,
                cv2.LINE_AA
            )

        annotated_name = f"{Path(image_path).stem}_multi_packages.jpg"
        out_path = str(settings.UPLOAD_DIR / annotated_name)
        cv2.imwrite(out_path, img)
        return out_path

# Singleton Detector instance
detector_service = YOLODetector()

