import re
from typing import Optional, List, Dict, Any, Tuple
from app.schemas.extraction import ExtractedField
from app.schemas.ocr import OCRLine

class DatesExtractor:
    """
    Comprehensive Date of Manufacture/Packing & Expiry/Best Before Extractor.
    Complies with Legal Metrology (PC) Rules, Rule 6(1)(d) & FSSAI / Cosmetic labeling norms.
    Capabilities:
    1. Robust OCR-noise-tolerant header matching (MFD, MFG, PKD, PACKED, DOM, DOP, Vad, Mfo, MF6, MED, PKO, DEST DEFORE, BEST BEFORE, EXP)
    2. Multi-line vertical stack scanning (Header on line N, Date on line N+1 / N+2)
    3. Compound date pair parsing & disambiguation (e.g., '(A)07/2026,06/2029' -> 07/2026 as Mfg, 06/2029 as Expiry)
    4. 2-Column spatial alignment for tabular label layouts
    5. Relative shelf life declarations (e.g., '24 Months from Mfd Date', 'Best before 6 months from packaging')
    6. Standalone packaging date fallbacks
    """

    # Month name regex
    MONTH_NAMES = r'(?:JAN(?:UARY)?|FEB(?:RUARY)?|MAR(?:CH)?|APR(?:IL)?|MAY|JUN(?:E)?|JUL(?:Y)?|AUG(?:UST)?|SEP(?:TEMBER)?|OCT(?:OBER)?|NOV(?:EMBER)?|DEC(?:EMBER)?)'

    # Date pattern matching: MM/YYYY, MM/YY, DD/MM/YYYY, DD/MM/YY, Month YYYY, DD-Month-YYYY, etc.
    DATE_REGEX_PARSER = re.compile(
        rf'(?:'
        rf'(?:(?:[0-3]?[0-9][\/\-\.\s]+)?(?:0[1-9]|1[0-2]|{MONTH_NAMES})[\/\-\.\s]+(?:20[2-3][0-9]|[2-3][0-9]))|'
        rf'(?:(?:0?[1-9]|1[0-2])[\/\-\.](?:20[2-3][0-9]|[2-3][0-9]))|'
        rf'(?:(?:0?[1-9]|1[0-2])[\/\-\.][2-3][0-9](?=[0-2][0-9]:[0-5][0-9]|\b))|'
        rf'(?:{MONTH_NAMES}[\s\/\-\.]+(?:20[2-3][0-9]|[2-3][0-9]))'
        rf')',
        re.IGNORECASE
    )

    # Relative shelf life pattern (e.g., "24 Months from Mfd Date", "6 Months from Packing", "Use within 2 years")
    RELATIVE_SHELF_LIFE_REGEX = re.compile(
        r'(?:(?:BEST\s*BEFORE|USE\s*WITHIN|SHELF\s*LIFE)[\s:\.\-]*([0-9]{1,2}\s*(?:MONTHS?|YEARS?|DAYS?)(?:\s*(?:FROM|OF)\s*(?:MFG|MFD|PKD|PACKING|MANUFACTURE|DATE))?)|'
        r'([0-9]{1,2}\s*(?:MONTHS?|YEARS?)\s*(?:FROM|OF)\s*(?:MFG|MFD|PKD|PACKING|MANUFACTURE|DATE)))',
        re.IGNORECASE
    )

    # Mfg / Packaging Header Regex
    MFG_HEADER_REGEX = re.compile(
        r'(?:'
        r'\b(?:MFD|MFG|MANUFACTURED|MANUFACTURE|PACKED|PACKING|PKD|PKGD|P\.K\.D|M\.F\.D|M\.F\.G)\b|'
        r'\b(?:DOM|DOP|D\.O\.M|D\.O\.P|PROD\s*DATE|PRODUCTION\s*DATE|MFG\s*DT|MFD\s*DT)\b|'
        r'\b(?:MONTH\s*(?:AND|&)\s*YEAR\s*OF\s*(?:MFG|MANUFACTURE|PACKING|PKD))\b|'
        r'\b(?:DATE\s*OF\s*(?:MFG|MANUFACTURE|PACKING|PKD))\b|'
        r'\b(?:MFD\s*[\(\[A-Za-z0-9\s\)\]]*&\s*USE\s*BEFORE)\b|'
        r'\b(?:MFG\s*(?:AND|&)\s*PKGD\s*ON|PACKED\s*ON|MFD\s*ON|MANUFACTURED\s*ON)\b|'
        r'\b(?:MFG\.\s*MM\/YY|MFD\.\s*MM\/YY|MFD\/PKD|MFG\/PKD)\b|'
        r'\b(?:Vad|Mfo|MF6|MED|PKO|PK6|PXD)\b|'
        r'MF[DdGg][\s:\.\-=]+|PK[Dd][\s:\.\-=]+'
        r')',
        re.IGNORECASE
    )

    # Expiry / Best Before Header Regex
    EXP_HEADER_REGEX = re.compile(
        r'(?:'
        r'\b(?:EXP|EXPIRY|EXP\.?DATE|EXPIRY\s*DATE|USE\s*BY|BEST\s*BEFORE|CONSUME\s*BEFORE|SHELF\s*LIFE|VALID\s*UPTO|E\.X\.P|USE\s*BEFORE)\b|'
        r'\b(?:DEST\s*DEFORE|BEST\s*BEF0RE|DEST\s*BEFORE|BE5T\s*BEFORE|USE\s*BV|EXP\s*DT)\b|'
        r'EXP[\s:\.\-=]+|BEST\s*BEFORE[\s:\.\-=]+|USE\s*BEFORE[\s:\.\-=]+'
        r')',
        re.IGNORECASE
    )

    @classmethod
    def _extract_dates_from_string(cls, text: str) -> List[str]:
        # Strip plant code prefixes like (A), (05), (B), [A], etc.
        clean = re.sub(r'[\(\[]\s*[A-Za-z0-9]{1,3}\s*[\)\]]', ' ', text)
        matches = [m.group(0).strip() for m in cls.DATE_REGEX_PARSER.finditer(clean)]
        # Filter out standalone 4-digit numbers that are not valid dates
        valid = []
        for m in matches:
            clean_m = re.sub(r'\s+', ' ', m).strip(' ,.-;')
            if clean_m and len(clean_m) >= 4:
                valid.append(clean_m)
        return valid

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
    def extract_all_dates(cls, lines: List[OCRLine]) -> Tuple[Optional[ExtractedField], Optional[ExtractedField]]:
        """
        Extracts both Mfg Date and Expiry Date with holistic cross-line and multi-date analysis.
        """
        if not lines:
            return None, None

        mfg_candidates: List[Dict[str, Any]] = []
        exp_candidates: List[Dict[str, Any]] = []

        # 1. Single-Line Direct Scanning
        for idx, line in enumerate(lines):
            text = line.text.strip()
            dates_in_line = cls._extract_dates_from_string(text)
            rel_match = cls.RELATIVE_SHELF_LIFE_REGEX.search(text)

            is_mfg_hdr = bool(cls.MFG_HEADER_REGEX.search(text))
            is_exp_hdr = bool(cls.EXP_HEADER_REGEX.search(text))

            # Case A: Line has both MFD and EXP headers or compound dates e.g. "MFD: 07/26 EXP: 06/29" or "(A)07/2026,06/2029"
            if len(dates_in_line) >= 2:
                # First date is Mfg Date, Second date is Expiry Date
                mfg_candidates.append({
                    "normalized": dates_in_line[0],
                    "raw": text,
                    "confidence": min(0.99, round(line.confidence * 0.95, 4)),
                    "bbox": line.bbox,
                    "source": "COMPOUND_LINE_MFG"
                })
                exp_candidates.append({
                    "normalized": dates_in_line[1],
                    "raw": text,
                    "confidence": min(0.99, round(line.confidence * 0.95, 4)),
                    "bbox": line.bbox,
                    "source": "COMPOUND_LINE_EXP"
                })
            elif len(dates_in_line) == 1:
                date_val = dates_in_line[0]
                if is_mfg_hdr and not is_exp_hdr:
                    mfg_candidates.append({
                        "normalized": date_val,
                        "raw": text,
                        "confidence": min(0.99, round(line.confidence * 0.96, 4)),
                        "bbox": line.bbox,
                        "source": "SINGLE_LINE_MFG"
                    })
                elif is_exp_hdr and not is_mfg_hdr:
                    exp_candidates.append({
                        "normalized": date_val,
                        "raw": text,
                        "confidence": min(0.99, round(line.confidence * 0.96, 4)),
                        "bbox": line.bbox,
                        "source": "SINGLE_LINE_EXP"
                    })
                else:
                    # Ambiguous single date on a line
                    mfg_candidates.append({
                        "normalized": date_val,
                        "raw": text,
                        "confidence": min(0.95, round(line.confidence * 0.85, 4)),
                        "bbox": line.bbox,
                        "source": "AMBIGUOUS_DATE"
                    })

            if rel_match:
                rel_val = (rel_match.group(1) or rel_match.group(2) or rel_match.group(0)).strip()
                exp_candidates.append({
                    "normalized": rel_val,
                    "raw": text,
                    "confidence": min(0.98, round(line.confidence * 0.94, 4)),
                    "bbox": line.bbox,
                    "source": "RELATIVE_SHELF_LIFE"
                })

        # 2. Multi-Line Vertical Stack & Spatial 2-Column Scanning
        for idx, line in enumerate(lines):
            text = line.text.strip()
            is_mfg_hdr = bool(cls.MFG_HEADER_REGEX.search(text))
            is_exp_hdr = bool(cls.EXP_HEADER_REGEX.search(text))

            if is_mfg_hdr or is_exp_hdr:
                header_bbox = line.bbox
                h_center_y = (header_bbox[1] + header_bbox[3]) / 2.0 if len(header_bbox) == 4 else 0
                h_height = max(1, header_bbox[3] - header_bbox[1]) if len(header_bbox) == 4 else 20

                # 2A: Vertical Stack (Scan next 1 to 3 lines)
                for offset in range(1, 4):
                    if idx + offset < len(lines):
                        next_line = lines[idx + offset]
                        next_text = next_line.text.strip()
                        next_dates = cls._extract_dates_from_string(next_text)
                        next_rel = cls.RELATIVE_SHELF_LIFE_REGEX.search(next_text)

                        combined_raw = f"{text} {next_text}"
                        combined_bbox = [
                            min(header_bbox[0], next_line.bbox[0]),
                            min(header_bbox[1], next_line.bbox[1]),
                            max(header_bbox[2], next_line.bbox[2]),
                            max(header_bbox[3], next_line.bbox[3]),
                        ] if (len(header_bbox) == 4 and len(next_line.bbox) == 4) else header_bbox

                        mean_conf = (line.confidence + next_line.confidence) / 2.0
                        decay = 0.95 if offset == 1 else (0.88 if offset == 2 else 0.80)

                        if len(next_dates) >= 2:
                            # Compound dates in adjacent line e.g., Line N: "MFd :", Line N+1: "(A)07/2026,06/2029"
                            mfg_candidates.append({
                                "normalized": next_dates[0],
                                "raw": combined_raw,
                                "confidence": min(0.99, round(mean_conf * decay, 4)),
                                "bbox": combined_bbox,
                                "source": "VERTICAL_COMPOUND_MFG"
                            })
                            exp_candidates.append({
                                "normalized": next_dates[1],
                                "raw": combined_raw,
                                "confidence": min(0.99, round(mean_conf * decay, 4)),
                                "bbox": combined_bbox,
                                "source": "VERTICAL_COMPOUND_EXP"
                            })
                        elif len(next_dates) == 1:
                            if is_mfg_hdr:
                                mfg_candidates.append({
                                    "normalized": next_dates[0],
                                    "raw": combined_raw,
                                    "confidence": min(0.99, round(mean_conf * decay, 4)),
                                    "bbox": combined_bbox,
                                    "source": "VERTICAL_STACKED_MFG"
                                })
                            elif is_exp_hdr:
                                exp_candidates.append({
                                    "normalized": next_dates[0],
                                    "raw": combined_raw,
                                    "confidence": min(0.99, round(mean_conf * decay, 4)),
                                    "bbox": combined_bbox,
                                    "source": "VERTICAL_STACKED_EXP"
                                })

                        if next_rel and is_exp_hdr:
                            rel_val = (next_rel.group(1) or next_rel.group(2) or next_rel.group(0)).strip()
                            exp_candidates.append({
                                "normalized": rel_val,
                                "raw": combined_raw,
                                "confidence": min(0.98, round(mean_conf * decay, 4)),
                                "bbox": combined_bbox,
                                "source": "VERTICAL_RELATIVE_EXP"
                            })

                # 2B: Spatial 2-Column Row Pairing
                for other_idx, other_line in enumerate(lines):
                    if other_idx == idx:
                        continue
                    other_text = other_line.text.strip()
                    other_bbox = other_line.bbox
                    if len(header_bbox) == 4 and len(other_bbox) == 4:
                        o_center_y = (other_bbox[1] + other_bbox[3]) / 2.0
                        overlap = cls._vertical_overlap(header_bbox, other_bbox)
                        y_dist = abs(h_center_y - o_center_y)

                        is_same_row = (overlap > 0.30) or (y_dist <= h_height * 0.85)
                        is_to_right = other_bbox[0] >= header_bbox[0] - 20

                        if is_same_row and is_to_right:
                            other_dates = cls._extract_dates_from_string(other_text)
                            combined_raw = f"{text} {other_text}"
                            combined_bbox = [
                                min(header_bbox[0], other_bbox[0]),
                                min(header_bbox[1], other_bbox[1]),
                                max(header_bbox[2], other_bbox[2]),
                                max(header_bbox[3], other_bbox[3]),
                            ]
                            mean_conf = (line.confidence + other_line.confidence) / 2.0

                            if len(other_dates) >= 2:
                                mfg_candidates.append({
                                    "normalized": other_dates[0],
                                    "raw": combined_raw,
                                    "confidence": min(0.99, round(mean_conf * 0.96, 4)),
                                    "bbox": combined_bbox,
                                    "source": "SPATIAL_2COL_COMPOUND_MFG"
                                })
                                exp_candidates.append({
                                    "normalized": other_dates[1],
                                    "raw": combined_raw,
                                    "confidence": min(0.99, round(mean_conf * 0.96, 4)),
                                    "bbox": combined_bbox,
                                    "source": "SPATIAL_2COL_COMPOUND_EXP"
                                })
                            elif len(other_dates) == 1:
                                if is_mfg_hdr:
                                    mfg_candidates.append({
                                        "normalized": other_dates[0],
                                        "raw": combined_raw,
                                        "confidence": min(0.99, round(mean_conf * 0.96, 4)),
                                        "bbox": combined_bbox,
                                        "source": "SPATIAL_2COL_MFG"
                                    })
                                elif is_exp_hdr:
                                    exp_candidates.append({
                                        "normalized": other_dates[0],
                                        "raw": combined_raw,
                                        "confidence": min(0.99, round(mean_conf * 0.96, 4)),
                                        "bbox": combined_bbox,
                                        "source": "SPATIAL_2COL_EXP"
                                    })

        mfg_field: Optional[ExtractedField] = None
        exp_field: Optional[ExtractedField] = None

        if mfg_candidates:
            def score_mfg(c: Dict[str, Any]) -> float:
                s = c["confidence"]
                if "SINGLE_LINE" in c["source"]:
                    s += 0.25
                elif "COMPOUND" in c["source"]:
                    s += 0.22
                elif "VERTICAL" in c["source"]:
                    s += 0.20
                elif "SPATIAL" in c["source"]:
                    s += 0.18
                return s

            mfg_candidates.sort(key=score_mfg, reverse=True)
            best_mfg = mfg_candidates[0]
            mfg_field = ExtractedField(
                field_name="mfg_date",
                display_name="Date of Manufacture / Packing",
                raw_value=best_mfg["raw"],
                normalized_value=best_mfg["normalized"],
                confidence=best_mfg["confidence"],
                detection_method=f"OCR_{best_mfg['source']}",
                bbox=best_mfg["bbox"],
                is_detected=True,
                metadata={
                    "legal_rule": "Rule 6(1)(d) - Month and Year of Manufacture/Packing",
                    "source_strategy": best_mfg["source"],
                    "all_candidates": [
                        {"value": c["normalized"], "raw": c["raw"], "confidence": c["confidence"]}
                        for c in mfg_candidates[:5]
                    ]
                }
            )

        if exp_candidates:
            def score_exp(c: Dict[str, Any]) -> float:
                s = c["confidence"]
                if "SINGLE_LINE" in c["source"] or "RELATIVE" in c["source"]:
                    s += 0.25
                elif "COMPOUND" in c["source"]:
                    s += 0.22
                elif "VERTICAL" in c["source"]:
                    s += 0.20
                return s

            exp_candidates.sort(key=score_exp, reverse=True)
            best_exp = exp_candidates[0]
            exp_field = ExtractedField(
                field_name="expiry_date",
                display_name="Expiry / Best Before Date",
                raw_value=best_exp["raw"],
                normalized_value=best_exp["normalized"],
                confidence=best_exp["confidence"],
                detection_method=f"OCR_{best_exp['source']}",
                bbox=best_exp["bbox"],
                is_detected=True,
                metadata={
                    "legal_rule": "Rule 6(1)(d) - Expiry / Best Before Declaration",
                    "source_strategy": best_exp["source"],
                    "all_candidates": [
                        {"value": c["normalized"], "raw": c["raw"], "confidence": c["confidence"]}
                        for c in exp_candidates[:5]
                    ]
                }
            )

        return mfg_field, exp_field

    @classmethod
    def extract_mfg_date(cls, lines: List[OCRLine]) -> Optional[ExtractedField]:
        mfg_field, _ = cls.extract_all_dates(lines)
        return mfg_field

    @classmethod
    def extract_expiry_date(cls, lines: List[OCRLine]) -> Optional[ExtractedField]:
        _, exp_field = cls.extract_all_dates(lines)
        return exp_field
