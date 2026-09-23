import re
from typing import Optional, List, Dict, Any
from app.schemas.extraction import ExtractedField
from app.schemas.ocr import OCRLine

class ConsumerCareExtractor:
    """
    Extracts Consumer Care Contact Information.
    Complies with Legal Metrology (PC) Rules, Rule 6(1)(da) - 
    Mandatory Name/Designation, Telephone number, Email ID, Address for consumer complaints.
    """

    EMAIL_PATTERN = re.compile(r'([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)', re.IGNORECASE)
    
    # Specific phone pattern excluding generic 'NO.' to prevent FSSAI license / Batch numbers from matching
    PHONE_PATTERN = re.compile(
        r'(?:'
        r'(?:TEL(?:EPHONE)?|PHONE|HELPLINE|TOLL[\s-]*FREE|CALL\s*(?:US)?|CUSTOMER\s*CARE|CARE\s*NO|HELPLINE\s*NO|दूरभाष|फोन|टोल\s*फ्री)[\s:\.\-]*([+0-9\s\-()]{7,16})|'
        r'\b(1800[\s\-]*[0-9]{3}[\s\-]*[0-9]{3,4})\b|'
        r'\b(\+91[\s\-]?[6-9][0-9]{9})\b'
        r')',
        re.IGNORECASE
    )

    CARE_KEYWORD_PATTERN = re.compile(
        r'(?:'
        r'\b(?:CONSUMER|CUSTOMER|QUERY|QUERIES|FEEDBACK|COMPLAINT|GRIEVANCE|CARE\s*CELL)\b'
        r'(?:[\s/&]*(?:CARE|CELL|FEEDBACK|GRIEVANCE|EXECUTIVE|SERVICE|CONTACT|SUPPORT|OFFICE|DETAILS|REPLACE))?|'
        r'(?:उपभोक्ता\s*सेवा|ग्राहक\s*सेवा|कंज्यूमर\s*केयर|शिकायत\s*निवारण|कस्टमर\s*केयर|सहायता\s*केंद्र|संपर्क)'
        r')',
        re.IGNORECASE
    )


    INVALID_PHONE_LINE_TERMS = ["LIC", "LICENSE", "FSSAI", "BATCH", "LOT", "BARCODE", "NET WT", "MRP", "MFD", "EXP"]

    @classmethod
    def _is_valid_phone(cls, phone_str: str, full_line_text: str) -> bool:
        digits_only = re.sub(r'[^0-9]', '', phone_str)
        # FSSAI license numbers are 14 digits (often starting with 100...)
        if len(digits_only) == 14 and digits_only.startswith("1"):
            return False
        # Disallow if line is clearly a license / barcode / batch line
        if any(term in full_line_text.upper() for term in cls.INVALID_PHONE_LINE_TERMS):
            return False
        # Valid length: 7 to 12 digits (toll-free 1800, 10-digit mobile, or 8-digit landline + STD)
        if len(digits_only) < 7 or len(digits_only) > 13:
            return False
        return True

    @classmethod
    def extract(cls, lines: List[OCRLine]) -> Optional[ExtractedField]:
        detected_details: List[str] = []
        best_bbox = None
        raw_lines = []
        has_email = False
        has_phone = False
        has_address = False

        for idx, line in enumerate(lines):
            text = line.text.strip()
            is_relevant = False

            # 1. Check email
            email_match = cls.EMAIL_PATTERN.search(text)
            if email_match:
                detected_details.append(f"Email: {email_match.group(1)}")
                is_relevant = True
                has_email = True

            # 2. Check helpline phone (with strict validation)
            phone_match = cls.PHONE_PATTERN.search(text)
            if phone_match:
                matched_phone = phone_match.group(1) or phone_match.group(2) or phone_match.group(3)
                if matched_phone:
                    clean_phone = matched_phone.strip(" :-.")
                    if cls._is_valid_phone(clean_phone, text):
                        detected_details.append(f"Helpline: {clean_phone}")
                        is_relevant = True
                        has_phone = True

            # 3. Check care keyword & scan for contact text
            if cls.CARE_KEYWORD_PATTERN.search(text) and not any(term in text.upper() for term in ["LIC", "FSSAI", "INGREDIENTS"]):
                is_relevant = True
                # Clean up introductory keywords
                care_text = text
                # Look at next line if this line is just a header like "For Feedback/Queries Write to:"
                if len(care_text) < 40 and idx + 1 < len(lines):
                    next_line = lines[idx + 1]
                    n_text = next_line.text.strip()
                    if not any(term in n_text.upper() for term in ["LIC", "FSSAI", "MRP", "MFD", "EXP", "BATCH"]):
                        care_text = f"{care_text} {n_text}"
                        if any(c in n_text.upper() for c in ["ADDRESS", "EXECUTIVE", "PLOT", "ROAD", "CARE", "MAIL"]):
                            has_address = True

                if not any(d.startswith("Contact:") for d in detected_details):
                    detected_details.append(f"Contact: {care_text}")

            if is_relevant:
                raw_lines.append(text)
                if best_bbox is None:
                    best_bbox = list(line.bbox) if len(line.bbox) == 4 else [0, 0, 100, 100]
                elif len(line.bbox) == 4:
                    best_bbox[0] = min(best_bbox[0], line.bbox[0])
                    best_bbox[1] = min(best_bbox[1], line.bbox[1])
                    best_bbox[2] = max(best_bbox[2], line.bbox[2])
                    best_bbox[3] = max(best_bbox[3], line.bbox[3])

        if detected_details:
            normalized_str = " | ".join(detected_details)

            # Semantic confidence calibration:
            # Full contact (Email + Phone) -> 0.95
            # Phone or Email -> 0.90
            # Only keyword / incomplete contact -> 0.50 (flags UNCERTAIN/WARNING for inspector review)
            if has_email and has_phone:
                calibrated_conf = 0.96
            elif has_email or has_phone:
                calibrated_conf = 0.90
            elif has_address:
                calibrated_conf = 0.72
            else:
                calibrated_conf = 0.50

            return ExtractedField(
                field_name="consumer_care",
                display_name="Consumer Care Information",
                raw_value="; ".join(raw_lines),
                normalized_value=normalized_str,
                confidence=calibrated_conf,
                detection_method="OCR_REGEX",
                bbox=best_bbox,
                is_detected=True,
                metadata={
                    "items": detected_details,
                    "has_email": has_email,
                    "has_phone": has_phone,
                    "has_address": has_address,
                    "legal_rule": "Rule 6(1)(da) - Name, Address, Telephone, Email of Consumer Care"
                }
            )

        return None
