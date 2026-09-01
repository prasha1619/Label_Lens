import os
import json
from pathlib import Path
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database.session import get_db
from app.schemas.inspection import InspectionResponse
from app.api.v1.endpoints.inspections import format_inspection_response
from app.services.pipeline import run_inspection_pipeline

router = APIRouter()

DEMO_SAMPLES = [
    {
        "key": "compliant_shampoo",
        "title": "Compliant Herbal Shampoo (200ml)",
        "category": "cosmetics_and_toiletries",
        "filename": "compliant_shampoo.png",
        "expected_verdict": "COMPLIANT",
        "description": "Fully compliant cosmetic label containing MRP (₹249), Net Qty (200 ml), MFD (06/2026), full manufacturer postal address, and complete consumer care helpline & email.",
        "scenario": "Ideal compliant test case passing all statutory checks."
    },
    {
        "key": "missing_consumer_care_biscuit",
        "title": "Biscuits (Missing Consumer Care)",
        "category": "food_and_beverages",
        "filename": "missing_consumer_care_biscuit.png",
        "expected_verdict": "NON_COMPLIANT",
        "description": "Packaged food label having MRP and Net Weight, but omitting mandatory Consumer Grievance / Customer Care details under Rule 6(1)(da).",
        "scenario": "Mandatory field deficiency triggering violation & inspector recommendation."
    },
    {
        "key": "blurry_label_oil",
        "title": "Cooking Oil (Blurry / Low Quality)",
        "category": "food_and_beverages",
        "filename": "blurry_label_oil.png",
        "expected_verdict": "UNABLE_TO_VERIFY",
        "description": "Motion-blurred capture failing CV sharpness threshold (blur score < 40). Demonstrates anti-hallucination policy.",
        "scenario": "Quality assessment failure returning 'Unable to verify — manual inspection required'."
    },
    {
        "key": "non_standard_qty_snack",
        "title": "Potato Chips (Snack Multipack)",
        "category": "packaged_commodity",
        "filename": "non_standard_qty_snack.png",
        "expected_verdict": "COMPLIANT",
        "description": "Multipack snack label (2 x 50 g) with MRP ₹40, date declaration, and country of origin.",
        "scenario": "Multipack calculation and unit normalization."
    },
    {
        "key": "sample_electronics",
        "title": "USB-C Fast Charger (Electronics)",
        "category": "electronics_and_appliances",
        "filename": "sample_electronics.png",
        "expected_verdict": "COMPLIANT",
        "description": "Electronic accessory with Unit Count (1 N), MRP ₹799, Importer address, and Country of Origin declaration.",
        "scenario": "Electronics unit count & country of origin verification."
    }
]

@router.get("/samples", response_model=List[Dict[str, Any]])
def list_demo_samples():
    """
    Returns the list of curated demo product label scenarios and sample metadata.
    """
    return DEMO_SAMPLES

@router.get("/samples/{sample_key}/image")
def get_demo_sample_image(sample_key: str):
    """
    Streams the raw demo image file.
    """
    sample = next((s for s in DEMO_SAMPLES if s["key"] == sample_key), None)
    if not sample:
        raise HTTPException(status_code=404, detail="Demo sample not found.")

    image_path = settings.DEMO_DIR / "images" / sample["filename"]
    if not image_path.exists():
        raise HTTPException(status_code=404, detail="Demo image file not found on disk.")

    return FileResponse(path=str(image_path), media_type="image/png")

@router.post("/run/{sample_key}", response_model=InspectionResponse)
def run_demo_inspection(sample_key: str, db: Session = Depends(get_db)):
    """
    Executes the real pipeline on a curated demo sample.
    """
    sample = next((s for s in DEMO_SAMPLES if s["key"] == sample_key), None)
    if not sample:
        raise HTTPException(status_code=404, detail="Demo sample not found.")

    image_path = settings.DEMO_DIR / "images" / sample["filename"]
    if not image_path.exists():
        raise HTTPException(status_code=404, detail="Demo image file not found on disk.")

    inspection = run_inspection_pipeline(
        image_path=str(image_path),
        original_filename=sample["filename"],
        product_category=sample["category"],
        is_demo=True,
        execution_mode="DEMO_SAMPLE",
        db=db
    )

    return format_inspection_response(inspection)
