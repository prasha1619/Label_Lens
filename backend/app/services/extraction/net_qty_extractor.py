import re
from typing import Optional, List, Dict, Any
from app.schemas.extraction import ExtractedField
from app.schemas.ocr import OCRLine

class NetQuantityExtractor:
    """
    Extracts and normalizes Net Quantity declarations.
    Complies with Legal Metrology (Packaged Commodities) Rules, Rule 6(1)(c) & Rule 11.
    Standard SI units: g, kg, ml, l / L, m, cm, mm, sq m, N / U (units/pieces).
    """

    UNIT_NORMALIZATION_MAP = {
        "g": "g", "gm": "g", "gms": "g", "gram": "g", "grams": "g",
        "kg": "kg", "kgs": "kg", "kilo": "kg", "kilogram": "kg", "kilograms": "kg",
        "ml": "ml", "m.l.": "ml", "m.l": "ml", "millilitre": "ml", "millilitres": "ml", "milliliter": "ml",
        "mi": "ml", "m|": "ml", "m1": "ml", "@l": "ml", "mi": "ml", "ml.": "ml", "m1.": "ml",
        "l": "L", "lt": "L", "ltr": "L", "ltrs": "L", "liter": "L", "litre": "L", "litres": "L",
        "n": "N", "u": "Units", "unit": "Units", "units": "Units", "pc": "Pieces", "pcs": "Pieces", "piece": "Pieces", "pieces": "Pieces",
        "m": "m", "meter": "m", "metre": "m", "meters": "m", "cm": "cm", "mm": "mm"
    }

    QTY_HEADER_REGEX = re.compile(
        r'(?:'
        r'\b(?:NET\s*(?:WT\.?|WEIGHT|QTY\.?|QUANTITY|VOL\.?|VOLUME|CONTENT(?:S)?)|NET|CONTENT(?:S)?)\b[\s:\.\-\{\}\(\)]*'
        r')',
        re.IGNORECASE
    )

    # Dual declaration pattern: e.g. "100 ml (98.3 g)" or "100ml (98.3g)"
    DUAL_PATTERN = re.compile(
        r'([0-9]+(?:\.[0-9]+)?)\s*(MLS?|ML|MI|M1|LTRS?|LTR|L|GMS?|GM|G|KGS?|KG)\s*[\(\{\[]\s*([0-9]+(?:\.[0-9]+)?)\s*(GMS?|GM|G|KGS?|KG|MLS?|ML|MI|M1)\s*[\)\}\]]',
        re.IGNORECASE
    )

    # Patterns matching net quantity declarations
    PATTERNS = [
        # Net Qty / Net Weight / Net Content: 180 ml / 1.5 kg / 2 N
        re.compile(
            r'(?:NET\s*(?:WT\.?|WEIGHT|QTY\.?|QUANTITY|VOL\.?|VOLUME|CONTENT(?:S)?|\(WHEN\s*PACKED\))?)[\s:\.\-\{\}\(\)]*([0-9]+(?:\.[0-9]+)?)\s*(GMS?|GM|G|KGS?|KG|MLS?|ML|MI|M1|LTRS?|LTR|LT|L|PCS?|PIECES?|UNITS?|UNIT|N|U|@L)\b',
            re.IGNORECASE
        ),
        # Multi-pack quantity: 2 x 100 g / 4 x 50 ml
        re.compile(
            r'(?:NET\s*(?:QTY|WT|WEIGHT)?)?[\s:\.]*([0-9]+)\s*[xX*]\s*([0-9]+(?:\.[0-9]+)?)\s*(GMS?|GM|G|KGS?|KG|MLS?|ML|MI|M1|LTRS?|LTR|LT|L|PCS?|UNITS?|N)\b',
            re.IGNORECASE
        ),
        # Standalone numeric with standard metrology unit: 500 g / 250 ml / 1 kg
        re.compile(
            r'\b([0-9]+(?:\.[0-9]+)?)\s*(GMS?|GM|G|KGS?|KG|MLS?|ML|MI|LTRS?|LTR|LT|L|PCS?|PIECES?|UNITS?|N)\b',
            re.IGNORECASE
        )
    ]

    @classmethod
    def _clean_ocr_noise(cls, text: str) -> str:
        """Fixes common OCR letter-digit substitutions preceding metric units."""
        def fix_digits(m):
            raw = m.group(1)
            fixed = raw.replace('o', '0').replace('O', '0').replace('I', '1').replace('l', '1').replace('Q', '0').replace('J', '')
            return f"{fixed} {m.group(2)}"
        
        cleaned = re.sub(
            r'\b([0-9oOIlQJ]+(?:\.[0-9oOIlQ]+)?)\s*(mls?|ml|mi|m1|g|gm|gms|kg|kgs|ltrs?|ltr|lt|l|pcs?|units?|n|u)\b',
            fix_digits,
            text,
            flags=re.IGNORECASE
        )
        return cleaned

    @classmethod
    def _vertical_overlap(cls, bbox1: List[int], bbox2: List[int]) -> float:
        if not bbox1 or not bbox2 or len(bbox1) < 4 or len(bbox2) < 4:
            return 0.0
        y1 = max(bbox1[1], bbox2[1])
        y2 = min(bbox1[3], bbox2[3])
        if y2 <= y1:
            return 0.0
        h1 = max(1, bbox1[3] - bbox1[1])
        h2 = max(1, bbox2[3] - bbox2[1])
        return (y2 - y1) / min(h1, h2)

    @classmethod
    def extract(cls, lines: List[OCRLine]) -> Optional[ExtractedField]:
        best_match: Optional[Dict[str, Any]] = None

        # 1. Single-Line direct scans
        for idx, line in enumerate(lines):
            raw_orig = line.text.strip()
            text = cls._clean_ocr_noise(raw_orig)

            # Check Dual Declaration pattern (e.g., "100 ml (98.3 g)")
            dual_match = cls.DUAL_PATTERN.search(text)
            if dual_match:
                v1_str, u1_raw, v2_str, u2_raw = dual_match.groups()
                try:
                    v1 = float(v1_str)
                    v2 = float(v2_str)
                    u1 = cls.UNIT_NORMALIZATION_MAP.get(u1_raw.lower(), u1_raw.lower())
                    u2 = cls.UNIT_NORMALIZATION_MAP.get(u2_raw.lower(), u2_raw.lower())
                    v1_fmt = f"{v1:g}" if v1.is_integer() else f"{v1:.2f}"
                    v2_fmt = f"{v2:g}" if v2.is_integer() else f"{v2:.2f}"
                    norm_val = f"{v1_fmt} {u1} ({v2_fmt} {u2})"

                    return ExtractedField(
                        field_name="net_quantity",
                        display_name="Net Quantity",
                        raw_value=raw_orig,
                        normalized_value=norm_val,
                        unit=u1,
                        confidence=min(0.99, round(line.confidence * 0.98, 4)),
                        detection_method="OCR_REGEX_DUAL",
                        bbox=line.bbox,
                        is_detected=True,
                        metadata={
                            "is_dual_declaration": True,
                            "primary_quantity": v1,
                            "primary_unit": u1,
                            "secondary_quantity": v2,
                            "secondary_unit": u2,
                            "legal_rule": "Rule 6(1)(c) - Net Quantity (Dual Units)"
                        }
                    )
                except ValueError:
                    pass

            # Check Multipack pattern
            multi_match = cls.PATTERNS[1].search(text)
            if multi_match:
                count = int(multi_match.group(1))
                val = float(multi_match.group(2))
                raw_unit = multi_match.group(3).lower()
                norm_unit = cls.UNIT_NORMALIZATION_MAP.get(raw_unit, raw_unit)
                val_str = f"{val:g}" if val.is_integer() else f"{val:.2f}"
                total_val = count * val
                total_str = f"{total_val:g}" if total_val.is_integer() else f"{total_val:.2f}"
                normalized_val = f"{count} x {val_str} {norm_unit} (Total: {total_str} {norm_unit})"

                return ExtractedField(
                    field_name="net_quantity",
                    display_name="Net Quantity",
                    raw_value=raw_orig,
                    normalized_value=normalized_val,
                    unit=norm_unit,
                    confidence=min(0.99, round(line.confidence * 0.95, 4)),
                    detection_method="OCR_REGEX_MULTIPACK",
                    bbox=line.bbox,
                    is_detected=True,
                    metadata={
                        "is_multipack": True,
                        "package_count": count,
                        "unit_weight": val,
                        "unit": norm_unit,
                        "total_quantity": total_val
                    }
                )

            # Check standard single-line patterns
            for pattern_idx in [0, 2]:
                pattern = cls.PATTERNS[pattern_idx]
                match = pattern.search(text)
                if match:
                    val_str = match.group(1)
                    raw_unit = match.group(2).lower()
                    
                    try:
                        val_float = float(val_str)
                    except ValueError:
                        continue

                    # Filter out implausible years / numbers (e.g., 2026 g, 1000000)
                    if val_float <= 0 or val_float > 50000:
                        continue

                    norm_unit = cls.UNIT_NORMALIZATION_MAP.get(raw_unit, raw_unit)
                    clean_val = f"{val_float:g}" if val_float.is_integer() else f"{val_float:.2f}"
                    normalized_val = f"{clean_val} {norm_unit}"

                    # Pattern 0 (explicit Net Qty keyword) is given higher confidence weight
                    weight = 1.0 if pattern_idx == 0 else 0.82
                    confidence = min(0.99, round(line.confidence * weight, 4))

                    if best_match is None or confidence > best_match["confidence"] or (pattern_idx == 0 and best_match.get("pattern_idx") == 2):
                        best_match = {
                            "raw_value": raw_orig,
                            "normalized_value": normalized_val,
                            "unit": norm_unit,
                            "numeric_value": val_float,
                            "confidence": confidence,
                            "bbox": line.bbox,
                            "pattern_idx": pattern_idx,
                            "source": "SINGLE_LINE"
                        }

        # 2. Multi-Line Vertical Stack & Spatial 2-Column Scans
        for idx, line in enumerate(lines):
            raw_orig = line.text.strip()
            text = cls._clean_ocr_noise(raw_orig)
            if cls.QTY_HEADER_REGEX.search(text):
                header_bbox = line.bbox

                # 2A: Next line vertically
                for offset in [1, 2, 3]:
                    if idx + offset < len(lines):
                        next_line = lines[idx + offset]
                        next_raw = next_line.text.strip()
                        next_text = cls._clean_ocr_noise(next_raw)

                        # Dual match on stacked line
                        dual_m = cls.DUAL_PATTERN.search(next_text)
                        if dual_m:
                            v1_str, u1_raw, v2_str, u2_raw = dual_m.groups()
                            try:
                                v1 = float(v1_str)
                                v2 = float(v2_str)
                                u1 = cls.UNIT_NORMALIZATION_MAP.get(u1_raw.lower(), u1_raw.lower())
                                u2 = cls.UNIT_NORMALIZATION_MAP.get(u2_raw.lower(), u2_raw.lower())
                                v1_fmt = f"{v1:g}" if v1.is_integer() else f"{v1:.2f}"
                                v2_fmt = f"{v2:g}" if v2.is_integer() else f"{v2:.2f}"
                                norm_val = f"{v1_fmt} {u1} ({v2_fmt} {u2})"
                                return ExtractedField(
                                    field_name="net_quantity",
                                    display_name="Net Quantity",
                                    raw_value=f"{raw_orig} {next_raw}",
                                    normalized_value=norm_val,
                                    unit=u1,
                                    confidence=min(0.99, round(next_line.confidence * 0.98, 4)),
                                    detection_method="OCR_VERTICAL_DUAL",
                                    bbox=next_line.bbox,
                                    is_detected=True,
                                    metadata={"is_dual_declaration": True}
                                )
                            except ValueError:
                                pass

                        m = cls.PATTERNS[2].search(next_text) or cls.PATTERNS[0].search(next_text)
                        if m:
                            val_str = m.group(1)
                            raw_unit = m.group(2).lower()
                            try:
                                val_float = float(val_str)
                                if 0 < val_float <= 50000:
                                    norm_unit = cls.UNIT_NORMALIZATION_MAP.get(raw_unit, raw_unit)
                                    clean_val = f"{val_float:g}" if val_float.is_integer() else f"{val_float:.2f}"
                                    normalized_val = f"{clean_val} {norm_unit}"
                                    mean_conf = (line.confidence + next_line.confidence) / 2.0
                                    conf = min(0.99, round(mean_conf * 0.95, 4))
                                    combined_bbox = [
                                        min(header_bbox[0], next_line.bbox[0]),
                                        min(header_bbox[1], next_line.bbox[1]),
                                        max(header_bbox[2], next_line.bbox[2]),
                                        max(header_bbox[3], next_line.bbox[3]),
                                    ] if (len(header_bbox) == 4 and len(next_line.bbox) == 4) else header_bbox

                                    if best_match is None or conf >= best_match["confidence"]:
                                        best_match = {
                                            "raw_value": f"{raw_orig} {next_raw}",
                                            "normalized_value": normalized_val,
                                            "unit": norm_unit,
                                            "numeric_value": val_float,
                                            "confidence": conf,
                                            "bbox": combined_bbox,
                                            "pattern_idx": 0,
                                            "source": "VERTICAL_STACKED"
                                        }
                            except ValueError:
                                pass

        if best_match:
            return ExtractedField(
                field_name="net_quantity",
                display_name="Net Quantity",
                raw_value=best_match["raw_value"],
                normalized_value=best_match["normalized_value"],
                unit=best_match["unit"],
                confidence=best_match["confidence"],
                detection_method=f"OCR_{best_match.get('source', 'REGEX')}",
                bbox=best_match["bbox"],
                is_detected=True,
                metadata={
                    "numeric_quantity": best_match["numeric_value"],
                    "unit": best_match["unit"],
                    "legal_rule": "Rule 6(1)(c) - Net Quantity in Standard Units of Weight/Measure"
                }
            )

        return None
