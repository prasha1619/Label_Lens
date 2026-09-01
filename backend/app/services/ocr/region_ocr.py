"""Run OCR on detector-guided crops and map its evidence back to the full image."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import List

from PIL import Image, ImageEnhance, ImageOps

from app.schemas.cv import DetectionRegion
from app.schemas.ocr import OCRLine, OCRResultSchema, OCRWord
from app.services.ocr.ocr_manager import OCRManager


def extract_region_text(
    image_path: str,
    regions: List[DetectionRegion],
    ocr_manager: OCRManager,
    min_confidence: float = 0.60,
    padding_ratio: float = 0.06,
) -> OCRResultSchema | None:
    """OCR high-confidence detector regions and convert crop boxes to image coordinates."""
    selected_regions = [region for region in regions if region.confidence >= min_confidence]
    if not selected_regions:
        return None

    lines: List[OCRLine] = []
    elapsed_ms = 0.0
    engine_names: List[str] = []

    with Image.open(image_path) as source:
        image = source.convert("RGB")
        width, height = image.size

        for region in selected_regions:
            x1, y1, x2, y2 = region.bbox
            pad_x = int((x2 - x1) * padding_ratio)
            pad_y = int((y2 - y1) * padding_ratio)
            left, top = max(0, x1 - pad_x), max(0, y1 - pad_y)
            right, bottom = min(width, x2 + pad_x), min(height, y2 + pad_y)
            if right <= left or bottom <= top:
                continue

            temp_path = None
            try:
                with tempfile.NamedTemporaryFile(
                    suffix=".png", prefix="labellens_region_", delete=False
                ) as temp_file:
                    temp_path = temp_file.name
                image.crop((left, top, right, bottom)).save(temp_path)
                # Full-image OCR has already handled orientation.  Searching
                # rotations for every small detector crop is costly and makes
                # a single camera scan take tens of seconds.
                result = ocr_manager.extract(temp_path, allow_rotation=False)
                elapsed_ms += result.processing_time_ms
                engine_names.append(result.engine)

                for crop_line in result.lines:
                    bbox = crop_line.bbox
                    full_bbox = [bbox[0] + left, bbox[1] + top, bbox[2] + left, bbox[3] + top]
                    words = [
                        OCRWord(
                            text=word.text,
                            confidence=word.confidence,
                            bbox=[word.bbox[0] + left, word.bbox[1] + top, word.bbox[2] + left, word.bbox[3] + top],
                        )
                        for word in crop_line.words
                    ]
                    lines.append(
                        OCRLine(
                            line_number=len(lines) + 1,
                            text=crop_line.text,
                            confidence=crop_line.confidence,
                            bbox=full_bbox,
                            words=words,
                        )
                    )
            finally:
                if temp_path and os.path.exists(temp_path):
                    os.remove(temp_path)

    if not lines:
        return None
    confidences = [line.confidence for line in lines]
    return OCRResultSchema(
        engine=f"{engine_names[0]} + YOLO crops" if engine_names else "YOLO crop OCR",
        total_lines=len(lines),
        mean_confidence=round(sum(confidences) / len(confidences), 4),
        raw_full_text="\n".join(line.text for line in lines),
        lines=lines,
        processing_time_ms=round(elapsed_ms, 2),
    )


def extract_lower_declaration_text(
    image_path: str,
    ocr_manager: OCRManager,
    *,
    top_ratio: float = 0.66,
    bottom_ratio: float = 0.94,
    scale: int = 4,
) -> OCRResultSchema | None:
    """OCR the lower declaration strip at high resolution.

    MRP, unit sale price, batch, and date declarations are commonly printed in
    a narrow band near the bottom of toiletries and food packs. On a full-pack
    image their glyphs can be only a few pixels high, even when the overall
    image passes blur checks. Cropping and enlarging that band preserves the
    evidence without accepting a price from an arbitrary part of the label.
    """
    temp_path = None
    try:
        with Image.open(image_path) as source:
            image = source.convert("RGB")
            width, height = image.size
            top, bottom = int(height * top_ratio), int(height * bottom_ratio)
            if width < 40 or bottom - top < 20:
                return None

            band = image.crop((0, top, width, bottom))
            band = ImageOps.autocontrast(band)
            band = ImageEnhance.Contrast(band).enhance(1.7)
            band = band.resize((width * scale, (bottom - top) * scale), Image.Resampling.LANCZOS)

            with tempfile.NamedTemporaryFile(suffix=".png", prefix="labellens_price_band_", delete=False) as temp_file:
                temp_path = temp_file.name
            band.save(temp_path)

        result = ocr_manager.extract(temp_path, allow_rotation=False)
        if not result or not result.lines:
            return None

        for line in result.lines:
            line.bbox = [
                int(line.bbox[0] / scale), int(line.bbox[1] / scale) + top,
                int(line.bbox[2] / scale), int(line.bbox[3] / scale) + top,
            ]
            for word in line.words:
                word.bbox = [
                    int(word.bbox[0] / scale), int(word.bbox[1] / scale) + top,
                    int(word.bbox[2] / scale), int(word.bbox[3] / scale) + top,
                ]
        result.engine = f"{result.engine} + declaration-strip OCR"
        return result
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)
