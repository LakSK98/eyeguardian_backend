from fastapi import APIRouter
from app.schemas import HealthResponse
from app.config import settings

router = APIRouter(tags=["Health"])

@router.get("/api/health", response_model=HealthResponse)
def health_check():
    """Service health check endpoint."""
    return HealthResponse(
        status="OK",
        version=settings.APP_VERSION,
        app=settings.APP_NAME
    )
