import pytest
from app.schemas.ocr import OCRLine, OCRWord
from app.services.extraction.net_qty_extractor import NetQuantityExtractor

def make_line(text: str, confidence: float = 0.95) -> OCRLine:
    return OCRLine(
        line_number=1,
        text=text,
        confidence=confidence,
        bbox=[10, 10, 200, 40],
        words=[OCRWord(text=text, confidence=confidence, bbox=[10, 10, 200, 40])]
    )

def test_net_quantity_grams():
    lines = [make_line("Net Weight: 500 g")]
    field = NetQuantityExtractor.extract(lines)
    assert field is not None
    assert field.normalized_value == "500 g"
    assert field.unit == "g"

def test_net_quantity_milliliters():
    lines = [make_line("Net Volume : 180 ml")]
    field = NetQuantityExtractor.extract(lines)
    assert field is not None
    assert field.normalized_value == "180 ml"
    assert field.unit == "ml"

def test_net_quantity_multipack():
    lines = [make_line("Net Quantity: 2 x 50 g")]
    field = NetQuantityExtractor.extract(lines)
    assert field is not None
    assert "2 x 50 g" in field.normalized_value
    assert field.metadata.get("is_multipack") is True
    assert field.metadata.get("total_quantity") == 100.0

def test_net_quantity_units_count():
    lines = [make_line("Net Quantity: 1 N")]
    field = NetQuantityExtractor.extract(lines)
    assert field is not None
    assert field.normalized_value == "1 N"
