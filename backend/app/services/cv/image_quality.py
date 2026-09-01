import math
from typing import List, Tuple, Optional
from PIL import Image, ImageStat, ImageFilter
from app.core.logging import logger
from app.schemas.cv import QualityAssessment

try:
    import cv2
    import numpy as np
    HAS_OPENCV = True
except ImportError:
    HAS_OPENCV = False
    logger.info("OpenCV/NumPy not available directly; using PIL-based CV analysis.")

class ImageQualityAnalyzer:
    """
    Evaluates product label images for:
    - Resolution & Aspect ratio
    - Blur (Laplacian variance sharpness)
    - Brightness & Contrast
    - Glare / Highlight saturation
    - Skew / Perspective distortion
    """
    
    MIN_WIDTH = 400
    MIN_HEIGHT = 400
    BLUR_THRESHOLD_FAIL = 40.0
    BLUR_THRESHOLD_WARN = 75.0
    BRIGHTNESS_MIN = 25.0
    BRIGHTNESS_MAX = 250.0
    CONTRAST_MIN = 20.0
    GLARE_MAX_RATIO = 0.25  # 25% maximum blown-out highlight pixels

    @classmethod
    def evaluate(cls, image_path: str) -> QualityAssessment:
        reasons: List[str] = []
        status = "PASS"
        is_acceptable = True

        try:
            with Image.open(image_path) as img:
                width, height = img.size
                
                # Check 1: Resolution
                if width < cls.MIN_WIDTH or height < cls.MIN_HEIGHT:
                    reasons.append(
                        f"Low resolution: {width}x{height}px (Minimum required is {cls.MIN_WIDTH}x{cls.MIN_HEIGHT}px)"
                    )
                    status = "FAIL"
                    is_acceptable = False

                # Convert to Grayscale for metrics
                gray_img = img.convert("L")
                
                # Check 2: Brightness & Contrast
                stat = ImageStat.Stat(gray_img)
                brightness = float(stat.mean[0])
                contrast = float(stat.stddev[0])
                
                if brightness < cls.BRIGHTNESS_MIN:
                    reasons.append(f"Image is too dark (mean luminance: {brightness:.1f}/255). Details may be unreadable.")
                    if status != "FAIL":
                        status = "WARNING"
                elif brightness > cls.BRIGHTNESS_MAX:
                    reasons.append(f"Image is overexposed (mean luminance: {brightness:.1f}/255). Text may be washed out.")
                    if status != "FAIL":
                        status = "WARNING"
                        
                if contrast < cls.CONTRAST_MIN:
                    reasons.append(f"Low contrast ({contrast:.1f}). Text is hard to distinguish from label background.")
                    if status != "FAIL":
                        status = "WARNING"

                # Check 3: Glare / Highlight saturation
                histogram = gray_img.histogram()
                total_pixels = width * height
                highlight_pixels = sum(histogram[252:])
                glare_ratio = highlight_pixels / total_pixels if total_pixels > 0 else 0.0
                
                if glare_ratio > cls.GLARE_MAX_RATIO:
                    reasons.append(
                        f"Excessive surface glare / reflection detected ({glare_ratio*100:.1f}% oversaturated pixels)."
                    )
                    if status != "FAIL":
                        status = "WARNING"

                # Check 4: Blur / Sharpness
                blur_score = cls._calculate_blur_score(image_path, gray_img)
                if blur_score < cls.BLUR_THRESHOLD_FAIL:
                    reasons.append(
                        f"Significant motion blur or out-of-focus capture (sharpness score: {blur_score:.1f}, threshold: {cls.BLUR_THRESHOLD_FAIL})."
                    )
                    status = "FAIL"
                    is_acceptable = False
                elif blur_score < cls.BLUR_THRESHOLD_WARN:
                    reasons.append(
                        f"Mild blur detected (sharpness score: {blur_score:.1f}). Text recognition confidence may be degraded."
                    )
                    if status != "FAIL":
                        status = "WARNING"

                # Check 5: Skew estimation
                skew_angle = cls._estimate_skew_angle(image_path)

        except Exception as e:
            logger.error(f"Error evaluating image quality for {image_path}: {e}")
            return QualityAssessment(
                status="FAIL",
                is_acceptable=False,
                blur_score=0.0,
                brightness_score=0.0,
                contrast_score=0.0,
                glare_score=0.0,
                skew_angle=0.0,
                width=0,
                height=0,
                reasons=[f"Image could not be decoded or processed: {str(e)}"]
            )

        return QualityAssessment(
            status=status,
            is_acceptable=is_acceptable,
            blur_score=round(blur_score, 2),
            brightness_score=round(brightness, 2),
            contrast_score=round(contrast, 2),
            glare_score=round(glare_ratio, 4),
            skew_angle=round(skew_angle, 2),
            width=width,
            height=height,
            reasons=reasons
        )

    @classmethod
    def _calculate_blur_score(cls, image_path: str, gray_pil_img: Image.Image) -> float:
        """Calculates blur score using Laplacian variance."""
        if HAS_OPENCV:
            try:
                cv_img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
                if cv_img is not None:
                    laplacian = cv2.Laplacian(cv_img, cv2.CV_64F)
                    return float(laplacian.var())
            except Exception:
                pass
        
        edges = gray_pil_img.filter(ImageFilter.FIND_EDGES)
        stat = ImageStat.Stat(edges)
        return float(stat.var[0])

    @classmethod
    def _estimate_skew_angle(cls, image_path: str) -> float:
        """Estimates label text skew angle in degrees."""
        if HAS_OPENCV:
            try:
                cv_img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
                if cv_img is not None:
                    thresh = cv2.threshold(cv_img, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
                    coords = np.column_stack(np.where(thresh > 0))
                    if len(coords) > 50:
                        angle = cv2.minAreaRect(coords)[-1]
                        if angle < -45:
                            angle = -(90 + angle)
                        else:
                            angle = -angle
                        return float(angle)
            except Exception:
                pass
        return 0.0

def check_image_quality(image_path: str) -> QualityAssessment:
    return ImageQualityAnalyzer.evaluate(image_path)
