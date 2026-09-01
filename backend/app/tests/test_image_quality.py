import pytest
import os
from pathlib import Path
from app.services.cv.image_quality import check_image_quality
from app.core.config import settings

def test_image_quality_on_compliant_sample():
    image_path = str(settings.DEMO_DIR / "images" / "compliant_shampoo.png")
    assert os.path.exists(image_path), f"Demo image {image_path} must exist"
    
    result = check_image_quality(image_path)
    assert result.is_acceptable is True
    assert result.width >= 400
    assert result.height >= 400
    assert result.blur_score >= 40.0

def test_image_quality_on_blurry_sample():
    image_path = str(settings.DEMO_DIR / "images" / "blurry_label_oil.png")
    assert os.path.exists(image_path), f"Demo image {image_path} must exist"
    
    result = check_image_quality(image_path)
    assert result.status == "FAIL"
    assert result.is_acceptable is False
    assert any("blur" in r.lower() or "sharpness" in r.lower() for r in result.reasons)
