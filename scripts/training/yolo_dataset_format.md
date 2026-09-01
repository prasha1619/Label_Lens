# YOLO Fine-Tuning Dataset Format for Legal Metrology Label Compliance

This document describes how to structure, annotate, and train a custom YOLO model (e.g., YOLO11) for detecting mandatory Legal Metrology declaration regions on product packages.

---

## 1. Class Taxonomy

| Class ID | Class Name | Description | Legal Reference |
|---|---|---|---|
| `0` | `product_name` | Common or generic name of commodity | Rule 6(1)(a) |
| `1` | `mrp` | Maximum Retail Price declaration (incl. taxes) | Rule 6(1)(e) |
| `2` | `net_quantity` | Net weight, volume, or unit count | Rule 6(1)(c) |
| `3` | `mfg_date` | Date / Month / Year of manufacture or packing | Rule 6(1)(d) |
| `4` | `expiry_date` | Expiry Date / Best Before declaration | Rule 6(1)(d) |
| `5` | `manufacturer` | Name and address of manufacturer/packer/importer | Rule 6(1)(b) |
| `6` | `consumer_care` | Customer care phone, email, or postal address | Rule 6(1)(da) |
| `7` | `country_of_origin` | Country of origin on package | Rule 6(10) |

---

## 2. Directory Structure

```
dataset/
├── data.yaml
├── images/
│   ├── train/
│   │   ├── img001.jpg
│   │   ├── img002.jpg
│   └── val/
│       ├── img101.jpg
│       └── img102.jpg
└── labels/
    ├── train/
    │   ├── img001.txt
    │   ├── img002.txt
    └── val/
        ├── img101.txt
        └── img102.txt
```

---

## 3. Annotation Format

Each `.txt` label file must contain one line per bounding box:
```
<class_id> <x_center> <y_center> <width> <height>
```
*Coordinates are normalized between `0.0` and `1.0` relative to image dimensions.*

### Example `img001.txt`:
```
0 0.485 0.120 0.720 0.080
1 0.350 0.340 0.420 0.050
2 0.310 0.280 0.380 0.045
3 0.320 0.410 0.390 0.040
5 0.500 0.620 0.850 0.120
6 0.500 0.840 0.820 0.090
```

---

## 4. `data.yaml` Specification

```yaml
path: /path/to/dataset
train: images/train
val: images/val

names:
  0: product_name
  1: mrp
  2: net_quantity
  3: mfg_date
  4: expiry_date
  5: manufacturer
  6: consumer_care
  7: country_of_origin
```

---

## 5. Training Command

Run the training script:
```bash
python scripts/training/train_yolo_legal_detector.py --data dataset/data.yaml --epochs 100 --imgsz 640
```
Or directly with ultralytics CLI:
```bash
yolo task=detect mode=train model=yolo11n.pt data=dataset/data.yaml epochs=100 imgsz=640 project=models name=legal_detector
```

Copy the best checkpoint to:
```bash
cp models/legal_detector/weights/best.pt models/legal_label_detector.pt
```
Restart LabelLens to activate custom YOLO region detection!
