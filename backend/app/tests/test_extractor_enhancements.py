import pytest
from app.schemas.ocr import OCRLine, OCRWord
from app.services.extraction.entity_extractor import EntityExtractor
from app.services.extraction.net_qty_extractor import NetQuantityExtractor
from app.services.extraction.consumer_care_extractor import ConsumerCareExtractor
from app.services.extraction.field_extractor import LabelFieldExtractor
from app.schemas.ocr import OCRResultSchema

def make_line(line_num: int, text: str, confidence: float = 0.95, bbox=None) -> OCRLine:
    if bbox is None:
        bbox = [10, 10 + line_num * 30, 200, 35 + line_num * 30]
    return OCRLine(
        line_number=line_num,
        text=text,
        confidence=confidence,
        bbox=bbox,
        words=[OCRWord(text=text, confidence=confidence, bbox=bbox)]
    )

def test_generic_name_namkeen_and_exclusion_of_price_lines():
    # Top line has OCR noise "Nle Price :" which should NOT be picked as generic name
    lines = [
        make_line(1, "Nle Price :", confidence=0.92),
        make_line(2, "Kakaji", confidence=0.90),
        make_line(3, "PUNJABI TADKA", confidence=0.96),
        make_line(4, "Swad Sargam", confidence=0.88),
    ]
    field = EntityExtractor.extract_generic_name(lines)
    assert field is not None
    assert field.normalized_value == "Punjabi Tadka"
    assert field.detection_method == "TAXONOMY_MATCH"
    assert field.confidence >= 0.85

def test_manufacturer_with_multiline_and_allergen_exclusion():
    # Label contains allergen statement and multiline manufactured & marketed by
    lines = [
        make_line(1, "This Product is processed on equipment that also processes foods containing Wheat, Peanuts, Tree nuts", confidence=0.94),
        make_line(2, "Manufactured & Marketed by:", confidence=0.93),
        make_line(3, "FASTFOOD PRIVATE LIMITED", confidence=0.96),
        make_line(4, "Plot No. 7-8, Sector 12, Industrial Area, Karnal", confidence=0.91),
    ]
    field = EntityExtractor.extract_manufacturer(lines)
    assert field is not None
    assert "FASTFOOD PRIVATE LIMITED" in field.normalized_value
    assert "foods containing Wheat" not in field.normalized_value

def test_net_quantity_decimal_formatting():
    lines = [make_line(1, "NET WT : 50.5g", confidence=0.95)]
    field = NetQuantityExtractor.extract(lines)
    assert field is not None
    assert field.normalized_value == "50.5 g"
    assert field.unit == "g"

def test_consumer_care_fssai_lic_no_excluded():
    lines = [
        make_line(1, "Lic. No. 100200640021", confidence=0.96),
        make_line(2, "For Feedback or Queries Write to:", confidence=0.91),
        make_line(3, "Customer Care Executive at customercare@fastfood.in", confidence=0.94),
        make_line(4, "Helpline: 1800-180-2020", confidence=0.95),
    ]
    field = ConsumerCareExtractor.extract(lines)
    assert field is not None
    # 100200640021 must NOT be the helpline
    assert "100200640021" not in field.normalized_value
    assert "1800-180-2020" in field.normalized_value
    assert "customercare@fastfood.in" in field.normalized_value
    assert field.confidence >= 0.90

def test_full_field_extraction_orchestration():
    lines = [
        make_line(1, "Nle Price :", confidence=0.90),
        make_line(2, "Kakaji", confidence=0.88),
        make_line(3, "PUNJABI TADKA", confidence=0.95),
        make_line(4, "MRP : 30.00", confidence=0.93),
        make_line(5, "NET WT : 50.5g", confidence=0.95),
        make_line(6, "USP : Rs. 0.59 Per g", confidence=0.92),
        make_line(7, "MFD : 01/08/2026", confidence=0.94),
        make_line(8, "EXP : 31/01/2027", confidence=0.94),
        make_line(9, "This Product is processed on equipment that also processes foods containing Wheat, Peanuts", confidence=0.90),
        make_line(10, "Manufactured & Marketed by:", confidence=0.92),
        make_line(11, "FASTFOOD PRIVATE LIMITED", confidence=0.95),
        make_line(12, "Plot No. 7-8, Karnal", confidence=0.90),
        make_line(13, "Lic. No. 100200640021", confidence=0.95),
        make_line(14, "Consumer Care Email: care@fastfood.in", confidence=0.93),
        make_line(15, "Helpline: 1800-180-2020", confidence=0.95),
        make_line(16, "PRODUCT OF INDIA", confidence=0.96),
    ]
    ocr_result = OCRResultSchema(
        engine="TestOCR",
        total_lines=len(lines),
        mean_confidence=0.93,
        raw_full_text="\n".join(l.text for l in lines),
        lines=lines,
        processing_time_ms=50.0
    )
    result = LabelFieldExtractor.extract_all(ocr_result, product_category="packaged_commodity")
    
    assert "product_name" in result.fields
    assert result.fields["product_name"].normalized_value == "Punjabi Tadka"

    assert "mrp" in result.fields
    assert result.fields["mrp"].normalized_value == "₹30"

    assert "net_quantity" in result.fields
    assert result.fields["net_quantity"].normalized_value == "50.5 g"

    assert "manufacturer" in result.fields
    assert "FASTFOOD PRIVATE LIMITED" in result.fields["manufacturer"].normalized_value

    assert "consumer_care" in result.fields
    assert "100200640021" not in result.fields["consumer_care"].normalized_value
    assert "1800-180-2020" in result.fields["consumer_care"].normalized_value
    assert "care@fastfood.in" in result.fields["consumer_care"].normalized_value

    assert "country_of_origin" in result.fields
    assert result.fields["country_of_origin"].normalized_value == "India"


def test_date_extractor_month_name_formats():
    from app.services.extraction.dates_extractor import DatesExtractor

    # Test full month names
    lines_january = [make_line(1, "MFD ON: 15th January 2026", confidence=0.95)]
    mfg_jan = DatesExtractor.extract_mfg_date(lines_january)
    assert mfg_jan is not None
    assert mfg_jan.normalized_value == "15/01/2026"

    # Test 3-letter month abbreviations
    lines_feb = [make_line(1, "PKD: FEB 2026", confidence=0.95)]
    mfg_feb = DatesExtractor.extract_mfg_date(lines_feb)
    assert mfg_feb is not None
    assert mfg_feb.normalized_value == "02/2026"

    # Test Month Day Year format
    lines_mar = [make_line(1, "BEST BEFORE: March 20, 2027", confidence=0.94)]
    exp_mar = DatesExtractor.extract_expiry_date(lines_mar)
    assert exp_mar is not None
    assert exp_mar.normalized_value == "20/03/2027"

    # Test Sept / September
    lines_sept = [make_line(1, "MFD. DATE: Sept 2026", confidence=0.96)]
    mfg_sept = DatesExtractor.extract_mfg_date(lines_sept)
    assert mfg_sept is not None
    assert mfg_sept.normalized_value == "09/2026"

    # Test compound month names (e.g. MFD: Jan 2026 EXP: Dec 2028)
    lines_compound = [make_line(1, "MFD: JAN 2026 EXP: DEC 2028", confidence=0.97)]
    mfg_c, exp_c = DatesExtractor.extract_all_dates(lines_compound)
    assert mfg_c is not None and mfg_c.normalized_value == "01/2026"
    assert exp_c is not None and exp_c.normalized_value == "12/2028"

