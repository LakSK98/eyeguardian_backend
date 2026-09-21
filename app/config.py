import os
from pathlib import Path
from pydantic_settings import BaseSettings

# Project root directory
BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    APP_NAME: str = "EyeGUARDIAN Vision Backend"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Server configuration
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000

    # CORS configuration
    FRONTEND_ORIGIN: str = "http://localhost:3000"

    # Database
    DATABASE_URL: str = f"sqlite:///{BASE_DIR / 'eyeguardian.db'}"

    # Directory Paths
    BASE_DIR: Path = BASE_DIR
    DATA_DIR: Path = BASE_DIR / "data"
    SCREENINGS_DATA_DIR: Path = BASE_DIR / "data" / "screenings"
    EXTERNAL_EYE_DATA_DIR: Path = BASE_DIR / "data" / "external_eye"
    MODELS_DIR: Path = BASE_DIR / "models"
    MODEL_FILE_PATH: Path = BASE_DIR / "models" / "external_eye.keras"
    CLASS_NAMES_FILE_PATH: Path = BASE_DIR / "models" / "class_names.json"

    # Image Upload & Validation Limits
    MAX_UPLOAD_SIZE_MB: int = 10
    ALLOWED_IMAGE_EXTENSIONS: list[str] = [".jpg", ".jpeg", ".png"]

    # Image Quality Check Thresholds (Prototype Demonstration - Not Clinically Validated)
    MIN_IMAGE_WIDTH: int = 200
    MIN_IMAGE_HEIGHT: int = 200
    BLUR_THRESHOLD: float = 40.0         # Laplacian variance minimum
    BRIGHTNESS_MIN: float = 35.0         # Grayscale mean minimum
    BRIGHTNESS_MAX: float = 230.0        # Grayscale mean maximum

    # Supported Hardware Device IDs
    VALID_DEVICE_IDS: list[str] = ["LEFT_CAM_01", "RIGHT_CAM_01"]

    model_config = {
        "env_file": str(BASE_DIR / ".env"),
        "env_file_encoding": "utf-8",
        "extra": "ignore"
    }

settings = Settings()

# Ensure standard working directories exist
os.makedirs(settings.SCREENINGS_DATA_DIR, exist_ok=True)
os.makedirs(settings.EXTERNAL_EYE_DATA_DIR, exist_ok=True)
os.makedirs(settings.MODELS_DIR, exist_ok=True)
