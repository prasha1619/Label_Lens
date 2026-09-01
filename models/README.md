# LabelLens Model Directory

This directory stores deep learning model weights for the LabelLens Computer Vision pipeline.

## Default Weights Location
- `legal_label_detector.pt`: Custom trained YOLO object detection model fine-tuned on Indian packaged commodity labels.

## Configurable Environment Variable
You can configure the model path via `.env` or system environment variables:
```bash
MODEL_PATH=/models/legal_label_detector.pt
```

## Behavior when model is unconfigured
If `legal_label_detector.pt` is not present in this directory, LabelLens:
1. Truthfully displays: `"AI detection model not configured — demo/inference mode unavailable."` in the CV detector module.
2. Continues executing the OCR, Field Extraction, and Legal Metrology Rule Engine pipeline without fabricating synthetic bounding box detections.
3. Allows inspectors to upload images and review full statutory compliance via OCR.
