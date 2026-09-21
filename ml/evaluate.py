"""
EyeGUARDIAN Vision - Model Evaluation Pipeline
Evaluates the trained MobileNetV2 model against validation/test eye images.

Outputs:
- Overall Accuracy
- Macro & Weighted Precision, Recall, F1 Score
- Scikit-learn Classification Report
- Confusion Matrix
"""

import sys
import json
import argparse
import logging
from pathlib import Path
import numpy as np

# Fix Windows console encoding
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("eyeguardian.evaluate")

def parse_args():
    parser = argparse.ArgumentParser(description="Evaluate MobileNetV2 External Eye Screening Model")
    parser.add_argument(
        "--data-dir",
        type=str,
        default=str(PROJECT_ROOT / "data" / "external_eye"),
        help="Path to external eye dataset directory containing class subfolders"
    )
    parser.add_argument(
        "--model-path",
        type=str,
        default=str(PROJECT_ROOT / "models" / "external_eye.keras"),
        help="Path to trained .keras model"
    )
    parser.add_argument(
        "--classes-path",
        type=str,
        default=str(PROJECT_ROOT / "models" / "class_names.json"),
        help="Path to class names JSON"
    )
    parser.add_argument("--batch-size", type=int, default=16, help="Batch size")
    parser.add_argument("--val-split", type=float, default=0.2, help="Validation set split ratio")
    return parser.parse_args()

def evaluate():
    args = parse_args()
    data_dir = Path(args.data_dir)
    model_path = Path(args.model_path)
    classes_path = Path(args.classes_path)

    if not model_path.exists():
        logger.error(f"Model file not found at {model_path}. Please run ml/train.py first.")
        sys.exit(1)

    import tensorflow as tf
    from tensorflow.keras.applications.mobilenet_v2 import preprocess_input
    from sklearn.metrics import classification_report, confusion_matrix, accuracy_score, precision_recall_fscore_support

    # Load class names
    if classes_path.exists():
        with open(classes_path, "r", encoding="utf-8") as f:
            classes = json.load(f)
    else:
        classes = sorted([d.name for d in data_dir.iterdir() if d.is_dir()])

    logger.info(f"Evaluating model on classes: {classes}")

    # Load evaluation/validation dataset
    val_ds = tf.keras.utils.image_dataset_from_directory(
        data_dir,
        validation_split=args.val_split,
        subset="validation",
        seed=42,
        image_size=(224, 224),
        batch_size=args.batch_size,
        label_mode="int",
        class_names=classes,
        shuffle=False
    )

    # Load model
    logger.info(f"Loading trained model from {model_path}...")
    model = tf.keras.models.load_model(str(model_path))

    y_true = []
    y_pred = []

    for images, labels in val_ds:
        # Apply preprocessing
        images_prep = preprocess_input(images)
        preds = model.predict(images_prep, verbose=0)
        predicted_classes = np.argmax(preds, axis=1)

        y_true.extend(labels.numpy().tolist())
        y_pred.extend(predicted_classes.tolist())

    if len(y_true) == 0:
        logger.error("No validation samples were loaded. Please check dataset size and split.")
        sys.exit(1)

    y_true = np.array(y_true)
    y_pred = np.array(y_pred)

    class_indices = list(range(len(classes)))
    acc = accuracy_score(y_true, y_pred)
    precision, recall, f1, _ = precision_recall_fscore_support(y_true, y_pred, average="weighted", zero_division=0)
    conf_matrix = confusion_matrix(y_true, y_pred, labels=class_indices)
    report = classification_report(
        y_true,
        y_pred,
        labels=class_indices,
        target_names=classes,
        zero_division=0
    )

    print("\n=======================================================")
    print("      EyeGUARDIAN Vision - Model Evaluation Report     ")
    print("=======================================================")
    print(f"Overall Accuracy:  {acc * 100:.2f}%")
    print(f"Weighted Precision:{precision:.4f}")
    print(f"Weighted Recall:   {recall:.4f}")
    print(f"Weighted F1-Score: {f1:.4f}")
    print("\nClassification Report:\n")
    print(report)
    print("Confusion Matrix (rows: True, cols: Predicted):")
    print(conf_matrix)
    print("=======================================================\n")

    return {
        "accuracy": acc,
        "precision": precision,
        "recall": recall,
        "f1": f1
    }

if __name__ == "__main__":
    evaluate()
