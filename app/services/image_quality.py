import logging
from typing import Dict, Any, Tuple
import cv2
import numpy as np
from app.config import settings

logger = logging.getLogger("eyeguardian.image_quality")

class ImageQualityChecker:
    """
    OpenCV-based image quality evaluation for preliminary eye screening.
    
    IMPORTANT DISCLAIMER:
    The blur (Laplacian variance) and brightness metrics and threshold values
    implemented here are prototype thresholds for demonstration and preliminary
    screening filtering only. They are NOT clinically validated diagnostic thresholds.
    """

    def __init__(
        self,
        min_width: int = settings.MIN_IMAGE_WIDTH,
        min_height: int = settings.MIN_IMAGE_HEIGHT,
        blur_threshold: float = settings.BLUR_THRESHOLD,
        brightness_min: float = settings.BRIGHTNESS_MIN,
        brightness_max: float = settings.BRIGHTNESS_MAX,
    ):
        self.min_width = min_width
        self.min_height = min_height
        self.blur_threshold = blur_threshold
        self.brightness_min = brightness_min
        self.brightness_max = brightness_max

    def evaluate_bytes(self, image_bytes: bytes) -> Dict[str, Any]:
        """
        Evaluate image quality from raw bytes.
        
        Checks:
        1. Non-empty data
        2. Decodability via OpenCV
        3. Minimum dimensions (width x height)
        4. Blur metric (Laplacian variance)
        5. Brightness metric (mean grayscale intensity)
        """
        if not image_bytes or len(image_bytes) == 0:
            return {
                "ok": False,
                "quality_score": 0.0,
                "blur_score": 0.0,
                "brightness": 0.0,
                "reason": "IMAGE_EMPTY_OR_CORRUPT: Empty image buffer received."
            }

        # Decode image using OpenCV
        np_arr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

        if img is None:
            logger.warning("Failed to decode image buffer.")
            return {
                "ok": False,
                "quality_score": 0.0,
                "blur_score": 0.0,
                "brightness": 0.0,
                "reason": "IMAGE_DECODE_FAILED: Image could not be decoded as a valid JPEG/PNG."
            }

        return self.evaluate_cv2_image(img)

    def evaluate_file(self, file_path: str) -> Dict[str, Any]:
        """Evaluate image quality from a file on disk."""
        img = cv2.imread(file_path, cv2.IMREAD_COLOR)
        if img is None:
            return {
                "ok": False,
                "quality_score": 0.0,
                "blur_score": 0.0,
                "brightness": 0.0,
                "reason": "IMAGE_READ_FAILED: Unable to read file from disk."
            }
        return self.evaluate_cv2_image(img)

    def evaluate_cv2_image(self, img: np.ndarray) -> Dict[str, Any]:
        """Run OpenCV quality metrics on a decoded BGR image array."""
        h, w = img.shape[:2]

        # 1. Dimension Check
        if w < self.min_width or h < self.min_height:
            logger.info(f"Image resolution too small: {w}x{h} < {self.min_width}x{self.min_height}")
            return {
                "ok": False,
                "quality_score": 0.20,
                "blur_score": 0.0,
                "brightness": 0.0,
                "reason": f"IMAGE_DIMENSIONS_TOO_SMALL: Image resolution ({w}x{h}) is below minimum ({self.min_width}x{self.min_height})."
            }

        # Convert to Grayscale for metrics
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # 2. Blur Metric: Laplacian Variance
        # A higher variance indicates sharper edges and lower blur
        blur_score = float(cv2.Laplacian(gray, cv2.CV_64F).var())

        # 3. Brightness Metric: Grayscale Mean
        brightness = float(np.mean(gray))

        # Check thresholds
        reasons = []
        is_blurry = blur_score < self.blur_threshold
        is_too_dark = brightness < self.brightness_min
        is_too_bright = brightness > self.brightness_max

        if is_blurry:
            reasons.append(f"Image is excessively blurry (blur score {blur_score:.1f} < threshold {self.blur_threshold:.1f})")
        if is_too_dark:
            reasons.append(f"Image is under-exposed (brightness {brightness:.1f} < threshold {self.brightness_min:.1f})")
        if is_too_bright:
            reasons.append(f"Image is over-exposed/washed out (brightness {brightness:.1f} > threshold {self.brightness_max:.1f})")

        # Compute normalized prototype quality score [0.0 to 1.0]
        # Blur subscore: saturate at 200.0
        blur_sub = min(1.0, blur_score / 150.0)
        # Brightness subscore: ideal around 128
        brightness_diff = abs(brightness - 128.0)
        brightness_sub = max(0.0, 1.0 - (brightness_diff / 128.0))

        quality_score = round(float(0.6 * blur_sub + 0.4 * brightness_sub), 2)
        # Clamp to [0.05, 0.99]
        quality_score = max(0.05, min(0.99, quality_score))

        if reasons:
            failure_reason = "IMAGE_QUALITY_FAILED: " + "; ".join(reasons) + ". Another capture is needed."
            logger.info(f"Image quality check failed: {failure_reason}")
            return {
                "ok": False,
                "quality_score": quality_score,
                "blur_score": round(blur_score, 1),
                "brightness": round(brightness, 1),
                "reason": failure_reason
            }

        return {
            "ok": True,
            "quality_score": quality_score,
            "blur_score": round(blur_score, 1),
            "brightness": round(brightness, 1),
            "reason": "OK"
        }

image_quality_checker = ImageQualityChecker()
