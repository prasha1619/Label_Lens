import os
import uuid
import shutil
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, status
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
    FieldOverrideRequest
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

    # Format detected fields
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
            metadata=df.metadata_info or {}
        )
        for df in inspection.detected_fields
    ]

    # Format compliance checks
    compliance_checks = [
        RuleCheckResult(
            rule_id=cc.rule_id,
            rule_title=cc.rule_title,
            legal_reference=cc.legal_reference or "",
            field_name=cc.field_name,
            display_name=cc.rule_title,
            is_mandatory=cc.is_mandatory,
            status=LegalStatusEnum(cc.status),
            detected_value=cc.detected_value,
            raw_ocr_value=next((df.raw_value for df in inspection.detected_fields if df.field_name == cc.field_name), None),
            confidence=cc.confidence,
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

    return InspectionResponse(
        id=inspection.id,
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
        cv_model_version=inspection.cv_model_version,
        ocr_version=inspection.ocr_version,
        rule_set_version=inspection.rule_set_version,
        processing_time_ms=inspection.processing_time_ms,
        error_message=inspection.error_message,
        created_at=inspection.created_at,
        updated_at=inspection.updated_at,
        image=primary_image_schema,
        images=images_schema,
        ocr_summary=ocr_summary,
        detected_fields=detected_fields,
        compliance_checks=compliance_checks,
        violations=violations
    )

@router.post("", response_model=InspectionResponse, status_code=status.HTTP_201_CREATED)
def create_inspection(
    files: Optional[List[UploadFile]] = File(None),
    file: Optional[UploadFile] = File(None),
    product_category: str = Form("packaged_commodity"),
    panel_types: Optional[str] = Form(None),
    is_demo: bool = Form(False),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Uploads 1 or more packaged product label images (multi-panel: PDP front, back, side)
    and executes the end-to-end Legal Metrology cross-panel compliance pipeline.

    This endpoint intentionally remains synchronous. FastAPI therefore runs the
    CPU-heavy OCR/vision pipeline in its request worker pool instead of on the
    shared asyncio event loop, keeping History, dashboard, and health requests
    responsive while a live scan is in progress.
    """
    # Collect all uploaded files (support both `files` multi-upload and `file` single-upload)
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

    # Parse panel types if supplied
    parsed_panels: List[str] = []
    if panel_types:
        try:
            parsed_panels = json.loads(panel_types)
        except Exception:
            parsed_panels = [p.strip() for p in panel_types.split(",") if p.strip()]

    default_panel_names = ["front", "back", "side", "top", "general"]

    image_inputs: List[dict] = []

    for idx, f in enumerate(uploaded_files):
        # 1. Validate file extension
        ext = f.filename.split(".")[-1].lower() if "." in f.filename else ""
        if ext not in settings.ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file format '.{ext}' for file '{f.filename}'. Allowed formats: {', '.join(settings.ALLOWED_EXTENSIONS)}"
            )

        # 2. Save uploaded file securely
        unique_filename = f"{uuid.uuid4().hex}_{f.filename}"
        file_path = settings.UPLOAD_DIR / unique_filename

        try:
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(f.file, buffer)
        except Exception as e:
            logger.error(f"Failed to save uploaded file '{f.filename}': {e}")
            raise HTTPException(status_code=500, detail=f"Failed to store uploaded image '{f.filename}'.")

        # 3. Check file size
        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        if file_size_mb > settings.MAX_UPLOAD_SIZE_MB:
            os.remove(file_path)
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File '{f.filename}' size ({file_size_mb:.1f}MB) exceeds maximum limit of {settings.MAX_UPLOAD_SIZE_MB}MB."
            )

        # Assign panel type
        p_type = parsed_panels[idx] if idx < len(parsed_panels) else (
            default_panel_names[idx] if idx < len(default_panel_names) else f"Photo {idx + 1}"
        )

        image_inputs.append({
            "path": str(file_path),
            "filename": f.filename,
            "panel_type": p_type,
            "image_index": idx
        })

    # 4. Run end-to-end multi-panel pipeline
    try:
        inspection = run_inspection_pipeline(
            image_inputs=image_inputs,
            product_category=product_category,
            is_demo=is_demo,
            execution_mode="LIVE_PIPELINE" if not is_demo else "DEMO_SAMPLE",
            db=db
        )
        inspection.user_id = user.id
        db.commit()
        return format_inspection_response(inspection)
    except Exception as e:
        logger.exception(f"Inspection pipeline execution failed: {e}")
        raise HTTPException(status_code=500, detail=f"Pipeline execution error: {str(e)}")

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
