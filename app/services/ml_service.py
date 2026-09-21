import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
import numpy as np
import cv2
from app.config import settings

logger = logging.getLogger("eyeguardian.ml_service")

# Default classes for external eye screening
DEFAULT_CLASSES = ["normal", "redness", "ptosis", "leukocoria", "other_abnormal"]

class ExternalEyeMLService:
    """
    TensorFlow/Keras Machine Learning Service for external eye screening inference.
    
    IMPORTANT DISCLAIMER:
    This service is designed for PRELIMINARY SCREENING demonstrations only.
    Class predictions and confidence levels are NOT confirmed medical diagnoses.
    """

    def __init__(
        self,
        model_path: Path = settings.MODEL_FILE_PATH,
        class_names_path: Path = settings.CLASS_NAMES_FILE_PATH
    ):
        self.model_path = model_path
        self.class_names_path = class_names_path
        self.model = None
        self.class_names = DEFAULT_CLASSES
        self.is_ready = False
        self._load_model()

    def _load_model(self) -> None:
        """Attempt to load the trained Keras model and class names JSON."""
        if not self.model_path.exists():
            logger.warning(
                f"ML model artifact not found at {self.model_path}. "
                "Backend will run with ML_MODEL_NOT_READY fallback."
            )
            self.is_ready = False
            return

        try:
            import tensorflow as tf
            logger.info(f"Loading Keras model from {self.model_path}...")
            self.model = tf.keras.models.load_model(str(self.model_path))

            if self.class_names_path.exists():
                with open(self.class_names_path, "r", encoding="utf-8") as f:
                    self.class_names = json.load(f)
                logger.info(f"Loaded class names: {self.class_names}")
            else:
                logger.info(f"Class names file not found. Using default classes: {self.class_names}")

            self.is_ready = True
            logger.info("External Eye ML model loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load ML model from {self.model_path}: {e}", exc_info=True)
            self.model = None
            self.is_ready = False

    def reload(self) -> bool:
        """Reload the model after training completes."""
        self._load_model()
        return self.is_ready

    def predict_image_path(self, file_path: str, eye_side: str = "unknown") -> Dict[str, Any]:
        """Run ML inference on an image file on disk."""
        if not self.is_ready or self.model is None:
            return {
                "model_status": "ML_MODEL_NOT_READY",
                "predicted_class": None,
                "confidence": None,
                "risk_level": "uncertain",
                "findings": [
                    "External eye ML model is not loaded. Image prediction is not available."
                ]
            }

        try:
            # Read image using OpenCV
            img = cv2.imread(file_path)
            if img is None:
                return {
                    "model_status": "IMAGE_LOAD_FAILED",
                    "predicted_class": None,
                    "confidence": None,
                    "risk_level": "uncertain",
                    "findings": [f"Unable to read eye image file at {file_path}"]
                }

            return self.predict_cv2_image(img, eye_side=eye_side)
        except Exception as e:
            logger.error(f"Error during ML inference on {file_path}: {e}", exc_info=True)
            return {
                "model_status": "INFERENCE_ERROR",
                "predicted_class": None,
                "confidence": None,
                "risk_level": "uncertain",
                "findings": [f"Error during preliminary inference: {str(e)}"]
            }

    def predict_cv2_image(self, img: np.ndarray, eye_side: str = "unknown") -> Dict[str, Any]:
        """
        Preprocess image array and perform MobileNetV2 inference.
        """
        import tensorflow as tf
        from tensorflow.keras.applications.mobilenet_v2 import preprocess_input

        # Convert BGR to RGB
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        # Resize to 224x224 as required by standard MobileNetV2
        img_resized = cv2.resize(img_rgb, (224, 224), interpolation=cv2.INTER_AREA)

        # Expand batch dimension and apply MobileNetV2 normalization [-1, 1]
        batch = np.expand_dims(img_resized.astype(np.float32), axis=0)
        batch_preprocessed = preprocess_input(batch)

        # Predict probabilities
        probabilities = self.model.predict(batch_preprocessed, verbose=0)[0]
        predicted_idx = int(np.argmax(probabilities))
        confidence = float(probabilities[predicted_idx])
        predicted_class = self.class_names[predicted_idx] if predicted_idx < len(self.class_names) else "unknown"

        # Determine preliminary risk level and non-diagnostic findings
        # Non-diagnostic language strictly enforced
        if predicted_class == "normal":
            risk_level = "low"
            findings = [
                f"Preliminary screening for the {eye_side} eye indicates an appearance consistent with typical external eye structure."
            ]
        else:
            risk_level = "attention"
            findings = [
                f"Preliminary screening flagged possible appearance indicator '{predicted_class}' for the {eye_side} eye.",
                "This is a software screening indicator and not a medical diagnosis. A clinical assessment by an eye-care professional is advised if symptoms persist."
            ]

        return {
            "model_status": "OK",
            "predicted_class": predicted_class,
            "confidence": round(confidence, 2),
            "risk_level": risk_level,
            "findings": findings
        }

    def fundus_analysis_placeholder(self) -> Dict[str, Any]:
        """
        Fundus imaging architecture placeholder.
        External eye OV2640 camera images must never be evaluated as fundus retinal images.
        """
        return {
            "model_status": "FUNDUS_MODEL_NOT_IMPLEMENTED",
            "predicted_class": None,
            "confidence": None,
            "risk_level": "uncertain",
            "findings": [
                "Fundus retinal imaging requires dedicated optical attachments and controlled illumination. Fundus model is not active."
            ]
        }

ml_service = ExternalEyeMLService()
