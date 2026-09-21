import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from app.config import settings
from app.database import engine, Base
import app.models  # Ensure all models are imported before creating tables
from app.routes import health, screenings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s"
)
logger = logging.getLogger("eyeguardian.main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown event handler."""
    logger.info("Initializing SQLite database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database initialized successfully.")
    yield
    logger.info("Shutting down EyeGUARDIAN Vision Backend.")

app = FastAPI(
    title="EyeGUARDIAN Vision Backend",
    description=(
        "REST API backend for the EyeGUARDIAN Vision wearable eye-screening prototype. "
        "Provides image ingestion from ESP32-CAM boards, OpenCV quality checking, "
        "TensorFlow transfer-learning screening inference, vision test recording, "
        "and non-diagnostic risk scoring."
    ),
    version=settings.APP_VERSION,
    lifespan=lifespan
)

from fastapi.staticfiles import StaticFiles
from pathlib import Path

# CORS Configuration - Allow all origins for prototype frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Routers
app.include_router(health.router)
app.include_router(screenings.router)

# Mount static files for uploaded screening images
if settings.SCREENINGS_DATA_DIR.exists():
    app.mount("/data/screenings", StaticFiles(directory=str(settings.SCREENINGS_DATA_DIR)), name="screenings_data")

# Mount frontend static application (now lives inside the backend repo at frontend/)
frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
if frontend_dir.exists():
    logger.info(f"Mounting frontend directory: {frontend_dir}")
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")

# Custom Exception Handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle schema validation errors cleanly."""
    logger.warning(f"Validation error for {request.url.path}: {exc.errors()}")
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": "Validation Error",
            "detail": exc.errors()
        }
    )

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Catch-all to prevent unhandled stack trace exposure."""
    logger.error(f"Unhandled server error on {request.url.path}: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal Server Error",
            "detail": "An unexpected error occurred during processing. Please check server logs."
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.BACKEND_HOST,
        port=settings.BACKEND_PORT,
        reload=True
    )
