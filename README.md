# LabelLens: Production-Style AI Legal Metrology Label Compliance System

## Authentication setup

Configure `JWT_SECRET_KEY`, `REFRESH_TOKEN_EXPIRE_DAYS`, `COOKIE_SECURE`, `DATABASE_URL`, and `CORS_ORIGINS` from `.env.example`. For PostgreSQL deployments run `cd backend && alembic upgrade head` before starting the API. The local SQLite development bootstrap applies the corresponding schema update automatically.

**SIH Problem Statement**: *AI/Computer-Vision Legal Metrology Label Compliance*

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.7+-3178C6?logo=typescript&logoColor=white)](https://www.typescriptlang.org)
[![Vite](https://img.shields.io/badge/Vite-6.0+-646CFF?logo=vite&logoColor=white)](https://vitejs.dev)
[![TailwindCSS](https://img.shields.io/badge/TailwindCSS-3.4+-06B6D4?logo=tailwindcss&logoColor=white)](https://tailwindcss.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql&logoColor=white)](https://www.postgresql.org)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)](https://www.docker.com)

---

## 1. Project Overview

**LabelLens** is an end-to-end, production-grade automated compliance inspection platform engineered to audit pre-packaged commodity labels against the statutory requirements of the **Legal Metrology (Packaged Commodities) Rules, 2011** (and applicable FSSAI, BIS, and CDSCO amendments).

### Core Principle: Zero Hallucination Policy
The system **never** marks a product label as compliant merely because OCR failed to observe a violation. If image quality (blur, glare, lighting, resolution) is degraded, or mandatory fields are occluded, the system explicitly returns:
> **`“Unable to verify — manual inspection required.”`**

---

## 2. Architecture & Pipeline

```
                              ┌────────────────────────┐
                              │ Inspector / Client App │
                              └───────────┬────────────┘
                                          │ (Image Upload / Camera)
                                          ▼
                              ┌────────────────────────┐
                              │   FastAPI REST Engine  │
                              └───────────┬────────────┘
                                          │
                   ┌──────────────────────┴──────────────────────┐
                   ▼                                             ▼
       ┌────────────────────────┐                   ┌────────────────────────┐
       │   Image Quality Check  │                   │  OpenCV Preprocessing  │
       │ (Laplacian blur/glare) │                   │  (CLAHE / De-skewing)  │
       └───────────┬────────────┘                   └────────────┬───────────┘
                   └──────────────────────┬──────────────────────┘
                                          │
                                          ▼
                              ┌────────────────────────┐
                              │  Modular YOLO Detector │
                              │ (Region Localization)  │
                              └───────────┬────────────┘
                                          │
                                          ▼
                              ┌────────────────────────┐
                              │       OCR Engine       │
                              │ (PaddleOCR / EasyOCR)  │
                              └───────────┬────────────┘
                                          │
                                          ▼
                              ┌────────────────────────┐
                              │ Field Extraction Engine│
                              │ (MRP, Qty, Dates, Mfg) │
                              └───────────┬────────────┘
                                          │
                                          ▼
                              ┌────────────────────────┐
                              │ Declarative Rule Engine│
                              │ (Category JSON Rules)  │
                              └───────────┬────────────┘
                                          │
                   ┌──────────────────────┴──────────────────────┐
                   ▼                                             ▼
       ┌────────────────────────┐                   ┌────────────────────────┐
       │ Bounding Box Evidence  │                   │ PDF Audit Report Gen   │
       │ (Color-coded Overlays) │                   │ (ReportLab Exporter)   │
       └───────────┬────────────┘                   └────────────┬───────────┘
                   └──────────────────────┬──────────────────────┘
                                          │
                                          ▼
                              ┌────────────────────────┐
                              │ PostgreSQL / SQLite DB │
                              │ (Audit Logs & History) │
                              └────────────────────────┘
```

---

## 3. Technology Stack

- **Frontend**: React 19, TypeScript, Vite, Tailwind CSS, Lucide Icons, HTML5 Canvas / SVG overlay.
- **Backend API**: Python 3.11+, FastAPI, Pydantic v2, SQLAlchemy 2.0, Uvicorn.
- **Computer Vision**: OpenCV, NumPy, Pillow.
- **Region Detector**: Modular `BaseDetector` with YOLO compatibility (`MODEL_PATH`).
- **OCR Subsystem**: Modular `BaseOCRService` with PaddleOCR, EasyOCR, and Tesseract support.
- **Rule Engine**: Declarative JSON rule definitions decoupled from application code.
- **Report Generation**: ReportLab PDF compliance report generator.
- **Database**: PostgreSQL (Production/Docker) with SQLite fallback for instant zero-config local runs.

---

## 4. Quickstart: Running Locally

### Prerequisites
- Python 3.10+
- Node.js 18+ and npm
- (Optional) Docker and Docker Compose

### Step 1: Clone and Configure Environment
```bash
git clone https://github.com/your-org/labellens.git
cd labellens
cp .env.example .env
```

### Step 2: Set Up Backend
```bash
cd backend
python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On Linux/macOS:
# source venv/bin/activate

pip install -r requirements.txt
```

Generate demo test assets:
```bash
python ../scripts/setup/seed_demo_assets.py
```

Start the FastAPI backend server:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
*API Swagger Documentation is available at: [http://localhost:8000/api/docs](http://localhost:8000/api/docs)*

### Step 3: Set Up Frontend
In a new terminal:
```bash
cd frontend
npm install
npm run dev
```
*Frontend UI is available at: [http://localhost:5173](http://localhost:5173)*

---

## 5. Docker Deployment

Deploy the entire stack (PostgreSQL + FastAPI + React + Nginx) with a single command:
```bash
docker compose up --build -d
```
- Frontend UI: `http://localhost`
- Backend API: `http://localhost:8000`
- API Docs: `http://localhost:8000/api/docs`

To stop:
```bash
docker compose down
```

---

## 6. YOLO Detection Model Configuration

The object detection module supports custom trained weights (e.g. YOLO11).

1. Set the environment variable in `.env`:
   ```bash
   MODEL_PATH=models/legal_label_detector.pt
   ```
2. Place your fine-tuned `.pt` weights file into `models/legal_label_detector.pt`.
3. If no model is configured, the application **does not fabricate fake detections**; instead, it truthfully reports:
   > `“AI detection model not configured — demo/inference mode unavailable.”`
   and continues executing the complete OCR and Legal Metrology Rule analysis pipeline.

### Training a Custom YOLO Model
Follow the guide in [`scripts/training/yolo_dataset_format.md`](file:///c:/Users/prash/OneDrive/Desktop/labellens/scripts/training/yolo_dataset_format.md) and execute:
```bash
python scripts/training/train_yolo_legal_detector.py --data dataset/data.yaml --epochs 100 --imgsz 640
```

---

## 7. Declarative Legal Rule Engine

Legal rules are stored as declarative JSON files in `backend/app/services/rules/definitions/`:

- `packaged_commodity.json`: Standard General Packaged Commodities
- `food_and_beverages.json`: Food & Beverages (FSSAI + Legal Metrology)
- `cosmetics_and_toiletries.json`: Cosmetics & Toiletries
- `electronics_and_appliances.json`: Electronics & Electrical Appliances
- `pharmaceuticals.json`: Pharmaceuticals & Healthcare

### Status Determination Matrix
| Evaluation Criteria | Legal Status | Action / Meaning |
|---|---|---|
| Mandatory field detected & Confidence $\ge$ Pass Threshold | `PASS` | Compliant declaration |
| Mandatory field detected & Confidence between Warn and Pass | `WARNING` / `UNCERTAIN` | Inspector manual review recommended |
| Mandatory field absent in OCR output | `NOT_DETECTED` | Potential statutory violation flagged |
| Image fails blur / brightness / glare check | `UNABLE_TO_VERIFY` | Re-capture required; no false pass |
| Optional field absent | `NOT_APPLICABLE` | Non-mandatory declaration |

---

## 8. API Reference

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/inspections` | Upload image and trigger inspection pipeline |
| `GET` | `/api/v1/inspections` | List paginated previous inspections with search/filters |
| `GET` | `/api/v1/inspections/dashboard/metrics` | Aggregate KPIs and status metrics |
| `GET` | `/api/v1/inspections/{id}` | Detailed inspection results & bounding boxes |
| `GET` | `/api/v1/inspections/{id}/report` | Download official PDF audit report |
| `GET` | `/api/v1/inspections/{id}/image` | Stream original or annotated image |
| `GET` | `/api/v1/rules` | List all Legal Metrology categories |
| `GET` | `/api/v1/rules/{category_id}` | Detailed rules for a specific category |
| `GET` | `/api/v1/demo/samples` | List curated demo test scenarios |
| `POST` | `/api/v1/demo/run/{sample_key}` | Execute inspection on demo sample |
| `GET` | `/api/v1/health` | Real-time system health & model status |

---

## 9. Automated Testing

Run the automated test suite with pytest:
```bash
cd backend
pytest app/tests/ -v
```

Tests include:
- `test_image_quality.py`: Blur detection, glare ratio, and resolution validation.
- `test_mrp_extraction.py`: Regex and fuzzy parsing of ₹, Rs, MRP variants.
- `test_net_qty_extraction.py`: SI unit extraction and multi-pack parsing.
- `test_rule_engine.py`: Unit tests for rule evaluations across all status states.
- `test_api.py`: FastAPI endpoint tests for health, upload, demo runs, and reports.

---

## 10. Statutory Legal Disclaimer

> [!IMPORTANT]
> **STATUTORY LEGAL DISCLAIMER:** AI-assisted screening result. Final legal determination requires verification by an authorized inspector/competent authority under the **Legal Metrology Act, 2009** and **Legal Metrology (Packaged Commodities) Rules, 2011**. This software provides automated screening evidence and does not replace official statutory certification.
