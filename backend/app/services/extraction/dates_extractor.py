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

    # Month name to 2-digit numeric mapping
    MONTH_MAP: Dict[str, str] = {
        "jan": "01", "january": "01",
        "feb": "02", "february": "02",
        "mar": "03", "march": "03",
        "apr": "04", "april": "04",
        "may": "05",
        "jun": "06", "june": "06",
        "jul": "07", "july": "07",
        "aug": "08", "august": "08",
        "sep": "09", "sept": "09", "september": "09",
        "oct": "10", "october": "10",
        "nov": "11", "november": "11",
        "dec": "12", "december": "12",
    }

    # Month name regex supporting all 3-letter, 4-letter (Sept), and full month names
    MONTH_NAMES = r'(?:JAN(?:UARY)?|FEB(?:RUARY)?|MAR(?:CH)?|APR(?:IL)?|MAY|JUN(?:E)?|JUL(?:Y)?|AUG(?:UST)?|SEP(?:T|TEMBER)?|OCT(?:OBER)?|NOV(?:EMBER)?|DEC(?:EMBER)?)'

    # Date pattern matching: Day-Month-Year, Month-Day-Year, Month-Year, MM/YYYY, DD/MM/YYYY, ISO, etc.
    DATE_REGEX_PARSER = re.compile(
        rf'(?:'
        # 1. Day + Month (name or num) + Year (e.g., 15 Jan 2026, 15th January 2026, 15-01-2026, 15/Jan/26)
        rf'(?:(?:0?[1-9]|[12][0-9]|3[01])(?:st|nd|rd|th)?[\s\/\-\.]+(?:0[1-9]|1[0-2]|{MONTH_NAMES})[\s\/\-\.]+(?:20[2-3][0-9]|[2-3][0-9]))|'
        # 2. Month name + Day + Year (e.g., Jan 15, 2026, January 15th 2026, Jan 15 2026)
        rf'(?:(?:{MONTH_NAMES})[\s\/\-\.]+(?:0?[1-9]|[12][0-9]|3[01])(?:st|nd|rd|th)?(?:,)?[\s\/\-\.]+(?:20[2-3][0-9]|[2-3][0-9]))|'
        # 3. Month name + Year (e.g., Jan 2026, January 2026, JAN-2026, JAN/26)
        rf'(?:(?:{MONTH_NAMES})[\s\/\-\.]+(?:20[2-3][0-9]|[2-3][0-9]))|'
        # 4. Numeric MM/YYYY or MM/YY (e.g., 07/2026, 07-2026, 07/26)
        rf'(?:(?:0?[1-9]|1[0-2])[\/\-\.](?:20[2-3][0-9]|[2-3][0-9]))|'
        # 5. ISO Format: YYYY-MM-DD or YYYY-MM (e.g., 2026-06-15, 2026-Jan-15, 2026-06)
        rf'(?:(?:20[2-3][0-9])[\/\-\.](?:0?[1-9]|1[0-2]|{MONTH_NAMES})(?:[\/\-\.](?:0?[1-9]|[12][0-9]|3[01]))?)'
        rf')',
        re.IGNORECASE
    )

    # Relative shelf life pattern (e.g., "24 Months from Mfd Date", "6 Months from Packing", "Use within 2 years", "पैकिंग से 6 महीने")
    RELATIVE_SHELF_LIFE_REGEX = re.compile(
        r'(?:(?:BEST\s*BEFORE|USE\s*WITHIN|SHELF\s*LIFE)[\s:\.\-]*([0-9]{1,2}\s*(?:MONTHS?|YEARS?|DAYS?)(?:\s*(?:FROM|OF)\s*(?:MFG|MFD|PKD|PACKING|MANUFACTURE|DATE))?)|'
        r'([0-9]{1,2}\s*(?:MONTHS?|YEARS?)\s*(?:FROM|OF)\s*(?:MFG|MFD|PKD|PACKING|MANUFACTURE|DATE))|'
        r'(?:(?:पैकिंग|निर्माण|उत्पादन)\s*(?:की\s*तारीख\s*)?से\s*([0-9]{1,2})\s*(?:माह|महीने|वर्ष|दिन)))',
        re.IGNORECASE
    )

    # Mfg / Packaging Header Regex (handles English OCR noise + Hindi declarations)
    MFG_HEADER_REGEX = re.compile(
        r'(?:'
        r'\b(?:MFD|MFG|MANUFACTURED|MANUFACTURE|PACKED|PACKING|PKD|PKGD|P\.K\.D|M\.F\.D|M\.F\.G)\b|'
        r'\b(?:DOM|DOP|D\.O\.M|D\.O\.P|PROD\s*DATE|PRODUCTION\s*DATE|MFG\s*DT|MFD\s*DT)\b|'
        r'\b(?:MONTH\s*(?:AND|&)\s*YEAR\s*OF\s*(?:MFG|MANUFACTURE|PACKING|PKD))\b|'
        r'\b(?:DATE\s*OF\s*(?:MFG|MANUFACTURE|PACKING|PKD))\b|'
        r'\b(?:MFD\s*[\(\[A-Za-z0-9\s\)\]]*&\s*USE\s*BEFORE)\b|'
        r'\b(?:MFG\s*(?:AND|&)\s*PKGD\s*ON|PACKED\s*ON|MFD\s*ON|MANUFACTURED\s*ON)\b|'
        r'\b(?:MFG\.\s*MM\/YY|MFD\.\s*MM\/YY|MFD\/PKD|MFG\/PKD)\b|'
        r'(?:निर्माण\s*तिथि|पैकिंग\s*तिथि|पैकिंग\s*की\s*तारीख|उत्पादन\s*तिथि|पैकिंग\s*माह|निर्माण\s*माह|एमएफडी|पीकेडी)|'
        r'\b(?:Vad|Mfo|MF6|MED|PKO|PK6|PXD)\b|'
        r'MF[DdGg][\s:\.\-=]+|PK[Dd][\s:\.\-=]+'
        r')',
        re.IGNORECASE
    )

    # Expiry / Best Before Header Regex (handles English OCR noise + Hindi declarations)
    EXP_HEADER_REGEX = re.compile(
        r'(?:'
        r'\b(?:EXP|EXPIRY|EXP\.?DATE|EXPIRY\s*DATE|USE\s*BY|BEST\s*BEFORE|CONSUME\s*BEFORE|SHELF\s*LIFE|VALID\s*UPTO|E\.X\.P|USE\s*BEFORE)\b|'
        r'\b(?:DEST\s*DEFORE|BEST\s*BEF0RE|DEST\s*BEFORE|BE5T\s*BEFORE|USE\s*BV|EXP\s*DT)\b|'
        r'(?:उपयोग\s*की\s*अंतिम\s*तिथि|सर्वश्रेष्ठ\s*पहले|अवसान\s*तिथि|समाप्ति\s*तिथि|उपभोग\s*की\s*अंतिम\s*तिथि|उपयोग\s*से\s*पहले)|'
        r'EXP[\s:\.\-=]+|BEST\s*BEFORE[\s:\.\-=]+|USE\s*BEFORE[\s:\.\-=]+'
        r')',
        re.IGNORECASE
    )


    @classmethod
    def normalize_date_string(cls, raw: str) -> str:
        """
        Normalizes any extracted date string (including month names, ordinal suffixes, 2-digit years)
        into standard MM/YYYY or DD/MM/YYYY format.
        Examples:
          - 'Jan 2026' -> '01/2026'
          - 'January 2026' -> '01/2026'
          - '15 Jan 2026' -> '15/01/2026'
          - '15th January 2026' -> '15/01/2026'
          - 'Jan 15, 2026' -> '15/01/2026'
          - '15-07-2026' -> '15/07/2026'
          - '07/26' -> '07/2026'
          - '2026-07-15' -> '15/07/2026'
        """
        if not raw:
            return raw

        clean = re.sub(r'[\(\[\)\]]', '', raw).strip(' ,.-;:')
        clean_lower = clean.lower()

        # Check for Month Name + Day + Year e.g. "Jan 15, 2026" or "January 15th 2026"
        m_month_day_year = re.match(
            rf'({cls.MONTH_NAMES})[\s\/\-\.]+(0?[1-9]|[12][0-9]|3[01])(?:st|nd|rd|th)?(?:,)?[\s\/\-\.]+(20[2-3][0-9]|[2-3][0-9])',
            clean,
            re.IGNORECASE
        )
        if m_month_day_year:
            m_str, d_str, y_str = m_month_day_year.groups()
            month_num = cls.MONTH_MAP.get(m_str.lower(), "01")
            day_num = f"{int(d_str):02d}"
            year_num = f"20{y_str}" if len(y_str) == 2 else y_str
            return f"{day_num}/{month_num}/{year_num}"

        # Check for Day + Month Name + Year e.g. "15 Jan 2026", "15th January 2026", "15-Jan-26"
        m_day_month_year = re.match(
            rf'(0?[1-9]|[12][0-9]|3[01])(?:st|nd|rd|th)?[\s\/\-\.]+({cls.MONTH_NAMES})[\s\/\-\.]+(20[2-3][0-9]|[2-3][0-9])',
            clean,
            re.IGNORECASE
        )
        if m_day_month_year:
            d_str, m_str, y_str = m_day_month_year.groups()
            month_num = cls.MONTH_MAP.get(m_str.lower(), "01")
            day_num = f"{int(d_str):02d}"
            year_num = f"20{y_str}" if len(y_str) == 2 else y_str
            return f"{day_num}/{month_num}/{year_num}"

        # Check for Month Name + Year e.g. "Jan 2026", "January 2026", "JAN/26", "JAN-2026"
        m_month_year = re.match(
            rf'({cls.MONTH_NAMES})[\s\/\-\.]+(20[2-3][0-9]|[2-3][0-9])',
            clean,
            re.IGNORECASE
        )
        if m_month_year:
            m_str, y_str = m_month_year.groups()
            month_num = cls.MONTH_MAP.get(m_str.lower(), "01")
            year_num = f"20{y_str}" if len(y_str) == 2 else y_str
            return f"{month_num}/{year_num}"

        # Check for ISO Year-Month-Day or Year-Month (e.g. 2026-06-15, 2026/06)
        m_iso = re.match(
            r'(20[2-3][0-9])[\/\-\.](0?[1-9]|1[0-2]|' + cls.MONTH_NAMES + r')(?:[\/\-\.](0?[1-9]|[12][0-9]|3[01]))?',
            clean,
            re.IGNORECASE
        )
        if m_iso:
            y_str, m_str, d_str = m_iso.groups()
            month_num = cls.MONTH_MAP.get(m_str.lower(), f"{int(m_str):02d}" if m_str.isdigit() else "01")
            if d_str:
                day_num = f"{int(d_str):02d}"
                return f"{day_num}/{month_num}/{y_str}"
            return f"{month_num}/{y_str}"

        # Check for Numeric DD/MM/YYYY or DD-MM-YY (3 parts)
        m_num_3 = re.match(
            r'(0?[1-9]|[12][0-9]|3[01])[\/\-\.](0?[1-9]|1[0-2])[\/\-\.](20[2-3][0-9]|[2-3][0-9])',
            clean
        )
        if m_num_3:
            d_str, m_str, y_str = m_num_3.groups()
            day_num = f"{int(d_str):02d}"
            month_num = f"{int(m_str):02d}"
            year_num = f"20{y_str}" if len(y_str) == 2 else y_str
            return f"{day_num}/{month_num}/{year_num}"

        # Check for Numeric MM/YYYY or MM/YY (2 parts)
        m_num_2 = re.match(
            r'(0?[1-9]|1[0-2])[\/\-\.](20[2-3][0-9]|[2-3][0-9])',
            clean
        )
        if m_num_2:
            m_str, y_str = m_num_2.groups()
            month_num = f"{int(m_str):02d}"
            year_num = f"20{y_str}" if len(y_str) == 2 else y_str
            return f"{month_num}/{year_num}"

        return clean

    @classmethod
    def _extract_dates_from_string(cls, text: str) -> List[str]:
        # Strip plant code prefixes like (A), (05), (B), [A], etc.
        clean = re.sub(r'[\(\[]\s*[A-Za-z0-9]{1,3}\s*[\)\]]', ' ', text)
        matches = [m.group(0).strip() for m in cls.DATE_REGEX_PARSER.finditer(clean)]
        # Filter out standalone numbers and normalize
        valid = []
        for m in matches:
            clean_m = re.sub(r'\s+', ' ', m).strip(' ,.-;')
            if clean_m and len(clean_m) >= 4:
                normalized_val = cls.normalize_date_string(clean_m)
                valid.append(normalized_val)

        # Header-anchored partial date e.g. "EXP:16/12" or "EXP: 16/12" or "MFD: 17/06"
        if not valid:
            partial_m = re.search(r'(?:EXP|EXPIRY|USE\s*BY|BEST\s*BEFORE|MFD|MFG|PKD)[\s:\.\-]*([0-3]?[0-9][\/\-\.](?:0?[1-9]|1[0-2]))(?=[^\d]|$)', clean, re.IGNORECASE)
            if partial_m:
                p_date = partial_m.group(1).strip()
                if p_date and len(p_date) >= 3:
                    valid.append(p_date)

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

        # Helper to parse normalized date strings into comparable (year, month, day) tuples
        def parse_date_key(d_str: str) -> Tuple[int, int, int]:
            if not d_str:
                return (9999, 99, 99)
            parts = [int(p) for p in re.findall(r'\d+', d_str)]
            if len(parts) == 3:
                # DD/MM/YYYY
                return (parts[2], parts[1], parts[0])
            elif len(parts) == 2:
                # MM/YYYY
                return (parts[1], parts[0], 1)
            elif len(parts) == 1 and parts[0] > 1900:
                return (parts[0], 1, 1)
            return (9999, 99, 99)

        # Multi-Date Fallback & Disambiguation:
        # If we have multiple distinct dates on the label, resolve earlier -> Mfg Date and later -> Expiry Date
        all_candidate_dates: Dict[str, Dict[str, Any]] = {}
        for c in mfg_candidates + exp_candidates:
            v = c["normalized"]
            if v and v not in all_candidate_dates:
                all_candidate_dates[v] = c

        has_exp_header = any(cls.EXP_HEADER_REGEX.search(l.text) for l in lines)
        has_mfg_header = any(cls.MFG_HEADER_REGEX.search(l.text) for l in lines)

        # Collect distinct chronological dates
        distinct_dates = sorted(
            [d for d in all_candidate_dates.keys() if parse_date_key(d)[0] < 9999],
            key=parse_date_key
        )

        if len(distinct_dates) >= 2:
            earlier_val = distinct_dates[0]
            later_val = distinct_dates[-1]

            # If Expiry Date is missing or both picked the same date, assign chronologically
            if not exp_field or (mfg_field and mfg_field.normalized_value == exp_field.normalized_value):
                c_exp = all_candidate_dates[later_val]
                exp_field = ExtractedField(
                    field_name="expiry_date",
                    display_name="Expiry / Best Before Date",
                    raw_value=c_exp["raw"],
                    normalized_value=later_val,
                    confidence=min(0.99, round(c_exp["confidence"] * 0.95, 4)),
                    detection_method="OCR_CHRONOLOGICAL_PAIR_EXP",
                    bbox=c_exp["bbox"],
                    is_detected=True,
                    metadata={
                        "legal_rule": "Rule 6(1)(d) - Expiry / Best Before Declaration",
                        "source_strategy": "CHRONOLOGICAL_PAIR_EXP",
                        "all_candidates": [{"value": later_val, "raw": c_exp["raw"], "confidence": c_exp["confidence"]}]
                    }
                )

            # Ensure Mfg Date is assigned to the earlier date
            if not mfg_field or mfg_field.normalized_value == later_val:
                c_mfg = all_candidate_dates[earlier_val]
                mfg_field = ExtractedField(
                    field_name="mfg_date",
                    display_name="Date of Manufacture / Packing",
                    raw_value=c_mfg["raw"],
                    normalized_value=earlier_val,
                    confidence=min(0.99, round(c_mfg["confidence"] * 0.95, 4)),
                    detection_method="OCR_CHRONOLOGICAL_PAIR_MFG",
                    bbox=c_mfg["bbox"],
                    is_detected=True,
                    metadata={
                        "legal_rule": "Rule 6(1)(d) - Month and Year of Manufacture/Packing",
                        "source_strategy": "CHRONOLOGICAL_PAIR_MFG",
                        "all_candidates": [{"value": earlier_val, "raw": c_mfg["raw"], "confidence": c_mfg["confidence"]}]
                    }
                )

        # Year completion for partial expiry dates (e.g., "16/12" where day/month without year)
        if exp_field and exp_field.normalized_value and mfg_field and mfg_field.normalized_value:
            exp_parts = [int(p) for p in re.findall(r'\d+', exp_field.normalized_value)]
            mfg_parts = [int(p) for p in re.findall(r'\d+', mfg_field.normalized_value)]
            # Only complete if exp_parts is Day/Month (both <= 31 and month <= 12, not MM/YYYY)
            if len(exp_parts) == 2 and exp_parts[0] <= 31 and exp_parts[1] <= 12 and len(mfg_parts) in (2, 3):
                mfg_year = mfg_parts[-1]
                if mfg_year < 100:
                    mfg_year += 2000
                mfg_month = mfg_parts[1] if len(mfg_parts) == 3 else mfg_parts[0]
                exp_day = exp_parts[0]
                exp_month = exp_parts[1]
                exp_year = mfg_year if exp_month >= mfg_month else mfg_year + 1
                exp_field.normalized_value = f"{exp_day:02d}/{exp_month:02d}/{exp_year}"

        return mfg_field, exp_field

    @classmethod
    def extract_mfg_date(cls, lines: List[OCRLine]) -> Optional[ExtractedField]:
        mfg_field, _ = cls.extract_all_dates(lines)
        return mfg_field

    @classmethod
    def extract_expiry_date(cls, lines: List[OCRLine]) -> Optional[ExtractedField]:
        _, exp_field = cls.extract_all_dates(lines)
        return exp_field

    @classmethod
    def validate_date_consistency(
        cls,
        mfg_date_input: Optional[Any],
        expiry_date_input: Optional[Any]
    ) -> "DateConsistencyResult":
        """
        Validates dual-date chronological consistency between Manufacturing/Packing Date
        and Expiry / Best Before date.
        Accepts either string dates (e.g. "01/2026") or ExtractedField objects.
        Returns a rich DateConsistencyResult with: is_valid (bool), status ("PASS" | "FAIL" | "REVIEW"), explanation (str).
        """
        mfg_date_str = mfg_date_input.normalized_value if isinstance(mfg_date_input, ExtractedField) else (str(mfg_date_input) if mfg_date_input else None)
        expiry_date_str = expiry_date_input.normalized_value if isinstance(expiry_date_input, ExtractedField) else (str(expiry_date_input) if expiry_date_input else None)

        if not mfg_date_str or not expiry_date_str:
            return DateConsistencyResult(
                is_valid=True,
                status="PASS" if mfg_date_str else "REVIEW",
                explanation="Single date declaration provided. Dual-date consistency check not applicable."
            )

        def parse_date_tuple(d_str: str) -> Optional[Tuple[int, int, int]]:
            nums = [int(n) for n in re.findall(r'\d+', d_str)]
            if len(nums) == 3:
                d, m, y = nums[0], nums[1], nums[2]
                if y < 100: y += 2000
                return (y, m, d)
            elif len(nums) == 2:
                m, y = nums[0], nums[1]
                if y < 100: y += 2000
                return (y, m, 1)
            return None

        mfg_tuple = parse_date_tuple(mfg_date_str)
        exp_tuple = parse_date_tuple(expiry_date_str)

        if not mfg_tuple or not exp_tuple:
            return DateConsistencyResult(
                is_valid=True,
                status="REVIEW",
                explanation="Date format contains non-standard text/relative declaration; manual verification recommended."
            )

        # Compare year, month, day: Expiry date must not precede Manufacturing date
        if exp_tuple < mfg_tuple:
            return DateConsistencyResult(
                is_valid=False,
                status="FAIL",
                explanation=f"Inconsistent date sequence: Expiry/Best Before ({expiry_date_str}) precedes or matches preceding Manufacturing Date ({mfg_date_str})."
            )

        # Calculate approximate month difference
        months_diff = (exp_tuple[0] - mfg_tuple[0]) * 12 + (exp_tuple[1] - mfg_tuple[1])
        if months_diff > 120:  # >10 years
            return DateConsistencyResult(
                is_valid=True,
                status="REVIEW",
                explanation=f"Shelf life of {months_diff} months ({months_diff//12} years) is unusually long; inspector verification advised."
            )

        return DateConsistencyResult(
            is_valid=True,
            status="PASS",
            explanation=f"Dual-date consistency verified: Expiry ({expiry_date_str}) correctly follows Manufacturing Date ({mfg_date_str})."
        )


class DateConsistencyResult(dict):
    """Rich result object supporting dict access, attribute access, and tuple unpacking (is_valid, msg)."""
    def __init__(self, is_valid: bool, status: str, explanation: str):
        super().__init__(is_valid=is_valid, status=status, explanation=explanation)
        self.is_valid = is_valid
        self.status = status
        self.explanation = explanation

    def __iter__(self):
        yield self.is_valid
        yield self.explanation

    def __bool__(self):
        return self.is_valid


