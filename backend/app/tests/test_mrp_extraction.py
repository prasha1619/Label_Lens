import pytest
from app.schemas.ocr import OCRLine, OCRWord
from app.services.extraction.mrp_extractor import MRPExtractor

def make_line(text: str, confidence: float = 0.95, bbox=None) -> OCRLine:
    if bbox is None:
        bbox = [10, 10, 200, 40]
    return OCRLine(
        line_number=1,
        text=text,
        confidence=confidence,
        bbox=bbox,
        words=[OCRWord(text=text, confidence=confidence, bbox=bbox)]
    )

def test_mrp_standard_rs_format():
    lines = [make_line("M.R.P. : Rs. 249.00 (Incl. of all taxes)")]
    field = MRPExtractor.extract(lines)
    assert field is not None
    assert field.field_name == "mrp"
    assert field.normalized_value == "₹249"
    assert field.metadata.get("has_tax_inclusive") is True

def test_mrp_symbol_format():
    lines = [make_line("MRP ₹ 199.50")]
    field = MRPExtractor.extract(lines)
    assert field is not None
    assert field.normalized_value == "₹199.50"

def test_mrp_standalone_currency():
    lines = [make_line("₹ 45 (INCLUSIVE OF ALL TAXES)")]
    field = MRPExtractor.extract(lines)
    assert field is not None
    assert field.normalized_value == "₹45"

def test_mrp_price_strip_with_unit_sale_price():
    """The total MRP must win over the per-ml amount on a compact price strip."""
    field = MRPExtractor.extract([make_line("₹ 99/-  ₹ 0.50/ml   06:17", confidence=0.91)])
    assert field is not None
    assert field.normalized_value == "₹99"

def test_mrp_no_price_present():
    lines = [make_line("Manufactured by ABC Ltd Haridwar")]
    field = MRPExtractor.extract(lines)
    assert field is None

def test_mrp_from_declaration_table_when_caption_is_unreadable():
    """A faint MRP caption may be lost while the price/USP table is readable."""
    lines = [
        make_line("249.00", confidence=0.96, bbox=[318, 1030, 392, 1060]),
        make_line("USP per ml", confidence=0.80, bbox=[166, 1062, 242, 1088]),
        make_line("8.30", confidence=0.99, bbox=[322, 1054, 370, 1082]),
    ]
    field = MRPExtractor.extract(lines)
    assert field is not None
    assert field.normalized_value == "₹249"
    assert field.detection_method == "OCR_TABLE_POSITIONAL_MRP"
