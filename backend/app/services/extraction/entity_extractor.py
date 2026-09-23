import re
from typing import Optional, List, Dict, Any
from app.schemas.extraction import ExtractedField
from app.schemas.ocr import OCRLine

class EntityExtractor:
    """
    Extracts Manufacturer, Packer, Importer, Country of Origin, and Generic Commodity Names.
    Complies with Legal Metrology (PC) Rules, Rule 6(1)(a), 6(1)(b) & Rule 6(10).
    """

    # Strict header regex requiring 'BY', 'FOR', or full 'MANUFACTURED / PACKED / MARKETED :'
    # Note: bare 'MFD :' or 'MFG :' is excluded because that is standard manufacture date notation.
    MFG_HEADER_REGEX = re.compile(
        r'(?:'
        r'\b(?:MANUFACTURED|MFD|MFG|PRODUCED|PACKED|PKD|PKGD|MARKETED|MKTD)\b'
        r'(?:\s*(?:IN\s*INDIA|[&/+]|AND|TRADEMARK\s*OWNED)\s*(?:MARKETED|PACKED|PKD|MFD|MANUFACTURED|MFG|DISTRIBUTED|IMPORTED))?'
        r'\s*(?:BY|FOR)\b|'
        r'\b(?:MANUFACTURED|PACKED|MARKETED|PRODUCED)\s*(?:IN\s*INDIA)?\s*:|'
        r'(?:द्वारा\s*निर्मित|निर्माता|द्वारा\s*पैक्ड|पैकर|विपणक|उत्पादक)[\s:\.\-]*'
        r')',
        re.IGNORECASE
    )

    COMPANY_SUFFIX_PATTERN = re.compile(
        r'\b(?:PVT\.?\s*LTD\.?|PRIVATE\s*LIMITED|LTD\.?|LIMITED|CORP(?:ORATION)?|INC\.?|INDUSTRIES|ENTERPRISES|LABORATORIES|PRODUCTS|FORMULATIONS|BAKES|COSMETICS|AG|GMBH|प्रा\.?\s*लि\.?|प्राइवेट\s*लिमिटेड|लिमिटेड|उद्योग)\b',
        re.IGNORECASE
    )

    PROMINENT_MFR_PATTERN = re.compile(
        r'\b(?:BEIERSDORF|NIVEA|UNILEVER|HUL|PROCTER|GAMBLE|P&G|DABUR|PATANJALI|ITC|NESTLE|AMUL|MARICO|EMAMI|GODREJ|COLGATE|PALMOLIVE|RECKITT|BENCKISER|LOREAL|L\'OREAL|JOHNSON|CADBURY|BRITANNIA|PARLE|HALDIRAM|MCNROE|WIPRO|HIMALAYA|FASTFOOD|डाबर|पतंजलि|अमूल|नेस्ले|ब्रिटानिया|पारले|हल्दीराम)\b',
        re.IGNORECASE
    )

    ALLERGEN_OR_NON_COMPANY_WORDS = [
        "CONTAINING", "CONTAINS", "PROCESSED ON", "EQUIPMENT", "FACILITY", "ALLERGEN",
        "WHEAT", "PEANUT", "PEANUTS", "TREE NUT", "SOY", "MILK", "GLUTEN", "SESAME",
        "STORAGE", "KEEP IN", "DRY PLACE", "STORE IN", "COOL & DRY", "INGREDIENTS",
        "NUTRITIONAL", "SERVED", "RECIPE", "BEST BEFORE", "EXPIRY", "BATCH NO",
        "LIC. NO", "FSSAI", "FOR FEEDBACK", "HELPLINE", "CUSTOMER CARE"
    ]

    DATE_LIKE_REGEX = re.compile(r'^\s*(?:[0-3]?[0-9][\/\-\.\s]+)?(?:0[1-9]|1[0-2]|[A-Z]{3,9})[\/\-\.\s]+(?:20[2-3][0-9]|[2-3][0-9])\b', re.IGNORECASE)

    PACKER_PATTERNS = [
        re.compile(r'(?:PACKED|PKD)\.?\s*(?:BY)?[\s:\.]*([A-Z0-9\s,\.\-&()\u0900-\u097F]{3,100})', re.IGNORECASE),
        re.compile(r'(?:पैकर|द्वारा\s*पैक्ड)[\s:\.]*([A-Z0-9\s,\.\-&()\u0900-\u097F]{3,100})', re.IGNORECASE)
    ]

    IMPORTER_PATTERNS = [
        re.compile(r'(?:IMPORTED|IMPORT)\.?\s*(?:BY)?[\s:\.]*([A-Z0-9\s,\.\-&()\u0900-\u097F]{3,100})', re.IGNORECASE),
        re.compile(r'(?:आयातक|द्वारा\s*आयातित)[\s:\.]*([A-Z0-9\s,\.\-&()\u0900-\u097F]{3,100})', re.IGNORECASE)
    ]

    ORIGIN_PATTERNS = [
        re.compile(r'(?:COUNTRY\s*OF\s*ORIGIN|MADE\s*IN|PRODUCT\s*OF)[\s:\.]*([A-Z\s\u0900-\u097F]{3,30})', re.IGNORECASE),
        re.compile(r'(?:मूल\s*देश|भारत\s*में\s*निर्मित|उत्पादक\s*देश)[\s:\.]*([A-Z\s\u0900-\u097F]{3,30})', re.IGNORECASE)
    ]


    GENERIC_NAMES = [
        "PUNJABI TADKA", "NAMKEEN", "BHUJIA", "ALOO BHUJIA", "KHATTA MEETHA", "MOONG DAL",
        "CHIPS", "POTATO CHIPS", "SNACKS", "MIXTURE", "SEV", "RATLAMI SEV", "WAFERS",
        "PAPAD", "EXTRUDED SNACKS", "SWEETS", "INSTANT NOODLES", "NOODLES", "PASTA",
        "SHAMPOO", "HAIR OIL", "SOAP", "BATH SOAP", "BISCUITS", "COOKIES", "EDIBLE OIL", 
        "MUSTARD OIL", "SUNFLOWER OIL", "WHEAT FLOUR", "ATTA", "RICE", "TEA", "COFFEE",
        "DETERGENT", "TOOTHPASTE", "HAND WASH", "FACE CREAM", "MOISTURIZER", "BATTERY",
        "POWER BANK", "CHARGER", "LED BULB", "CABLE", "HEADPHONES", "TABLETS", "CAPSULES",
        "PERFUME", "EAU DE PARFUM", "DEODORANT", "BODY SPRAY", "ROOM FRESHENER",
        "MANGO DRINK", "MANGO JUICE", "FRUIT DRINK", "BEVERAGE", "JUICE", "READY TO SERVE FRUIT BEVERAGE"
    ]

    DISALLOWED_BRANDING_TERMS = [
        "PRICE", "SALE", "RATE", "MRP", "USP", "RS", "INR", "₹", "NET", "WT", "WEIGHT",
        "QTY", "QUANTITY", "VAL", "VALUE", "LIC", "FSSAI", "BATCH", "LOT", "CONTAIN",
        "ALLERGEN", "NLE", "DATE", "MFD", "EXP", "PKD", "USE", "BEST", "BEFORE",
        "NUTRITION", "ENERGY", "PROTEIN", "FAT", "CARB", "TABLE", "STORAGE", "KEEP",
        "INSTRUCTIONS", "FEEDBACK", "QUERIES", "CARE", "HELPLINE", "SERVING", "SIZE",
        "PERCENT", "%", "INGREDIENTS", "FLAVOUR", "FLAVOR", "PRODUCT OF", "TAX", "TAXES",
        "INCLUSIVE", "INCL", "PACKAGING", "PACKAGING BY", "SEE TOP", "FOR DATE", "COMMODITY"
    ]

    @classmethod
    def _is_allergen_or_invalid_company_line(cls, text: str) -> bool:
        t_up = text.upper()
        if any(term in t_up for term in cls.ALLERGEN_OR_NON_COMPANY_WORDS):
            return True
        if cls.DATE_LIKE_REGEX.search(text):
            return True
        return False

    @classmethod
    def extract_manufacturer(cls, lines: List[OCRLine]) -> Optional[ExtractedField]:
        best_candidate: Optional[Dict[str, Any]] = None

        # Strategy 1: Header-guided match (Manufactured By / Marketed By / Mfg & Pkd By)
        for idx, line in enumerate(lines):
            text = line.text.strip()
            if cls._is_allergen_or_invalid_company_line(text):
                continue

            header_match = cls.MFG_HEADER_REGEX.search(text)
            if header_match:
                after_header = text[header_match.end():].strip(" :-.")
                entity_parts = []
                bbox = list(line.bbox) if len(line.bbox) == 4 else [0, 0, 100, 100]

                if len(after_header) >= 3 and not cls._is_allergen_or_invalid_company_line(after_header):
                    entity_parts.append(after_header)

                # Scan subsequent 1-4 lines for company name and address
                for offset in range(1, 5):
                    if idx + offset < len(lines):
                        next_line = lines[idx + offset]
                        n_text = next_line.text.strip()

                        if cls._is_allergen_or_invalid_company_line(n_text):
                            break
                        if cls.MFG_HEADER_REGEX.search(n_text):
                            break

                        has_suffix = bool(cls.COMPANY_SUFFIX_PATTERN.search(n_text) or cls.PROMINENT_MFR_PATTERN.search(n_text))
                        has_addr = any(term in n_text.upper() for term in ["ROAD", "NAGAR", "IND", "PLOT", "SECTOR", "STATE", "PIN", "ESTATE", "DIST", "VILLAGE", "KASNA", "HARIDWAR", "KUNDLI", "DELHI", "MUMBAI", "P.O."])

                        if has_suffix or has_addr or (len(entity_parts) == 0 and len(n_text) >= 4):
                            entity_parts.append(n_text)
                            if len(next_line.bbox) == 4:
                                bbox[0] = min(bbox[0], next_line.bbox[0])
                                bbox[1] = min(bbox[1], next_line.bbox[1])
                                bbox[2] = max(bbox[2], next_line.bbox[2])
                                bbox[3] = max(bbox[3], next_line.bbox[3])
                            if len(entity_parts) >= 3:
                                break
                        elif len(entity_parts) > 0:
                            break

                if entity_parts:
                    full_entity = ", ".join(entity_parts)
                    clean_norm = re.sub(r'^(?:IN\s*INDIA\s*BY[\s:\.]*|\(A\)|\(B\)|\(C\))\s*', '', full_entity, flags=re.IGNORECASE).strip()
                    conf = min(0.98, round(line.confidence * 0.94, 4))
                    if best_candidate is None or conf > best_candidate["confidence"]:
                        best_candidate = {
                            "raw": text,
                            "normalized": clean_norm if len(clean_norm) > 4 else full_entity,
                            "confidence": conf,
                            "bbox": bbox
                        }

        # Strategy 2: Fallback scan for standalone company names with PVT LTD / LIMITED or known brands
        if not best_candidate:
            for idx, line in enumerate(lines):
                text = line.text.strip()
                if cls._is_allergen_or_invalid_company_line(text):
                    continue

                if cls.COMPANY_SUFFIX_PATTERN.search(text) or cls.PROMINENT_MFR_PATTERN.search(text):
                    combined_text = text
                    bbox = list(line.bbox) if len(line.bbox) == 4 else [0, 0, 100, 100]
                    if idx + 1 < len(lines):
                        next_t = lines[idx + 1].text.strip()
                        if not cls._is_allergen_or_invalid_company_line(next_t) and any(c in next_t.upper() for c in ["PLOT", "ROAD", "NAGAR", "ESTATE", "LTD", "PVT", "INDIA", "GERMANY", "P.O."]):
                            combined_text = f"{text}, {next_t}"
                            if len(lines[idx + 1].bbox) == 4:
                                bbox[2] = max(bbox[2], lines[idx + 1].bbox[2])
                                bbox[3] = max(bbox[3], lines[idx + 1].bbox[3])
                    best_candidate = {
                        "raw": combined_text,
                        "normalized": combined_text,
                        "confidence": min(0.90, round(line.confidence * 0.88, 4)),
                        "bbox": bbox
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
                if len(val) >= 2 and not any(term in val.upper() for term in ["PRICE", "MRP", "NET", "WT"]):
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
            if any(term in text for term in cls.DISALLOWED_BRANDING_TERMS):
                continue
            if cls.MFG_HEADER_REGEX.search(line.text) or cls.COMPANY_SUFFIX_PATTERN.search(line.text):
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

        # Priority 3: Fallback to prominent top branding line (with strict noise filter & realistic confidence)
        if lines:
            for candidate_line in lines[:6]:
                c_text = candidate_line.text.strip()
                c_upper = c_text.upper()

                # Exclude noise, headers, colons, numbers, or disallowed words
                if len(c_text) < 3 or len(c_text) > 40:
                    continue
                if c_text.endswith(":") or ":" in c_text:
                    continue
                if any(term in c_upper for term in cls.DISALLOWED_BRANDING_TERMS):
                    continue
                if re.search(r'\d', c_text):
                    continue

                # Fallback heuristic: mark confidence calibrated to trigger manual review / warning
                calibrated_conf = min(0.55, round(candidate_line.confidence * 0.50, 4))
                return ExtractedField(
                    field_name="product_name",
                    display_name="Generic Name / Product Description",
                    raw_value=c_text,
                    normalized_value=c_text.title(),
                    confidence=calibrated_conf,
                    detection_method="HEURISTIC_TOP_LINE",
                    bbox=candidate_line.bbox,
                    is_detected=True,
                    metadata={
                        "legal_rule": "Rule 6(1)(a) - Common or Generic Name",
                        "heuristic_note": "Extracted via top branding line heuristic. Manual verification recommended."
                    }
                )

        return None
