import os
import uuid
from datetime import datetime, timezone
import logging
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Header, UploadFile, File, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import Screening, EyeImage, VisionTest, Analysis
from app.schemas import (
    ScreeningCreate,
    ScreeningResponse,
    ScreeningStatusResponse,
    ImageQualityStatus,
    ImageUploadResponse,
    VisionTestCreate,
    VisionTestResponse,
    AnalyseResponse,
    SingleAnalysisResult,
    ResultResponse,
    ImageSideQuality,
    VisionTestsSummary
)
from app.services.image_quality import image_quality_checker
from app.services.ml_service import ml_service
from app.services.scoring import scoring_service

logger = logging.getLogger("eyeguardian.screenings")

router = APIRouter(prefix="/api/screenings", tags=["Screenings"])

DEVICE_EYE_MAP = {
    "LEFT_CAM_01": "left",
    "RIGHT_CAM_01": "right"
}

@router.post("", response_model=ScreeningResponse, status_code=status.HTTP_201_CREATED)
def create_screening(data: ScreeningCreate, db: Session = Depends(get_db)):
    """
    Initialize a new preliminary screening session.
    Generates a unique screening_id and provides target camera device identifiers.
    """
    unique_id = uuid.uuid4().hex[:12]
    
    screening = Screening(
        screening_id=unique_id,
        user_name=data.user_name,
        age=data.age,
        sex=data.sex,
        symptoms=data.symptoms,
        status="waiting_for_images"
    )
    db.add(screening)
    db.commit()
    db.refresh(screening)

    # Ensure dedicated folder for uploaded screening images exists
    screening_dir = settings.SCREENINGS_DATA_DIR / unique_id
    os.makedirs(screening_dir, exist_ok=True)

    logger.info(f"Screening created: {unique_id} for user: {data.user_name}")

    return ScreeningResponse(
        screening_id=screening.screening_id,
        status=screening.status,
        camera_devices=settings.VALID_DEVICE_IDS
    )


@router.get("/{screening_id}", response_model=ScreeningStatusResponse)
def get_screening_status(screening_id: str, db: Session = Depends(get_db)):
    """
    Get the status of an ongoing screening, including received cameras and quality scores.
    """
    screening = db.query(Screening).filter(Screening.screening_id == screening_id).first()
    if not screening:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Screening '{screening_id}' not found."
        )

    images = db.query(EyeImage).filter(EyeImage.screening_id == screening_id).all()
    image_statuses = [
        ImageQualityStatus(
            eye_side=img.eye_side,
            device_id=img.device_id,
            quality_ok=img.quality_ok,
            quality_score=img.quality_score
        )
        for img in images
    ]

    return ScreeningStatusResponse(
        screening_id=screening.screening_id,
        status=screening.status,
        created_at=screening.created_at,
        images=image_statuses
    )


@router.post("/{screening_id}/images", response_model=ImageUploadResponse)
async def upload_screening_image(
    screening_id: str,
    file: UploadFile = File(...),
    x_device_id: Optional[str] = Header(None, alias="X-Device-Id"),
    db: Session = Depends(get_db)
):
    """
    Upload an eye image from an ESP32-CAM board or testing client.
    Requires header X-Device-Id (LEFT_CAM_01 or RIGHT_CAM_01).
    Validates quality with OpenCV before saving.
    """
    # 1. Validate screening exists
    screening = db.query(Screening).filter(Screening.screening_id == screening_id).first()
    if not screening:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Screening '{screening_id}' not found."
        )

    # 2. Validate Device Header
    if not x_device_id or x_device_id not in settings.VALID_DEVICE_IDS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid or missing 'X-Device-Id' header. Must be one of: {settings.VALID_DEVICE_IDS}"
        )

    eye_side = DEVICE_EYE_MAP[x_device_id]

    # 3. Read image bytes and validate size
    image_bytes = await file.read()
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if len(image_bytes) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Image size ({len(image_bytes)} bytes) exceeds maximum limit of {settings.MAX_UPLOAD_SIZE_MB}MB."
        )

    if len(image_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded image file is empty."
        )

    # 4. Perform OpenCV Quality Check
    quality_result = image_quality_checker.evaluate_bytes(image_bytes)

    # 5. Save image to disk regardless (for inspection/retry history)
    screening_dir = settings.SCREENINGS_DATA_DIR / screening_id
    os.makedirs(screening_dir, exist_ok=True)
    timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    file_name = f"{eye_side}_{timestamp_str}.jpg"
    file_path = str(screening_dir / file_name)

    with open(file_path, "wb") as f:
        f.write(image_bytes)

    logger.info(
        f"Image uploaded for screening {screening_id} ({x_device_id} -> {eye_side}): "
        f"quality_ok={quality_result['ok']}, score={quality_result['quality_score']}"
    )

    # 6. Save or update EyeImage record in SQLite
    existing_img = db.query(EyeImage).filter(
        EyeImage.screening_id == screening_id,
        EyeImage.eye_side == eye_side
    ).first()

    if existing_img:
        existing_img.device_id = x_device_id
        existing_img.file_path = file_path
        existing_img.quality_score = quality_result["quality_score"]
        existing_img.quality_ok = quality_result["ok"]
        existing_img.blur_score = quality_result["blur_score"]
        existing_img.brightness = quality_result["brightness"]
        existing_img.reason = quality_result["reason"]
    else:
        eye_image = EyeImage(
            screening_id=screening_id,
            device_id=x_device_id,
            eye_side=eye_side,
            file_path=file_path,
            quality_score=quality_result["quality_score"],
            quality_ok=quality_result["ok"],
            blur_score=quality_result["blur_score"],
            brightness=quality_result["brightness"],
            reason=quality_result["reason"]
        )
        db.add(eye_image)

    # 7. Update Screening status
    all_images = db.query(EyeImage).filter(EyeImage.screening_id == screening_id).all()
    sides_received = {img.eye_side for img in all_images}

    if "left" in sides_received and "right" in sides_received:
        screening.status = "images_received"
    else:
        screening.status = "partial_images_received"

    db.commit()

    return ImageUploadResponse(
        ok=quality_result["ok"],
        quality_score=quality_result["quality_score"],
        blur_score=quality_result["blur_score"],
        brightness=quality_result["brightness"],
        reason=quality_result["reason"],
        eye_side=eye_side,
        device_id=x_device_id
    )


@router.post("/{screening_id}/vision-tests", response_model=VisionTestResponse)
def submit_vision_tests(
    screening_id: str,
    data: VisionTestCreate,
    db: Session = Depends(get_db)
):
    """
    Record user responses and scores for colour-vision and near-vision tests.
    """
    screening = db.query(Screening).filter(Screening.screening_id == screening_id).first()
    if not screening:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Screening '{screening_id}' not found."
        )

    existing_vt = db.query(VisionTest).filter(VisionTest.screening_id == screening_id).first()
    if existing_vt:
        existing_vt.color_score = data.color_score
        existing_vt.near_vision_score = data.near_vision_score
        existing_vt.color_answers = data.color_answers
        existing_vt.near_answers = data.near_answers
    else:
        vt = VisionTest(
            screening_id=screening_id,
            color_score=data.color_score,
            near_vision_score=data.near_vision_score,
            color_answers=data.color_answers,
            near_answers=data.near_answers
        )
        db.add(vt)

    screening.status = "vision_tests_completed"
    db.commit()

    logger.info(f"Vision tests recorded for {screening_id}: color={data.color_score}, near={data.near_vision_score}")

    return VisionTestResponse(
        status="recorded",
        color_score=data.color_score,
        near_vision_score=data.near_vision_score
    )


@router.post("/{screening_id}/analyse", response_model=AnalyseResponse)
def analyse_screening(screening_id: str, db: Session = Depends(get_db)):
    """
    Run image quality check and ML inference on all uploaded eye images.
    Synthesizes vision tests and symptoms to compute preliminary screening score.
    """
    screening = db.query(Screening).filter(Screening.screening_id == screening_id).first()
    if not screening:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Screening '{screening_id}' not found."
        )

    images = db.query(EyeImage).filter(EyeImage.screening_id == screening_id).all()
    if not images:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No images available for analysis. Please capture and upload eye images before requesting analysis."
        )

    # Clear previous analyses for clean idempotency
    db.query(Analysis).filter(Analysis.screening_id == screening_id).delete()

    analyses_results: List[SingleAnalysisResult] = []
    analyses_dicts = []
    image_qualities = {}

    for img in images:
        image_qualities[img.eye_side] = {
            "ok": img.quality_ok,
            "score": img.quality_score
        }

        # If image quality check passed, proceed to ML inference
        if img.quality_ok:
            pred = ml_service.predict_image_path(img.file_path, eye_side=img.eye_side)
        else:
            pred = {
                "model_status": "IMAGE_QUALITY_FAILED",
                "predicted_class": None,
                "confidence": None,
                "risk_level": "uncertain",
                "findings": [
                    f"Image quality check failed for {img.eye_side} eye ({img.reason}). Image was not submitted to ML model."
                ]
            }

        analysis_record = Analysis(
            screening_id=screening_id,
            eye_side=img.eye_side,
            model_status=pred["model_status"],
            predicted_class=pred.get("predicted_class"),
            confidence=pred.get("confidence"),
            risk_level=pred["risk_level"],
            findings=pred.get("findings", [])
        )
        db.add(analysis_record)

        res_obj = SingleAnalysisResult(
            eye_side=img.eye_side,
            model_status=pred["model_status"],
            predicted_class=pred.get("predicted_class"),
            confidence=pred.get("confidence"),
            risk_level=pred["risk_level"],
            findings=pred.get("findings", [])
        )
        analyses_results.append(res_obj)
        analyses_dicts.append(pred | {"eye_side": img.eye_side})

    # Retrieve vision test if available
    vt_record = db.query(VisionTest).filter(VisionTest.screening_id == screening_id).first()
    vt_dict = None
    if vt_record:
        vt_dict = {
            "color_score": vt_record.color_score,
            "near_vision_score": vt_record.near_vision_score
        }

    # Calculate overall preliminary score
    scored_result = scoring_service.calculate_screening_result(
        screening_id=screening_id,
        analyses=analyses_dicts,
        image_qualities=image_qualities,
        vision_test=vt_dict,
        symptoms=screening.symptoms
    )

    screening.status = "analyzed"
    db.commit()

    logger.info(f"Screening {screening_id} analyzed: score={scored_result['overall_score']}, risk={scored_result['overall_risk']}")

    return AnalyseResponse(
        screening_id=screening_id,
        status="analyzed",
        analyses=analyses_results,
        overall_risk=scored_result["overall_risk"],
        overall_score=scored_result["overall_score"]
    )


@router.get("/{screening_id}/result", response_model=ResultResponse)
def get_screening_result(screening_id: str, db: Session = Depends(get_db)):
    """
    Retrieve the complete structured preliminary screening result and referral guidance.
    """
    screening = db.query(Screening).filter(Screening.screening_id == screening_id).first()
    if not screening:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Screening '{screening_id}' not found."
        )

    images = db.query(EyeImage).filter(EyeImage.screening_id == screening_id).all()
    analyses = db.query(Analysis).filter(Analysis.screening_id == screening_id).all()
    vt_record = db.query(VisionTest).filter(VisionTest.screening_id == screening_id).first()

    image_qualities = {}
    for img in images:
        image_qualities[img.eye_side] = {
            "ok": img.quality_ok,
            "score": img.quality_score
        }

    analyses_dicts = [
        {
            "eye_side": a.eye_side,
            "model_status": a.model_status,
            "predicted_class": a.predicted_class,
            "confidence": a.confidence,
            "risk_level": a.risk_level,
            "findings": a.findings or []
        }
        for a in analyses
    ]

    vt_dict = None
    if vt_record:
        vt_dict = {
            "color_score": vt_record.color_score,
            "near_vision_score": vt_record.near_vision_score
        }

    scored = scoring_service.calculate_screening_result(
        screening_id=screening_id,
        analyses=analyses_dicts,
        image_qualities=image_qualities,
        vision_test=vt_dict,
        symptoms=screening.symptoms
    )

    analyses_objs = [
        SingleAnalysisResult(
            eye_side=a["eye_side"],
            model_status=a["model_status"],
            predicted_class=a["predicted_class"],
            confidence=a["confidence"],
            risk_level=a["risk_level"],
            findings=a["findings"]
        )
        for a in analyses_dicts
    ]

    vt_summary = None
    if vt_dict:
        vt_summary = VisionTestsSummary(
            color_score=vt_dict["color_score"],
            near_vision_score=vt_dict["near_vision_score"]
        )

    img_quality_dict = {
        side: ImageSideQuality(ok=val["ok"], score=val["score"])
        for side, val in scored["image_quality"].items()
    }

    return ResultResponse(
        screening_id=screening_id,
        overall_score=scored["overall_score"],
        overall_risk=scored["overall_risk"],
        image_quality=img_quality_dict,
        analyses=analyses_objs,
        vision_tests=vt_summary,
        guidance=scored["guidance"],
        disclaimer=scored["disclaimer"]
    )
