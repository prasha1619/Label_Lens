import os
import uuid
import shutil
from typing import List, Optional, Dict, Any, Union
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, status, Request
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from app.core.config import settings
from app.core.logging import logger
from app.core.exceptions import ResourceNotFoundException, LabelLensException
from app.database.session import get_db
from app.models.inspection import Inspection, ImageRecord, OCRResult, DetectedField, ComplianceCheck, Violation
import json
from app.schemas.inspection import (
    InspectionResponse, InspectionListResponse, InspectionListItem, DashboardMetrics, ImageRecordSchema,
    FieldOverrideRequest, ReviewActionRequest, MultiPackageScanResponse
)
from app.schemas.extraction import ExtractedField
from app.schemas.rule import RuleCheckResult, ViolationSummary, LegalStatusEnum
from app.services.pipeline import run_inspection_pipeline
from app.services.reports.pdf_generator import generate_pdf_report
from app.api.v1.endpoints.auth import get_current_user
from app.models.user import User

router = APIRouter()

def format_inspection_response(inspection: Inspection) -> InspectionResponse:
    images_schema: List[ImageRecordSchema] = []
    for img in inspection.images:
        images_schema.append(
            ImageRecordSchema(
                id=img.id,
                original_filename=img.original_filename,
                file_path=img.file_path,
                annotated_file_path=img.annotated_file_path,
                file_size_bytes=img.file_size_bytes,
                panel_type=img.panel_type or "front",
                image_index=img.image_index or 0,
                width=img.width,
                height=img.height,
                mime_type=img.mime_type,
                quality_status=img.quality_status,
                blur_score=img.blur_score,
                brightness_score=img.brightness_score,
                contrast_score=img.contrast_score,
                glare_score=img.glare_score,
                quality_reasons=img.quality_reasons or []
            )
        )

    primary_image_schema = images_schema[0] if images_schema else None

    # Format detected fields with source panel & conflict flags
    detected_fields = [
        ExtractedField(
            field_name=df.field_name,
            display_name=df.display_name,
            raw_value=df.raw_value,
            normalized_value=df.normalized_value,
            unit=df.unit,
            confidence=df.confidence,
            detection_method=df.detection_method,
            bbox=df.bbox,
            is_detected=bool(df.raw_value or df.normalized_value),
            metadata={
                **(df.metadata_info or {}),
                "source_panel": df.source_panel or (df.metadata_info.get("source_panel") if df.metadata_info else "Front Panel"),
                "has_conflict": df.has_conflict
            }
        )
        for df in inspection.detected_fields
    ]

    # Format compliance checks with source panel & conflict detection
    compliance_checks = [
        RuleCheckResult(
            rule_id=cc.rule_id,
            rule_title=cc.rule_title,
            legal_reference=cc.legal_reference or "",
            field_name=cc.field_name,
            display_name=cc.rule_title,
            is_mandatory=cc.is_mandatory,
            is_applicable=getattr(cc, "is_applicable", True),
            applicability_reason="Statutory declaration requirement",
            status=LegalStatusEnum(cc.status) if cc.status in LegalStatusEnum.__members__.values() else (LegalStatusEnum.REVIEW if cc.status == "WARNING" else LegalStatusEnum.PASS),
            detected_value=cc.detected_value,
            raw_ocr_value=next((df.raw_value for df in inspection.detected_fields if df.field_name == cc.field_name), None),
            confidence=cc.confidence,
            source_panel=getattr(cc, "source_panel", None) or next((df.source_panel for df in inspection.detected_fields if df.field_name == cc.field_name), "Front Panel"),
            conflict_detected=getattr(cc, "conflict_detected", False) or next((df.has_conflict for df in inspection.detected_fields if df.field_name == cc.field_name), False),
            explanation=cc.explanation,
            inspector_recommendation=cc.inspector_recommendation,
            bbox=cc.bbox,
            evidence_available=bool(cc.bbox)
        )
        for cc in inspection.compliance_checks
    ]

    # Format violations
    violations = [
        ViolationSummary(
            field_name=v.field_name,
            severity=v.severity,
            rule_id=v.rule_id,
            legal_reference=v.legal_provision,
            reason=v.reason,
            recommendation=v.recommendation
        )
        for v in inspection.violations
    ]

    # OCR Lines Summary
    raw_ocr_lines = [
        {"line": o.line_number, "text": o.raw_text, "confidence": o.confidence, "bbox": o.bbox}
        for o in inspection.ocr_results
    ]
    raw_full_text = "\n".join([o.raw_text for o in inspection.ocr_results])
    ocr_summary = {
        "engine": inspection.ocr_version or "PaddleOCR",
        "total_lines": len(inspection.ocr_results),
        "raw_full_text": raw_full_text,
        "lines": raw_ocr_lines
    }

    # Count explicit states
    review_checks_count = sum(1 for c in compliance_checks if c.status == LegalStatusEnum.REVIEW)
    na_checks_count = sum(1 for c in compliance_checks if c.status == LegalStatusEnum.N_A)

    return InspectionResponse(
        id=inspection.id,
        package_id=getattr(inspection, "package_id", "Package #1") or "Package #1",
        parent_scan_id=getattr(inspection, "parent_scan_id", None),
        product_name=inspection.product_name,
        product_category=inspection.product_category,
        overall_status=inspection.overall_status,
        compliance_score=inspection.compliance_score,
        is_demo=inspection.is_demo,
        execution_mode=inspection.execution_mode,
        total_checks=inspection.total_checks,
        passed_checks=inspection.passed_checks,
        failed_checks=inspection.failed_checks,
        warning_checks=inspection.warning_checks,
        undetected_checks=inspection.undetected_checks,
        uncertain_checks=inspection.uncertain_checks,
        review_checks_count=review_checks_count,
        na_checks_count=na_checks_count,
        cv_model_version=inspection.cv_model_version,
        ocr_version=inspection.ocr_version,
        rule_set_version=inspection.rule_set_version,
        processing_time_ms=inspection.processing_time_ms,
        error_message=inspection.error_message,
        is_offline_synced=getattr(inspection, "is_offline_synced", False),
        created_at=inspection.created_at,
        updated_at=inspection.updated_at,
        image=primary_image_schema,
        images=images_schema,
        ocr_summary=ocr_summary,
        detected_fields=detected_fields,
        compliance_checks=compliance_checks,
        violations=violations,
        conflicts=getattr(inspection, "conflicts", []) or [],
        review_decisions=getattr(inspection, "review_decisions", []) or [],
        anomaly_signals=getattr(inspection, "anomaly_signals", []) or []
    )

@router.post("", response_model=InspectionResponse, status_code=status.HTTP_201_CREATED)
def create_inspection(
    files: Optional[List[UploadFile]] = File(None),
    file: Optional[UploadFile] = File(None),
    product_category: str = Form("packaged_commodity"),
    panel_types: Optional[str] = Form(None),
    is_demo: bool = Form(False),
    package_id: Optional[str] = Form("Package #1"),
    parent_scan_id: Optional[str] = Form(None),
    is_offline_synced: bool = Form(False),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Uploads 1 or more packaged product label images (multi-panel: PDP front, back, side)
    and executes the end-to-end Legal Metrology cross-panel compliance pipeline.
    """
    uploaded_files: List[UploadFile] = []
    if files:
        uploaded_files.extend(files)
    if file:
        uploaded_files.append(file)

    if not uploaded_files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No image files provided for inspection."
        )

    parsed_panels: List[str] = []
    if panel_types:
        try:
            parsed_panels = json.loads(panel_types)
        except Exception:
            parsed_panels = [p.strip() for p in panel_types.split(",") if p.strip()]

    default_panel_names = ["front", "back", "side", "top", "general"]
    image_inputs: List[dict] = []

    for idx, f in enumerate(uploaded_files):
        ext = f.filename.split(".")[-1].lower() if "." in f.filename else ""
        if ext not in settings.ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file format '.{ext}' for file '{f.filename}'. Allowed formats: {', '.join(settings.ALLOWED_EXTENSIONS)}"
            )

        unique_filename = f"{uuid.uuid4().hex}_{f.filename}"
        file_path = settings.UPLOAD_DIR / unique_filename

        try:
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(f.file, buffer)
        except Exception as e:
            logger.error(f"Failed to save uploaded file '{f.filename}': {e}")
            raise HTTPException(status_code=500, detail=f"Failed to store uploaded image '{f.filename}'.")

        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        if file_size_mb > settings.MAX_UPLOAD_SIZE_MB:
            os.remove(file_path)
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File '{f.filename}' size ({file_size_mb:.1f}MB) exceeds maximum limit of {settings.MAX_UPLOAD_SIZE_MB}MB."
            )

        p_type = parsed_panels[idx] if idx < len(parsed_panels) else (
            default_panel_names[idx] if idx < len(default_panel_names) else f"Photo {idx + 1}"
        )

        image_inputs.append({
            "path": str(file_path),
            "filename": f.filename,
            "panel_type": p_type,
            "image_index": idx
        })

    try:
        inspection = run_inspection_pipeline(
            image_inputs=image_inputs,
            product_category=product_category,
            package_id=package_id or "Package #1",
            parent_scan_id=parent_scan_id,
            is_demo=is_demo,
            execution_mode="LIVE_PIPELINE" if not is_demo else "DEMO_SAMPLE",
            db=db
        )
        inspection.user_id = user.id
        inspection.is_offline_synced = is_offline_synced
        db.commit()
        return format_inspection_response(inspection)
    except Exception as e:
        logger.exception(f"Inspection pipeline execution failed: {e}")
        raise HTTPException(status_code=500, detail=f"Pipeline execution error: {str(e)}")

@router.post("/multi-package-scan", response_model=Dict[str, Any])
def create_multi_package_scan(
    file: UploadFile = File(...),
    product_category: str = Form("packaged_commodity"),
    is_demo: bool = Form(False),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Accepts a single camera frame or retail shelf image containing multiple packaged commodities,
    segments each package with YOLO / CV, runs isolated OCR/compliance for each package,
    and returns an aggregated multi-package inspection scan response.
    """
    ext = file.filename.split(".")[-1].lower() if "." in file.filename else ""
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported image format '.{ext}'.")

    unique_filename = f"{uuid.uuid4().hex}_{file.filename}"
    file_path = settings.UPLOAD_DIR / unique_filename

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    from app.services.pipeline import run_multi_package_scan
    scan_result = run_multi_package_scan(
        image_path=str(file_path),
        original_filename=file.filename,
        product_category=product_category,
        is_demo=is_demo,
        execution_mode="LIVE_PIPELINE" if not is_demo else "DEMO_SAMPLE",
        db=db
    )

    for insp in scan_result["packages"]:
        insp.user_id = user.id
    db.commit()

    return {
        "scan_id": scan_result["scan_id"],
        "total_packages": scan_result["total_packages"],
        "overall_verdict": scan_result["overall_verdict"],
        "annotated_overview_url": scan_result.get("annotated_overview_url"),
        "packages": [format_inspection_response(p) for p in scan_result["packages"]]
    }


@router.get("", response_model=InspectionListResponse)
def list_inspections(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    category: Optional[str] = None,
    status_filter: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Returns paginated inspection audit records with optional filtering.
    """
    query = db.query(Inspection)
    if user.role != 'admin':
        query = query.filter(Inspection.user_id == user.id)

    if category:
        query = query.filter(Inspection.product_category == category)
    if status_filter:
        query = query.filter(Inspection.overall_status == status_filter)
    if search:
        query = query.filter(Inspection.product_name.ilike(f"%{search}%"))

    total = query.count()
    inspections = query.order_by(desc(Inspection.created_at)).offset((page - 1) * limit).limit(limit).all()

    items = [
        InspectionListItem(
            id=insp.id,
            product_name=insp.product_name,
            product_category=insp.product_category,
            overall_status=insp.overall_status,
            compliance_score=insp.compliance_score,
            quality_status=insp.image.quality_status if insp.image else "PASS",
            total_checks=insp.total_checks,
            passed_checks=insp.passed_checks,
            failed_checks=insp.failed_checks,
            created_at=insp.created_at,
            original_filename=insp.image.original_filename if insp.image else None,
            annotated_image_available=bool(insp.image and insp.image.annotated_file_path),
            image_count=len(insp.images) if insp.images else 1
        )
        for insp in inspections
    ]

    return InspectionListResponse(total=total, page=page, limit=limit, items=items)

@router.get("/dashboard/metrics", response_model=DashboardMetrics)
def get_dashboard_metrics(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """
    Returns aggregate compliance KPIs, status breakdowns, and recent audits for the dashboard.
    """
    base = db.query(Inspection)
    if user.role != 'admin': base = base.filter(Inspection.user_id == user.id)
    total = base.count()
    compliant = base.filter(Inspection.overall_status == "COMPLIANT").count()
    non_compliant = base.filter(Inspection.overall_status == "NON_COMPLIANT").count()
    needs_review = base.filter(Inspection.overall_status == "NEEDS_REVIEW").count()
    unable_verify = base.filter(Inspection.overall_status == "UNABLE_TO_VERIFY").count()

    avg_score_res = base.with_entities(func.avg(Inspection.compliance_score)).scalar()
    avg_score = round(float(avg_score_res), 1) if avg_score_res is not None else 0.0

    # Category distribution
    cat_counts = base.with_entities(Inspection.product_category, func.count(Inspection.id)).group_by(Inspection.product_category).all()
    category_distribution = {cat: count for cat, count in cat_counts}

    # Recent inspections
    recent_records = base.order_by(desc(Inspection.created_at)).limit(5).all()
    recent_items = [
        InspectionListItem(
            id=insp.id,
            product_name=insp.product_name,
            product_category=insp.product_category,
            overall_status=insp.overall_status,
            compliance_score=insp.compliance_score,
            quality_status=insp.image.quality_status if insp.image else "PASS",
            total_checks=insp.total_checks,
            passed_checks=insp.passed_checks,
            failed_checks=insp.failed_checks,
            created_at=insp.created_at,
            original_filename=insp.image.original_filename if insp.image else None,
            annotated_image_available=bool(insp.image and insp.image.annotated_file_path),
            image_count=len(insp.images) if insp.images else 1
        )
        for insp in recent_records
    ]

    return DashboardMetrics(
        total_inspections=total,
        compliant_count=compliant,
        non_compliant_count=non_compliant,
        needs_review_count=needs_review,
        unable_to_verify_count=unable_verify,
        average_compliance_score=avg_score,
        category_distribution=category_distribution,
        recent_inspections=recent_items
    )

@router.post("/ar-frame", response_model=Dict[str, Any])
async def process_ar_camera_frame(
    request: Request,
    file: UploadFile = File(...),
    active_panel: str = Form("front"),
    package_id: str = Form("Package #1"),
    product_category: str = Form("packaged_commodity"),
    accumulated_panels_json: Optional[str] = Form(None),
    is_demo: bool = Form(False),
    db: Session = Depends(get_db)
):
    """
    AR-Inspection Live Camera Frame Processor:
    Takes an active video frame, identifies package boundaries with YOLO11, executes OCR on visible regions,
    fuses multi-panel evidence, evaluates statutory compliance, and returns responsive bounding box coordinates
    and 4-state visual indicators (PASS / FAIL / REVIEW / N/A) for interactive AR projection.
    """
    from app.services.ar_inspection_service import ARInspectionService
    try:
        user = None
        try:
            user = get_current_user(request, db)
        except Exception:
            pass

        content = await file.read()
        hist_panels = []
        if accumulated_panels_json:
            try:
                hist_panels = json.loads(accumulated_panels_json)
            except Exception:
                hist_panels = []

        result = ARInspectionService.analyze_frame(
            image_bytes=content,
            active_panel=active_panel,
            package_id=package_id,
            product_category=product_category,
            accumulated_panels=hist_panels,
            is_demo=is_demo
        )
        return result
    except Exception as e:
        logger.exception(f"AR frame processing error: {e}")
        raise HTTPException(status_code=500, detail=f"AR inspection frame error: {str(e)}")


@router.post("/ar-save", response_model=InspectionResponse)
async def save_ar_inspection(
    request: Request,
    file: UploadFile = File(...),
    active_panel: str = Form("front"),
    package_id: str = Form("Package #1"),
    product_category: str = Form("packaged_commodity"),
    accumulated_panels_json: Optional[str] = Form(None),
    is_demo: bool = Form(False),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Saves an AR camera scan as a persistent Inspection in the database,
    logging the audit trail, storing the image, evaluating compliance rules,
    and generating an official PDF report available for immediate download.
    """
    try:
        content = await file.read()
        unique_filename = f"ar_scan_{uuid.uuid4().hex[:12]}.jpg"
        file_path = settings.UPLOAD_DIR / unique_filename
        with open(file_path, "wb") as buffer:
            buffer.write(content)

        image_inputs = [{
            "path": str(file_path),
            "filename": unique_filename,
            "panel_type": active_panel,
            "image_index": 0
        }]

        inspection = run_inspection_pipeline(
            image_inputs=image_inputs,
            product_category=product_category,
            package_id=package_id or "Package #1",
            parent_scan_id=None,
            is_demo=is_demo,
            execution_mode="AR_SCAN",
            db=db
        )

        if user:
            inspection.user_id = user.id
            db.commit()
            db.refresh(inspection)

        # Ensure PDF report is generated and ready for download
        try:
            report_path = settings.REPORTS_DIR / f"Inspection_Report_{inspection.id}.pdf"
            generate_pdf_report(inspection, str(report_path))
        except Exception as pe:
            logger.warning(f"Could not generate PDF report for saved AR inspection {inspection.id}: {pe}")

        return format_inspection_response(inspection)
    except Exception as e:
        logger.exception(f"Error saving AR inspection: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save AR inspection: {str(e)}")


@router.get("/{inspection_id}", response_model=InspectionResponse)
def get_inspection(inspection_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """
    Retrieves full inspection details with bounding box evidence, raw OCR lines, and compliance checks.
    """
    inspection = db.query(Inspection).filter(Inspection.id == inspection_id, *( [] if user.role == 'admin' else [Inspection.user_id == user.id] )).first()
    if not inspection:
        raise ResourceNotFoundException("Inspection", inspection_id)
    return format_inspection_response(inspection)

@router.post("/{inspection_id}/override-field", response_model=InspectionResponse)
def override_inspection_field(
    inspection_id: str,
    override: FieldOverrideRequest,
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    """
    Allows an inspector to manually provide a verified value for a field that was not detected.
    This updates both the detected_fields and compliance_checks tables and re-evaluates status.
    """
    inspection = db.query(Inspection).filter(Inspection.id == inspection_id, *( [] if user.role == 'admin' else [Inspection.user_id == user.id] )).first()
    if not inspection:
        raise ResourceNotFoundException("Inspection", inspection_id)

    # Update or insert detected field
    existing_field = next((f for f in inspection.detected_fields if f.field_name == override.field_name), None)
    if existing_field:
        existing_field.normalized_value = override.value
        existing_field.raw_value = f"[MANUAL OVERRIDE] {override.value}"
        existing_field.confidence = 1.0
        existing_field.detection_method = "MANUAL_INSPECTOR"
        existing_field.unit = override.unit or existing_field.unit
    else:
        new_field = DetectedField(
            id=f"{inspection_id}_{override.field_name}_override",
            inspection_id=inspection_id,
            field_name=override.field_name,
            display_name=override.field_name.replace("_", " ").title(),
            raw_value=f"[MANUAL OVERRIDE] {override.value}",
            normalized_value=override.value,
            unit=override.unit,
            confidence=1.0,
            detection_method="MANUAL_INSPECTOR",
            bbox=None,
            metadata_info=json.dumps({"note": override.note or "Manually verified by inspector"})
        )
        inspection.detected_fields.append(new_field)

    # Update compliance check
    existing_check = next((c for c in inspection.compliance_checks if c.field_name == override.field_name), None)
    if existing_check:
        existing_check.status = "PASS"
        existing_check.detected_value = override.value
        existing_check.confidence = 1.0
        existing_check.explanation = f"Manually verified by inspector. Value: {override.value}. Note: {override.note or 'Manual verification'}"
        existing_check.inspector_recommendation = "Field verified manually. Declaration confirmed."

    # Recalculate counts
    all_checks = inspection.compliance_checks
    inspection.passed_checks = sum(1 for c in all_checks if c.status == "PASS")
    inspection.failed_checks = sum(1 for c in all_checks if c.status == "FAIL")
    inspection.warning_checks = sum(1 for c in all_checks if c.status == "WARNING")
    inspection.undetected_checks = sum(1 for c in all_checks if c.status == "NOT_DETECTED")

    # Update overall status
    if inspection.undetected_checks == 0 and inspection.failed_checks == 0 and inspection.warning_checks == 0:
        inspection.overall_status = "COMPLIANT"
    elif inspection.undetected_checks > 0 or inspection.failed_checks > 0:
        inspection.overall_status = "NON_COMPLIANT"
    else:
        inspection.overall_status = "NEEDS_REVIEW"

    total = inspection.total_checks or 1
    inspection.compliance_score = round((inspection.passed_checks / total) * 100, 1)

    db.commit()
    db.refresh(inspection)
    logger.info(f"Manual field override applied for {inspection_id} - field '{override.field_name}' set to '{override.value}'")
    return format_inspection_response(inspection)


@router.post("/{inspection_id}/review", response_model=InspectionResponse)
def submit_human_review(
    inspection_id: str,
    review: ReviewActionRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Human-in-the-Loop Review Decision Endpoint:
    Records an inspector's verified determination on conflicting, uncertain, or flagged declarations.
    Maintains an immutable statutory audit trail with reviewer identity, decision timestamp, original AI findings, and verified values.
    """
    inspection = db.query(Inspection).filter(Inspection.id == inspection_id, *( [] if user.role == 'admin' else [Inspection.user_id == user.id] )).first()
    if not inspection:
        raise ResourceNotFoundException("Inspection", inspection_id)

    from datetime import datetime, timezone
    now_iso = datetime.now(timezone.utc).isoformat()
    reviewer_title = review.reviewer_name or user.full_name or "Statutory Inspector"

    existing_field = next((f for f in inspection.detected_fields if f.field_name == review.field_name), None)
    orig_val = existing_field.normalized_value if existing_field else None

    # 1. Record immutable review decision
    decision_record = {
        "field_name": review.field_name,
        "action": review.action,
        "confirmed_value": review.confirmed_value,
        "source_panel": review.source_panel or (existing_field.source_panel if existing_field else "Manual Inspector Entry"),
        "reviewer_name": reviewer_title,
        "reviewer_id": user.id,
        "note": review.note or "Verified by statutory inspector",
        "timestamp": now_iso,
        "original_ai_value": orig_val,
        "final_verified_value": review.confirmed_value
    }
    
    current_reviews = list(inspection.review_decisions or [])
    current_reviews.append(decision_record)
    inspection.review_decisions = current_reviews

    # 2. Update Detected Field
    if existing_field:
        existing_field.normalized_value = review.confirmed_value
        existing_field.confidence = 1.0
        existing_field.has_conflict = False
        existing_field.detection_method = f"HUMAN_VERIFIED ({reviewer_title})"
        if review.source_panel:
            existing_field.source_panel = review.source_panel
    else:
        new_field = DetectedField(
            id=f"{inspection_id}_{review.field_name}_reviewed",
            inspection_id=inspection_id,
            field_name=review.field_name,
            display_name=review.field_name.replace("_", " ").title(),
            raw_value=f"[VERIFIED] {review.confirmed_value}",
            normalized_value=review.confirmed_value,
            confidence=1.0,
            source_panel=review.source_panel or "Manual Review",
            has_conflict=False,
            detection_method=f"HUMAN_VERIFIED ({reviewer_title})"
        )
        inspection.detected_fields.append(new_field)

    # 3. Update Compliance Check
    existing_check = next((c for c in inspection.compliance_checks if c.field_name == review.field_name), None)
    if existing_check:
        existing_check.status = "PASS" if review.action == "CONFIRM_VALUE" else "FAIL"
        existing_check.detected_value = review.confirmed_value
        existing_check.confidence = 1.0
        existing_check.conflict_detected = False
        existing_check.explanation = f"Declaration verified by {reviewer_title}. Value: {review.confirmed_value}. Note: {review.note or 'Human audit verification'}"
        existing_check.inspector_recommendation = "Statutory declaration confirmed by inspector."

    # 4. Remove resolved conflict from conflicts list
    current_conflicts = list(inspection.conflicts or [])
    inspection.conflicts = [c for c in current_conflicts if c.get("field_name") != review.field_name]

    # 5. Recalculate summary metrics & overall status
    all_checks = inspection.compliance_checks
    inspection.passed_checks = sum(1 for c in all_checks if c.status == "PASS")
    inspection.failed_checks = sum(1 for c in all_checks if c.status in ["FAIL", "NOT_DETECTED"] and c.is_mandatory)
    inspection.warning_checks = sum(1 for c in all_checks if c.status in ["WARNING", "REVIEW"])
    inspection.undetected_checks = sum(1 for c in all_checks if c.status == "NOT_DETECTED")
    inspection.uncertain_checks = sum(1 for c in all_checks if c.status == "REVIEW")

    has_mandatory_fail = any(c.status in ["FAIL", "NOT_DETECTED"] and c.is_mandatory for c in all_checks)
    has_remaining_reviews = any(c.status in ["REVIEW", "WARNING", "UNCERTAIN"] for c in all_checks) or len(inspection.conflicts) > 0

    if has_mandatory_fail:
        inspection.overall_status = "NON_COMPLIANT"
    elif has_remaining_reviews:
        inspection.overall_status = "NEEDS_REVIEW"
    else:
        inspection.overall_status = "COMPLIANT"

    total = inspection.total_checks or 1
    inspection.compliance_score = round((inspection.passed_checks / total) * 100, 1)

    db.commit()
    db.refresh(inspection)

    # Regenerate PDF dossier with updated human review
    try:
        generate_pdf_report(inspection)
    except Exception as e:
        logger.error(f"Failed to regenerate PDF report after human review: {e}")

    logger.info(f"Human review saved for inspection {inspection_id}, field '{review.field_name}'. Overall status: {inspection.overall_status}")
    return format_inspection_response(inspection)


@router.get("/{inspection_id}/evidence", response_model=Dict[str, Any])
def get_inspection_evidence(
    inspection_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Returns structured visual evidence, bounding boxes, and panel references for all declarations.
    """
    inspection = db.query(Inspection).filter(Inspection.id == inspection_id, *( [] if user.role == 'admin' else [Inspection.user_id == user.id] )).first()
    if not inspection:
        raise ResourceNotFoundException("Inspection", inspection_id)

    evidence_items = []
    for f in inspection.detected_fields:
        evidence_items.append({
            "field_name": f.field_name,
            "display_name": f.display_name,
            "normalized_value": f.normalized_value,
            "raw_value": f.raw_value,
            "confidence": f.confidence,
            "source_panel": f.source_panel or "Front Panel",
            "bbox": f.bbox,
            "has_conflict": f.has_conflict,
            "all_sources": f.metadata_info.get("all_panel_sources", []) if f.metadata_info else []
        })

    return {
        "inspection_id": inspection.id,
        "package_id": getattr(inspection, "package_id", "Package #1"),
        "total_fields": len(evidence_items),
        "conflicts": inspection.conflicts or [],
        "evidence": evidence_items
    }


@router.get("/scan/{scan_id}/packages", response_model=List[InspectionResponse])
def get_scan_packages(
    scan_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Returns all package inspections belonging to a multi-package scan session.
    """
    inspections = db.query(Inspection).filter(
        Inspection.parent_scan_id == scan_id,
        *( [] if user.role == 'admin' else [Inspection.user_id == user.id] )
    ).all()

    return [format_inspection_response(insp) for insp in inspections]



@router.get("/{inspection_id}/report")
def download_pdf_report(inspection_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """
    Generates and downloads the official PDF Compliance Report for the specified inspection.
    """
    inspection = db.query(Inspection).filter(Inspection.id == inspection_id, *( [] if user.role == 'admin' else [Inspection.user_id == user.id] )).first()
    if not inspection:
        raise ResourceNotFoundException("Inspection", inspection_id)

    report_path = settings.REPORTS_DIR / f"Inspection_Report_{inspection.id}.pdf"
    if not report_path.exists() or report_path.stat().st_size == 0:
        try:
            generate_pdf_report(inspection, str(report_path))
        except Exception as e:
            logger.error(f"Failed generating PDF report for {inspection_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Unable to publish/generate compliance PDF report: {str(e)}"
            )

    safe_cat = (inspection.product_category or "commodity").replace(' ', '_')
    return FileResponse(
        path=str(report_path),
        filename=f"LabelLens_Report_{safe_cat}_{inspection.id[:8]}.pdf",
        media_type="application/pdf"
    )

@router.get("/{inspection_id}/image")
def get_inspection_image(
    inspection_id: str,
    image_index: int = Query(0, ge=0),
    image_id: Optional[str] = Query(None),
    annotated: bool = Query(True),
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    """
    Streams original or bounding-box annotated label image for any uploaded panel.
    """
    inspection = db.query(Inspection).filter(Inspection.id == inspection_id, *( [] if user.role == 'admin' else [Inspection.user_id == user.id] )).first()
    if not inspection or not inspection.images:
        raise ResourceNotFoundException("Inspection Image", inspection_id)

    target_image = None
    if image_id:
        target_image = next((img for img in inspection.images if img.id == image_id), None)

    if not target_image:
        if 0 <= image_index < len(inspection.images):
            target_image = inspection.images[image_index]
        else:
            target_image = inspection.images[0]

    img_path = target_image.annotated_file_path if (annotated and target_image.annotated_file_path) else target_image.file_path
    
    if not os.path.exists(img_path):
        img_path = target_image.file_path
        if not os.path.exists(img_path):
            raise HTTPException(status_code=404, detail="Image file not found on disk.")

    ext = os.path.splitext(img_path)[1].replace(".", "").lower()
    media_type = f"image/{ext}" if ext in ["jpeg", "jpg", "png", "webp"] else "image/jpeg"
    return FileResponse(path=img_path, media_type=media_type)

@router.delete("/{inspection_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_inspection(inspection_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """
    Deletes an inspection record and associated uploaded files across all panels.
    """
    inspection = db.query(Inspection).filter(Inspection.id == inspection_id, *( [] if user.role == 'admin' else [Inspection.user_id == user.id] )).first()
    if not inspection:
        raise ResourceNotFoundException("Inspection", inspection_id)

    for img in inspection.images:
        if img.file_path and os.path.exists(img.file_path):
            try:
                os.remove(img.file_path)
            except Exception:
                pass
        if img.annotated_file_path and os.path.exists(img.annotated_file_path):
            try:
                os.remove(img.annotated_file_path)
            except Exception:
                pass

    db.delete(inspection)
    db.commit()
    return None


