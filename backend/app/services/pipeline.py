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
from app.services.extraction.category_classifier import auto_detect_category
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
        package_id: str = "Package #1",
        parent_scan_id: Optional[str] = None,
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
            f"Starting inspection pipeline for {package_id} with {len(normalized_inputs)} image panel(s) "
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

            logger.info(f"Processing {package_id} Panel #{p_idx} [{p_type}]: '{p_name}'...")

            # Quality Assessment
            quality: QualityAssessment = check_image_quality(p_path)
            logger.info(f"Panel #{p_idx} Quality: {quality.status} (Blur: {quality.blur_score})")

            # Image Preprocessing
            preprocessed_path = preprocess_image(p_path)

            # Object / Region Detection (YOLO)
            cv_detections = detector_service.detect(p_path)
            primary_cv_version = cv_detections.model_version

            # OCR Extraction (English + Hindi)
            ocr_result = ocr_manager.extract(p_path, preprocessed_path=preprocessed_path)
            needs_region_recovery = (
                ocr_result.total_lines < 4 or ocr_result.mean_confidence < 0.55
            )
            region_ocr_result = (
                extract_region_text(p_path, cv_detections.regions, ocr_manager)
                if needs_region_recovery else None
            )
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

            # Retry lower declaration strip if MRP missing
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

        # 2. Auto-detect category from aggregated OCR text across all panels
        combined_ocr_text = "\n".join(
            m["ocr_result"].raw_full_text for m in per_panel_meta if m["ocr_result"].raw_full_text
        )
        final_category, category_was_auto_detected, category_confidence = auto_detect_category(
            combined_ocr_text,
            user_category=product_category,
        )
        if category_was_auto_detected:
            product_category = final_category
            for i, payload in enumerate(per_panel_payloads):
                updated_extraction = extract_fields(
                    payload.ocr_result,
                    product_category=product_category,
                    cv_detections=per_panel_meta[i]["cv_detections"],
                )
                per_panel_payloads[i] = PanelExtractionPayload(
                    image_index=payload.image_index,
                    panel_type=payload.panel_type,
                    filename=payload.filename,
                    extraction_result=updated_extraction,
                    ocr_result=payload.ocr_result,
                )

        # 3. Cross-Panel Field Fusion Engine & Conflict Detection
        fused_extraction = FieldFusionEngine.fuse_panels(per_panel_payloads, product_category=product_category)

        # 4. Consolidated Quality Assessment
        best_quality = min(per_panel_meta, key=lambda m: 0 if m["quality"].is_acceptable else 1)["quality"]

        # 5. Legal Compliance Rule Engine (with Applicability, Dual-Date, and Anomaly Checks)
        compliance_result = evaluate_compliance(fused_extraction, best_quality, category_id=product_category)
        logger.info(
            f"Rule Evaluation ({package_id}): Verdict={compliance_result.overall_status}, Score={compliance_result.compliance_score}"
        )

        # 6. Generate Annotated Visual Evidence Overlays for each panel
        for meta in per_panel_meta:
            p_idx = meta["image_index"]
            p_path = meta["file_path"]
            fields_for_annotation = []

            for check in compliance_result.rule_checks:
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

        # 7. Summary counts
        passed_count = sum(1 for c in compliance_result.rule_checks if c.status.value == "PASS")
        failed_count = sum(1 for c in compliance_result.rule_checks if c.status.value in ["FAIL", "NOT_DETECTED"] and c.is_mandatory)
        warning_count = sum(1 for c in compliance_result.rule_checks if c.status.value in ["WARNING", "REVIEW"])
        undetected_count = sum(1 for c in compliance_result.rule_checks if c.status.value in ["NOT_DETECTED", "FAIL"])
        uncertain_count = sum(1 for c in compliance_result.rule_checks if c.status.value in ["UNCERTAIN", "REVIEW"])

        elapsed_ms = (time.time() - start_time) * 1000.0

        # Extract product name
        product_name_field = fused_extraction.fields.get("product_name")
        product_name = product_name_field.normalized_value if product_name_field else f"Packaged Commodity ({package_id})"

        # 8. Create DB Records
        inspection = Inspection(
            package_id=package_id,
            parent_scan_id=parent_scan_id,
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
            conflicts=compliance_result.conflicts,
            anomaly_signals=compliance_result.anomaly_signals,
            cv_model_version=primary_cv_version,
            ocr_version=primary_ocr_version,
            rule_set_version=compliance_result.rule_set_version,
            processing_time_ms=round(elapsed_ms, 2)
        )
        inspection._category_auto_detected = category_was_auto_detected
        inspection._category_confidence = round(category_confidence, 3)

        # Image Records for all panels
        for meta in per_panel_meta:
            f_path = meta["file_path"]
            f_size = os.path.getsize(f_path) if os.path.exists(f_path) else 0
            q: QualityAssessment = meta["quality"]

            img_rec = ImageRecord(
                inspection=inspection,
                package_id=package_id,
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

        # Detected Fields with Panel and Conflict metadata
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
                    source_panel=f.metadata.get("source_panel") or f.metadata.get("panel_type"),
                    has_conflict=bool(f.metadata.get("has_conflict", False)),
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
                    is_applicable=check.is_applicable,
                    status=check.status.value,
                    detected_value=check.detected_value,
                    confidence=check.confidence,
                    source_panel=check.source_panel,
                    conflict_detected=check.conflict_detected,
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
                        "package_id": package_id,
                        "category": product_category,
                        "category_auto_detected": category_was_auto_detected,
                        "category_confidence": round(category_confidence, 3),
                        "status": compliance_result.overall_status.value,
                        "panel_count": len(normalized_inputs),
                        "checks": len(compliance_result.rule_checks),
                        "conflicts": len(compliance_result.conflicts),
                        "duration_ms": elapsed_ms
                    }
                )
            )
            db.commit()
            db.refresh(inspection)
            inspection._category_auto_detected = category_was_auto_detected
            inspection._category_confidence = round(category_confidence, 3)

            # Generate PDF Report
            try:
                generate_pdf_report(inspection)
            except Exception as e:
                logger.error(f"Error generating PDF report for inspection {inspection.id}: {e}")

        logger.info(
            f"Pipeline completed successfully in {elapsed_ms:.1f}ms for Inspection ID: {inspection.id} ({package_id}) "
            f"({len(normalized_inputs)} panels analyzed, category='{product_category}', "
            f"status={compliance_result.overall_status.value})"
        )
        return inspection

def run_inspection_pipeline(
    image_path: Optional[str] = None,
    original_filename: Optional[str] = None,
    image_inputs: Optional[List[Dict[str, Any]]] = None,
    product_category: str = "packaged_commodity",
    package_id: str = "Package #1",
    parent_scan_id: Optional[str] = None,
    is_demo: bool = False,
    execution_mode: str = "LIVE_PIPELINE",
    db: Optional[Session] = None
) -> Inspection:
    return InspectionPipeline.run(
        image_path=image_path,
        original_filename=original_filename,
        image_inputs=image_inputs,
        product_category=product_category,
        package_id=package_id,
        parent_scan_id=parent_scan_id,
        is_demo=is_demo,
        execution_mode=execution_mode,
        db=db
    )

def run_multi_package_scan(
    image_path: str,
    original_filename: Optional[str] = None,
    product_category: str = "packaged_commodity",
    is_demo: bool = False,
    execution_mode: str = "LIVE_PIPELINE",
    db: Optional[Session] = None
) -> Dict[str, Any]:
    """
    Detects multiple packaged commodities in a single camera frame or image,
    segments each package into an isolated sub-image, runs independent OCR and compliance pipelines,
    and returns an aggregated multi-package inspection scan response.
    """
    import uuid
    scan_id = str(uuid.uuid4())
    logger.info(f"Initiating Multi-Package Scan [Scan ID: {scan_id}] on '{image_path}'...")

    # Detect packages in the frame
    detection_res = detector_service.detect_packages(image_path)
    detected_packages = detection_res.packages

    inspections: List[Inspection] = []

    for pkg in detected_packages:
        pkg_crop_path = pkg.cropped_image_path or image_path
        pkg_inspection = run_inspection_pipeline(
            image_path=pkg_crop_path,
            original_filename=f"{pkg.package_id}_{original_filename or os.path.basename(image_path)}",
            product_category=product_category,
            package_id=pkg.package_id,
            parent_scan_id=scan_id,
            is_demo=is_demo,
            execution_mode=execution_mode,
            db=db
        )
        inspections.append(pkg_inspection)

    # Determine overall scan verdict
    if any(i.overall_status == "NON_COMPLIANT" for i in inspections):
        overall_verdict = "NON_COMPLIANT"
    elif any(i.overall_status in ["NEEDS_REVIEW", "UNABLE_TO_VERIFY"] for i in inspections):
        overall_verdict = "NEEDS_REVIEW"
    else:
        overall_verdict = "COMPLIANT"

    return {
        "scan_id": scan_id,
        "total_packages": len(inspections),
        "overall_verdict": overall_verdict,
        "annotated_overview_url": detection_res.annotated_frame_path,
        "packages": inspections
    }

