import argparse
import os
import sys
from pathlib import Path


def validate_dataset(data_yaml: str) -> None:
    """Validate the YOLO dataset before starting an expensive training run."""
    from validate_yolo_dataset import validate_dataset as run_validation

    errors = run_validation(Path(data_yaml), quiet=True)
    if errors:
        print("ERROR: Dataset validation failed:")
        for error in errors:
            print(f"  - {error}")
        sys.exit(2)

def train_custom_detector(
    data_yaml: str,
    epochs: int = 100,
    batch: int = 16,
    imgsz: int = 640,
    output_dir: str = "models",
    base_model: str = "yolo11n.pt",
):
    """
    Fine-tunes a YOLO model for Legal Metrology label regions.
    """
    try:
        from ultralytics import YOLO
    except ImportError:
        print("ERROR: ultralytics is not installed. Please run: pip install ultralytics")
        sys.exit(1)

    validate_dataset(data_yaml)
    print(f"Starting Legal Metrology YOLO fine-tuning with dataset: {data_yaml}")
    print(f"Epochs: {epochs} | Batch: {batch} | Image Size: {imgsz}")

    # Load base YOLO11 nano model
    model = YOLO(base_model)

    # Train
    results = model.train(
        data=data_yaml,
        epochs=epochs,
        batch=batch,
        imgsz=imgsz,
        project=output_dir,
        name="legal_detector",
        save=True,
        plots=True
    )

    best_weights = Path(output_dir) / "legal_detector" / "weights" / "best.pt"
    target_weights = Path(output_dir) / "legal_label_detector.pt"

    if best_weights.exists():
        import shutil
        shutil.copy(best_weights, target_weights)
        print(f"\nTraining Complete! Best model saved to: {target_weights}")
        print("LabelLens will automatically load these custom weights on next startup.")
    else:
        print(f"Training finished. Check results in {output_dir}/legal_detector")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train custom Legal Metrology YOLO region detector")
    parser.add_argument("--data", type=str, default="dataset/data.yaml", help="Path to data.yaml")
    parser.add_argument("--epochs", type=int, default=100, help="Number of training epochs")
    parser.add_argument("--batch", type=int, default=16, help="Batch size")
    parser.add_argument("--imgsz", type=int, default=640, help="Image resolution")
    parser.add_argument("--output", type=str, default="models", help="Output directory")
    parser.add_argument("--model", type=str, default="yolo11n.pt", help="Base YOLO checkpoint to fine-tune")

    args = parser.parse_args()
    train_custom_detector(args.data, args.epochs, args.batch, args.imgsz, args.output, args.model)
