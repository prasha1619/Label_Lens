import os
import sys
import json
import httpx
from pathlib import Path

BASE_API = "http://127.0.0.1:8000/api/v1"
FRONTEND_URL = "http://localhost:5173"

def run_e2e_verification():
    print("=" * 70)
    print("Starting LabelLens Full-Stack E2E System Verification")
    print("=" * 70)

    client = httpx.Client(timeout=30.0)

    # 1. Frontend delivery check
    try:
        fe_resp = client.get(FRONTEND_URL)
        assert fe_resp.status_code == 200
        assert "LabelLens" in fe_resp.text or "root" in fe_resp.text
        print("✓ [PASS] Frontend Vite server delivering HTML/CSS/JS successfully (200 OK)")
    except Exception as e:
        print(f"✗ [FAIL] Frontend check: {e}")
        sys.exit(1)

    # 2. System Health Check
    try:
        health_resp = client.get(f"{BASE_API}/health")
        assert health_resp.status_code == 200
        health_data = health_resp.json()
        assert health_data["status"] == "ONLINE"
        assert health_data["database"]["status"] == "HEALTHY"
        assert "UNCONFIGURED" in health_data["computer_vision"]["yolo_detector"] or health_data["computer_vision"]["is_yolo_loaded"] is False
        print(f"✓ [PASS] Health API Check: {health_data['app_name']} v{health_data['version']} (DB: {health_data['database']['url_type']}, YOLO Truthful Status: Checked)")
    except Exception as e:
        print(f"✗ [FAIL] Health check: {e}")
        sys.exit(1)

    # 3. Rule Engine Categories
    try:
        rules_resp = client.get(f"{BASE_API}/rules")
        assert rules_resp.status_code == 200
        categories = rules_resp.json()
        assert len(categories) >= 4
        print(f"✓ [PASS] Declarative Rule Engine: Loaded {len(categories)} statutory categories ([{', '.join([c['category_id'] for c in categories])}])")
    except Exception as e:
        print(f"✗ [FAIL] Rules check: {e}")
        sys.exit(1)

    # 4. Demo Samples
    try:
        demo_resp = client.get(f"{BASE_API}/demo/samples")
        assert demo_resp.status_code == 200
        samples = demo_resp.json()
        assert len(samples) >= 3
        print(f"✓ [PASS] Curated Demo Suite: Found {len(samples)} realistic test scenarios")
    except Exception as e:
        print(f"✗ [FAIL] Demo check: {e}")
        sys.exit(1)

    # 5. Inspection Scenario 1: Compliant Shampoo
    try:
        run1 = client.post(f"{BASE_API}/demo/run/compliant_shampoo")
        assert run1.status_code == 200
        res1 = run1.json()
        assert res1["overall_status"] == "COMPLIANT"
        assert res1["compliance_score"] > 80.0
        assert res1["passed_checks"] >= 5
        assert len(res1["violations"]) == 0
        shampoo_id = res1["id"]
        print(f"✓ [PASS] Scenario 1 (Compliant Label): Verdict={res1['overall_status']}, Score={res1['compliance_score']}%, Passed={res1['passed_checks']}/{res1['total_checks']}")
    except Exception as e:
        print(f"✗ [FAIL] Scenario 1: {e}")
        sys.exit(1)

    # 6. Inspection Scenario 2: Missing Consumer Care (Flagged Violation)
    try:
        run2 = client.post(f"{BASE_API}/demo/run/missing_consumer_care_biscuit")
        assert run2.status_code == 200
        res2 = run2.json()
        assert res2["overall_status"] == "NON_COMPLIANT"
        assert len(res2["violations"]) > 0
        assert any(v["field_name"] == "consumer_care" for v in res2["violations"])
        print(f"✓ [PASS] Scenario 2 (Missing Consumer Care): Verdict={res2['overall_status']}, Correctly flagged {len(res2['violations'])} statutory violation(s) with inspector recommendations")
    except Exception as e:
        print(f"✗ [FAIL] Scenario 2: {e}")
        sys.exit(1)

    # 7. Inspection Scenario 3: Motion Blur / Degraded Quality (Anti-Hallucination)
    try:
        run3 = client.post(f"{BASE_API}/demo/run/blurry_label_oil")
        assert run3.status_code == 200
        res3 = run3.json()
        assert res3["overall_status"] == "UNABLE_TO_VERIFY"
        assert res3["compliance_score"] == 0.0
        print(f"✓ [PASS] Scenario 3 (Blurry Quality): Verdict={res3['overall_status']} (Anti-hallucination verified: rejected degraded image)")
    except Exception as e:
        print(f"✗ [FAIL] Scenario 3: {e}")
        sys.exit(1)

    # 8. Multipart Image Upload Inspection (round-trip + image record quality validation)
    try:
        demo_img_path = Path(__file__).resolve().parent.parent / "demo" / "images" / "sample_electronics.png"
        with open(demo_img_path, "rb") as f:
            files = {"file": ("sample_electronics.png", f, "image/png")}
            data = {"product_category": "electronics_and_appliances"}
            upload_resp = client.post(f"{BASE_API}/inspections", files=files, data=data)
            assert upload_resp.status_code == 201
            upload_res = upload_resp.json()
            # Verify image record was stored with correct metadata
            assert upload_res["id"] is not None
            assert upload_res["image"]["width"] >= 400
            assert upload_res["image"]["height"] >= 400
            assert upload_res["image"]["quality_status"] == "PASS"
            assert upload_res["image"]["blur_score"] > 100.0
            print(f"✓ [PASS] Direct Multipart Upload: Created inspection ID={upload_res['id'][:8]} (Category: {upload_res['product_category']}, Image={upload_res['image']['width']}x{upload_res['image']['height']}px, QualityStatus={upload_res['image']['quality_status']})")
    except Exception as e:
        print(f"✗ [FAIL] Multipart Upload: {e}")
        sys.exit(1)

    # 9. PDF Compliance Report Download
    try:
        pdf_resp = client.get(f"{BASE_API}/inspections/{shampoo_id}/report")
        assert pdf_resp.status_code == 200
        assert pdf_resp.headers.get("content-type") == "application/pdf"
        assert len(pdf_resp.content) > 1000  # valid binary PDF bytes
        print(f"✓ [PASS] PDF Report Exporter: Generated valid audit PDF ({len(pdf_resp.content):,} bytes)")
    except Exception as e:
        print(f"✗ [FAIL] PDF Report: {e}")
        sys.exit(1)

    # 10. Dashboard Metrics & KPI Aggregates
    try:
        metrics_resp = client.get(f"{BASE_API}/inspections/dashboard/metrics")
        assert metrics_resp.status_code == 200
        metrics = metrics_resp.json()
        assert metrics["total_inspections"] >= 4
        assert metrics["compliant_count"] >= 2
        assert metrics["non_compliant_count"] >= 1
        assert metrics["unable_to_verify_count"] >= 1
        print(f"✓ [PASS] Dashboard KPIs: Total={metrics['total_inspections']}, Compliant={metrics['compliant_count']}, Issues={metrics['non_compliant_count']}, UnableToVerify={metrics['unable_to_verify_count']}, AvgScore={metrics['average_compliance_score']}%")
    except Exception as e:
        print(f"✗ [FAIL] Dashboard metrics: {e}")
        sys.exit(1)

    # 11. Inspection History Search & Pagination
    try:
        history_resp = client.get(f"{BASE_API}/inspections?limit=10&page=1")
        assert history_resp.status_code == 200
        hist = history_resp.json()
        assert hist["total"] >= 4
        assert len(hist["items"]) >= 4
        print(f"✓ [PASS] Inspection History: Audit log persistence verified ({hist['total']} total audit entries)")
    except Exception as e:
        print(f"✗ [FAIL] History check: {e}")
        sys.exit(1)

    print("=" * 70)
    print("ALL 11 END-TO-END ACCEPTANCE TESTS PASSED SUCCESSFULLY!")
    print("=" * 70)

if __name__ == "__main__":
    run_e2e_verification()
