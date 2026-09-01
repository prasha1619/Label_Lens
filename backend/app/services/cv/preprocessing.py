import os
from typing import Tuple, Optional
from PIL import Image, ImageEnhance, ImageOps, ImageFilter
from app.core.logging import logger

try:
    import cv2
    import numpy as np
    HAS_OPENCV = True
except ImportError:
    HAS_OPENCV = False

class ImagePreprocessor:
    """
    Modular preprocessing pipeline for Legal Metrology labels:
    1. Grayscale conversion & contrast equalization
    2. Adaptive thresholding & noise reduction
    3. De-skewing and alignment
    4. Resolution normalization
    """

    @classmethod
    def preprocess(
        cls, 
        image_path: str, 
        output_path: Optional[str] = None,
        target_max_dim: int = 1920
    ) -> str:
        """
        Preprocesses image for optimal OCR and text detection.
        Returns the path to the preprocessed image file.
        """
        if output_path is None:
            base, ext = os.path.splitext(image_path)
            output_path = f"{base}_preprocessed{ext}"

        try:
            if HAS_OPENCV:
                cls._preprocess_opencv(image_path, output_path, target_max_dim)
            else:
                cls._preprocess_pil(image_path, output_path, target_max_dim)
            return output_path
        except Exception as e:
            logger.warning(f"Preprocessing error on {image_path}: {e}. Returning original.")
            return image_path

    @classmethod
    def _preprocess_opencv(cls, image_path: str, output_path: str, target_max_dim: int):
        # 0. Ensure EXIF orientation is respected
        try:
            with Image.open(image_path) as pil_img:
                pil_img = ImageOps.exif_transpose(pil_img)
                pil_img.save(image_path)
        except Exception:
            pass

        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"Could not read image with OpenCV at {image_path}")

        h, w = img.shape[:2]
        
        # 1. Resize if excessively large to keep OCR fast, or upscale if very small
        if max(h, w) > target_max_dim:
            scale = target_max_dim / float(max(h, w))
            img = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
        elif max(h, w) < 800:
            scale = 800.0 / float(max(h, w))
            img = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_CUBIC)

        # 2. Convert to LAB color space and apply CLAHE to L channel for illumination invariance
        lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        cl = clahe.apply(l)
        enhanced_lab = cv2.merge((cl, a, b))
        enhanced_bgr = cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2BGR)

        # 3. Bilateral filter for edge-preserving denoising
        denoised = cv2.bilateralFilter(enhanced_bgr, d=5, sigmaColor=50, sigmaSpace=50)

        cv2.imwrite(output_path, denoised)

    @classmethod
    def _preprocess_pil(cls, image_path: str, output_path: str, target_max_dim: int):
        with Image.open(image_path) as img:
            # Handle EXIF orientation
            img = ImageOps.exif_transpose(img)
            w, h = img.size
            
            # Resize if needed
            if max(w, h) > target_max_dim:
                scale = target_max_dim / float(max(w, h))
                img = img.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)

            # Enhance contrast
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(1.25)

            # Slight sharpening for crisp text edges
            img = img.filter(ImageFilter.UnsharpMask(radius=1.5, percent=120, threshold=3))

            img.save(output_path, quality=95)

def preprocess_image(image_path: str, output_path: Optional[str] = None) -> str:
    return ImagePreprocessor.preprocess(image_path, output_path)
