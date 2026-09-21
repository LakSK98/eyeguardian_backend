import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.services.ml_service import ml_service

def verify():
    print(f"Model is_ready: {ml_service.is_ready}")
    print(f"Loaded Classes ({len(ml_service.class_names)}): {ml_service.class_names}")

    test_classes = ["normal", "Cataract", "Conjunctivitis", "Eyelid", "Uveitis"]
    for c in test_classes:
        folder = Path(f"data/external_eye/{c}")
        files = list(folder.glob("*.jpg")) or list(folder.glob("*.png"))
        if not files:
            continue
        sample = files[0]
        res = ml_service.predict_image_path(str(sample), eye_side="left")
        print(f"Ground Truth: {c:<15} | Predicted: {res.get('predicted_class', 'None'):<15} | Conf: {res.get('confidence')} | Risk: {res.get('risk_level')}")
        for f in res.get("findings", [])[:2]:
            print(f"   -> {f}")
        print("-" * 60)

if __name__ == "__main__":
    verify()
