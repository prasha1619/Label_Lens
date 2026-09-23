from typing import List, Dict, Any, Optional
from app.schemas.extraction import FieldNormalizationResult
from app.schemas.cv import QualityAssessment
from app.services.extraction.dates_extractor import DatesExtractor
from app.core.logging import logger

class AnomalyRiskEngine:
    """
    Evaluates multi-panel declarations and detection signals to identify potential anomalies and risk signals.
    Employs measured statutory terminology:
    - 'Potential Anomaly'
    - 'Risk Signal'
    - 'Requires Review'
    Strictly avoids unsupported legal assertions (e.g., 'Fraud', 'Fake', 'Illegal') without human verification.
    """

    @classmethod
    def evaluate_risk_signals(
        cls,
        extraction_result: FieldNormalizationResult,
        quality_assessment: QualityAssessment,
        conflicts: Optional[List[Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        signals: List[Dict[str, Any]] = []

        # Signal 1: Cross-Panel Conflicts
        conflicts_to_check = conflicts or getattr(extraction_result, "_conflicts", [])
        for conf in conflicts_to_check:
            signals.append({
                "signal_type": "CROSS_PANEL_CONFLICT",
                "severity": "HIGH",
                "label": "Potential Anomaly",
                "title": f"Conflicting {conf.get('display_name', conf.get('field_name'))} Declarations",
                "description": f"Cross-panel mismatch detected: {conf.get('conflict_summary')}.",
                "recommended_action": "Inspector verification required in Human-in-the-Loop Review Queue.",
                "evidence_sources": conf.get("sources", [])
            })

        # Signal 2: Dual-Date Validation Anomaly
        mfg_field = extraction_result.fields.get("mfg_date")
        exp_field = extraction_result.fields.get("expiry_date")
        if mfg_field and exp_field and mfg_field.normalized_value and exp_field.normalized_value:
            date_check = DatesExtractor.validate_date_consistency(
                mfg_field.normalized_value,
                exp_field.normalized_value
            )
            if not date_check.get("is_valid") or date_check.get("status") in ["FAIL", "REVIEW"]:
                signals.append({
                    "signal_type": "DATE_CHRONOLOGY_ANOMALY",
                    "severity": "HIGH" if date_check.get("status") == "FAIL" else "MEDIUM",
                    "label": "Potential Anomaly" if date_check.get("status") == "FAIL" else "Risk Signal",
                    "title": "Date Chronology Discrepancy",
                    "description": date_check.get("explanation"),
                    "recommended_action": "Manually verify printed packaging batch details and expiry stamps.",
                    "evidence_sources": [
                        {"field": "mfg_date", "value": mfg_field.normalized_value, "panel": mfg_field.metadata.get("panel_type")},
                        {"field": "expiry_date", "value": exp_field.normalized_value, "panel": exp_field.metadata.get("panel_type")}
                    ]
                })

        # Signal 3: Image Quality Degradation / Occlusion Risk
        if not quality_assessment.is_acceptable or quality_assessment.status in ["WARNING", "FAIL"]:
            reasons = "; ".join(quality_assessment.reasons) if quality_assessment.reasons else "Low contrast/glare"
            signals.append({
                "signal_type": "IMAGE_QUALITY_RISK",
                "severity": "MEDIUM",
                "label": "Risk Signal",
                "title": "Label Capture Degradation",
                "description": f"Image quality limitations ({reasons}) may affect automated extraction confidence.",
                "recommended_action": "Re-capture under standardized diffuse illumination if uncertain.",
                "evidence_sources": []
            })

        # Signal 4: Low Confidence Declarations
        for fname, field in extraction_result.fields.items():
            if field.is_detected and field.confidence < 0.50 and not field.metadata.get("has_conflict"):
                signals.append({
                    "signal_type": "LOW_CONFIDENCE_OCR",
                    "severity": "LOW",
                    "label": "Risk Signal",
                    "title": f"Low Confidence {field.display_name}",
                    "description": f"Extracted value '{field.normalized_value}' has confidence {int(field.confidence*100)}%.",
                    "recommended_action": "Verify field against physical packaging.",
                    "evidence_sources": [{"field": fname, "value": field.normalized_value, "panel": field.metadata.get("panel_type")}]
                })

        logger.info(f"Anomaly Risk Engine identified {len(signals)} risk signal(s).")
        return signals
