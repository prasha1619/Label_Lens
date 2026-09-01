import re
from typing import Optional, List, Dict, Any
from app.schemas.extraction import ExtractedField
from app.schemas.ocr import OCRLine

class EntityExtractor:
    """
    Extracts Manufacturer, Packer, Importer, Country of Origin, and Generic Commodity Names.
    Complies with Legal Metrology (PC) Rules, Rule 6(1)(a), 6(1)(b) & Rule 6(10).
    """

    MFG_PATTERNS = [
        re.compile(r'(?:MFD|MANUFACTURED|MFG)\.?\s*(?:IN\s*INDIA\s*)?(?:AND\s*PACKED\s*)?(?:BY|FOR|:)\s*([A-Z0-9\s,\.\-&()]{3,100})', re.IGNORECASE),
        re.compile(r'MARKETED\s*(?:AND\s*TRADEMARK\s*OWNED\s*)?(?:BY|FOR|:)\s*([A-Z0-9\s,\.\-&()]{3,100})', re.IGNORECASE)
    ]

    COMPANY_SUFFIX_PATTERN = re.compile(
        r'\b(?:PVT\.?\s*LTD\.?|PRIVATE\s*LIMITED|LTD\.?|LIMITED|CORP(?:ORATION)?|INC\.?|INDUSTRIES|ENTERPRISES|LABORATORIES|PRODUCTS|FORMULATIONS|FOODS|BAKES|COSMETICS|CARE|AG|GMBH)\b',
        re.IGNORECASE
    )

    PROMINENT_MFR_PATTERN = re.compile(
        r'\b(?:BEIERSDORF|NIVEA|UNILEVER|HUL|PROCTER|GAMBLE|P&G|DABUR|PATANJALI|ITC|NESTLE|AMUL|MARICO|EMAMI|GODREJ|COLGATE|PALMOLIVE|RECKITT|BENCKISER|LOREAL|L\'OREAL|JOHNSON|CADBURY|BRITANNIA|PARLE|HALDIRAM|MCNROE|WIPRO|HIMALAYA)\b',
        re.IGNORECASE
    )

    PACKER_PATTERNS = [
        re.compile(r'(?:PACKED|PKD)\.?\s*(?:BY)?[\s:\.]*([A-Z0-9\s,\.\-&()]{3,100})', re.IGNORECASE)
    ]

    IMPORTER_PATTERNS = [
        re.compile(r'(?:IMPORTED|IMPORT)\.?\s*(?:BY)?[\s:\.]*([A-Z0-9\s,\.\-&()]{3,100})', re.IGNORECASE)
    ]

    ORIGIN_PATTERNS = [
        re.compile(r'(?:COUNTRY\s*OF\s*ORIGIN|MADE\s*IN|PRODUCT\s*OF)[\s:\.]*([A-Z\s]{3,30})', re.IGNORECASE)
    ]

    GENERIC_NAMES = [
        "SHAMPOO", "HAIR OIL", "SOAP", "BISCUITS", "COOKIES", "NOODLES", "EDIBLE OIL", 
        "MUSTARD OIL", "SUNFLOWER OIL", "WHEAT FLOUR", "ATTA", "RICE", "TEA", "COFFEE",
        "DETERGENT", "TOOTHPASTE", "HAND WASH", "FACE CREAM", "MOISTURIZER", "BATTERY",
        "POWER BANK", "CHARGER", "LED BULB", "CABLE", "HEADPHONES", "TABLETS", "CAPSULES",
        "PERFUME", "EAU DE PARFUM", "DEODORANT", "BODY SPRAY", "ROOM FRESHENER"
    ]

    @classmethod
    def extract_manufacturer(cls, lines: List[OCRLine]) -> Optional[ExtractedField]:
        best_candidate: Optional[Dict[str, Any]] = None

        for idx, line in enumerate(lines):
            text = line.text.strip()
            
            # Check direct pattern match on current line
            for pattern in cls.MFG_PATTERNS:
                match = pattern.search(text)
                if match:
                    raw_entity = match.group(1).strip()
                    entity_str = raw_entity
                    bbox = list(line.bbox) if len(line.bbox) == 4 else [0, 0, 100, 100]

                    # If line is a reference header like "MANUFACTURED IN INDIA BY : READ THE FIRST CHARACTER OF THE MFD."
                    # scan following lines for the actual entity names (e.g. "(A) McNROE CONSUMER PRODUCTS PVT. LTD...")
                    if "READ THE FIRST CHARACTER" in text.upper() or len(entity_str) < 15:
                        for offset in range(1, 4):
                            if idx + offset < len(lines):
                                next_line = lines[idx + offset]
                                n_text = next_line.text.strip()
                                if cls.COMPANY_SUFFIX_PATTERN.search(n_text) or any(term in n_text.upper() for term in ["LTD", "PVT", "ROAD", "PLOT", "SECTOR", "ESTATE"]):
                                    entity_str = n_text
                                    if len(next_line.bbox) == 4:
                                        bbox[2] = max(bbox[2], next_line.bbox[2])
                                        bbox[3] = max(bbox[3], next_line.bbox[3])
                                    break
                    else:
                        # Append address from next line if it continues with address cues
                        if idx + 1 < len(lines):
                            next_line = lines[idx + 1]
                            n_text = next_line.text.strip()
                            if any(term in n_text.upper() for term in ["ROAD", "NAGAR", "IND", "PLOT", "SECTOR", "STATE", "PIN", "ESTATE", "DIST"]):
                                entity_str += f", {n_text}"
                                if len(next_line.bbox) == 4:
                                    bbox[2] = max(bbox[2], next_line.bbox[2])
                                    bbox[3] = max(bbox[3], next_line.bbox[3])

                    clean_norm = re.sub(r'^(?:IN\s*INDIA\s*BY[\s:\.]*|\(A\)|\(B\)|\(C\))\s*', '', entity_str, flags=re.IGNORECASE).strip()
                    conf = min(0.98, round(line.confidence * 0.92, 4))

                    if best_candidate is None or conf > best_candidate["confidence"]:
                        best_candidate = {
                            "raw": text,
                            "normalized": clean_norm if len(clean_norm) > 4 else entity_str,
                            "confidence": conf,
                            "bbox": bbox
                        }

        # Fallback: scan for any prominent line containing company suffixes like PVT LTD or known manufacturer brands
        if not best_candidate:
            for idx, line in enumerate(lines):
                text = line.text.strip()
                if cls.COMPANY_SUFFIX_PATTERN.search(text) or cls.PROMINENT_MFR_PATTERN.search(text):
                    # Combine adjacent address line if present (e.g. Beiersdorf Hamburg)
                    combined_text = text
                    if idx + 1 < len(lines):
                        next_t = lines[idx + 1].text.strip()
                        if any(c in next_t.upper() for c in ["HAMBURG", "MUMBAI", "DELHI", "ROAD", "LTD", "PVT", "INDIA", "GERMANY", "P.O."]):
                            combined_text = f"{text}, {next_t}"
                    best_candidate = {
                        "raw": combined_text,
                        "normalized": combined_text,
                        "confidence": min(0.95, round(line.confidence * 0.90, 4)),
                        "bbox": line.bbox
                    }
                    break

        if best_candidate:
            return ExtractedField(
                field_name="manufacturer",
                display_name="Manufacturer / Packer Details",
                raw_value=best_candidate["raw"],
                normalized_value=best_candidate["normalized"],
                confidence=best_candidate["confidence"],
                detection_method="OCR_REGEX",
                bbox=best_candidate["bbox"],
                is_detected=True,
                metadata={"legal_rule": "Rule 6(1)(b) - Name and Address of Manufacturer/Packer"}
            )

        return None

    @classmethod
    def extract_country_of_origin(cls, lines: List[OCRLine]) -> Optional[ExtractedField]:
        for line in lines:
            text = line.text.strip()
            for pattern in cls.ORIGIN_PATTERNS:
                match = pattern.search(text)
                if match:
                    raw_c = match.group(1).strip()
                    # Clean up common noise e.g. "INDUA" -> "India", "INDIA;" -> "India"
                    clean_c = re.sub(r'[^A-Za-z]', '', raw_c).title()
                    if "Ind" in clean_c:
                        clean_c = "India"
                    return ExtractedField(
                        field_name="country_of_origin",
                        display_name="Country of Origin",
                        raw_value=text,
                        normalized_value=clean_c,
                        confidence=min(0.98, round(line.confidence * 0.95, 4)),
                        detection_method="OCR_REGEX",
                        bbox=line.bbox,
                        is_detected=True,
                        metadata={"legal_rule": "Rule 6(10) - Country of Origin on Imported/Packaged Goods"}
                    )
        return None

    GENERIC_NAME_HEADER_REGEX = re.compile(
        r'(?:GENERIC\s*NAME|COMMON\s*NAME|NAME\s*OF\s*(?:THE\s*)?COMMODITY|PRODUCT\s*NAME|COMMODITY)[\s:\.\-]*([A-Z0-9\s,\.\-&()]{2,60})',
        re.IGNORECASE
    )

    @classmethod
    def extract_generic_name(cls, lines: List[OCRLine]) -> Optional[ExtractedField]:
        # Priority 1: Explicit "Generic Name: ..." / "Commodity: ..." declaration
        for line in lines:
            text = line.text.strip()
            m = cls.GENERIC_NAME_HEADER_REGEX.search(text)
            if m:
                val = m.group(1).strip()
                if len(val) >= 2:
                    return ExtractedField(
                        field_name="product_name",
                        display_name="Generic Name / Product Description",
                        raw_value=text,
                        normalized_value=val.title(),
                        confidence=min(0.99, round(line.confidence * 0.98, 4)),
                        detection_method="OCR_EXPLICIT_HEADER",
                        bbox=line.bbox,
                        is_detected=True,
                        metadata={"legal_rule": "Rule 6(1)(a) - Common or Generic Name of Commodity"}
                    )

        # Priority 2: Standalone or clean short lines matching product taxonomy
        for line in lines:
            text = line.text.strip().upper()
            # Skip ingredients / caution / legal paragraphs
            if any(term in text for term in ["INGREDIENT", "ALCOHOL", "CAUTION", "HARMFUL", "%", "STORE AT"]):
                continue

            for name in cls.GENERIC_NAMES:
                if name in text and len(text) <= 50:
                    return ExtractedField(
                        field_name="product_name",
                        display_name="Generic Name / Product Description",
                        raw_value=line.text.strip(),
                        normalized_value=line.text.strip().title(),
                        confidence=min(0.98, round(line.confidence * 0.92, 4)),
                        detection_method="TAXONOMY_MATCH",
                        bbox=line.bbox,
                        is_detected=True,
                        metadata={"legal_rule": "Rule 6(1)(a) - Common or Generic Name of Commodity"}
                    )

        # Priority 3: Fallback to prominent top branding line
        if lines:
            for candidate_line in lines[:5]:
                c_text = candidate_line.text.strip()
                if len(c_text) >= 3 and not any(term in c_text.upper() for term in ["MRP", "MFD", "EXP", "BATCH", "INGREDIENT", "%", "NET", "PVT", "LTD"]):
                    return ExtractedField(
                        field_name="product_name",
                        display_name="Generic Name / Product Description",
                        raw_value=c_text,
                        normalized_value=c_text.title(),
                        confidence=round(candidate_line.confidence * 0.75, 4),
                        detection_method="HEURISTIC_TOP_LINE",
                        bbox=candidate_line.bbox,
                        is_detected=True,
                        metadata={"legal_rule": "Rule 6(1)(a) - Common or Generic Name"}
                    )

        return None

