# pyrefly: ignore [missing-import]
import pytest
from app.schemas.cv import QualityAssessment
from app.schemas.extraction import FieldNormalizationResult, ExtractedField
from app.schemas.rule import LegalStatusEnum, OverallComplianceStatus
from app.services.rules.rule_engine import evaluate_compliance

def make_quality(status: str = "PASS", is_acceptable: bool = True, blur_score: float = 120.0, reasons=None) -> QualityAssessment:
    return QualityAssessment(
        status=status,
        is_acceptable=is_acceptable,
        blur_score=blur_score,
        brightness_score=130.0,
        contrast_score=60.0,
        glare_score=0.02,
        skew_angle=0.0,
        width=800,
        height=1000,
        reasons=reasons or []
    )

def test_rule_engine_unable_to_verify_on_degraded_image():
    quality = make_quality(status="FAIL", is_acceptable=False, blur_score=22.0, reasons=["Motion blur detected"])
    extraction = FieldNormalizationResult(
        category_id="packaged_commodity",
        fields={},
        raw_to_normalized_map={},
        extracted_count=0
    )

    result = evaluate_compliance(extraction, quality, category_id="packaged_commodity")
    assert result.overall_status == OverallComplianceStatus.UNABLE_TO_VERIFY
    assert result.compliance_score == 0.0
    assert len(result.violations) > 0
    assert any(c.status == LegalStatusEnum.UNABLE_TO_VERIFY for c in result.rule_checks)

def test_rule_engine_compliant_when_all_mandatory_fields_present():
    quality = make_quality(status="PASS", is_acceptable=True)
    fields = {
        "product_name": ExtractedField(field_name="product_name", display_name="Generic Name", raw_value="Shampoo", normalized_value="Shampoo", confidence=0.95),
        "net_quantity": ExtractedField(field_name="net_quantity", display_name="Net Qty", raw_value="200 ml", normalized_value="200 ml", confidence=0.94),
        "mrp": ExtractedField(field_name="mrp", display_name="MRP", raw_value="Rs 249", normalized_value="₹249", confidence=0.96),
        "mfg_date": ExtractedField(field_name="mfg_date", display_name="Mfg Date", raw_value="06/2026", normalized_value="06/2026", confidence=0.92),
        "manufacturer": ExtractedField(field_name="manufacturer", display_name="Manufacturer", raw_value="ABC Ltd", normalized_value="ABC Ltd", confidence=0.90),
        "consumer_care": ExtractedField(field_name="consumer_care", display_name="Consumer Care", raw_value="care@abc.com", normalized_value="Email: care@abc.com", confidence=0.93),
        "country_of_origin": ExtractedField(field_name="country_of_origin", display_name="Country", raw_value="India", normalized_value="India", confidence=0.95)
    }
    extraction = FieldNormalizationResult(
        category_id="packaged_commodity",
        fields=fields,
        raw_to_normalized_map={},
        extracted_count=len(fields)
    )

    result = evaluate_compliance(extraction, quality, category_id="packaged_commodity")
    assert result.overall_status == OverallComplianceStatus.COMPLIANT
    assert result.compliance_score >= 85.0
    assert len(result.violations) == 0

def test_rule_engine_non_compliant_when_mandatory_field_missing():
    quality = make_quality(status="PASS", is_acceptable=True)
    # Omit mandatory consumer_care
    fields = {
        "product_name": ExtractedField(field_name="product_name", display_name="Generic Name", raw_value="Biscuits", normalized_value="Biscuits", confidence=0.95),
        "net_quantity": ExtractedField(field_name="net_quantity", display_name="Net Qty", raw_value="100 g", normalized_value="100 g", confidence=0.94),
        "mrp": ExtractedField(field_name="mrp", display_name="MRP", raw_value="Rs 30", normalized_value="₹30", confidence=0.96),
        "mfg_date": ExtractedField(field_name="mfg_date", display_name="Mfg Date", raw_value="05/2026", normalized_value="05/2026", confidence=0.92),
        "manufacturer": ExtractedField(field_name="manufacturer", display_name="Manufacturer", raw_value="Crunchy Bakes", normalized_value="Crunchy Bakes", confidence=0.90)
    }
    extraction = FieldNormalizationResult(
        category_id="food_and_beverages",
        fields=fields,
        raw_to_normalized_map={},
        extracted_count=len(fields)
    )

    result = evaluate_compliance(extraction, quality, category_id="food_and_beverages")
    assert result.overall_status == OverallComplianceStatus.NON_COMPLIANT
    assert len(result.violations) > 0
    assert any(v.field_name == "consumer_care" for v in result.violations)
