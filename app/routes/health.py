from fastapi import APIRouter
from app.schemas import HealthResponse
from app.config import settings
from app.services.ml_service import ml_service

router = APIRouter(tags=["System"])

@router.get("/api/health", response_model=HealthResponse)
def health_check():
    """Service health check endpoint."""
    return HealthResponse(
        status="OK",
        version=settings.APP_VERSION,
        app=settings.APP_NAME
    )

@router.get("/api/model/status")
def get_model_status():
    """Check current ML model status, classes, and artifact path."""
    return {
        "model_ready": ml_service.is_ready,
        "classes": ml_service.class_names,
        "model_file_exists": settings.MODEL_FILE_PATH.exists(),
        "model_file_path": str(settings.MODEL_FILE_PATH)
    }

@router.post("/api/model/reload")
def reload_model():
    """Reload trained model weights from disk without restarting backend."""
    success = ml_service.reload()
    return {
        "reloaded": success,
        "model_ready": ml_service.is_ready,
        "classes": ml_service.class_names
    }
