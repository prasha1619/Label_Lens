import os
import time
from datetime import datetime
from typing import Optional, Dict, Any, List, Union
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.logging import logger
from app.models.inspection import (
    Inspection, ImageRecord, OCRResult, DetectedField, ComplianceCheck, Violation
)
from app.models.audit import AuditLog
from app.services.cv.image_quality import check_image_quality
from app.services.cv.preprocessing import preprocess_image
from app.services.cv.detector import detector_service
from app.services.cv.visualization import draw_detections
from app.services.ocr.ocr_manager import ocr_manager
from app.services.ocr.region_ocr import extract_lower_declaration_text, extract_region_text
from app.services.extraction.field_extractor import extract_fields
from app.services.extraction.field_fusion import FieldFusionEngine, PanelExtractionPayload
from app.services.rules.rule_engine import evaluate_compliance
from app.services.reports.pdf_generator import generate_pdf_report
from app.schemas.cv import QualityAssessment

class InspectionPipeline:
    """
    End-to-End Multi-Panel Compliance Pipeline:
    Per Panel (Quality -> Preprocess -> YOLO -> OCR -> Field Extract) 
    -> Cross-Panel Field Fusion -> Legal Rule Engine -> Multi-Image Annotation -> Report -> DB.
    """

    @classmethod
    def run(
        cls,
        image_path: Optional[str] = None,
        original_filename: Optional[str] = None,
        image_inputs: Optional[List[Dict[str, Any]]] = None,
        product_category: str = "packaged_commodity",
        is_demo: bool = False,
        execution_mode: str = "LIVE_PIPELINE",
        db: Optional[Session] = None
    ) -> Inspection:
        start_time = time.time()

        # Normalize inputs into a unified list of image records
        normalized_inputs: List[Dict[str, Any]] = []
        if image_inputs:
            for idx, item in enumerate(image_inputs):
                normalized_inputs.append({
                    "path": item.get("path") or item.get("file_path"),
                    "filename": item.get("filename") or item.get("original_filename") or f"image_{idx}.jpg",
                    "panel_type": item.get("panel_type") or "front",
                    "image_index": idx
                })
        elif image_path:
            normalized_inputs.append({
                "path": image_path,
                "filename": original_filename or os.path.basename(image_path),
                "panel_type": "front",
                "image_index": 0
            })

        if not normalized_inputs:
            raise ValueError("No image inputs provided to inspection pipeline.")

        logger.info(
            f"Starting inspection pipeline for {len(normalized_inputs)} image panel(s) "
            f"(Category: {product_category}, Mode: {execution_mode})..."
        )

        per_panel_payloads: List[PanelExtractionPayload] = []
        per_panel_meta: List[Dict[str, Any]] = []
        primary_cv_version = "YOLO11-Legal"
        primary_ocr_version = "PaddleOCR"

        # 1. Process each panel individually through CV & OCR
        for input_item in normalized_inputs:
            p_idx = input_item["image_index"]
            p_path = input_item["path"]
            p_name = input_item["filename"]
            p_type = input_item["panel_type"]

            logger.info(f"Processing Panel #{p_idx} [{p_type}]: '{p_name}'...")

            # Quality Assessment
            quality: QualityAssessment = check_image_quality(p_path)
            logger.info(f"Panel #{p_idx} Quality: {quality.status} (Blur: {quality.blur_score})")

            # Image Preprocessing
            preprocessed_path = preprocess_image(p_path)

            # Object / Region Detection (YOLO)
            cv_detections = detector_service.detect(p_path)
            primary_cv_version = cv_detections.model_version

            # OCR Extraction
            ocr_result = ocr_manager.extract(p_path, preprocessed_path=preprocessed_path)
            # A trained detector lets OCR focus on small declaration blocks as well as the
            # full package. Crop results come first so field extraction prefers this evidence.
            region_ocr_result = extract_region_text(p_path, cv_detections.regions, ocr_manager)
            if region_ocr_result:
                combined_lines = region_ocr_result.lines + ocr_result.lines
                for line_number, line in enumerate(combined_lines, start=1):
                    line.line_number = line_number
                ocr_result.lines = combined_lines
                ocr_result.total_lines = len(combined_lines)
                ocr_result.raw_full_text = "\n".join(line.text for line in combined_lines)
                ocr_result.mean_confidence = round(
                    sum(line.confidence for line in combined_lines) / len(combined_lines), 4
                )
                ocr_result.processing_time_ms += region_ocr_result.processing_time_ms
                ocr_result.engine = region_ocr_result.engine
            primary_ocr_version = ocr_result.engine
            logger.info(f"Panel #{p_idx} OCR complete: {ocr_result.total_lines} lines extracted.")

            # Domain Field Extraction for this panel
            panel_extraction = extract_fields(ocr_result, product_category=product_category, cv_detections=cv_detections)

            # Full-label OCR can miss the tiny price band on the lower back panel.
            # Retry only when MRP is absent, then rerun extraction with that focused
            # evidence. This is deliberately conditional to keep normal scans fast.
            if "mrp" not in panel_extraction.fields:
                declaration_ocr = extract_lower_declaration_text(p_path, ocr_manager)
                if declaration_ocr:
                    combined_lines = declaration_ocr.lines + ocr_result.lines
                    for line_number, line in enumerate(combined_lines, start=1):
                        line.line_number = line_number
                    ocr_result.lines = combined_lines
                    ocr_result.total_lines = len(combined_lines)
                    ocr_result.raw_full_text = "\n".join(line.text for line in combined_lines)
                    ocr_result.mean_confidence = round(
                        sum(line.confidence for line in combined_lines) / len(combined_lines), 4
                    )
                    ocr_result.processing_time_ms += declaration_ocr.processing_time_ms
                    ocr_result.engine = declaration_ocr.engine
                    panel_extraction = extract_fields(
                        ocr_result, product_category=product_category, cv_detections=cv_detections
                    )
                    logger.info(
                        f"Panel #{p_idx} declaration-strip OCR retry: "
                        f"MRP {'detected' if 'mrp' in panel_extraction.fields else 'still not detected'}."
                    )

            payload = PanelExtractionPayload(
                image_index=p_idx,
                panel_type=p_type,
                filename=p_name,
                extraction_result=panel_extraction,
                ocr_result=ocr_result
            )
            per_panel_payloads.append(payload)

            per_panel_meta.append({
                "image_index": p_idx,
                "panel_type": p_type,
                "filename": p_name,
                "file_path": p_path,
                "quality": quality,
                "ocr_result": ocr_result,
                "cv_detections": cv_detections,
                "extraction": panel_extraction
            })

        # 2. Cross-Panel Field Fusion Engine
        fused_extraction = FieldFusionEngine.fuse_panels(per_panel_payloads, product_category=product_category)

        # 3. Determine Consolidated Quality Assessment
        # If at least one panel is acceptable, allow rule engine evaluation with multi-panel consensus
        best_quality = min(per_panel_meta, key=lambda m: 0 if m["quality"].is_acceptable else 1)["quality"]

        # 4. Legal Compliance Rule Engine
        compliance_result = evaluate_compliance(fused_extraction, best_quality, category_id=product_category)
        logger.info(
            f"Rule Evaluation: Verdict={compliance_result.overall_status}, Score={compliance_result.compliance_score}"
        )

        # 5. Generate Annotated Visual Evidence Overlays for each panel
        for meta in per_panel_meta:
            p_idx = meta["image_index"]
            p_path = meta["file_path"]
            fields_for_annotation = []

            for check in compliance_result.rule_checks:
                # Find if check corresponds to a field detected on this panel
                field_obj = fused_extraction.fields.get(check.field_name)
                field_img_idx = field_obj.metadata.get("image_index", 0) if (field_obj and field_obj.metadata) else 0

                if field_img_idx == p_idx and check.bbox and len(check.bbox) == 4:
                    fields_for_annotation.append({
                        "field_name": check.field_name,
                        "display_name": check.display_name,
                        "value": check.detected_value,
                        "confidence": check.confidence,
                        "status": check.status.value,
                        "bbox": check.bbox
                    })

            annotated_path = draw_detections(p_path, fields_for_annotation)
            meta["annotated_path"] = annotated_path

        # 6. Calculate summary counts
        passed_count = sum(1 for c in compliance_result.rule_checks if c.status.value == "PASS")
        failed_count = sum(1 for c in compliance_result.rule_checks if c.status.value == "FAIL")
        warning_count = sum(1 for c in compliance_result.rule_checks if c.status.value == "WARNING")
        undetected_count = sum(1 for c in compliance_result.rule_checks if c.status.value == "NOT_DETECTED")
        uncertain_count = sum(1 for c in compliance_result.rule_checks if c.status.value == "UNCERTAIN")

        elapsed_ms = (time.time() - start_time) * 1000.0

        # Extract product name if detected
        product_name_field = fused_extraction.fields.get("product_name")
        product_name = product_name_field.normalized_value if product_name_field else "Packaged Commodity"

        # 7. Create DB Records
        inspection = Inspection(
            product_name=product_name,
            product_category=product_category,
            overall_status=compliance_result.overall_status.value,
            compliance_score=compliance_result.compliance_score,
            is_demo=is_demo,
            execution_mode=execution_mode,
            total_checks=len(compliance_result.rule_checks),
            passed_checks=passed_count,
            failed_checks=failed_count,
            warning_checks=warning_count,
            undetected_checks=undetected_count,
            uncertain_checks=uncertain_count,
            cv_model_version=primary_cv_version,
            ocr_version=primary_ocr_version,
            rule_set_version=compliance_result.rule_set_version,
            processing_time_ms=round(elapsed_ms, 2)
        )

        # Image Records for all panels
        for meta in per_panel_meta:
            f_path = meta["file_path"]
            f_size = os.path.getsize(f_path) if os.path.exists(f_path) else 0
            q: QualityAssessment = meta["quality"]

            img_rec = ImageRecord(
                inspection=inspection,
                panel_type=meta["panel_type"],
                image_index=meta["image_index"],
                original_filename=meta["filename"],
                file_path=f_path,
                annotated_file_path=meta.get("annotated_path"),
                file_size_bytes=f_size,
                width=q.width,
                height=q.height,
                mime_type=f"image/{os.path.splitext(f_path)[1].replace('.', '')}",
                quality_status=q.status,
                blur_score=q.blur_score,
                brightness_score=q.brightness_score,
                contrast_score=q.contrast_score,
                glare_score=q.glare_score,
                skew_angle=q.skew_angle,
                quality_reasons=q.reasons
            )
            inspection.images.append(img_rec)

        # OCR Lines across all panels
        line_num = 1
        for meta in per_panel_meta:
            ocr_res = meta["ocr_result"]
            for line in ocr_res.lines:
                inspection.ocr_results.append(
                    OCRResult(
                        inspection=inspection,
                        raw_text=line.text,
                        confidence=line.confidence,
                        bbox=line.bbox,
                        line_number=line_num,
                        engine=ocr_res.engine
                    )
                )
                line_num += 1

        # Detected Fields with Panel metadata
        for fname, f in fused_extraction.fields.items():
            inspection.detected_fields.append(
                DetectedField(
                    inspection=inspection,
                    field_name=f.field_name,
                    display_name=f.display_name,
                    raw_value=f.raw_value,
                    normalized_value=f.normalized_value,
                    unit=f.unit,
                    confidence=f.confidence,
                    detection_method=f.detection_method,
                    bbox=f.bbox,
                    metadata_info=f.metadata
                )
            )

        # Compliance Checks
        for check in compliance_result.rule_checks:
            field_obj = fused_extraction.fields.get(check.field_name)
            check_bbox = check.bbox or (field_obj.bbox if field_obj else None)

            inspection.compliance_checks.append(
                ComplianceCheck(
                    inspection=inspection,
                    rule_id=check.rule_id,
                    rule_title=check.rule_title,
                    legal_reference=check.legal_reference,
                    field_name=check.field_name,
                    is_mandatory=check.is_mandatory,
                    status=check.status.value,
                    detected_value=check.detected_value,
                    confidence=check.confidence,
                    explanation=check.explanation,
                    inspector_recommendation=check.inspector_recommendation,
                    bbox=check_bbox
                )
            )

        # Violations
        for viol in compliance_result.violations:
            inspection.violations.append(
                Violation(
                    inspection=inspection,
                    field_name=viol.field_name,
                    severity=viol.severity,
                    rule_id=viol.rule_id,
                    legal_provision=viol.legal_reference,
                    reason=viol.reason,
                    recommendation=viol.recommendation
                )
            )

        # Save to DB if session provided
        if db:
            db.add(inspection)
            db.add(
                AuditLog(
                    inspection_id=inspection.id,
                    action="INSPECTION_ANALYSIS_COMPLETED",
                    actor="AI_PIPELINE",
                    details={
                        "category": product_category,
                        "status": compliance_result.overall_status.value,
                        "panel_count": len(normalized_inputs),
                        "checks": len(compliance_result.rule_checks),
                        "duration_ms": elapsed_ms
                    }
                )
            )
            db.commit()
            db.refresh(inspection)

            # Generate PDF Report immediately and cache
            try:
                generate_pdf_report(inspection)
            except Exception as e:
                logger.error(f"Error generating PDF report for inspection {inspection.id}: {e}")

        logger.info(
            f"Pipeline completed successfully in {elapsed_ms:.1f}ms for Inspection ID: {inspection.id} "
            f"({len(normalized_inputs)} panels analyzed)"
        )
        return inspection

def run_inspection_pipeline(
    image_path: Optional[str] = None,
    original_filename: Optional[str] = None,
    image_inputs: Optional[List[Dict[str, Any]]] = None,
    product_category: str = "packaged_commodity",
    is_demo: bool = False,
    execution_mode: str = "LIVE_PIPELINE",
    db: Optional[Session] = None
) -> Inspection:
    return InspectionPipeline.run(
        image_path=image_path,
        original_filename=original_filename,
        image_inputs=image_inputs,
        product_category=product_category,
        is_demo=is_demo,
        execution_mode=execution_mode,
        db=db
    )
