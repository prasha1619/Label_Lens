from typing import Dict, List, Optional, Any
from app.schemas.extraction import FieldNormalizationResult, ExtractedField
from app.schemas.cv import QualityAssessment
from app.schemas.rule import (
    LegalStatusEnum,
    OverallComplianceStatus,
    RuleCheckResult,
    ViolationSummary,
    ComplianceEvaluationResult,
    RuleRequirementSchema,
    ProductCategorySchema
)
from app.services.rules.rule_loader import RuleLoader
from app.services.extraction.dates_extractor import DatesExtractor
from app.services.risk.anomaly_detector import AnomalyRiskEngine
from app.core.config import settings
from app.core.logging import logger

class LegalComplianceRuleEngine:
    """
    Evaluates extracted label declarations against statutory Legal Metrology rules.
    Guarantees explainability, confidence thresholds, applicability verification,
    cross-panel conflict resolution, and anti-hallucination policies.
    """

    @classmethod
    def _is_rule_applicable(
        cls,
        req: RuleRequirementSchema,
        extraction_result: FieldNormalizationResult,
        category_id: str
    ) -> tuple[bool, str]:
        """
        Determines if a rule genuinely applies to the commodity instance.
        Ensures 'Not Detected' does not become 'N/A' for mandatory applicable rules.
        """
        if getattr(req, "is_conditional", False):
            cond = getattr(req, "applicability_condition", "")
            if cond == "imported_only":
                origin_field = extraction_result.fields.get("country_of_origin")
                is_imported = origin_field and origin_field.normalized_value and origin_field.normalized_value.upper() != "INDIA"
                if not is_imported:
                    return False, "Applicable only to imported packaged commodities."
            elif cond == "perishable_only":
                if category_id not in ["food_and_beverages", "pharmaceuticals"]:
                    return False, f"Expiry declaration not required for non-perishable category '{category_id}'."

        return True, "Mandatory statutory declaration requirement."

    @classmethod
    def evaluate(
        cls,
        extraction_result: FieldNormalizationResult,
        quality_assessment: QualityAssessment,
        category_id: str = "packaged_commodity"
    ) -> ComplianceEvaluationResult:
        
        category_schema: Optional[ProductCategorySchema] = RuleLoader.get_category_rules(category_id)
        if not category_schema:
            category_schema = RuleLoader.get_category_rules("packaged_commodity")

        rule_checks: List[RuleCheckResult] = []
        violations: List[ViolationSummary] = []
        
        # Check 1: Image Quality Guardrail
        if not quality_assessment.is_acceptable or quality_assessment.status == "FAIL":
            reasons_str = "; ".join(quality_assessment.reasons) if quality_assessment.reasons else "Image quality too low for reliable OCR"
            
            for req in category_schema.rules:
                rule_checks.append(
                    RuleCheckResult(
                        rule_id=req.rule_id,
                        rule_title=req.title,
                        legal_reference=req.legal_reference,
                        field_name=req.field_name,
                        display_name=req.title,
                        is_mandatory=req.is_mandatory,
                        is_applicable=True,
                        applicability_reason="Mandatory declaration",
                        status=LegalStatusEnum.REVIEW,
                        detected_value=None,
                        raw_ocr_value=None,
                        confidence=None,
                        source_panel=None,
                        conflict_detected=False,
                        explanation=f"Unable to verify declaration due to image degradation ({reasons_str}).",
                        inspector_recommendation="Manual physical inspection required with higher-resolution, well-lit label capture.",
                        bbox=None,
                        evidence_available=False
                    )
                )

            violations.append(
                ViolationSummary(
                    field_name="image_quality",
                    severity="HIGH",
                    rule_id="LM_QUALITY_ASSURANCE",
                    legal_reference="Standard Inspection Protocol",
                    reason=f"Image quality insufficient: {reasons_str}",
                    recommendation="Re-capture label image with adequate lighting, sharp focus, and zero glare."
                )
            )

            return ComplianceEvaluationResult(
                product_category=category_id,
                rule_set_version=settings.RULE_SET_VERSION,
                overall_status=OverallComplianceStatus.UNABLE_TO_VERIFY,
                compliance_score=0.0,
                rule_checks=rule_checks,
                violations=violations,
                conflicts=[],
                anomaly_signals=[]
            )

        # Check 2: Evaluate Applicability & Declarations
        total_mandatory = 0
        passed_mandatory = 0
        total_confidence_sum = 0.0
        confidence_count = 0

        # Run Dual-Date Check if both dates present
        mfg_field = extraction_result.fields.get("mfg_date")
        exp_field = extraction_result.fields.get("expiry_date")
        date_consistency_result = None
        if mfg_field and exp_field and mfg_field.normalized_value and exp_field.normalized_value:
            date_consistency_result = DatesExtractor.validate_date_consistency(
                mfg_field.normalized_value,
                exp_field.normalized_value
            )

        for req in category_schema.rules:
            is_applicable, app_reason = cls._is_rule_applicable(req, extraction_result, category_id)
            field: Optional[ExtractedField] = extraction_result.fields.get(req.field_name)

            if not is_applicable:
                rule_checks.append(
                    RuleCheckResult(
                        rule_id=req.rule_id,
                        rule_title=req.title,
                        legal_reference=req.legal_reference,
                        field_name=req.field_name,
                        display_name=req.title,
                        is_mandatory=False,
                        is_applicable=False,
                        applicability_reason=app_reason,
                        status=LegalStatusEnum.N_A,
                        detected_value=field.normalized_value if field else None,
                        raw_ocr_value=field.raw_value if field else None,
                        confidence=field.confidence if field else None,
                        source_panel=field.metadata.get("source_panel") if field and field.metadata else None,
                        conflict_detected=False,
                        explanation=f"Requirement not applicable: {app_reason}",
                        inspector_recommendation="Non-applicable requirement under current category/origin configuration.",
                        bbox=field.bbox if field else None,
                        evidence_available=bool(field and field.bbox)
                    )
                )
                continue

            if req.is_mandatory:
                total_mandatory += 1

            if field and field.is_detected and field.normalized_value:
                conf_pct = field.confidence * 100.0
                total_confidence_sum += conf_pct
                confidence_count += 1
                source_panel = field.source_panel or field.metadata.get("source_panel") or field.metadata.get("panel_type") or "Front Panel"
                has_conflict = bool(field.has_conflict or field.metadata.get("has_conflict", False))

                if has_conflict:
                    status = LegalStatusEnum.REVIEW
                    conflict_summary = (field.conflict_entry.get("description") if field.conflict_entry else None) or field.metadata.get("conflict_entry", {}).get("conflict_summary", "Discrepancy across panels")
                    explanation = f"⚠ Cross-panel conflict detected: {conflict_summary}. Human review required."
                    recommendation = "Inspect front and back physical label evidence to resolve mismatched declarations."
                elif req.field_name == "mfg_date" and date_consistency_result and not date_consistency_result["is_valid"]:
                    status = LegalStatusEnum.FAIL
                    explanation = date_consistency_result["explanation"]
                    recommendation = "Check manufacturing date batch stamp."
                elif req.field_name == "expiry_date" and date_consistency_result and date_consistency_result["status"] == "REVIEW":
                    status = LegalStatusEnum.REVIEW
                    explanation = date_consistency_result["explanation"]
                    recommendation = "Verify shelf life and expiry period against manufacturer guidelines."
                elif conf_pct >= req.min_confidence_pass:
                    status = LegalStatusEnum.PASS
                    explanation = f"Required '{req.title}' detected with high confidence ({int(conf_pct)}%) on {source_panel}. Format valid."
                    recommendation = "Declaration verified compliant."
                    if req.is_mandatory:
                        passed_mandatory += 1
                elif conf_pct >= req.min_confidence_warning:
                    status = LegalStatusEnum.REVIEW
                    explanation = f"Declaration detected with moderate confidence ({int(conf_pct)}%) on {source_panel}. Low clarity."
                    recommendation = "Inspector should manually cross-verify the printed text against packaging."
                else:
                    status = LegalStatusEnum.REVIEW
                    explanation = f"Declaration detected with low confidence ({int(conf_pct)}%). OCR reading may be noisy."
                    recommendation = "Manual verification required in Review Queue."

                rule_checks.append(
                    RuleCheckResult(
                        rule_id=req.rule_id,
                        rule_title=req.title,
                        legal_reference=req.legal_reference,
                        field_name=req.field_name,
                        display_name=field.display_name,
                        is_mandatory=req.is_mandatory,
                        is_applicable=True,
                        applicability_reason="Mandatory declaration requirement",
                        status=status,
                        detected_value=field.normalized_value,
                        raw_ocr_value=field.raw_value,
                        confidence=round(field.confidence, 4),
                        source_panel=source_panel,
                        conflict_detected=has_conflict,
                        explanation=explanation,
                        inspector_recommendation=recommendation,
                        bbox=field.bbox,
                        evidence_available=bool(field.bbox)
                    )
                )

                if status == LegalStatusEnum.FAIL or (status == LegalStatusEnum.REVIEW and has_conflict):
                    violations.append(
                        ViolationSummary(
                            field_name=req.field_name,
                            severity="HIGH" if status == LegalStatusEnum.FAIL else "MEDIUM",
                            rule_id=req.rule_id,
                            legal_reference=req.legal_reference,
                            reason=explanation,
                            recommendation=recommendation
                        )
                    )

            else:
                # Field was NOT detected in OCR
                if req.is_mandatory:
                    status = LegalStatusEnum.FAIL
                    explanation = f"No matching declaration found for mandatory field '{req.title}' in the provided label images."
                    recommendation = req.recommendation_template
                    
                    violations.append(
                        ViolationSummary(
                            field_name=req.field_name,
                            severity=req.severity_if_missing,
                            rule_id=req.rule_id,
                            legal_reference=req.legal_reference,
                            reason=explanation,
                            recommendation=recommendation
                        )
                    )
                else:
                    status = LegalStatusEnum.N_A
                    explanation = f"Optional field '{req.title}' not declared."
                    recommendation = "Non-mandatory field. No violation."

                rule_checks.append(
                    RuleCheckResult(
                        rule_id=req.rule_id,
                        rule_title=req.title,
                        legal_reference=req.legal_reference,
                        field_name=req.field_name,
                        display_name=req.title,
                        is_mandatory=req.is_mandatory,
                        is_applicable=is_applicable,
                        applicability_reason=app_reason,
                        status=status,
                        detected_value=None,
                        raw_ocr_value=None,
                        confidence=None,
                        source_panel=None,
                        conflict_detected=False,
                        explanation=explanation,
                        inspector_recommendation=recommendation,
                        bbox=None,
                        evidence_available=False
                    )
                )

        # Evaluate Risk Signals & Conflicts
        conflicts_list = getattr(extraction_result, "_conflicts", [])
        anomaly_signals = AnomalyRiskEngine.evaluate_risk_signals(
            extraction_result,
            quality_assessment,
            conflicts=conflicts_list
        )

        # Determine Overall Status
        has_fails = any(c.status in [LegalStatusEnum.FAIL, LegalStatusEnum.NOT_DETECTED] and c.is_mandatory for c in rule_checks)
        has_reviews = any(c.status in [LegalStatusEnum.REVIEW, LegalStatusEnum.WARNING, LegalStatusEnum.UNCERTAIN] for c in rule_checks)

        if has_fails:
            overall_status = OverallComplianceStatus.NON_COMPLIANT
        elif has_reviews or quality_assessment.status == "WARNING" or len(conflicts_list) > 0:
            overall_status = OverallComplianceStatus.NEEDS_REVIEW
        else:
            overall_status = OverallComplianceStatus.COMPLIANT

        # Calculate Secondary Coverage Metric (0-100)
        coverage_ratio = (passed_mandatory / total_mandatory) if total_mandatory > 0 else 0.0
        avg_confidence = (total_confidence_sum / confidence_count) if confidence_count > 0 else 0.0
        compliance_score = round((coverage_ratio * 0.7 + (avg_confidence / 100.0) * 0.3) * 100.0, 1)

        return ComplianceEvaluationResult(
            product_category=category_id,
            rule_set_version=settings.RULE_SET_VERSION,
            overall_status=overall_status,
            compliance_score=compliance_score,
            rule_checks=rule_checks,
            violations=violations,
            conflicts=conflicts_list,
            anomaly_signals=anomaly_signals
        )

def evaluate_compliance(
    extraction_result: FieldNormalizationResult,
    quality_assessment: QualityAssessment,
    category_id: str = "packaged_commodity"
) -> ComplianceEvaluationResult:
    return LegalComplianceRuleEngine.evaluate(extraction_result, quality_assessment, category_id)

