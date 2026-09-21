"""
EyeGUARDIAN Vision - End-to-End Standalone API Test Runner
Exercises the full screening flow using FastAPI TestClient with lifespan context.
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

    print("=========================================================", flush=True)
    print("   EyeGUARDIAN Vision - End-to-End API Test Runner       ", flush=True)
    print("=========================================================", flush=True)

    with TestClient(app) as client:
        # 1. Health Check
        print("\n[Step 1] Checking GET /api/health...", flush=True)
        r = client.get("/api/health")
        assert r.status_code == 200, f"Health check failed: {r.text}"
        print(f"-> Health OK: {r.json()}", flush=True)

        # 2. Create Screening
        print("\n[Step 2] Creating Screening POST /api/screenings...", flush=True)
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
        print(f"-> Screening created successfully! ID: {screening_id}", flush=True)
        print(f"-> Camera devices: {screening_data['camera_devices']}", flush=True)

        # 3. Check Initial Status
        print(f"\n[Step 3] Checking initial status GET /api/screenings/{screening_id}...", flush=True)
        r = client.get(f"/api/screenings/{screening_id}")
        assert r.status_code == 200
        print(f"-> Initial Status: {r.json()['status']}", flush=True)

        # 4. Upload Left Eye Image (Sharp)
        print(f"\n[Step 4] Uploading Left Eye Image via LEFT_CAM_01...", flush=True)
        left_jpeg = generate_test_jpeg(width=320, height=240, blurry=False)
        r = client.post(
            f"/api/screenings/{screening_id}/images",
            headers={"X-Device-Id": "LEFT_CAM_01"},
            files={"file": ("left.jpg", io.BytesIO(left_jpeg), "image/jpeg")}
        )
        assert r.status_code == 200, f"Upload left image failed: {r.text}"
        left_res = r.json()
        print(f"-> Left upload result: OK={left_res['ok']}, Quality Score={left_res['quality_score']}, Blur={left_res['blur_score']}", flush=True)

        # 5. Upload Blurry Image Test (Image Quality Check Test)
        print(f"\n[Step 5] Testing Image Quality Rejection with Blurry Image...", flush=True)
        blurry_jpeg = generate_test_jpeg(width=320, height=240, blurry=True)
        r = client.post(
            f"/api/screenings/{screening_id}/images",
            headers={"X-Device-Id": "RIGHT_CAM_01"},
            files={"file": ("blurry.jpg", io.BytesIO(blurry_jpeg), "image/jpeg")}
        )
        assert r.status_code == 200
        blurry_res = r.json()
        print(f"-> Blurry image flagged: OK={blurry_res['ok']}, Reason: {blurry_res['reason']}", flush=True)

        # 6. Upload Right Eye Image (Sharp)
        print(f"\n[Step 6] Uploading Good Right Eye Image via RIGHT_CAM_01...", flush=True)
        right_jpeg = generate_test_jpeg(width=320, height=240, blurry=False)
        r = client.post(
            f"/api/screenings/{screening_id}/images",
            headers={"X-Device-Id": "RIGHT_CAM_01"},
            files={"file": ("right.jpg", io.BytesIO(right_jpeg), "image/jpeg")}
        )
        assert r.status_code == 200
        right_res = r.json()
        print(f"-> Right upload result: OK={right_res['ok']}, Quality Score={right_res['quality_score']}", flush=True)

        # 7. Check Updated Status
        print(f"\n[Step 7] Verifying updated status...", flush=True)
        r = client.get(f"/api/screenings/{screening_id}")
        assert r.status_code == 200
        status_data = r.json()
        print(f"-> Status: {status_data['status']}, Images received: {len(status_data['images'])}", flush=True)

        # 8. Submit Vision Tests
        print(f"\n[Step 8] Submitting Vision Tests POST /api/screenings/{screening_id}/vision-tests...", flush=True)
        vt_payload = {
            "color_answers": ["12", "8", "29"],
            "near_answers": ["A", "E", "F"],
            "color_score": 1.0,
            "near_vision_score": 0.9
        }
        r = client.post(f"/api/screenings/{screening_id}/vision-tests", json=vt_payload)
        assert r.status_code == 200
        print(f"-> Vision tests recorded: {r.json()}", flush=True)

        # 9. Run Analysis
        print(f"\n[Step 9] Requesting Analysis POST /api/screenings/{screening_id}/analyse...", flush=True)
        r = client.post(f"/api/screenings/{screening_id}/analyse")
        assert r.status_code == 200, f"Analysis failed: {r.text}"
        analyse_data = r.json()
        print(f"-> Analysis complete!", flush=True)
        print(f"-> Overall Risk: {analyse_data['overall_risk']}", flush=True)
        print(f"-> Overall Score: {analyse_data['overall_score']}/100", flush=True)
        print(f"-> Eye analyses: {analyse_data['analyses']}", flush=True)

        # 10. Fetch Final Result
        print(f"\n[Step 10] Fetching Screening Report GET /api/screenings/{screening_id}/result...", flush=True)
        r = client.get(f"/api/screenings/{screening_id}/result")
        assert r.status_code == 200, f"Get result failed: {r.text}"
        result_data = r.json()
        print(f"-> Report Retrieved Successfully!", flush=True)
        print(f"-> Overall Score: {result_data['overall_score']}", flush=True)
        print(f"-> Overall Risk:  {result_data['overall_risk']}", flush=True)
        print(f"-> Image Quality: {result_data['image_quality']}", flush=True)
        print(f"-> Disclaimer:    {result_data['disclaimer']}", flush=True)
        print(f"-> Guidance:      {result_data['guidance']}", flush=True)

        # 11. Test List Screenings (Historical Records)
        print(f"\n[Step 11] Testing GET /api/screenings (Database Listing)...", flush=True)
        r = client.get("/api/screenings")
        assert r.status_code == 200
        list_data = r.json()
        assert len(list_data) >= 1
        print(f"-> Historical Screenings Count: {len(list_data)}", flush=True)
        print(f"-> Latest Record: {list_data[0]['screening_id']} ({list_data[0]['user_name']})", flush=True)

        # 12. Test Frontend Static Mount
        print(f"\n[Step 12] Testing Static Frontend Serving GET /index.html...", flush=True)
        r = client.get("/index.html")
        assert r.status_code == 200
        assert "EyeGUARDIAN" in r.text
        print(f"-> Frontend static mount verified: Status {r.status_code} (HTML served)", flush=True)

        # 13. Test Frontend API Client file
        print(f"\n[Step 13] Testing Static JS Serving GET /js/api.js...", flush=True)
        r = client.get("/js/api.js")
        assert r.status_code == 200
        assert "EyeGuardAPI" in r.text
        print(f"-> Frontend api.js verified: Status {r.status_code} (JS served)", flush=True)

        print("\n=========================================================", flush=True)
        print("   ALL 13 END-TO-END TESTS COMPLETED SUCCESSFULLY!       ", flush=True)
        print("=========================================================", flush=True)

if __name__ == "__main__":
    run_e2e_flow()
