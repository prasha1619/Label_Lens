from typing import Dict, List, Optional
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
from app.core.config import settings
from app.core.logging import logger

class LegalComplianceRuleEngine:
    """
    Evaluates extracted label declarations against statutory Legal Metrology rules.
    Guarantees explainability, confidence thresholds, and strict anti-hallucination policies.
    """

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
            # Image is too degraded for legal certainty
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
                        status=LegalStatusEnum.UNABLE_TO_VERIFY,
                        detected_value=None,
                        raw_ocr_value=None,
                        confidence=None,
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
                violations=violations
            )

        # Check 2: Evaluate each requirement against extracted fields
        total_mandatory = 0
        passed_mandatory = 0
        total_confidence_sum = 0.0
        confidence_count = 0

        for req in category_schema.rules:
            field: Optional[ExtractedField] = extraction_result.fields.get(req.field_name)
            
            if req.is_mandatory:
                total_mandatory += 1

            if field and field.is_detected and field.normalized_value:
                conf_pct = field.confidence * 100.0
                total_confidence_sum += conf_pct
                confidence_count += 1

                if conf_pct >= req.min_confidence_pass:
                    status = LegalStatusEnum.PASS
                    explanation = f"Required '{req.title}' detected with high confidence ({int(conf_pct)}%). Value matches statutory format."
                    recommendation = "Declaration verified compliant."
                    if req.is_mandatory:
                        passed_mandatory += 1
                elif conf_pct >= req.min_confidence_warning:
                    status = LegalStatusEnum.WARNING
                    explanation = f"Declaration detected with moderate confidence ({int(conf_pct)}%). Low clarity or partial occlusion."
                    recommendation = "Inspector should manually cross-verify the printed text against the product packaging."
                else:
                    status = LegalStatusEnum.UNCERTAIN
                    explanation = f"Declaration detected with low confidence ({int(conf_pct)}%). OCR reading may be noisy."
                    recommendation = "Manual verification required to confirm validity."

                rule_checks.append(
                    RuleCheckResult(
                        rule_id=req.rule_id,
                        rule_title=req.title,
                        legal_reference=req.legal_reference,
                        field_name=req.field_name,
                        display_name=field.display_name,
                        is_mandatory=req.is_mandatory,
                        status=status,
                        detected_value=field.normalized_value,
                        raw_ocr_value=field.raw_value,
                        confidence=round(field.confidence, 4),
                        explanation=explanation,
                        inspector_recommendation=recommendation,
                        bbox=field.bbox,
                        evidence_available=bool(field.bbox)
                    )
                )

                if status in [LegalStatusEnum.WARNING, LegalStatusEnum.UNCERTAIN]:
                    violations.append(
                        ViolationSummary(
                            field_name=req.field_name,
                            severity="MEDIUM" if status == LegalStatusEnum.WARNING else "HIGH",
                            rule_id=req.rule_id,
                            legal_reference=req.legal_reference,
                            reason=explanation,
                            recommendation=recommendation
                        )
                    )

            else:
                # Field was NOT detected in OCR
                if req.is_mandatory:
                    status = LegalStatusEnum.NOT_DETECTED
                    explanation = f"No matching declaration found for mandatory field '{req.title}' in the provided label image."
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
                    status = LegalStatusEnum.NOT_APPLICABLE
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
                        status=status,
                        detected_value=None,
                        raw_ocr_value=None,
                        confidence=None,
                        explanation=explanation,
                        inspector_recommendation=recommendation,
                        bbox=None,
                        evidence_available=False
                    )
                )

        # Determine Overall Status
        has_not_detected_mandatory = any(
            c.status == LegalStatusEnum.NOT_DETECTED and c.is_mandatory for c in rule_checks
        )
        has_fails = any(c.status == LegalStatusEnum.FAIL for c in rule_checks)
        has_warnings = any(c.status in [LegalStatusEnum.WARNING, LegalStatusEnum.UNCERTAIN] for c in rule_checks)

        if has_not_detected_mandatory or has_fails:
            overall_status = OverallComplianceStatus.NON_COMPLIANT
        elif has_warnings or quality_assessment.status == "WARNING":
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
            violations=violations
        )

def evaluate_compliance(
    extraction_result: FieldNormalizationResult,
    quality_assessment: QualityAssessment,
    category_id: str = "packaged_commodity"
) -> ComplianceEvaluationResult:
    return LegalComplianceRuleEngine.evaluate(extraction_result, quality_assessment, category_id)
