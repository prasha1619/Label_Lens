import re
from typing import Optional, List, Dict, Any
from app.schemas.extraction import ExtractedField
from app.schemas.ocr import OCRLine

class MRPExtractor:
    """
    State-of-the-Art Maximum Retail Price (MRP) extractor for Legal Metrology Rule 6(1)(e).
    Capabilities:
    1. Robust OCR-noise-tolerant header matching (MRP, M.R.P., MaP, Mape, MaP=, MBP, MPP, Max Retail Price, Price, Rate)
    2. Tax phrases interposed between header and price (e.g., 'MRP (incl. of all taxes) : Rs. 249.00')
    3. Multi-line vertical neighborhood scanning (Header on Line N, Price on Line N+1 / N+2)
    4. 2-D spatial bounding-box alignment for 2-column dot-matrix/inkjet label tables
    5. Unit Sale Price (USP) disambiguation (e.g., differentiates total MRP from USP per ml/g)
    6. Fuzzy tax inclusivity recognition (incl. of all taxes, inclelelltaned, und 01 ionod, all taxes incl)
    7. Standalone currency with price fallback (e.g. 'Rs. 249.00', '₹ 249')
    """

    # MRP header regex (handles OCR substitutions & noise: 'MaP', 'Mape', 'MaP=', 'MBP', 'MPP', 'M.R.P.', 'MR P', etc.)
    MRP_HEADER_REGEX = re.compile(
        r'(?:'
        r'\b(?:M\.?R\.?P\.?|M\.?A\.?P\.?|M\.?P\.?P\.?|M\.?B\.?P\.?|M\s*R\s*P|M\s*A\s*P|MAX(?:IMUM)?\s*RETAIL\s*PRICE|RETAIL\s*PRICE|SALE\s*PRICE|PRICE|RATE)\b|'
        r'\b(?:Mape|MaP=|Map|MRF|MRA|NRP|WRP)\b|'
        r'M\.?R\.?P[\s:\.\-=e,\(\)]+|Mape|MaP='
        r')',
        re.IGNORECASE
    )

    # Unit sale price header regex (USP per ml/g/kg/unit)
    USP_HEADER_REGEX = re.compile(
        r'(?:\bUSP\b|UNIT\s*SALE\s*PRICE|USP\s*(?:PER|POR|/)|PER\s*(?:ML|GM|G|KG|L|LTR|N|UNIT|PIECE)|POR\s*ML|PERML)',
        re.IGNORECASE
    )

    # Tax inclusivity fuzzy patterns (handles standard declarations and noisy OCR artifacts)
    TAX_INCLUSIVE_PATTERNS = [
        re.compile(r'(?:INCL\.?|INCLUSIVE|INCLD|INCI|INCT|UNCT|UNCL|ICL|NCL|ONCI|ONCL)[\s\w\.\(\)]*(?:OF\s*)?(?:ALL\s*)?(?:TAX|TARES|TANOB|TAXES|TARED|TAND|TANED)', re.IGNORECASE),
        re.compile(r'(?:INCL|ONCI|INCI)\.?\s*(?:OF\s*)?(?:ALL\s*)?TAX', re.IGNORECASE),
        re.compile(r'INCLUSIVE\s*(?:OF\s*)?(?:ALL\s*)?TAX', re.IGNORECASE),
        re.compile(r'ALL\s*TAXES?\s*INCL', re.IGNORECASE),
        re.compile(r'TAXES?\s*INCL', re.IGNORECASE),
        re.compile(r'ELELLTANED|IONOD|DDTUES', re.IGNORECASE)
    ]

    # Currency symbols & prefixes
    CURRENCY_PREFIX_REGEX = re.compile(
        r'(?:\b(?:RS|INR|RE)\.?|[₹`\*\?])\s*',
        re.IGNORECASE
    )

    @classmethod
    def _is_tax_inclusive(cls, text: str) -> bool:
        for p in cls.TAX_INCLUSIVE_PATTERNS:
            if p.search(text):
                return True
        return False

    @classmethod
    def _clean_price_text(cls, text: str) -> str:
        # Standardize decimal spacing e.g., "249. 00" -> "249.00", "249 , 00" -> "249.00"
        clean = re.sub(r'(\d+)\s*[\.]\s*(\d{2})\b', r'\1.\2', text)
        clean = re.sub(r'(\d+)\s*[,]\s*(\d{2})\b', r'\1.\2', clean)
        # Remove trailing /- e.g. "249/-" -> "249"
        clean = re.sub(r'(\d+)\s*\/[-–]', r'\1', clean)
        return clean

    @classmethod
    def _is_plausible_price(cls, val: float, text: str, is_near_mrp_header: bool = False) -> bool:
        if val <= 0.5 or val > 50000:
            return False
        # Filter out numbers preceded by No./Art/Batch/Code/Item
        if re.search(rf'(?:NO|ART|ITEM|BATCH|LOT|CODE|REF|MODEL)[\s:\.\-]*0*{int(val)}', text, re.IGNORECASE):
            return False
        # Filter out 4-digit calendar years unless explicitly prefixed by currency / MRP
        if val in [2020, 2021, 2022, 2023, 2024, 2025, 2026, 2027, 2028, 2029, 2030, 2031]:
            if not is_near_mrp_header and not any(c in text.upper() for c in ["RS", "₹", "INR", "MRP", "MAP"]):
                return False
        # Filter out 5-6 digit pin codes or product codes unless currency is attached
        if val >= 10000 and val.is_integer():
            if not any(c in text.upper() for c in ["RS", "₹", "INR", "MRP"]):
                return False
        return True

    @classmethod
    def _extract_prices_from_line(cls, text: str) -> List[Dict[str, Any]]:
        """Extracts candidate numeric price values from a string."""
        clean = cls._clean_price_text(text)
        candidates = []

        # 1. Match numbers with currency prefix: e.g. "Rs. 249.00", "₹ 249", "INR 350"
        curr_pattern = re.compile(
            r'(?:\b(?:RS|INR|RE)\.?|[₹`\*\?])\s*([0-9]{1,6}(?:\.[0-9]{1,2})?)',
            re.IGNORECASE
        )
        for m in curr_pattern.finditer(clean):
            try:
                p_val = float(m.group(1))
                if cls._is_plausible_price(p_val, text, is_near_mrp_header=True):
                    candidates.append({"price": p_val, "has_currency": True, "span": m.span()})
            except ValueError:
                pass

        # 1B. Match combined MRP + USP e.g. "2502.50/ml" -> MRP 250, USP 2.50/ml
        combined_mrp_usp = re.search(r'\b([0-9]{2,5})\s*([0-9]+(?:\.[0-9]{1,2})?)\s*/\s*(?:ml|g|gm|kg|l|ltr|n|unit|piece)\b', clean, re.IGNORECASE)
        if combined_mrp_usp:
            try:
                p_val = float(combined_mrp_usp.group(1))
                if cls._is_plausible_price(p_val, text, is_near_mrp_header=True):
                    candidates.append({
                        "price": p_val,
                        "has_currency": False,
                        "span": combined_mrp_usp.span(),
                        "usp": combined_mrp_usp.group(2)
                    })
            except ValueError:
                pass

        # 2. Match standalone numbers: e.g. "249.00", "350", "99" (exclude dates, times, units)
        num_pattern = re.compile(r'(?<![\/\-\:\.0-9])([0-9]{1,5}(?:\.[0-9]{1,2})?)(?![\/\-\:\.0-9]|\s*(?:ml|g|gm|kg|l|ltr|pcs|units|n|u|months?|years?|days?|cm|mm|m)\b)', re.IGNORECASE)
        for m in num_pattern.finditer(clean):
            try:
                p_val = float(m.group(1))
                if cls._is_plausible_price(p_val, text, is_near_mrp_header=False):
                    if not any(abs(c["price"] - p_val) < 0.001 for c in candidates):
                        candidates.append({"price": p_val, "has_currency": False, "span": m.span()})
            except ValueError:
                pass

        return candidates

    @classmethod
    def _vertical_overlap(cls, bbox1: List[int], bbox2: List[int]) -> float:
        """Returns vertical overlap ratio between two bounding boxes."""
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
        if not lines:
            return None

        candidates: List[Dict[str, Any]] = []
        full_text_combined = " ".join(l.text for l in lines)
        global_has_tax = cls._is_tax_inclusive(full_text_combined)

        # Strategy 1: Flexible Single-line pattern
        # Handles cases where tax text or words are placed between MRP and price:
        # e.g., "MRP (Incl. of all taxes) Rs. 249.00", "MRP: Rs. 249.00 (Incl. of all taxes)"
        for idx, line in enumerate(lines):
            text = line.text.strip()
            if cls.MRP_HEADER_REGEX.search(text):
                prices = cls._extract_prices_from_line(text)
                for p_info in prices:
                    p_val = p_info["price"]
                    has_tax = cls._is_tax_inclusive(text) or global_has_tax
                    candidates.append({
                        "price": p_val,
                        "raw_value": text,
                        "confidence": min(0.99, round(line.confidence * 1.0, 4)),
                        "bbox": line.bbox,
                        "has_tax": has_tax,
                        "has_currency": p_info["has_currency"],
                        "source": "SINGLE_LINE_HEADER"
                    })

        # Strategy 2: Multi-Line Vertical Stack & Spatial 2-Column Scanning
        for idx, line in enumerate(lines):
            text = line.text.strip()
            if cls.MRP_HEADER_REGEX.search(text):
                header_bbox = line.bbox
                h_center_y = (header_bbox[1] + header_bbox[3]) / 2.0 if len(header_bbox) == 4 else 0
                h_height = max(1, header_bbox[3] - header_bbox[1]) if len(header_bbox) == 4 else 20

                # 2A: Scan adjacent lines vertically (e.g., next 1 to 7 lines below in 2-column or list layout)
                for offset in range(1, 8):
                    if idx + offset < len(lines):
                        next_line = lines[idx + offset]
                        next_text = next_line.text.strip()

                        prices = cls._extract_prices_from_line(next_text)
                        for p_info in prices:
                            p_val = p_info["price"]
                            combined_raw = f"{text} {next_text}"
                            has_tax = cls._is_tax_inclusive(combined_raw) or global_has_tax

                            combined_bbox = [
                                min(header_bbox[0], next_line.bbox[0]),
                                min(header_bbox[1], next_line.bbox[1]),
                                max(header_bbox[2], next_line.bbox[2]),
                                max(header_bbox[3], next_line.bbox[3]),
                            ] if (len(header_bbox) == 4 and len(next_line.bbox) == 4) else header_bbox

                            mean_conf = (line.confidence + next_line.confidence) / 2.0
                            # Weight decays slightly with vertical line distance
                            dist_decay = 0.96 if offset == 1 else (0.90 if offset == 2 else 0.82)

                            candidates.append({
                                "price": p_val,
                                "raw_value": combined_raw,
                                "confidence": min(0.99, round(mean_conf * dist_decay, 4)),
                                "bbox": combined_bbox,
                                "has_tax": has_tax,
                                "has_currency": p_info["has_currency"],
                                "source": "VERTICAL_STACKED"
                            })

                # 2B: Scan for 2-column horizontal row pairing
                for other_idx, other_line in enumerate(lines):
                    if other_idx == idx:
                        continue
                    other_text = other_line.text.strip()
                    if cls.USP_HEADER_REGEX.search(other_text):
                        continue

                    other_bbox = other_line.bbox
                    if len(header_bbox) == 4 and len(other_bbox) == 4:
                        o_center_y = (other_bbox[1] + other_bbox[3]) / 2.0
                        overlap = cls._vertical_overlap(header_bbox, other_bbox)
                        y_dist = abs(h_center_y - o_center_y)

                        is_same_row = (overlap > 0.30) or (y_dist <= h_height * 0.85)
                        is_to_right = other_bbox[0] >= header_bbox[0] - 20

                        if is_same_row and is_to_right:
                            prices = cls._extract_prices_from_line(other_text)
                            for p_info in prices:
                                p_val = p_info["price"]
                                combined_raw = f"{text} {other_text}"
                                has_tax = cls._is_tax_inclusive(combined_raw) or global_has_tax
                                combined_bbox = [
                                    min(header_bbox[0], other_bbox[0]),
                                    min(header_bbox[1], other_bbox[1]),
                                    max(header_bbox[2], other_bbox[2]),
                                    max(header_bbox[3], other_bbox[3]),
                                ]
                                mean_conf = (line.confidence + other_line.confidence) / 2.0
                                candidates.append({
                                    "price": p_val,
                                    "raw_value": combined_raw,
                                    "confidence": min(0.99, round(mean_conf * 0.98, 4)),
                                    "bbox": combined_bbox,
                                    "has_tax": has_tax,
                                    "has_currency": p_info["has_currency"],
                                    "source": "SPATIAL_2_COLUMN"
                                })

        # Strategy 3: Currency Symbols Fallback (e.g., "₹ 249.00", "Rs. 249.00")
        for idx, line in enumerate(lines):
            text = line.text.strip()
            if cls.CURRENCY_PREFIX_REGEX.search(text) and not cls.USP_HEADER_REGEX.search(text):
                prices = cls._extract_prices_from_line(text)
                for p_info in prices:
                    if p_info["has_currency"]:
                        p_val = p_info["price"]
                        has_tax = cls._is_tax_inclusive(text) or global_has_tax
                        candidates.append({
                            "price": p_val,
                            "raw_value": text,
                            "confidence": min(0.99, round(line.confidence * 0.90, 4)),
                            "bbox": line.bbox,
                            "has_tax": has_tax,
                            "has_currency": True,
                            "source": "CURRENCY_SYMBOL"
                        })

        # Strategy 4: structured declaration-table fallback. Some labels print a faint
        # MRP caption beside a clear price; OCR may lose the caption entirely. Treat a
        # price as MRP only when it occupies the row immediately above a recognised USP
        # row in the same two-column declaration table. This avoids accepting arbitrary
        # standalone numbers elsewhere on the label.
        for idx, price_line in enumerate(lines):
            if cls.USP_HEADER_REGEX.search(price_line.text):
                continue
            prices = [p for p in cls._extract_prices_from_line(price_line.text) if not p["has_currency"]]
            if not prices or len(price_line.bbox) != 4:
                continue

            for next_idx in range(idx + 1, min(idx + 4, len(lines))):
                usp_line = lines[next_idx]
                if not cls.USP_HEADER_REGEX.search(usp_line.text) or len(usp_line.bbox) != 4:
                    continue
                # A caption/value table has a short vertical distance and price value to
                # the right of the caption. The MRP value should exceed the USP value.
                row_gap = usp_line.bbox[1] - price_line.bbox[3]
                if row_gap < -8 or row_gap > max(80, (price_line.bbox[3] - price_line.bbox[1]) * 3):
                    continue
                usp_prices = cls._extract_prices_from_line(usp_line.text)
                for price_info in prices:
                    if price_line.bbox[0] <= usp_line.bbox[0] + 20:
                        continue
                    if usp_prices and price_info["price"] <= max(p["price"] for p in usp_prices):
                        continue
                    candidates.append({
                        "price": price_info["price"],
                        "raw_value": f"MRP table row: {price_line.text}; USP context: {usp_line.text}",
                        "confidence": min(0.80, round(price_line.confidence * 0.78, 4)),
                        "bbox": price_line.bbox,
                        "has_tax": global_has_tax,
                        "has_currency": False,
                        "source": "TABLE_POSITIONAL_MRP"
                    })

        if not candidates:
            return None

        # Prioritize and disambiguate candidates
        def score_candidate(c: Dict[str, Any]) -> float:
            score = c["confidence"]
            if c["source"] == "SINGLE_LINE_HEADER":
                score += 0.30
            elif c["source"] == "VERTICAL_STACKED":
                score += 0.25
            elif c["source"] == "SPATIAL_2_COLUMN":
                score += 0.20
            elif c["source"] == "CURRENCY_SYMBOL":
                score += 0.15
            elif c["source"] == "TABLE_POSITIONAL_MRP":
                score += 0.10

            if c.get("has_currency"):
                score += 0.10
            if c.get("usp"):
                score += 0.35
            if c.get("has_tax"):
                score += 0.05

            # Total retail price is typically greater than per-unit sale price
            if c["price"] >= 10.0:
                score += 0.05

            return score

        candidates.sort(key=score_candidate, reverse=True)
        best = candidates[0]

        price_float = best["price"]
        normalized_val = f"₹{price_float:g}" if price_float.is_integer() else f"₹{price_float:.2f}"

        return ExtractedField(
            field_name="mrp",
            display_name="Maximum Retail Price (MRP)",
            raw_value=best["raw_value"],
            normalized_value=normalized_val,
            unit="INR",
            confidence=best["confidence"],
            detection_method=f"OCR_{best['source']}",
            bbox=best["bbox"],
            is_detected=True,
            metadata={
                "numeric_price": price_float,
                "has_tax_inclusive": best["has_tax"],
                "source_strategy": best["source"],
                "legal_rule": "Rule 6(1)(e) - Retail Sale Price Declaration",
                "all_candidates": [
                    {"price": c["price"], "raw": c["raw_value"], "confidence": c["confidence"]}
                    for c in candidates[:5]
                ]
            }
        )
