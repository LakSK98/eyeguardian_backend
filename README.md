# EyeGUARDIAN Vision - Backend System

EyeGUARDIAN Vision is a prototype wearable preliminary eye-screening system using dual ESP32-CAM boards (OV2640 sensors) for non-diagnostic preliminary evaluation. This repository houses the Python REST backend, SQLite database, OpenCV image quality analysis, TensorFlow/Keras transfer-learning classification pipeline, scoring service, ESP32-CAM firmware, and test suites.

> [!IMPORTANT]
> **Medical Disclaimer & Non-Diagnostic Notice**:
> This software is intended strictly for **PRELIMINARY SCREENING DEMONSTRATIONS ONLY**. It does NOT provide a medical diagnosis, clinical grade confirmation, or treatment recommendation. All outputs represent preliminary risk indicators that recommend consultation with a qualified eye-care professional.

---

## Architecture Overview

```
Frontend Web App (http://localhost:3000)
    │
    │  REST API (JSON / Multipart)
    ▼
FastAPI Backend (http://localhost:8000)
    ├── SQLite Database (eyeguardian.db)
    ├── OpenCV Quality Checker (Blur & Exposure validation)
    ├── TensorFlow MobileNetV2 (External Eye Transfer Learning)
    ├── Scoring & Risk Engine (Multi-modal synthesis)
    └── ESP32-CAM Ingestion Nodes (LEFT_CAM_01 / RIGHT_CAM_01)
```

---

## 1. Prerequisites & Environment Setup

- **Python**: Python 3.10 or 3.11+
- **Operating System**: Windows / Linux / macOS
- **Hardware (Optional for physical testing)**:
  - 2x AI-Thinker ESP32-CAM boards with OV2640 cameras
  - FTDI USB-to-UART programmer (3.3V/5V)

### Clone / Navigate to Directory (Windows PowerShell)
```powershell
cd "c:\Users\Lakshitha\Downloads\Web Tech\EyeGuardBE\eyeguardian_backend"
```

### Create and Activate Virtual Environment (Recommended)
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### Install Dependencies
```powershell
pip install -r requirements.txt
```

---

## 2. Environment Configuration

Copy `.env.example` to `.env` (optional, defaults are built-in):
```powershell
Copy-Item .env.example .env
```

Configuration parameters:
| Parameter | Default | Purpose |
|---|---|---|
| `BACKEND_HOST` | `0.0.0.0` | Listen host interface |
| `BACKEND_PORT` | `8000` | Port for REST API server |
| `FRONTEND_ORIGIN` | `http://localhost:3000` | CORS origin for frontend |
| `DATABASE_URL` | `sqlite:///./eyeguardian.db` | SQLite database URI |
| `MAX_UPLOAD_SIZE_MB` | `10` | Maximum camera upload size |
| `BLUR_THRESHOLD` | `40.0` | Minimum Laplacian variance |
| `BRIGHTNESS_MIN` | `35.0` | Minimum grayscale intensity |
| `BRIGHTNESS_MAX` | `230.0` | Maximum grayscale intensity |

---

## 3. Starting the Backend Server

Start Uvicorn server:
```powershell
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

- **API Base URL**: `http://localhost:8000`
- **Interactive Swagger Docs**: `http://localhost:8000/docs`
- **ReDoc Documentation**: `http://localhost:8000/redoc`

---

## 4. API Endpoints & Screening Flow

### End-to-End Screening Sequence:

1. **Health Check**:
   ```http
   GET /api/health
   ```
   *Response*:
   ```json
   {
     "status": "OK",
     "version": "1.0.0",
     "app": "EyeGUARDIAN Vision Backend"
   }
   ```

2. **Start Screening Session**:
   ```http
   POST /api/screenings
   Content-Type: application/json

   {
     "user_name": "Kavindi",
     "age": 15,
     "sex": "female",
     "symptoms": ["headache", "blurred vision", "difficulty focusing"]
   }
   ```
   *Response*:
   ```json
   {
     "screening_id": "9b1c78e24fa1",
     "status": "waiting_for_images",
     "camera_devices": ["LEFT_CAM_01", "RIGHT_CAM_01"]
   }
   ```

3. **Check Screening Status**:
   ```http
   GET /api/screenings/{screening_id}
   ```

4. **Upload Eye Images (ESP32-CAM / Frontend / Test Client)**:
   ```http
   POST /api/screenings/{screening_id}/images
   X-Device-Id: LEFT_CAM_01
   Content-Type: multipart/form-data
   ```
   (Repeat for `X-Device-Id: RIGHT_CAM_01`)

   *Response on success*:
   ```json
   {
     "ok": true,
     "quality_score": 0.91,
     "blur_score": 132.5,
     "brightness": 121.4,
     "reason": "OK",
     "eye_side": "left",
     "device_id": "LEFT_CAM_01"
   }
   ```
   *Response on blurry/poor exposure capture*:
   ```json
   {
     "ok": false,
     "quality_score": 0.25,
     "blur_score": 12.3,
     "brightness": 115.0,
     "reason": "IMAGE_QUALITY_FAILED: Image is excessively blurry. Another capture is needed."
   }
   ```

5. **Submit Vision Test Results**:
   ```http
   POST /api/screenings/{screening_id}/vision-tests
   Content-Type: application/json

   {
     "color_answers": ["12", "8", "29"],
     "near_answers": ["A", "E", "F"],
     "color_score": 1.0,
     "near_vision_score": 0.9
   }
   ```

6. **Trigger Analysis**:
   ```http
   POST /api/screenings/{screening_id}/analyse
   ```

7. **Retrieve Complete Screening Result**:
   ```http
   GET /api/screenings/{screening_id}/result
   ```

---

## 5. Machine Learning Pipeline

### Dataset Structure
Place properly licensed and anonymized external-eye images under `data/external_eye/`:
```text
data/external_eye/
├── normal/
├── redness/
├── ptosis/
├── leukocoria/
└── other_abnormal/
```

> [!NOTE]
> To seed synthetic demonstration images immediately without downloading external patient data:
> ```powershell
> python scripts/seed_sample_data.py
> ```

### Training the Model
Train the MobileNetV2 transfer learning network:
```powershell
python ml/train.py --epochs 10 --batch-size 16
```
This saves:
- `models/external_eye.keras`
- `models/class_names.json`

### Evaluating the Model
Run full statistical evaluation on the validation split:
```powershell
python ml/evaluate.py
```
Prints Accuracy, Precision, Recall, F1 Score, Confusion Matrix, and Scikit-learn Classification Report.

---

## 6. ESP32-CAM Firmware Setup

1. Open Arduino IDE.
2. Install the ESP32 board package: `Tools` > `Board` > `Boards Manager...` > search for `esp32` by Espressif.
3. Open `firmware/esp32_cam.ino`.
4. In the sketch:
   - Set `WIFI_SSID` and `WIFI_PASSWORD`.
   - Set `BACKEND_HOST` to your computer's local Wi-Fi IPv4 address (e.g. `192.168.1.100`).
   - For board 1: `#define DEVICE_ID "LEFT_CAM_01"`
   - For board 2: `#define DEVICE_ID "RIGHT_CAM_01"`
5. Select Board: **AI Thinker ESP32-CAM**.
6. Connect FTDI programmer (connect GPIO 0 to GND during flash), compile and upload.
7. Disconnect GPIO 0 from GND and reboot the board.

---

## 7. Testing & Verification

### Running Automated Tests (Pytest)
```powershell
pytest -v
```

### Running Standalone End-to-End Simulation
```powershell
python scripts/test_api.py
```

---

## 8. Troubleshooting

- **CORS Issues with Frontend**:
  Update `FRONTEND_ORIGIN` in `.env` to match the exact URL of your frontend (e.g. `http://localhost:3000`).
- **ML Model Not Loaded / Fallback Active**:
  If `models/external_eye.keras` does not exist, the backend gracefully flags `model_status: "ML_MODEL_NOT_READY"` without crashing. Run `python scripts/seed_sample_data.py` followed by `python ml/train.py` to generate the weights.
- **ESP32 Camera Resetting (Brownout)**:
  ESP32-CAM Wi-Fi transmission causes current spikes. Ensure the power supply provides at least 5V @ 2A with a decoupling capacitor (e.g., 100uF - 470uF) across VCC and GND.
