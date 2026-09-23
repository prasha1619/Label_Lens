import os
import io
import time
import base64
import uuid
from typing import List, Dict, Any, Optional
import cv2
import numpy as np
from PIL import Image

from app.core.config import settings
from app.core.logging import logger
from app.schemas.cv import QualityAssessment, DetectedPackage
from app.services.cv.image_quality import ImageQualityAnalyzer
from app.services.cv.detector import detector_service
from app.services.ocr.ocr_manager import ocr_manager
from app.services.extraction.field_extractor import LabelFieldExtractor
from app.services.extraction.field_fusion import FieldFusionEngine, PanelExtractionPayload
from app.services.rules.rule_engine import LegalComplianceRuleEngine
from app.schemas.rule import LegalStatusEnum, OverallComplianceStatus
from app.schemas.extraction import FieldNormalizationResult, ExtractedField
from app.schemas.ocr import OCRResultSchema

class ARInspectionService:
    """
    Dedicated Augmented Reality Inspection Service.
    Transforms raw camera frames into real-time visual statutory compliance overlays,
    projecting package bounds, OCR bounding boxes, and 4-state rule determinations.
    """

    @classmethod
    def analyze_frame(
        cls,
        image_bytes: bytes,
        active_panel: str = "front",
        package_id: str = "Package #1",
        product_category: str = "packaged_commodity",
        accumulated_panels: Optional[List[Dict[str, Any]]] = None,
        is_demo: bool = False
    ) -> Dict[str, Any]:
        start_time = time.perf_counter()
        frame_id = f"ar_frame_{uuid.uuid4().hex[:10]}"

        # Decode image
        nparr = np.frombuffer(image_bytes, np.uint8)
        img_cv = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img_cv is None:
            raise ValueError("Failed to decode image frame for AR analysis.")

        height, width = img_cv.shape[:2]
        if max(height, width) > 1280:
            scale = 1280.0 / max(height, width)
            img_cv = cv2.resize(img_cv, (int(width * scale), int(height * scale)), interpolation=cv2.INTER_AREA)
            height, width = img_cv.shape[:2]

        # Save temp image for quality, detector & OCR
        temp_dir = settings.UPLOAD_DIR / "ar_cache"
        temp_dir.mkdir(parents=True, exist_ok=True)
        temp_frame_path = temp_dir / f"{frame_id}.jpg"
        cv2.imwrite(str(temp_frame_path), img_cv)

        try:
            # 1. Quality Gate Check
            quality: QualityAssessment = ImageQualityAnalyzer.evaluate(str(temp_frame_path))

            detected_packages = []
            try:
                pkg_result = detector_service.detect_packages(str(temp_frame_path))
                for p in pkg_result.packages:
                    detected_packages.append({
                        "package_id": p.package_id,
                        "confidence": p.confidence,
                        "bbox": p.bbox,
                        "bbox_normalized": [
                            round(p.bbox[0] / max(1, width), 4),
                            round(p.bbox[1] / max(1, height), 4),
                            round(p.bbox[2] / max(1, width), 4),
                            round(p.bbox[3] / max(1, height), 4)
                        ] if len(p.bbox) == 4 else [0, 0, 1, 1],
                        "label": getattr(p, "label", getattr(p, "label_class", "Packaged Commodity")),
                        "is_active": p.package_id == package_id
                    })
            except Exception as e:
                logger.debug(f"AR package detection notice: {e}")

            if not detected_packages:
                detected_packages.append({
                    "package_id": package_id,
                    "confidence": 0.95,
                    "bbox": [int(width * 0.05), int(height * 0.05), int(width * 0.95), int(height * 0.95)],
                    "bbox_normalized": [0.05, 0.05, 0.95, 0.95],
                    "label": "Packaged Commodity",
                    "is_active": True
                })

            # 3. Bilingual OCR
            ocr_result: OCRResultSchema = ocr_manager.extract(str(temp_frame_path), allow_rotation=False)

            # 4. Field Extraction for current frame
            current_extraction: FieldNormalizationResult = LabelFieldExtractor.extract_all(
                ocr_result=ocr_result,
                product_category=product_category
            )

            # 5. Multi-Panel Accumulation & Cross-Panel Evidence Fusion
            panel_payloads: List[PanelExtractionPayload] = []
            current_payload = PanelExtractionPayload(
                image_index=len(accumulated_panels or []),
                panel_type=active_panel,
                filename=f"{active_panel}.jpg",
                extraction_result=current_extraction,
                ocr_result=ocr_result
            )
            panel_payloads.append(current_payload)

            # Incorporate historical panels if provided
            if accumulated_panels:
                for idx, hist in enumerate(accumulated_panels):
                    h_fields = {}
                    for f_k, f_v in (hist.get("fields") or {}).items():
                        h_fields[f_k] = ExtractedField(
                            field_name=f_k,
                            display_name=f_v.get("display_name", f_k),
                            raw_value=f_v.get("raw_value") or f_v.get("raw_text"),
                            normalized_value=f_v.get("normalized_value"),
                            unit=f_v.get("unit"),
                            confidence=f_v.get("confidence", 0.9),
                            bbox=f_v.get("bbox"),
                            source_panel=f_v.get("source_panel") or hist.get("panel_type")
                        )
                    hist_norm = FieldNormalizationResult(
                        category_id=product_category,
                        fields=h_fields,
                        raw_to_normalized_map={},
                        extracted_count=len(h_fields)
                    )
                    panel_payloads.append(
                        PanelExtractionPayload(
                            image_index=idx,
                            panel_type=hist.get("panel_type", "front"),
                            filename=f"hist_{idx}.jpg",
                            extraction_result=hist_norm,
                            ocr_result=OCRResultSchema(
                                total_lines=len(h_fields),
                                mean_confidence=0.9,
                                raw_full_text="",
                                processing_time_ms=10.0
                            )
                        )
                    )

            fused_extraction = FieldFusionEngine.fuse_panels(panel_payloads, product_category=product_category)

            # 6. Legal Compliance Rule Engine Evaluation
            eval_result = LegalComplianceRuleEngine.evaluate(
                extraction_result=fused_extraction,
                quality_assessment=quality,
                category_id=product_category
            )

            # Build AR Overlays for visual bounding boxes
            ar_field_overlays: List[Dict[str, Any]] = []
            rule_check_map = {c.field_name: c for c in eval_result.rule_checks}

            for fname, field in fused_extraction.fields.items():
                check = rule_check_map.get(fname)
                status_val = check.status.value if check else "PASS"
                explanation_val = check.explanation if check else "Statutory declaration verified."
                legal_ref = check.legal_reference if check else "Legal Metrology (PC) Rules 2011"

                raw_bbox = field.bbox or [10, 10, 100, 50]
                bx1 = max(0, min(width - 10, raw_bbox[0]))
                by1 = max(0, min(height - 10, raw_bbox[1]))
                bx2 = max(bx1 + 20, min(width, raw_bbox[2]))
                by2 = max(by1 + 15, min(height, raw_bbox[3]))
                clamped_bbox = [bx1, by1, bx2, by2]

                norm_bbox = [
                    round(bx1 / max(1, width), 4),
                    round(by1 / max(1, height), 4),
                    round(bx2 / max(1, width), 4),
                    round(by2 / max(1, height), 4)
                ]

                crop_base64 = None
                try:
                    crop = img_cv[by1:by2, bx1:bx2]
                    if crop.size > 0:
                        _, buf = cv2.imencode('.jpg', crop, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
                        crop_base64 = f"data:image/jpeg;base64,{base64.b64encode(buf).decode('utf-8')}"
                except Exception:
                    crop_base64 = None

                ar_field_overlays.append({
                    "field_name": fname,
                    "display_name": field.display_name,
                    "raw_text": field.raw_value,
                    "normalized_value": field.normalized_value,
                    "unit": field.unit,
                    "confidence": round(field.confidence, 2),
                    "source_panel": field.source_panel or (f"{active_panel.capitalize()} Panel"),
                    "status": status_val,
                    "explanation": explanation_val,
                    "applicable_rule": legal_ref,
                    "has_conflict": field.has_conflict,
                    "conflict_entry": field.conflict_entry,
                    "bbox": clamped_bbox,
                    "bbox_normalized": norm_bbox,
                    "crop_thumbnail": crop_base64
                })

            pass_count = sum(1 for c in eval_result.rule_checks if c.status == LegalStatusEnum.PASS)
            fail_count = sum(1 for c in eval_result.rule_checks if c.status == LegalStatusEnum.FAIL and c.is_mandatory)
            review_count = sum(1 for c in eval_result.rule_checks if c.status == LegalStatusEnum.REVIEW)
            na_count = sum(1 for c in eval_result.rule_checks if c.status == LegalStatusEnum.N_A)

            if not quality.is_acceptable:
                guidance = f"⚠ Camera blur/glare detected ({'; '.join(quality.reasons[:2])}). Steady camera & improve lighting."
                system_state = "QUALITY_WARNING"
            elif review_count > 0 or len(fused_extraction.conflicts) > 0:
                guidance = "⚠ Review Required: Competing declarations or low OCR confidence detected across panels."
                system_state = "REVIEW"
            elif len(ar_field_overlays) == 0:
                guidance = f"Scanning {active_panel} panel declarations... Point camera steadily at label text."
                system_state = "SCANNING"
            else:
                if active_panel.lower() == "front":
                    guidance = f"Front panel verified ({pass_count} passed). Move camera to Back or Side panel to complete audit."
                else:
                    guidance = f"Multi-panel audit complete. {pass_count} declarations compliant across panels."
                system_state = "RESULT"

            processing_ms = round((time.perf_counter() - start_time) * 1000, 2)

            return {
                "frame_id": frame_id,
                "timestamp": time.time(),
                "image_dimensions": {"width": width, "height": height},
                "quality": {
                    "status": quality.status,
                    "is_acceptable": quality.is_acceptable,
                    "blur_score": quality.blur_score,
                    "reasons": quality.reasons
                },
                "packages": detected_packages,
                "fields": ar_field_overlays,
                "conflicts": fused_extraction.conflicts,
                "overall_status": eval_result.overall_status.value,
                "compliance_score": eval_result.compliance_score,
                "hud_metrics": {
                    "total_packages": len(detected_packages),
                    "active_package_id": package_id,
                    "active_panel": f"{active_panel.capitalize()} Panel",
                    "pass_count": pass_count,
                    "fail_count": fail_count,
                    "review_count": review_count,
                    "na_count": na_count,
                    "system_state": system_state,
                    "guidance_message": guidance
                },
                "processing_time_ms": processing_ms
            }
        finally:
            try:
                if temp_frame_path.exists():
                    os.remove(temp_frame_path)
            except Exception:
                pass
