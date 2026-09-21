"""
EyeGUARDIAN Vision - Synthetic Sample Dataset Generator
Creates sample prototype images for the 5 classes:
- normal
- redness
- ptosis
- leukocoria
- other_abnormal

This enables immediate out-of-the-box verification of:
- ml/train.py
- ml/evaluate.py
- app/services/ml_service.py
without downloading uncurated external patient images.
"""

import os
from pathlib import Path
import numpy as np
import cv2

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "external_eye"

CLASSES = {
    "normal": (210, 225, 235),       # Typical sclera tone
    "redness": (140, 140, 230),      # Elevated red channels (BGR)
    "ptosis": (180, 190, 200),       # Asymmetrical lid shading
    "leukocoria": (240, 240, 240),   # Bright pupil reflex
    "other_abnormal": (160, 180, 190)
}

def create_synthetic_eye_image(class_name: str, index: int) -> np.ndarray:
    """Generate a 250x250 RGB eye-like sample for testing."""
    img = np.ones((250, 250, 3), dtype=np.uint8) * 190

    # Add skin base tone
    img[:, :] = (180, 195, 215)

    # Eye aperture (ellipse)
    cv2.ellipse(img, (125, 125), (85, 45), 0, 0, 360, (230, 235, 240), -1)

    # Iris
    cv2.circle(img, (125, 125), 28, (80, 60, 45), -1)

    # Pupil
    pupil_color = (15, 15, 15)
    if class_name == "leukocoria":
        pupil_color = (245, 245, 245)  # White pupillary reflex
    cv2.circle(img, (125, 125), 12, pupil_color, -1)

    # Class specific features
    if class_name == "redness":
        # Add vascular redness
        overlay = img.copy()
        cv2.circle(overlay, (85, 125), 25, (50, 50, 220), -1)
        cv2.circle(overlay, (165, 125), 25, (50, 50, 220), -1)
        img = cv2.addWeighted(img, 0.6, overlay, 0.4, 0)
    elif class_name == "ptosis":
        # Drooping upper eyelid
        cv2.ellipse(img, (125, 110), (90, 35), 0, 0, 180, (170, 185, 205), -1)
    elif class_name == "other_abnormal":
        # Corneal clouding / patch
        cv2.circle(img, (115, 120), 10, (200, 200, 210), -1)

    # Add subtle random texture/noise so samples are not identical
    noise = np.random.normal(0, 4, img.shape).astype(np.int16)
    noisy_img = np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)

    return noisy_img

def seed_dataset(num_samples_per_class: int = 12):
    """Seed synthetic external eye dataset."""
    print(f"Seeding synthetic dataset to {DATA_DIR}...")
    for class_name in CLASSES:
        class_folder = DATA_DIR / class_name
        os.makedirs(class_folder, exist_ok=True)

        for i in range(1, num_samples_per_class + 1):
            img = create_synthetic_eye_image(class_name, i)
            file_path = class_folder / f"{class_name}_{i:03d}.jpg"
            cv2.imwrite(str(file_path), img, [cv2.IMWRITE_JPEG_QUALITY, 95])

    print(f"Dataset generated successfully! {len(CLASSES)} classes, {num_samples_per_class} images each.")

if __name__ == "__main__":
    seed_dataset()
