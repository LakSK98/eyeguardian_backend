from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

# Health Check Schema
class HealthResponse(BaseModel):
    status: str = "OK"
    version: str = "1.0.0"
    app: str = "EyeGUARDIAN Vision Backend"

# Screening Schemas
class ScreeningCreate(BaseModel):
    user_name: str = Field(..., min_length=1, max_length=100, json_schema_extra={"example": "Kavindi"})
    age: int = Field(..., ge=0, le=120, json_schema_extra={"example": 15})
    sex: str = Field(..., json_schema_extra={"example": "female"})
    symptoms: List[str] = Field(default_factory=list, json_schema_extra={"example": ["headache", "blurred vision", "difficulty focusing"]})

class ScreeningResponse(BaseModel):
    screening_id: str
    status: str
    camera_devices: List[str]

# Eye Image Schemas
class ImageQualityStatus(BaseModel):
    eye_side: str
    device_id: str
    quality_ok: bool
    quality_score: float

class ScreeningStatusResponse(BaseModel):
    screening_id: str
    status: str
    created_at: Optional[datetime] = None
    user_name: Optional[str] = None
    age: Optional[int] = None
    sex: Optional[str] = None
    symptoms: List[str] = []
    images: List[ImageQualityStatus] = []

class ScreeningUpdate(BaseModel):
    user_name: Optional[str] = None
    age: Optional[int] = None
    sex: Optional[str] = None
    symptoms: Optional[List[str]] = None
    affected_eye: Optional[str] = None
    symptom_duration: Optional[str] = None
    symptom_severity: Optional[str] = None
    symptom_notes: Optional[str] = None
    vision_aid: Optional[str] = None

class ImageUploadResponse(BaseModel):
    ok: bool
    quality_score: float
    blur_score: Optional[float] = None
    brightness: Optional[float] = None
    reason: str
    eye_side: Optional[str] = None
    device_id: Optional[str] = None

# Vision Test Schemas
class VisionTestCreate(BaseModel):
    color_answers: List[Any] = Field(default_factory=list, json_schema_extra={"example": ["12", "8", "29"]})
    near_answers: List[Any] = Field(default_factory=list, json_schema_extra={"example": ["A", "E", "F"]})
    color_score: float = Field(..., ge=0.0, le=1.0, json_schema_extra={"example": 1.0})
    near_vision_score: float = Field(..., ge=0.0, le=1.0, json_schema_extra={"example": 0.9})

class VisionTestResponse(BaseModel):
    status: str
    color_score: float
    near_vision_score: float

class ScreeningListItem(BaseModel):
    screening_id: str
    user_name: str
    age: int
    sex: str
    symptoms: List[str] = []
    status: str
    created_at: datetime
    images_count: int = 0
    has_vision_test: bool = False
    overall_risk: Optional[str] = None
    overall_score: Optional[int] = None

# Analysis Schemas
class SingleAnalysisResult(BaseModel):
    eye_side: str
    model_status: str
    predicted_class: Optional[str] = None
    confidence: Optional[float] = None
    risk_level: str
    findings: List[str] = []

class AnalyseResponse(BaseModel):
    screening_id: str
    status: str
    analyses: List[SingleAnalysisResult]
    overall_risk: str
    overall_score: int

# Result Report Schemas
class ImageSideQuality(BaseModel):
    ok: bool
    score: float

class VisionTestsSummary(BaseModel):
    color_score: float
    near_vision_score: float

class ResultResponse(BaseModel):
    screening_id: str
    overall_score: int
    overall_risk: str
    image_quality: Dict[str, ImageSideQuality]
    analyses: List[SingleAnalysisResult]
    vision_tests: Optional[VisionTestsSummary] = None
    guidance: List[str]
    disclaimer: str
    user_name: Optional[str] = None
    age: Optional[int] = None
    sex: Optional[str] = None
    symptoms: List[str] = []
    created_at: Optional[datetime] = None
    status: Optional[str] = None
    affected_eye: Optional[str] = None
    symptom_duration: Optional[str] = None
    symptom_severity: Optional[str] = None
    symptom_notes: Optional[str] = None
    vision_aid: Optional[str] = None
