"""Validate a LabelLens YOLO dataset without requiring Ultralytics or a GPU."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import List


EXPECTED_CLASS_COUNT = 8
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def _read_yaml_paths(data_yaml: Path) -> dict[str, str]:
    """Read the few YAML keys needed here without adding a PyYAML dependency."""
    values: dict[str, str] = {}
    for raw_line in data_yaml.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        if key.strip() in {"path", "train", "val"}:
            values[key.strip()] = value.strip().strip("\"'")
    return values


def validate_dataset(data_yaml: Path, quiet: bool = False) -> List[str]:
    errors: List[str] = []
    if not data_yaml.exists():
        return [f"Dataset configuration not found: {data_yaml}"]

    config = _read_yaml_paths(data_yaml)
    if not {"path", "train", "val"}.issubset(config):
        return ["data.yaml must define path, train, and val."]

    dataset_root = (data_yaml.parent / config["path"]).resolve()
    for split_key in ("train", "val"):
        image_dir = dataset_root / config[split_key]
        label_dir = dataset_root / "labels" / split_key
        images = [p for p in image_dir.glob("*") if p.suffix.lower() in IMAGE_EXTENSIONS] if image_dir.exists() else []
        if not images:
            errors.append(f"No images found in {image_dir}")
            continue
        if not label_dir.exists():
            errors.append(f"Label directory not found: {label_dir}")
            continue

        for image_path in images:
            label_path = label_dir / f"{image_path.stem}.txt"
            if not label_path.exists():
                errors.append(f"Missing label for {image_path.name}")
                continue
            for line_number, line in enumerate(label_path.read_text(encoding="utf-8").splitlines(), 1):
                parts = line.split()
                if len(parts) != 5:
                    errors.append(f"{label_path.name}:{line_number} must have 5 values")
                    continue
                try:
                    class_id = int(parts[0])
                    coords = [float(v) for v in parts[1:]]
                except ValueError:
                    errors.append(f"{label_path.name}:{line_number} contains non-numeric values")
                    continue
                if not 0 <= class_id < EXPECTED_CLASS_COUNT:
                    errors.append(f"{label_path.name}:{line_number} uses unknown class {class_id}")
                if any(not 0 < value <= 1 for value in coords[2:]) or any(not 0 <= value <= 1 for value in coords[:2]):
                    errors.append(f"{label_path.name}:{line_number} has invalid normalized coordinates")

    if not quiet:
        if errors:
            print("Dataset validation failed:")
            print("\n".join(f"- {error}" for error in errors))
        else:
            print("Dataset validation passed.")
    return errors


if __name__ == "__main__":
    yaml_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("dataset/data.yaml")
    sys.exit(1 if validate_dataset(yaml_path) else 0)
