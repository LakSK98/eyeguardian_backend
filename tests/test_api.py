import io
import pytest
from app.services.ml_service import ml_service

def test_health_endpoint(client):
    """Verify GET /api/health returns OK and app metadata."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "OK"
    assert "version" in data
    assert "EyeGUARDIAN" in data["app"]

def test_create_screening(client):
    """Verify POST /api/screenings creates a new session and returns IDs."""
    payload = {
        "user_name": "Kavindi",
        "age": 15,
        "sex": "female",
        "symptoms": ["headache", "blurred vision"]
    }
    response = client.post("/api/screenings", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "screening_id" in data
    assert data["status"] == "waiting_for_images"
    assert "LEFT_CAM_01" in data["camera_devices"]
    assert "RIGHT_CAM_01" in data["camera_devices"]

def test_get_screening(client):
    """Verify GET /api/screenings/{screening_id} returns session state."""
    # First create
    res = client.post("/api/screenings", json={"user_name": "TestUser", "age": 25, "sex": "male", "symptoms": []})
    screening_id = res.json()["screening_id"]

    # Query status
    response = client.get(f"/api/screenings/{screening_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["screening_id"] == screening_id
    assert data["status"] == "waiting_for_images"
    assert isinstance(data["images"], list)

def test_invalid_screening_id(client):
    """Verify GET and POST with invalid screening ID returns 404."""
    response = client.get("/api/screenings/non_existent_id_9999")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()

def test_invalid_camera_device(client, sharp_image_bytes):
    """Verify POST with invalid X-Device-Id returns 400."""
    res = client.post("/api/screenings", json={"user_name": "DeviceTest", "age": 20, "sex": "female"})
    screening_id = res.json()["screening_id"]

    response = client.post(
        f"/api/screenings/{screening_id}/images",
        headers={"X-Device-Id": "INVALID_CAM_99"},
        files={"file": ("test.jpg", io.BytesIO(sharp_image_bytes), "image/jpeg")}
    )
    assert response.status_code == 400
    assert "Invalid or missing 'X-Device-Id'" in response.json()["detail"]

def test_image_upload_sharp(client, sharp_image_bytes):
    """Verify uploading a high-quality image passes OpenCV checks."""
    res = client.post("/api/screenings", json={"user_name": "SharpTest", "age": 22, "sex": "female"})
    screening_id = res.json()["screening_id"]

    response = client.post(
        f"/api/screenings/{screening_id}/images",
        headers={"X-Device-Id": "LEFT_CAM_01"},
        files={"file": ("left.jpg", io.BytesIO(sharp_image_bytes), "image/jpeg")}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["quality_score"] > 0.5
    assert data["blur_score"] > 40.0
    assert data["eye_side"] == "left"
    assert data["device_id"] == "LEFT_CAM_01"

def test_image_quality_failure_blurry(client, blurry_image_bytes):
    """Verify uploading an overly blurry image fails quality checks and prompts recapture."""
    res = client.post("/api/screenings", json={"user_name": "BlurTest", "age": 22, "sex": "female"})
    screening_id = res.json()["screening_id"]

    response = client.post(
        f"/api/screenings/{screening_id}/images",
        headers={"X-Device-Id": "RIGHT_CAM_01"},
        files={"file": ("blurry.jpg", io.BytesIO(blurry_image_bytes), "image/jpeg")}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is False
    assert "IMAGE_QUALITY_FAILED" in data["reason"]
    assert "Another capture is needed" in data["reason"]

def test_vision_test_submission(client):
    """Verify submitting color and near vision tests."""
    res = client.post("/api/screenings", json={"user_name": "VisionTestUser", "age": 30, "sex": "male"})
    screening_id = res.json()["screening_id"]

    payload = {
        "color_answers": ["12", "8", "29"],
        "near_answers": ["A", "E", "F"],
        "color_score": 1.0,
        "near_vision_score": 0.85
    }
    response = client.post(f"/api/screenings/{screening_id}/vision-tests", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "recorded"
    assert data["color_score"] == 1.0
    assert data["near_vision_score"] == 0.85

def test_analysis_without_images(client):
    """Verify requesting analysis before uploading images returns 400."""
    res = client.post("/api/screenings", json={"user_name": "NoImageUser", "age": 28, "sex": "female"})
    screening_id = res.json()["screening_id"]

    response = client.post(f"/api/screenings/{screening_id}/analyse")
    assert response.status_code == 400
    assert "No images available for analysis" in response.json()["detail"]

def test_analysis_and_result_flow(client, sharp_image_bytes):
    """Verify full analysis execution and result retrieval."""
    # 1. Create
    res = client.post("/api/screenings", json={
        "user_name": "FullFlowUser",
        "age": 19,
        "sex": "female",
        "symptoms": ["headache"]
    })
    screening_id = res.json()["screening_id"]

    # 2. Upload Left and Right Images
    client.post(
        f"/api/screenings/{screening_id}/images",
        headers={"X-Device-Id": "LEFT_CAM_01"},
        files={"file": ("left.jpg", io.BytesIO(sharp_image_bytes), "image/jpeg")}
    )
    client.post(
        f"/api/screenings/{screening_id}/images",
        headers={"X-Device-Id": "RIGHT_CAM_01"},
        files={"file": ("right.jpg", io.BytesIO(sharp_image_bytes), "image/jpeg")}
    )

    # 3. Vision Tests
    client.post(f"/api/screenings/{screening_id}/vision-tests", json={
        "color_answers": ["12"],
        "near_answers": ["A"],
        "color_score": 0.95,
        "near_vision_score": 0.90
    })

    # 4. Trigger Analysis
    analyse_res = client.post(f"/api/screenings/{screening_id}/analyse")
    assert analyse_res.status_code == 200
    a_data = analyse_res.json()
    assert a_data["status"] == "analyzed"
    assert a_data["overall_risk"] in ["low", "attention", "uncertain"]
    assert 0 <= a_data["overall_score"] <= 100
    assert len(a_data["analyses"]) == 2

    # 5. Fetch Result Report
    result_res = client.get(f"/api/screenings/{screening_id}/result")
    assert result_res.status_code == 200
    r_data = result_res.json()
    assert r_data["screening_id"] == screening_id
    assert "left" in r_data["image_quality"]
    assert "right" in r_data["image_quality"]
    assert len(r_data["analyses"]) == 2
    assert r_data["vision_tests"]["color_score"] == 0.95
    assert len(r_data["guidance"]) >= 3
    assert "Preliminary screening only" in r_data["disclaimer"]
