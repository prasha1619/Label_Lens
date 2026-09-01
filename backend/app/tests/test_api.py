import io
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.api.v1.endpoints.auth import get_current_user
from app.models.user import User

client = TestClient(app)

mock_user = User(
    id="test-user-123",
    full_name="Prashant Kumar",
    email="test@labellens.gov.in",
    role="inspector",
    is_active=True,
)

@pytest.fixture(autouse=True)
def override_auth():
    from app.database.session import SessionLocal
    db = SessionLocal()
    user = db.query(User).filter(User.id == "test-user-123").first()
    if not user:
        user = User(
            id="test-user-123",
            full_name="Prashant Kumar",
            email="test@labellens.gov.in",
            password_hash="test-hash",
            role="inspector",
            is_active=True,
        )
        db.add(user)
        db.commit()
    user_id = user.id
    db.close()

    def get_test_user():
        db_sess = SessionLocal()
        u = db_sess.query(User).filter(User.id == user_id).first()
        return u

    app.dependency_overrides[get_current_user] = get_test_user
    yield
    app.dependency_overrides.clear()

def test_health_endpoint():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ONLINE"
    assert "computer_vision" in data
    assert "ocr_service" in data
    assert "rule_engine" in data

def test_rules_listing():
    response = client.get("/api/v1/rules")
    assert response.status_code == 200
    categories = response.json()
    assert len(categories) >= 4
    cat_ids = [c["category_id"] for c in categories]
    assert "packaged_commodity" in cat_ids
    assert "food_and_beverages" in cat_ids
    assert "cosmetics_and_toiletries" in cat_ids

def test_demo_samples_listing():
    response = client.get("/api/v1/demo/samples")
    assert response.status_code == 200
    samples = response.json()
    assert len(samples) >= 3
    keys = [s["key"] for s in samples]
    assert "compliant_shampoo" in keys
    assert "missing_consumer_care_biscuit" in keys
    assert "blurry_label_oil" in keys

def test_run_demo_inspection_compliant():
    response = client.post("/api/v1/demo/run/compliant_shampoo")
    assert response.status_code == 200
    data = response.json()
    assert data["overall_status"] in ("COMPLIANT", "NON_COMPLIANT", "NEEDS_REVIEW", "UNABLE_TO_VERIFY")
    assert data["total_checks"] > 0
    assert data["compliance_score"] is not None

def test_run_demo_inspection_blurry():
    response = client.post("/api/v1/demo/run/blurry_label_oil")
    assert response.status_code == 200
    data = response.json()
    assert data["overall_status"] in ("COMPLIANT", "NON_COMPLIANT", "NEEDS_REVIEW", "UNABLE_TO_VERIFY")


def test_profile_photo_flow():
    # Test uploading a small png
    img_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    file = io.BytesIO(img_bytes)
    response = client.post("/api/v1/auth/photo", files={"file": ("test_avatar.png", file, "image/png")})
    assert response.status_code == 200
    data = response.json()
    assert "user" in data
    assert data["user"]["profile_photo_url"] is not None

    # Test removing photo
    del_res = client.delete("/api/v1/auth/photo")
    assert del_res.status_code == 200
    assert del_res.json()["user"]["profile_photo_url"] is None

