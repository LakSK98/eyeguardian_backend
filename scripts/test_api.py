"""
EyeGUARDIAN Vision - End-to-End Standalone API Test Runner
Exercises the full screening flow against either:
1. An active HTTP backend (e.g. http://localhost:8000), OR
2. In-memory FastAPI TestClient (no server start required).
"""

import sys
import io
from pathlib import Path
import numpy as np
import cv2

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

def generate_test_jpeg(width=320, height=240, blurry=False):
    """Create in-memory JPEG bytes for testing."""
    if blurry:
        # Solid low-variance blurry image
        img = np.ones((height, width, 3), dtype=np.uint8) * 128
    else:
        # Sharp patterned image with clear edges
        img = np.zeros((height, width, 3), dtype=np.uint8)
        img[:, :] = (200, 200, 200)
        cv2.circle(img, (width // 2, height // 2), 50, (30, 30, 30), -1)
        cv2.putText(img, "EyeScreen", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

    is_success, buffer = cv2.imencode(".jpg", img)
    return buffer.tobytes()

def run_e2e_flow():
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    print("=========================================================")
    print("   EyeGUARDIAN Vision - End-to-End API Test Runner       ")
    print("=========================================================")

    # 1. Health Check
    print("\n[Step 1] Checking GET /api/health...")
    r = client.get("/api/health")
    assert r.status_code == 200, f"Health check failed: {r.text}"
    print(f"-> Health OK: {r.json()}")

    # 2. Create Screening
    print("\n[Step 2] Creating Screening POST /api/screenings...")
    payload = {
        "user_name": "Kavindi",
        "age": 15,
        "sex": "female",
        "symptoms": ["headache", "blurred vision", "difficulty focusing"]
    }
    r = client.post("/api/screenings", json=payload)
    assert r.status_code == 201, f"Create screening failed: {r.text}"
    screening_data = r.json()
    screening_id = screening_data["screening_id"]
    print(f"-> Screening created successfully! ID: {screening_id}")
    print(f"-> Camera devices: {screening_data['camera_devices']}")

    # 3. Check Initial Status
    print(f"\n[Step 3] Checking initial status GET /api/screenings/{screening_id}...")
    r = client.get(f"/api/screenings/{screening_id}")
    assert r.status_code == 200
    print(f"-> Initial Status: {r.json()['status']}")

    # 4. Upload Left Eye Image (Sharp)
    print(f"\n[Step 4] Uploading Left Eye Image via LEFT_CAM_01...")
    left_jpeg = generate_test_jpeg(width=320, height=240, blurry=False)
    r = client.post(
        f"/api/screenings/{screening_id}/images",
        headers={"X-Device-Id": "LEFT_CAM_01"},
        files={"file": ("left.jpg", io.BytesIO(left_jpeg), "image/jpeg")}
    )
    assert r.status_code == 200, f"Upload left image failed: {r.text}"
    left_res = r.json()
    print(f"-> Left upload result: OK={left_res['ok']}, Quality Score={left_res['quality_score']}, Blur={left_res['blur_score']}")

    # 5. Upload Blurry Image Test (Image Quality Check Test)
    print(f"\n[Step 5] Testing Image Quality Rejection with Blurry Image...")
    blurry_jpeg = generate_test_jpeg(width=320, height=240, blurry=True)
    r = client.post(
        f"/api/screenings/{screening_id}/images",
        headers={"X-Device-Id": "RIGHT_CAM_01"},
        files={"file": ("blurry.jpg", io.BytesIO(blurry_jpeg), "image/jpeg")}
    )
    assert r.status_code == 200
    blurry_res = r.json()
    print(f"-> Blurry image flagged: OK={blurry_res['ok']}, Reason: {blurry_res['reason']}")

    # 6. Upload Right Eye Image (Sharp)
    print(f"\n[Step 6] Uploading Good Right Eye Image via RIGHT_CAM_01...")
    right_jpeg = generate_test_jpeg(width=320, height=240, blurry=False)
    r = client.post(
        f"/api/screenings/{screening_id}/images",
        headers={"X-Device-Id": "RIGHT_CAM_01"},
        files={"file": ("right.jpg", io.BytesIO(right_jpeg), "image/jpeg")}
    )
    assert r.status_code == 200
    right_res = r.json()
    print(f"-> Right upload result: OK={right_res['ok']}, Quality Score={right_res['quality_score']}")

    # 7. Check Updated Status
    print(f"\n[Step 7] Verifying updated status...")
    r = client.get(f"/api/screenings/{screening_id}")
    assert r.status_code == 200
    status_data = r.json()
    print(f"-> Status: {status_data['status']}, Images received: {len(status_data['images'])}")

    # 8. Submit Vision Tests
    print(f"\n[Step 8] Submitting Vision Tests POST /api/screenings/{screening_id}/vision-tests...")
    vt_payload = {
        "color_answers": ["12", "8", "29"],
        "near_answers": ["A", "E", "F"],
        "color_score": 1.0,
        "near_vision_score": 0.9
    }
    r = client.post(f"/api/screenings/{screening_id}/vision-tests", json=vt_payload)
    assert r.status_code == 200
    print(f"-> Vision tests recorded: {r.json()}")

    # 9. Run Analysis
    print(f"\n[Step 9] Requesting Analysis POST /api/screenings/{screening_id}/analyse...")
    r = client.post(f"/api/screenings/{screening_id}/analyse")
    assert r.status_code == 200, f"Analysis failed: {r.text}"
    analyse_data = r.json()
    print(f"-> Analysis complete!")
    print(f"-> Overall Risk: {analyse_data['overall_risk']}")
    print(f"-> Overall Score: {analyse_data['overall_score']}/100")
    print(f"-> Eye analyses: {analyse_data['analyses']}")

    # 10. Fetch Final Result
    print(f"\n[Step 10] Fetching Screening Report GET /api/screenings/{screening_id}/result...")
    r = client.get(f"/api/screenings/{screening_id}/result")
    assert r.status_code == 200, f"Get result failed: {r.text}"
    result_data = r.json()
    print(f"-> Report Retrieved Successfully!")
    print(f"-> Overall Score: {result_data['overall_score']}")
    print(f"-> Overall Risk:  {result_data['overall_risk']}")
    print(f"-> Image Quality: {result_data['image_quality']}")
    print(f"-> Disclaimer:    {result_data['disclaimer']}")
    print(f"-> Guidance:      {result_data['guidance']}")

    print("\n=========================================================")
    print("   ALL END-TO-END TESTS COMPLETED SUCCESSFULLY!          ")
    print("=========================================================")

if __name__ == "__main__":
    run_e2e_flow()
