import sys
import os
sys.path.insert(0, os.path.abspath("backend"))

from app.services.ocr.ocr_manager import ocr_manager
from app.services.extraction.field_extractor import extract_fields
from app.services.extraction.mrp_extractor import MRPExtractor

image_paths = [
    "demo/images/compliant_shampoo.png",
    "demo/images/missing_consumer_care_biscuit.png",
    "demo/images/non_standard_qty_snack.png",
    "demo/images/sample_electronics.png"
]

for img_path in image_paths:
    print("=" * 50)
    print(f"Testing image: {img_path}")
    res = ocr_manager.extract(img_path)
    print(f"OCR Engine: {res.engine}, Total lines: {len(res.lines)}")
    for l in res.lines:
        print(f"  [{l.line_number}] {repr(l.text)} (conf: {l.confidence})")
    
    mrp = MRPExtractor.extract(res.lines)
    print(f"MRP Extracted: {repr(mrp.normalized_value) if mrp else 'None'}")
    
    fields = extract_fields(res)
    for k, v in fields.fields.items():
        print(f"  -> Field {k}: raw={repr(v.raw_value)}, norm={repr(v.normalized_value)}")
