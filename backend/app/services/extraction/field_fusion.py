from typing import List, Dict, Any, Optional
from app.schemas.extraction import ExtractedField, FieldNormalizationResult
from app.schemas.ocr import OCRResultSchema
from app.core.logging import logger

class PanelExtractionPayload:
    """Encapsulates the extraction output for an individual image panel."""
    def __init__(
        self,
        image_index: int,
        panel_type: str,
        filename: str,
        extraction_result: FieldNormalizationResult,
        ocr_result: OCRResultSchema
    ):
        self.image_index = image_index
        self.panel_type = panel_type
        self.filename = filename
        self.extraction_result = extraction_result
        self.ocr_result = ocr_result

class FieldFusionEngine:
    """
    Cross-Panel Field Fusion Engine for Multi-Photo Legal Metrology Inspections.
    Combines OCR detections across multiple package panels (Front PDP, Back, Sides, Top/Bottom)
    into a coherent statutory declaration graph, resolving ambiguities and prioritizing the highest
    confidence, most complete attributes.
    """

    # Statutory panel affinity: where certain fields typically reside on packaging
    PANEL_AFFINITY_WEIGHTS = {
        "front": {
            "product_name": 1.25,
            "net_quantity": 1.20,
        },
        "back": {
            "mrp": 1.15,
            "mfg_date": 1.15,
            "expiry_date": 1.15,
            "manufacturer": 1.20,
            "consumer_care": 1.20,
            "country_of_origin": 1.10,
        },
        "side": {
            "consumer_care": 1.15,
            "mrp": 1.10,
            "mfg_date": 1.10,
            "expiry_date": 1.10,
            "manufacturer": 1.10,
        },
        "neck": {
            "mfg_date": 1.20,
            "expiry_date": 1.20,
            "mrp": 1.15,
            "net_quantity": 1.10,
        },
        "top": {
            "mfg_date": 1.20,
            "expiry_date": 1.20,
        },
        "bottom": {
            "mfg_date": 1.20,
            "expiry_date": 1.20,
            "mrp": 1.10,
        },
        "batch": {
            "mfg_date": 1.25,
            "expiry_date": 1.25,
            "mrp": 1.20,
        },
        "seal": {
            "mfg_date": 1.20,
            "expiry_date": 1.20,
        },
        "nutritional": {
            "net_quantity": 1.15,
        }
    }

    @classmethod
    def fuse_panels(
        cls,
        payloads: List[PanelExtractionPayload],
        product_category: str = "packaged_commodity"
    ) -> FieldNormalizationResult:
        if not payloads:
            return FieldNormalizationResult(
                category_id=product_category,
                fields={},
                raw_to_normalized_map={},
                extracted_count=0
            )

        if len(payloads) == 1:
            # Single image fast-path: tag with image_index 0
            payload = payloads[0]
            for fname, field in payload.extraction_result.fields.items():
                if field.metadata is None:
                    field.metadata = {}
                field.metadata["image_index"] = payload.image_index
                field.metadata["panel_type"] = payload.panel_type
                field.metadata["source_filename"] = payload.filename
            return payload.extraction_result

        logger.info(f"Fusing statutory field extractions across {len(payloads)} image panels...")

        # Collect candidate detections by field name
        field_candidates: Dict[str, List[Dict[str, Any]]] = {}

        for p in payloads:
            panel_type_lower = (p.panel_type or "general").lower()
            affinity_map = cls.PANEL_AFFINITY_WEIGHTS.get(panel_type_lower, {})

            for fname, field in p.extraction_result.fields.items():
                # Compute weighted score based on OCR confidence + panel affinity
                affinity_bonus = affinity_map.get(fname, 1.0)
                
                # Bonus for having normalized value & unit
                completeness_bonus = 1.0
                if field.normalized_value:
                    completeness_bonus += 0.05
                if field.unit:
                    completeness_bonus += 0.05

                weighted_score = field.confidence * affinity_bonus * completeness_bonus

                if fname not in field_candidates:
                    field_candidates[fname] = []

                field_candidates[fname].append({
                    "field": field,
                    "weighted_score": weighted_score,
                    "image_index": p.image_index,
                    "panel_type": p.panel_type,
                    "filename": p.filename
                })

        # Select best detection for each field
        fused_fields: Dict[str, ExtractedField] = {}
        raw_to_norm_map: Dict[str, str] = {}

        for fname, candidates in field_candidates.items():
            # Sort candidates by weighted score descending
            candidates.sort(key=lambda c: c["weighted_score"], reverse=True)
            best_candidate = candidates[0]
            best_field: ExtractedField = best_candidate["field"]

            # Attach multi-panel metadata
            if best_field.metadata is None:
                best_field.metadata = {}

            best_field.metadata["image_index"] = best_candidate["image_index"]
            best_field.metadata["panel_type"] = best_candidate["panel_type"]
            best_field.metadata["source_filename"] = best_candidate["filename"]
            best_field.metadata["all_panel_sources"] = [
                {"image_index": c["image_index"], "panel_type": c["panel_type"], "confidence": c["field"].confidence}
                for c in candidates
            ]

            # Cross-validate / boost confidence if detected consistently on multiple panels
            if len(candidates) > 1:
                best_field.confidence = min(0.99, best_field.confidence + 0.05)
                best_field.detection_method = f"{best_field.detection_method}+MULTI_PANEL"

            fused_fields[fname] = best_field
            if best_field.raw_value and best_field.normalized_value:
                raw_to_norm_map[best_field.raw_value] = best_field.normalized_value

        logger.info(
            f"Multi-panel fusion complete: {len(fused_fields)} statutory declarations unified across {len(payloads)} panels."
        )

        return FieldNormalizationResult(
            category_id=product_category,
            fields=fused_fields,
            raw_to_normalized_map=raw_to_norm_map,
            extracted_count=len(fused_fields)
        )
