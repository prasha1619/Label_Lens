import pytest
from app.services.ar_inspection_service import ARInspectionService
import numpy as np
import cv2

def test_ar_inspection_service_frame_processing():
    # Create a synthetic label image (black background with clean white text)
    img = np.zeros((600, 600, 3), dtype=np.uint8)
    cv2.putText(img, "MRP Rs. 150.00", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
    cv2.putText(img, "NET WT: 500 g", (50, 200), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
    cv2.putText(img, "MFD: 01/2026", (50, 300), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
    
    _, img_encoded = cv2.imencode('.jpg', img)
    img_bytes = img_encoded.tobytes()

    result = ARInspectionService.analyze_frame(
        image_bytes=img_bytes,
        active_panel="front",
        package_id="Package #1",
        product_category="packaged_commodity"
    )

    assert result is not None
    assert "packages" in result
    assert "fields" in result
    assert "hud_metrics" in result
    assert result["hud_metrics"]["active_package_id"] == "Package #1"
    assert result["quality"]["is_acceptable"] is True
    assert result["processing_time_ms"] > 0


def test_ar_inspection_save_and_report():
    from fastapi.testclient import TestClient
    from app.main import app
    from app.models.user import User
    from app.database.session import SessionLocal
    from app.api.v1.endpoints.auth import get_current_user

    db = SessionLocal()
    user = db.query(User).filter(User.id == "test-ar-user").first()
    if not user:
        user = User(
            id="test-ar-user",
            full_name="Inspector AR",
            email="ar-inspector@labellens.gov.in",
            password_hash="test-hash",
            role="inspector",
            is_active=True,
        )
        db.add(user)
        db.commit()
    user_obj = user
    db.close()

    app.dependency_overrides[get_current_user] = lambda: user_obj
    try:
        img = np.zeros((600, 600, 3), dtype=np.uint8)
        cv2.putText(img, "MRP Rs. 250.00", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
        cv2.putText(img, "NET WT: 1 kg", (50, 200), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
        _, img_encoded = cv2.imencode('.jpg', img)

        client = TestClient(app)
        response = client.post(
            "/api/v1/inspections/ar-save",
            files={"file": ("frame.jpg", img_encoded.tobytes(), "image/jpeg")},
            data={
                "active_panel": "front",
                "package_id": "Package #1",
                "product_category": "packaged_commodity"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["product_category"] == "packaged_commodity"
        assert len(data.get("images", [])) > 0
        inspection_id = data["id"]

        # Verify report download endpoint works for the saved AR inspection
        report_res = client.get(f"/api/v1/inspections/{inspection_id}/report")
        assert report_res.status_code == 200
        assert report_res.headers["content-type"] == "application/pdf"
        assert len(report_res.content) > 0
    finally:
        app.dependency_overrides.clear()
