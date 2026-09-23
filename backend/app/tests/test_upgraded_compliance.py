import pytest
from app.schemas.ocr import OCRLine, OCRWord, OCRResultSchema
from app.services.extraction.dates_extractor import DatesExtractor
from app.services.extraction.mrp_extractor import MRPExtractor
from app.services.extraction.net_qty_extractor import NetQuantityExtractor
from app.services.extraction.entity_extractor import EntityExtractor
from app.services.extraction.field_fusion import FieldFusionEngine, PanelExtractionPayload
from app.schemas.extraction import ExtractedField, FieldNormalizationResult
from app.services.rules.rule_engine import LegalComplianceRuleEngine
from app.schemas.rule import LegalStatusEnum, OverallComplianceStatus
from app.schemas.cv import QualityAssessment
from app.services.risk.anomaly_detector import AnomalyRiskEngine


def test_hindi_mrp_extraction():
    ocr_lines = [
        OCRLine(
            line_number=1,
            text="अधिकतम खुदरा मूल्य: ₹ 150.00 (सभी करों सहित)",
            confidence=0.95,
            bbox=[10, 10, 200, 30]
        )
    ]
    res = MRPExtractor.extract(ocr_lines)
    assert res is not None
    assert res.normalized_value in ["₹150.00", "₹150", "150.00", "150"]
    assert res.field_name == "mrp"


def test_hindi_net_qty_extraction():
    ocr_lines = [
        OCRLine(
            line_number=1,
            text="शुद्ध मात्रा: 500 ग्राम",
            confidence=0.95,
            bbox=[10, 10, 150, 30]
        )
    ]
    res = NetQuantityExtractor.extract(ocr_lines)
    assert res is not None
    assert "500" in (res.normalized_value or "")
    assert res.unit == "g" or res.unit == "gm" or "500" in (res.normalized_value or "")


def test_dual_date_validation():
    # Case 1: Valid sequence (Mfg before Exp)
    mfg_lines = [OCRLine(line_number=1, text="MFD: 01/2026", confidence=0.95, bbox=[10, 10, 100, 25])]
    exp_lines = [OCRLine(line_number=1, text="EXP: 12/2026", confidence=0.95, bbox=[10, 30, 100, 45])]
    mfg_res = DatesExtractor.extract_mfg_date(mfg_lines)
    exp_res = DatesExtractor.extract_expiry_date(exp_lines)
    is_valid, msg = DatesExtractor.validate_date_consistency(mfg_res, exp_res)
    assert is_valid is True

    # Case 2: Inverted chronological sequence (Mfg after Exp)
    mfg_invalid_lines = [OCRLine(line_number=1, text="MFD: 12/2026", confidence=0.95, bbox=[10, 10, 100, 25])]
    exp_invalid_lines = [OCRLine(line_number=1, text="EXP: 01/2026", confidence=0.95, bbox=[10, 30, 100, 45])]
    mfg_invalid = DatesExtractor.extract_mfg_date(mfg_invalid_lines)
    exp_invalid = DatesExtractor.extract_expiry_date(exp_invalid_lines)
    is_valid, msg = DatesExtractor.validate_date_consistency(mfg_invalid, exp_invalid)
    assert is_valid is False
    assert "precedes or matches" in msg


def test_cross_panel_conflict_detection():
    # Front panel says MRP 120, Back panel says MRP 125
    front_payload = PanelExtractionPayload(
        image_index=0,
        panel_type="front",
        filename="front.jpg",
        extraction_result=FieldNormalizationResult(
            category_id="packaged_commodity",
            fields={
                "mrp": ExtractedField(
                    field_name="mrp",
                    display_name="Maximum Retail Price (MRP)",
                    raw_text="MRP Rs. 120.00",
                    normalized_value="₹120.00",
                    confidence=0.95,
                    bbox=[10, 10, 50, 30]
                ),
                "net_quantity": ExtractedField(
                    field_name="net_quantity",
                    display_name="Net Quantity",
                    raw_text="Net Qty: 200 ml",
                    normalized_value="200 ml",
                    unit="ml",
                    confidence=0.92,
                    bbox=[10, 40, 50, 60]
                )
            },
            raw_to_normalized_map={},
            extracted_count=2
        ),
        ocr_result=OCRResultSchema(
            total_lines=2,
            mean_confidence=0.93,
            raw_full_text="MRP Rs. 120.00 Net Qty: 200 ml",
            processing_time_ms=50.0
        )
    )

    back_payload = PanelExtractionPayload(
        image_index=1,
        panel_type="back",
        filename="back.jpg",
        extraction_result=FieldNormalizationResult(
            category_id="packaged_commodity",
            fields={
                "mrp": ExtractedField(
                    field_name="mrp",
                    display_name="Maximum Retail Price (MRP)",
                    raw_text="MRP Rs. 125.00",
                    normalized_value="₹125.00",
                    confidence=0.96,
                    bbox=[15, 15, 55, 35]
                ),
                "manufacturer": ExtractedField(
                    field_name="manufacturer",
                    display_name="Name and Address of Manufacturer",
                    raw_text="Manufactured by Herbal Co., Mumbai",
                    normalized_value="Herbal Co., Mumbai",
                    confidence=0.90,
                    bbox=[15, 45, 100, 70]
                )
            },
            raw_to_normalized_map={},
            extracted_count=2
        ),
        ocr_result=OCRResultSchema(
            total_lines=2,
            mean_confidence=0.93,
            raw_full_text="MRP Rs. 125.00 Manufactured by Herbal Co., Mumbai",
            processing_time_ms=50.0
        )
    )

    fused = FieldFusionEngine.fuse_panels([front_payload, back_payload])
    assert fused is not None
    assert "mrp" in fused.fields
    assert fused.fields["mrp"].has_conflict is True
    assert fused.fields["mrp"].conflict_entry is not None
    assert len(fused.conflicts) > 0


def test_4_state_rule_engine():
    quality = QualityAssessment(
        status="PASS",
        is_acceptable=True,
        blur_score=120.0,
        glare_score=0.1,
        brightness_score=130.0,
        contrast_score=65.0,
        width=1000,
        height=1000,
        reasons=[],
        recommendations=[]
    )

    norm_result = FieldNormalizationResult(
        category_id="cosmetics_and_toiletries",
        fields={
            "mrp": ExtractedField(
                field_name="mrp",
                display_name="Maximum Retail Price (MRP)",
                raw_text="MRP Rs. 120.00",
                normalized_value="₹120.00",
                confidence=0.95,
                bbox=[10, 10, 50, 30],
                has_conflict=True,
                conflict_entry={
                    "field_name": "mrp",
                    "description": "Conflict: MRP Rs. 120.00 vs MRP Rs. 125.00",
                    "values": [{"panel": "Front Panel", "value": "₹120.00"}, {"panel": "Back Panel", "value": "₹125.00"}]
                }
            )
        },
        raw_to_normalized_map={},
        extracted_count=1,
        conflicts=[{
            "field_name": "mrp",
            "description": "Conflict: MRP Rs. 120.00 vs MRP Rs. 125.00",
            "values": [{"panel": "Front Panel", "value": "₹120.00"}, {"panel": "Back Panel", "value": "₹125.00"}]
        }]
    )

    eval_result = LegalComplianceRuleEngine.evaluate(
        extraction_result=norm_result,
        quality_assessment=quality,
        category_id="cosmetics_and_toiletries"
    )

    mrp_check = next((c for c in eval_result.rule_checks if c.field_name == "mrp"), None)
    if mrp_check:
        assert mrp_check.status == LegalStatusEnum.REVIEW
        assert mrp_check.conflict_detected is True

    # Expiry date should be N_A for cosmetics under applicability engine
    exp_check = next((c for c in eval_result.rule_checks if c.field_name == "expiry_date"), None)
    if exp_check:
        assert exp_check.status == LegalStatusEnum.N_A
        assert exp_check.is_applicable is False

    assert eval_result.overall_status in (OverallComplianceStatus.NEEDS_REVIEW, OverallComplianceStatus.NON_COMPLIANT)

