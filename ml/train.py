"""
EyeGUARDIAN Vision - Model Training Pipeline
Transfer learning using MobileNetV2 for external eye screening classification.

DISCLAIMER:
This training script trains a demonstration prototype classifier.
Classes (normal, redness, ptosis, leukocoria, other_abnormal) and predictions
are preliminary screening indicators and do NOT represent clinically validated
diagnostic classifications.
"""

import os
import sys
import json
import argparse
import logging
from pathlib import Path

# Fix Windows console encoding for Keras progress bar characters
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
logger = logging.getLogger("eyeguardian.train")

def parse_args():
    parser = argparse.ArgumentParser(description="Train MobileNetV2 External Eye Screening Model")
    parser.add_argument(
        "--data-dir",
        type=str,
        default=str(PROJECT_ROOT / "data" / "external_eye"),
        help="Path to external eye dataset directory containing class subfolders"
    )
    parser.add_argument(
        "--output-model-path",
        type=str,
        default=str(PROJECT_ROOT / "models" / "external_eye.keras"),
        help="Path to save trained .keras model"
    )
    parser.add_argument(
        "--output-classes-path",
        type=str,
        default=str(PROJECT_ROOT / "models" / "class_names.json"),
        help="Path to save class names JSON"
    )
    parser.add_argument("--epochs", type=int, default=10, help="Number of training epochs")
    parser.add_argument("--batch-size", type=int, default=16, help="Batch size")
    parser.add_argument("--val-split", type=float, default=0.2, help="Validation set split ratio (0.0 - 1.0)")
    parser.add_argument("--learning-rate", type=float, default=1e-4, help="Learning rate for Adam optimizer")
    parser.add_argument("--weights", type=str, default="imagenet", help="Pretrained weights ('imagenet' or 'none')")
    parser.add_argument("--fine-tune", action="store_true", help="Unfreeze top layers for end-to-end fine-tuning")
    return parser.parse_args()

def train():
    args = parse_args()
    data_dir = Path(args.data_dir)
    output_model_path = Path(args.output_model_path)
    output_classes_path = Path(args.output_classes_path)

    os.makedirs(output_model_path.parent, exist_ok=True)

    if not data_dir.exists():
        logger.error(f"Dataset directory not found: {data_dir}")
        sys.exit(1)

    import tensorflow as tf
    from tensorflow.keras import layers, models
    from tensorflow.keras.applications import MobileNetV2
    from tensorflow.keras.applications.mobilenet_v2 import preprocess_input

    # Discover classes
    classes = sorted([d.name for d in data_dir.iterdir() if d.is_dir() and not d.name.startswith(".")])
    if not classes:
        logger.error(f"No class subfolders found in {data_dir}.")
        sys.exit(1)

    logger.info(f"Discovered classes ({len(classes)}): {classes}")

    # Count images
    total_images = sum(len(list(d.glob("*.*"))) for d in data_dir.iterdir() if d.is_dir())
    logger.info(f"Total dataset images: {total_images}")

    if total_images < len(classes) * 2:
        logger.warning(
            "Dataset has very few images. For production training, provide a larger, "
            "properly curated and ethically anonymized dataset."
        )

    img_size = (224, 224)
    seed = 42

    # Split dataset into training and validation
    train_ds = tf.keras.utils.image_dataset_from_directory(
        data_dir,
        validation_split=args.val_split,
        subset="training",
        seed=seed,
        image_size=img_size,
        batch_size=args.batch_size,
        label_mode="categorical",
        class_names=classes
    )

    val_ds = tf.keras.utils.image_dataset_from_directory(
        data_dir,
        validation_split=args.val_split,
        subset="validation",
        seed=seed,
        image_size=img_size,
        batch_size=args.batch_size,
        label_mode="categorical",
        class_names=classes
    )

    # Data Augmentation pipeline to increase robustness and reduce overfitting
    data_augmentation = tf.keras.Sequential([
        layers.RandomFlip("horizontal"),
        layers.RandomRotation(0.08),
        layers.RandomZoom(0.08),
    ], name="data_augmentation")

    # Autotune for performance
    AUTOTUNE = tf.data.AUTOTUNE
    train_ds = train_ds.map(
        lambda x, y: (data_augmentation(x, training=True), y),
        num_parallel_calls=AUTOTUNE
    )
    train_ds = train_ds.map(
        lambda x, y: (preprocess_input(x), y),
        num_parallel_calls=AUTOTUNE
    ).prefetch(buffer_size=AUTOTUNE)

    val_ds = val_ds.map(
        lambda x, y: (preprocess_input(x), y),
        num_parallel_calls=AUTOTUNE
    ).prefetch(buffer_size=AUTOTUNE)

    # Build Transfer Learning Model with MobileNetV2
    pretrained_weights = None if args.weights.lower() == "none" else args.weights
    logger.info(f"Initializing MobileNetV2 backbone (weights={pretrained_weights})...")
    base_model = MobileNetV2(
        input_shape=(224, 224, 3),
        include_top=False,
        weights=pretrained_weights
    )
    base_model.trainable = False  # Freeze base layers for initial transfer learning

    inputs = layers.Input(shape=(224, 224, 3))
    x = base_model(inputs, training=False)
    x = layers.GlobalAveragePooling2D(name="global_avg_pool")(x)
    x = layers.Dropout(0.3, name="dropout")(x)
    outputs = layers.Dense(len(classes), activation="softmax", name="predictions")(x)

    model = models.Model(inputs=inputs, outputs=outputs, name="EyeGUARDIAN_MobileNetV2")

    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=args.learning_rate),
        loss="categorical_crossentropy",
        metrics=["accuracy"]
    )

    model.summary(print_fn=logger.info)

    # Save class names mapping immediately
    logger.info(f"Saving class names to {output_classes_path}...")
    with open(output_classes_path, "w", encoding="utf-8") as f:
        json.dump(classes, f, indent=2)

    # Add Training Callbacks for Best Convergence on Real Images
    callbacks = [
        tf.keras.callbacks.EarlyStopping(
            monitor="val_loss",
            patience=5,
            restore_best_weights=True,
            verbose=1
        ),
        tf.keras.callbacks.ReduceLROnPlateau(
            monitor="val_loss",
            factor=0.5,
            patience=2,
            min_lr=1e-6,
            verbose=1
        ),
        tf.keras.callbacks.ModelCheckpoint(
            filepath=str(output_model_path),
            monitor="val_loss",
            save_best_only=True,
            verbose=1
        )
    ]

    # Train Head
    logger.info(f"Starting transfer learning training for {args.epochs} epochs...")
    history = model.fit(
        train_ds,
        validation_data=val_ds,
        epochs=args.epochs,
        callbacks=callbacks,
        verbose=1
    )

    # Optional Fine-Tuning Stage (unfreeze top layers for higher accuracy on real images)
    if args.fine_tune and args.epochs >= 4:
        logger.info("Starting fine-tuning: unfreezing top layers of MobileNetV2...")
        base_model.trainable = True
        # Freeze all layers except the last 30 layers
        for layer in base_model.layers[:-30]:
            layer.trainable = False

        model.compile(
            optimizer=tf.keras.optimizers.Adam(learning_rate=args.learning_rate * 0.1),
            loss="categorical_crossentropy",
            metrics=["accuracy"]
        )

        fine_tune_epochs = max(2, args.epochs // 2)
        logger.info(f"Fine-tuning for an additional {fine_tune_epochs} epochs...")
        model.fit(
            train_ds,
            validation_data=val_ds,
            epochs=fine_tune_epochs,
            callbacks=callbacks,
            verbose=1
        )

    # Save final best-restored model artifact
    logger.info(f"Saving final trained model to {output_model_path}...")
    model.save(str(output_model_path))

    logger.info(f"Training complete! Model artifact and {len(classes)} classes saved.")

if __name__ == "__main__":
    train()
