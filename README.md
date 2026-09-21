# EyeGUARDIAN Vision — Backend Setup Guide & API Reference

> A complete, self-contained guide to setting up, running, and testing the **EyeGUARDIAN Vision** Python backend on a fresh PC, along with the full REST API documentation.

---

## ⚡ Quick Start (On a Fresh PC)

Run these commands in Windows PowerShell:

```powershell
# 1. Clone the repository
git clone https://github.com/your-org/eyeguardian_backend.git
cd eyeguardian_backend

# 2. Allow PowerShell script execution (required on fresh Windows)
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

# 3. Create and activate a virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# 4. Install all dependencies
pip install -r requirements.txt

# 5. Start the backend server
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

👉 **Interactive Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)  
👉 **Health Check Endpoint**: [http://localhost:8000/api/health](http://localhost:8000/api/health)

---

## 1. Fresh PC Prerequisites

Before cloning and running the backend on a brand new PC, ensure the following are installed:

1. **Git**:
   - Download from [git-scm.com](https://git-scm.com/downloads).
2. **Python 3.10 or 3.11+**:
   - Download from [python.org](https://www.python.org/downloads/).
   - ⚠️ **CRITICAL ON WINDOWS**: Check the box **"Add python.exe to PATH"** during installation.
3. **Verify installations**:
   Open PowerShell and run:
   ```powershell
   git --version
   python --version
   pip --version
   ```

---

## 2. Step-by-Step Installation on a Fresh PC

### Step 2.1: Clone the Repository
```powershell
git clone https://github.com/your-org/eyeguardian_backend.git
cd eyeguardian_backend
```
> Replace `https://github.com/your-org/eyeguardian_backend.git` with your actual repository URL.

### Step 2.2: Enable PowerShell Script Execution
Fresh Windows installations restrict script execution by default. Run:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

### Step 2.3: Create and Activate Virtual Environment
Creating an isolated virtual environment prevents library conflicts:
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```
*(You will see `(venv)` appear at the beginning of your command line.)*

### Step 2.4: Install Required Packages
Install all backend, OpenCV, TensorFlow, and testing dependencies:
```powershell
pip install -r requirements.txt
```

### Step 2.5: (Optional) Configure Environment Variables
Copy `.env.example` to `.env` and edit as needed:
```powershell
Copy-Item .env.example .env
```
Default settings in `.env`:
```env
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000
FRONTEND_ORIGIN=http://localhost:3000
DATABASE_URL=sqlite:///./eyeguardian.db
MAX_UPLOAD_SIZE_MB=10
BLUR_THRESHOLD=40.0
BRIGHTNESS_MIN=35.0
BRIGHTNESS_MAX=230.0
```

---

## 3. Starting and Stopping the Server

### Starting the Server
```powershell
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
- `--host 0.0.0.0`: Listens on both localhost and local Wi-Fi IP (so ESP32-CAMs and other computers can connect).
- `--port 8000`: Backend server port.
- `--reload`: Automatically restarts the server whenever code changes.

### Stopping the Server
Press `Ctrl + C` in the PowerShell terminal.

---

## 4. Verifying the Fresh Installation

We provide two automated verification tools to ensure everything works on your fresh PC:

### Option A: One-Command Simulation Runner (Recommended)
In a new PowerShell window, run:
```powershell
python scripts/test_api.py
```
This automatically tests:
- Server health (`/api/health`)
- Creating a screening session (`/api/screenings`)
- Left and right eye camera uploads
- Rejection of blurry images via OpenCV
- Submitting interactive vision test answers
- Running TensorFlow MobileNetV2 ML inference
- Retrieving the final structured preliminary screening report

### Option B: Automated Pytest Suite
```powershell
python -m pytest -v tests/test_api.py
```
Executes 10 unit and integration tests covering all routes and error scenarios.

---

## 5. Machine Learning Setup on a Fresh PC

### 5.1 Generate Seed Sample Dataset (If You Don't Have Real Images Yet)
If testing on a fresh PC without real patient photos, generate 60 sample images across 5 classes:
```powershell
python scripts/seed_sample_data.py
```
This populates:
```text
data/external_eye/
├── normal/
├── redness/
├── ptosis/
├── leukocoria/
└── other_abnormal/
```

### 5.2 Training the Model on a Fresh PC
Train the MobileNetV2 transfer-learning classifier:
```powershell
$env:PYTHONIOENCODING="utf-8"
python ml/train.py --epochs 10 --batch-size 16 --learning-rate 0.0001 --fine-tune
```
This automatically saves:
- `models/external_eye.keras`
- `models/class_names.json`

### 5.3 Evaluating the Model
```powershell
$env:PYTHONIOENCODING="utf-8"
python ml/evaluate.py
```
Outputs accuracy, precision, recall, F1-score, and a complete confusion matrix.

### 5.4 Hot-Reloading Model Weights
To load newly trained weights without stopping your running server:
```http
POST http://localhost:8000/api/model/reload
```

---

## 6. Complete REST API Reference

**Base URL**: `http://localhost:8000`  
**Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)  
**ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

### Screening Lifecycle Sequence
```
1. POST /api/screenings            ──> Start screening & receive unique screening_id
2. POST /api/screenings/{id}/images ──> Upload camera captures (X-Device-Id: LEFT_CAM_01 / RIGHT_CAM_01)
3. GET  /api/screenings/{id}       ──> Poll until images are received
4. POST /api/screenings/{id}/vision-tests ──> Record interactive vision tests
5. POST /api/screenings/{id}/analyse      ──> Run OpenCV + ML inference + risk scoring
6. GET  /api/screenings/{id}/result       ──> Fetch structured report with guidance
```

---

### 6.1 System & Health Endpoints

#### `GET /api/health`
Check if backend is operational.
- **Response `200 OK`**:
  ```json
  {
    "status": "OK",
    "version": "1.0.0",
    "app": "EyeGUARDIAN Vision Backend"
  }
  ```

#### `GET /api/model/status`
Check whether the MobileNetV2 classification model is loaded and which classes are active.
- **Response `200 OK`**:
  ```json
  {
    "model_ready": true,
    "classes": ["leukocoria", "normal", "other_abnormal", "ptosis", "redness"],
    "model_file_exists": true,
    "model_file_path": "c:\\Users\\...\\models\\external_eye.keras"
  }
  ```

#### `POST /api/model/reload`
Reload freshly trained weights from `models/external_eye.keras` into memory.
- **Response `200 OK`**:
  ```json
  {
    "reloaded": true,
    "model_ready": true,
    "classes": ["leukocoria", "normal", "other_abnormal", "ptosis", "redness"]
  }
  ```

---

### 6.2 Screening Session Endpoints

#### `POST /api/screenings`
Initializes a new screening session with patient demographic details and reported symptoms.
- **Headers**: `Content-Type: application/json`
- **Request Body**:
  ```json
  {
    "user_name": "Kavindi",
    "age": 15,
    "sex": "female",
    "symptoms": [
      "headache",
      "blurred vision",
      "difficulty focusing"
    ]
  }
  ```
- **Response `201 Created`**:
  ```json
  {
    "screening_id": "65908dd9796e",
    "status": "waiting_for_images",
    "camera_devices": [
      "LEFT_CAM_01",
      "RIGHT_CAM_01"
    ]
  }
  ```
- **cURL Example**:
  ```bash
  curl -X POST "http://localhost:8000/api/screenings" \
    -H "Content-Type: application/json" \
    -d "{\"user_name\":\"Kavindi\",\"age\":15,\"sex\":\"female\",\"symptoms\":[\"blurred vision\"]}"
  ```

---

#### `GET /api/screenings/{screening_id}`
Poll current progress and quality checks of received images for a screening session.
- **Path Parameter**: `screening_id` (string)
- **Response `200 OK`**:
  ```json
  {
    "screening_id": "65908dd9796e",
    "status": "images_received",
    "created_at": "2026-09-21T09:20:00Z",
    "images": [
      {
        "eye_side": "left",
        "device_id": "LEFT_CAM_01",
        "quality_ok": true,
        "quality_score": 0.84
      },
      {
        "eye_side": "right",
        "device_id": "RIGHT_CAM_01",
        "quality_ok": true,
        "quality_score": 0.81
      }
    ]
  }
  ```
- **Error `404 Not Found`**:
  ```json
  {
    "detail": "Screening 'invalid_id' not found."
  }
  ```

---

#### `POST /api/screenings/{screening_id}/images`
Uploads an image file for either the left or right eye. Automatically runs OpenCV Laplacian variance blur estimation and brightness exposure checks.
- **Headers**:
  - `X-Device-Id` *(required)*: `LEFT_CAM_01` (maps to left eye) or `RIGHT_CAM_01` (maps to right eye)
  - `Content-Type: multipart/form-data`
- **Form Field**:
  - `file`: JPEG or PNG image binary (max size 10 MB)
- **Response `200 OK` (Quality Passed)**:
  ```json
  {
    "ok": true,
    "quality_score": 0.84,
    "blur_score": 142.6,
    "brightness": 128.4,
    "reason": "OK",
    "eye_side": "left",
    "device_id": "LEFT_CAM_01"
  }
  ```
- **Response `200 OK` (Quality Insufficient / Recapture Needed)**:
  ```json
  {
    "ok": false,
    "quality_score": 0.25,
    "blur_score": 12.3,
    "brightness": 24.1,
    "reason": "IMAGE_QUALITY_FAILED: Image is excessively blurry. Another capture is needed.",
    "eye_side": "left",
    "device_id": "LEFT_CAM_01"
  }
  ```
- **Error `400 Bad Request`**:
  ```json
  {
    "detail": "Invalid or missing 'X-Device-Id' header. Must be one of: ['LEFT_CAM_01', 'RIGHT_CAM_01']"
  }
  ```
- **Error `413 Request Entity Too Large`**:
  ```json
  {
    "detail": "Image size exceeds maximum limit of 10MB."
  }
  ```
- **cURL Example**:
  ```bash
  curl -X POST "http://localhost:8000/api/screenings/65908dd9796e/images" \
    -H "X-Device-Id: LEFT_CAM_01" \
    -F "file=@sample_eye.jpg"
  ```

---

#### `POST /api/screenings/{screening_id}/vision-tests`
Records interactive near-vision and colour-vision test answers and scores.
- **Headers**: `Content-Type: application/json`
- **Request Body**:
  ```json
  {
    "color_answers": [
      "12",
      "8",
      "29"
    ],
    "near_answers": [
      "A",
      "E",
      "F"
    ],
    "color_score": 1.0,
    "near_vision_score": 0.95
  }
  ```
- **Response `200 OK`**:
  ```json
  {
    "status": "recorded",
    "color_score": 1.0,
    "near_vision_score": 0.95
  }
  ```

---

#### `POST /api/screenings/{screening_id}/analyse`
Executes ML image classification on all uploaded eye images, evaluates vision tests, and calculates preliminary risk scores.
- **Response `200 OK`**:
  ```json
  {
    "screening_id": "65908dd9796e",
    "status": "analyzed",
    "overall_risk": "attention",
    "overall_score": 50,
    "analyses": [
      {
        "eye_side": "left",
        "model_status": "OK",
        "predicted_class": "redness",
        "confidence": 0.72,
        "risk_level": "attention",
        "findings": [
          "Preliminary screening flagged possible appearance indicator 'redness' for the left eye.",
          "This is a software screening indicator and not a medical diagnosis. A clinical assessment by an eye-care professional is advised if symptoms persist."
        ]
      },
      {
        "eye_side": "right",
        "model_status": "OK",
        "predicted_class": "normal",
        "confidence": 0.88,
        "risk_level": "low",
        "findings": [
          "Preliminary screening for the right eye indicates an appearance consistent with typical external eye structure."
        ]
      }
    ]
  }
  ```
- **Error `400 Bad Request`**:
  ```json
  {
    "detail": "No images available for analysis. Please capture and upload eye images before requesting analysis."
  }
  ```

---

#### `GET /api/screenings/{screening_id}/result`
Retrieves the comprehensive structured preliminary report, combining image analysis, vision test scores, overall risk tier, and medical disclaimers.
- **Path Parameter**: `screening_id` (string)
- **Response `200 OK`**:
  ```json
  {
    "screening_id": "65908dd9796e",
    "overall_score": 75,
    "overall_risk": "attention",
    "image_quality": {
      "left": {
        "ok": true,
        "score": 0.84
      },
      "right": {
        "ok": true,
        "score": 0.81
      }
    },
    "analyses": [
      {
        "eye_side": "left",
        "model_status": "OK",
        "predicted_class": "redness",
        "confidence": 0.72,
        "risk_level": "attention",
        "findings": [
          "Preliminary screening flagged possible appearance indicator 'redness' for the left eye.",
          "This is a software screening indicator and not a medical diagnosis. A clinical assessment by an eye-care professional is advised if symptoms persist."
        ]
      },
      {
        "eye_side": "right",
        "model_status": "OK",
        "predicted_class": "normal",
        "confidence": 0.88,
        "risk_level": "low",
        "findings": [
          "Preliminary screening for the right eye indicates an appearance consistent with typical external eye structure."
        ]
      }
    ],
    "vision_tests": {
      "color_score": 1.0,
      "near_vision_score": 0.95
    },
    "guidance": [
      "One or more preliminary screening risk indicators were flagged. A consultation with an optometrist or ophthalmologist is recommended.",
      "This result is preliminary screening information, not a medical diagnosis.",
      "If you have concerning symptoms or a concerning screening result, arrange an examination with a qualified eye-care professional.",
      "Do not use this result to start, stop, or change medical treatment."
    ],
    "disclaimer": "Preliminary screening only. Not a medical diagnosis."
  }
  ```

---

### 6.3 Standard HTTP Status Codes

| Code | Status | Meaning |
|---|---|---|
| `200` | OK | Request processed successfully |
| `201` | Created | Screening session created |
| `400` | Bad Request | Missing headers (`X-Device-Id`), invalid JSON, or missing images |
| `404` | Not Found | `screening_id` does not exist in SQLite database |
| `413` | Payload Too Large | Image exceeds the `MAX_UPLOAD_SIZE_MB` limit (10MB) |
| `500` | Internal Server Error | Handled gracefully; raw stack traces suppressed |

---

## 7. Fresh PC Troubleshooting Guide

| Issue | Likely Cause | Solution |
|---|---|---|
| `python : The term 'python' is not recognized` | Python was not added to PATH on installation | Re-run the Python installer and check **"Add python.exe to PATH"**, or restart PowerShell |
| `File ... cannot be loaded because running scripts is disabled` | Windows ExecutionPolicy restriction on new PC | Run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` in PowerShell before activating `venv` |
| `uvicorn : The term 'uvicorn' is not recognized` | User script directory is not in system PATH | Run `python -m uvicorn app.main:app ...` instead of `uvicorn` directly |
| `IMAGE_QUALITY_FAILED` | Uploaded image is blurry or has bad contrast | Ensure the camera is focused and illuminated; threshold requires `blur_score >= 40.0` |
| `ML_MODEL_NOT_READY` | Model weights `.keras` file has not been trained yet | Run `python scripts/seed_sample_data.py` followed by `python ml/train.py` |
| `Address already in use` (Port 8000) | Another process is holding port 8000 | Run on port 8001: `python -m uvicorn app.main:app --port 8001` or terminate the existing process |
| `CORS Error` in Browser | Frontend is hosted on a different port/URL | Update `FRONTEND_ORIGIN` in `.env` (e.g. `FRONTEND_ORIGIN=http://localhost:5173`) |
