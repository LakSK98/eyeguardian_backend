from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.database import Base

class Screening(Base):
    __tablename__ = "screenings"

    id = Column(Integer, primary_key=True, index=True)
    screening_id = Column(String(64), unique=True, index=True, nullable=False)
    user_name = Column(String(100), nullable=False)
    age = Column(Integer, nullable=False)
    sex = Column(String(20), nullable=False)
    symptoms = Column(JSON, nullable=False, default=list)
    status = Column(String(50), nullable=False, default="waiting_for_images")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Detailed symptom metadata (stored after symptoms.html step)
    affected_eye = Column(String(30), nullable=True)       # "Left", "Right", "Both"
    symptom_duration = Column(String(60), nullable=True)   # free text e.g. "2 weeks"
    symptom_severity = Column(String(20), nullable=True)   # "Mild", "Moderate", "Severe"
    symptom_notes = Column(String(500), nullable=True)

    # Patient metadata collected in patient.html
    vision_aid = Column(String(50), nullable=True)         # "Spectacles", "None", etc.

    images = relationship("EyeImage", back_populates="screening", cascade="all, delete-orphan")
    vision_test = relationship("VisionTest", back_populates="screening", uselist=False, cascade="all, delete-orphan")
    analyses = relationship("Analysis", back_populates="screening", cascade="all, delete-orphan")



class EyeImage(Base):
    __tablename__ = "eye_images"

    id = Column(Integer, primary_key=True, index=True)
    screening_id = Column(String(64), ForeignKey("screenings.screening_id", ondelete="CASCADE"), nullable=False)
    device_id = Column(String(50), nullable=False)
    eye_side = Column(String(20), nullable=False)  # "left" or "right"
    file_path = Column(String(255), nullable=False)
    quality_score = Column(Float, nullable=False, default=0.0)
    quality_ok = Column(Boolean, nullable=False, default=False)
    blur_score = Column(Float, nullable=True)
    brightness = Column(Float, nullable=True)
    reason = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    screening = relationship("Screening", back_populates="images")


class VisionTest(Base):
    __tablename__ = "vision_tests"

    id = Column(Integer, primary_key=True, index=True)
    screening_id = Column(String(64), ForeignKey("screenings.screening_id", ondelete="CASCADE"), nullable=False)
    color_score = Column(Float, nullable=False, default=0.0)
    near_vision_score = Column(Float, nullable=False, default=0.0)
    color_answers = Column(JSON, nullable=False, default=list)
    near_answers = Column(JSON, nullable=False, default=list)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    screening = relationship("Screening", back_populates="vision_test")


class Analysis(Base):
    __tablename__ = "analyses"

    id = Column(Integer, primary_key=True, index=True)
    screening_id = Column(String(64), ForeignKey("screenings.screening_id", ondelete="CASCADE"), nullable=False)
    eye_side = Column(String(20), nullable=False)  # "left", "right"
    model_status = Column(String(50), nullable=False)  # "OK", "ML_MODEL_NOT_READY", etc.
    predicted_class = Column(String(50), nullable=True)
    confidence = Column(Float, nullable=True)
    risk_level = Column(String(20), nullable=False, default="uncertain")  # "low", "attention", "uncertain"
    findings = Column(JSON, nullable=False, default=list)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    screening = relationship("Screening", back_populates="analyses")
