import os
from typing import List, Dict, Any, Optional
from PIL import Image, ImageDraw, ImageFont
from app.core.logging import logger

class AnnotationVisualizer:
    """
    Renders high-contrast, professional bounding boxes, label tags, and confidence badges
    onto product label images for visual evidence and explainability.
    """

    COLOR_PALETTE = {
        "PASS": (16, 185, 129, 255),       # Emerald Green
        "FAIL": (239, 68, 68, 255),        # Red
        "WARNING": (245, 158, 11, 255),     # Amber
        "UNCERTAIN": (217, 119, 6, 255),    # Dark Amber
        "NOT_DETECTED": (156, 163, 175, 255),# Gray
        "DEFAULT": (59, 130, 246, 255)      # Blue
    }

    @classmethod
    def annotate(
        cls,
        image_path: str,
        detected_fields: List[Dict[str, Any]],
        output_path: Optional[str] = None
    ) -> str:
        """
        Draws bounding boxes and labels on the image.
        detected_fields list items format:
        {
            "field_name": "MRP",
            "display_name": "MRP",
            "value": "₹249",
            "confidence": 0.94,
            "status": "PASS",
            "bbox": [x1, y1, x2, y2]
        }
        """
        if output_path is None:
            base, ext = os.path.splitext(image_path)
            output_path = f"{base}_annotated{ext}"

        try:
            with Image.open(image_path) as base_img:
                img = base_img.convert("RGBA")
                overlay = Image.new("RGBA", img.size, (255, 255, 255, 0))
                draw = ImageDraw.Draw(overlay)

                # Try loading a readable default or truetype font
                try:
                    font = ImageFont.truetype("arial.ttf", size=max(14, int(img.width * 0.018)))
                    small_font = ImageFont.truetype("arial.ttf", size=max(11, int(img.width * 0.014)))
                except Exception:
                    font = ImageFont.load_default()
                    small_font = font

                for field in detected_fields:
                    bbox = field.get("bbox")
                    if not bbox or len(bbox) != 4:
                        continue

                    x1, y1, x2, y2 = bbox
                    # Clamp to image boundaries
                    x1 = max(0, min(x1, img.width - 1))
                    y1 = max(0, min(y1, img.height - 1))
                    x2 = max(0, min(x2, img.width - 1))
                    y2 = max(0, min(y2, img.height - 1))

                    if x2 <= x1 or y2 <= y1:
                        continue

                    status = field.get("status", "DEFAULT").upper()
                    color = cls.COLOR_PALETTE.get(status, cls.COLOR_PALETTE["DEFAULT"])
                    fill_box = (color[0], color[1], color[2], 35)  # semi-transparent fill

                    # 1. Draw highlighted region rectangle
                    draw.rectangle([x1, y1, x2, y2], fill=fill_box, outline=color, width=3)

                    # 2. Draw label banner
                    display_name = field.get("display_name") or field.get("field_name", "Field")
                    val = field.get("value") or field.get("normalized_value") or ""
                    conf = field.get("confidence", 0.0)
                    conf_str = f"{int(conf * 100)}%" if conf else ""

                    label_text = f"{display_name}: {val}" if val else display_name
                    if conf_str:
                        label_text += f" ({conf_str})"

                    # Measure text box
                    text_bbox = draw.textbbox((x1, y1), label_text, font=font)
                    text_w = text_bbox[2] - text_bbox[0]
                    text_h = text_bbox[3] - text_bbox[1]

                    # Position tag above box if possible, otherwise inside
                    tag_y1 = max(0, y1 - text_h - 8)
                    tag_y2 = tag_y1 + text_h + 8
                    tag_x2 = min(img.width, x1 + text_w + 12)

                    # Draw badge background
                    draw.rectangle([x1, tag_y1, tag_x2, tag_y2], fill=color)
                    # Draw text in white
                    draw.text((x1 + 6, tag_y1 + 4), label_text, fill=(255, 255, 255, 255), font=font)

                # Composite overlay onto original image
                final_img = Image.alpha_composite(img, overlay).convert("RGB")
                final_img.save(output_path, quality=95)
                return output_path

        except Exception as e:
            logger.error(f"Failed to generate annotation image for {image_path}: {e}")
            return image_path

def draw_detections(image_path: str, detected_fields: List[Dict[str, Any]], output_path: Optional[str] = None) -> str:
    return AnnotationVisualizer.annotate(image_path, detected_fields, output_path)
