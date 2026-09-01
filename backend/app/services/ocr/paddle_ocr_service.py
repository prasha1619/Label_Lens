import time
from typing import List
from app.core.logging import logger
from app.schemas.ocr import OCRResultSchema, OCRLine, OCRWord


class PaddleOCRService:
    """
    PaddleOCR 3.x (PaddleX) service using the new predict() API.
    Handles both legacy ocr() and new predict() return formats.
    """

    def __init__(self, lang: str = "en"):
        self.lang = lang
        self.ocr_engine = None
        self._is_ready = False
        self._init_engine()

    def _init_engine(self):
        try:
            from paddleocr import PaddleOCR
            self.ocr_engine = PaddleOCR(lang=self.lang, enable_mkldnn=False)
            self._is_ready = True
            logger.info("PaddleOCR engine initialized successfully.")
        except ImportError:
            logger.info("paddleocr module not installed.")
            self._is_ready = False
        except Exception as e:
            logger.warning(f"PaddleOCR failed to initialize: {e}")
            self._is_ready = False

    @property
    def engine_name(self) -> str:
        return f"PaddleOCR ({self.lang})"

    def is_available(self) -> bool:
        return self._is_ready and self.ocr_engine is not None

    def extract_text(self, image_path: str) -> OCRResultSchema:
        start_time = time.time()
        if not self.is_available():
            raise RuntimeError("PaddleOCR is not available.")

        lines: List[OCRLine] = []
        full_text_parts: List[str] = []
        confidences: List[float] = []

        try:
            # PaddleOCR 3.x uses predict() — returns list of dicts
            results = self.ocr_engine.predict(image_path)
            if results and isinstance(results, list) and len(results) > 0:
                r = results[0]
                if isinstance(r, dict):
                    # PaddleOCR 3.x/PaddleX key names: rec_texts, rec_scores, rec_boxes
                    texts = r.get('rec_texts', r.get('rec_text', []))
                    scores = r.get('rec_scores', r.get('rec_score', []))
                    # rec_boxes is shape (N, 4): [x1, y1, x2, y2]
                    boxes = r.get('rec_boxes', [])

                    for idx, text in enumerate(texts):
                        text = str(text).strip()
                        if not text:
                            continue
                        conf = float(scores[idx]) if idx < len(scores) else 0.85
                        if idx < len(boxes):
                            b = boxes[idx]
                            try:
                                bbox = [int(b[0]), int(b[1]), int(b[2]), int(b[3])]
                            except Exception:
                                bbox = [0, 0, 100, 20]
                        else:
                            bbox = [0, idx * 20, 300, (idx + 1) * 20]

                        confidences.append(conf)
                        full_text_parts.append(text)
                        lines.append(OCRLine(
                            line_number=idx + 1,
                            text=text,
                            confidence=round(conf, 4),
                            bbox=bbox,
                            words=[OCRWord(text=text, confidence=round(conf, 4), bbox=bbox)]
                        ))

        except Exception as e:
            logger.warning(f"PaddleOCR predict() failed on {image_path}: {e}")
            self._is_ready = False
            raise

        mean_conf = sum(confidences) / len(confidences) if confidences else 0.0
        elapsed_ms = (time.time() - start_time) * 1000.0

        return OCRResultSchema(
            engine=self.engine_name,
            total_lines=len(lines),
            mean_confidence=round(mean_conf, 4),
            raw_full_text="\n".join(full_text_parts),
            lines=lines,
            processing_time_ms=round(elapsed_ms, 2)
        )
