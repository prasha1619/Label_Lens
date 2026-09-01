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
    PHONE_PATTERN = re.compile(r'(?:TEL|PHONE|HELPLINE|TOLL[\s-]*FREE|CALL|CARE|NO\.?)[\s:\.]*([+0-9\s\-()]{7,18})', re.IGNORECASE)
    CARE_KEYWORD_PATTERN = re.compile(
        r'(?:CONSUMER|CUSTOMER|QUERY|QUERIES|FEEDBACK|COMPLAINT|GRIEVANCE)[\s/&]*(?:CARE|CELL|FEEDBACK|GRIEVANCE|EXECUTIVE|SERVICE|CONTACT|SUPPORT|OFFICE)?',
        re.IGNORECASE
    )

    @classmethod
    def extract(cls, lines: List[OCRLine]) -> Optional[ExtractedField]:
        detected_details: List[str] = []
        best_bbox = None
        confidences = []
        raw_lines = []

        for line in lines:
            text = line.text.strip()
            is_relevant = False

            # Check email
            email_match = cls.EMAIL_PATTERN.search(text)
            if email_match:
                detected_details.append(f"Email: {email_match.group(1)}")
                is_relevant = True

            # Check helpline phone
            phone_match = cls.PHONE_PATTERN.search(text)
            if phone_match:
                clean_phone = phone_match.group(1).strip()
                if len(re.sub(r'[^0-9]', '', clean_phone)) >= 7:
                    detected_details.append(f"Helpline: {clean_phone}")
                    is_relevant = True

            # Check care keyword
            if cls.CARE_KEYWORD_PATTERN.search(text):
                is_relevant = True
                if not any(d.startswith("Details:") for d in detected_details):
                    detected_details.append(f"Contact: {text}")

            if is_relevant:
                raw_lines.append(text)
                confidences.append(line.confidence)
                if best_bbox is None:
                    best_bbox = list(line.bbox)
                else:
                    best_bbox[0] = min(best_bbox[0], line.bbox[0])
                    best_bbox[1] = min(best_bbox[1], line.bbox[1])
                    best_bbox[2] = max(best_bbox[2], line.bbox[2])
                    best_bbox[3] = max(best_bbox[3], line.bbox[3])

        if detected_details:
            normalized_str = " | ".join(detected_details)
            mean_conf = sum(confidences) / len(confidences) if confidences else 0.85
            return ExtractedField(
                field_name="consumer_care",
                display_name="Consumer Care Information",
                raw_value="; ".join(raw_lines),
                normalized_value=normalized_str,
                confidence=min(0.98, round(mean_conf * 0.95, 4)),
                detection_method="OCR_REGEX",
                bbox=best_bbox,
                is_detected=True,
                metadata={
                    "items": detected_details,
                    "legal_rule": "Rule 6(1)(da) - Name, Address, Telephone, Email of Consumer Care"
                }
            )

        return None
