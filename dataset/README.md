# LabelLens training dataset

Put annotated product-label images in this structure:

```text
dataset/
├── images/train/    # roughly 80% of images
├── images/val/      # remaining 20%, never used for gradient updates
├── labels/train/    # matching YOLO .txt files
└── labels/val/      # matching YOLO .txt files
```

Class IDs are fixed in `data.yaml`. Each image needs a matching `.txt` file, including an empty file if that image deliberately contains no applicable declaration.

Validate before training:

```powershell
python scripts/training/validate_yolo_dataset.py dataset/data.yaml
```

Then train:

```powershell
python scripts/training/train_yolo_legal_detector.py --data dataset/data.yaml --epochs 100 --batch 8 --imgsz 960
```
