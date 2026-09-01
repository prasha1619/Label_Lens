from typing import List, Dict, Optional, Any
from app.schemas.ocr import OCRResultSchema, OCRLine
from app.schemas.cv import CVDetectionResult
from app.schemas.extraction import ExtractedField, FieldNormalizationResult
from app.services.extraction.mrp_extractor import MRPExtractor
from app.services.extraction.net_qty_extractor import NetQuantityExtractor
from app.services.extraction.dates_extractor import DatesExtractor
from app.services.extraction.entity_extractor import EntityExtractor
from app.services.extraction.consumer_care_extractor import ConsumerCareExtractor
from app.core.logging import logger

class LabelFieldExtractor:
    """
    Modular field extraction orchestrator.
    Combines specialized domain extractors (MRP, Net Qty, Dates, Entities, Consumer Care)
    with CV/YOLO region guidance and OCR confidence scoring.
    """

    @classmethod
    def extract_all(
        cls, 
        ocr_result: OCRResultSchema, 
        product_category: str = "packaged_commodity",
        cv_detections: Optional[CVDetectionResult] = None
    ) -> FieldNormalizationResult:
        lines: List[OCRLine] = ocr_result.lines
        fields: Dict[str, ExtractedField] = {}
        raw_to_norm_map: Dict[str, str] = {}

        # 1. Extract MRP
        mrp_field = MRPExtractor.extract(lines)
        if mrp_field:
            fields["mrp"] = mrp_field
            raw_to_norm_map[mrp_field.raw_value] = mrp_field.normalized_value

        # 2. Extract Net Quantity
        qty_field = NetQuantityExtractor.extract(lines)
        if qty_field:
            fields["net_quantity"] = qty_field
            raw_to_norm_map[qty_field.raw_value] = qty_field.normalized_value

        # 3. Extract Dates (Mfg / Expiry)
        mfg_field = DatesExtractor.extract_mfg_date(lines)
        if mfg_field:
            fields["mfg_date"] = mfg_field
            raw_to_norm_map[mfg_field.raw_value] = mfg_field.normalized_value

        exp_field = DatesExtractor.extract_expiry_date(lines)
        if exp_field:
            fields["expiry_date"] = exp_field
            raw_to_norm_map[exp_field.raw_value] = exp_field.normalized_value

        # 4. Extract Entities (Manufacturer, Country of Origin, Generic Name)
        mfg_entity_field = EntityExtractor.extract_manufacturer(lines)
        if mfg_entity_field:
            fields["manufacturer"] = mfg_entity_field
            raw_to_norm_map[mfg_entity_field.raw_value] = mfg_entity_field.normalized_value

        origin_field = EntityExtractor.extract_country_of_origin(lines)
        if origin_field:
            fields["country_of_origin"] = origin_field
            raw_to_norm_map[origin_field.raw_value] = origin_field.normalized_value

        prod_name_field = EntityExtractor.extract_generic_name(lines)
        if prod_name_field:
            fields["product_name"] = prod_name_field
            raw_to_norm_map[prod_name_field.raw_value] = prod_name_field.normalized_value

        # 5. Extract Consumer Care details
        care_field = ConsumerCareExtractor.extract(lines)
        if care_field:
            fields["consumer_care"] = care_field
            raw_to_norm_map[care_field.raw_value] = care_field.normalized_value

        # 6. Fuse with YOLO detections if available
        if cv_detections and cv_detections.regions:
            for region in cv_detections.regions:
                cls_name = region.label_class
                if cls_name in fields:
                    # Update bounding box with high-precision YOLO box if OCR box is wider
                    if region.confidence > 0.6:
                        fields[cls_name].bbox = region.bbox
                        fields[cls_name].detection_method = "YOLO+OCR"

        logger.info(f"Field extraction complete for category '{product_category}'. Extracted {len(fields)} fields.")

        return FieldNormalizationResult(
            category_id=product_category,
            fields=fields,
            raw_to_normalized_map=raw_to_norm_map,
            extracted_count=len(fields)
        )

def extract_fields(
    ocr_result: OCRResultSchema, 
    product_category: str = "packaged_commodity",
    cv_detections: Optional[CVDetectionResult] = None
) -> FieldNormalizationResult:
    return LabelFieldExtractor.extract_all(ocr_result, product_category, cv_detections)
