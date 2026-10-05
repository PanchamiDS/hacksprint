"""YOLO adapter with a stable, dependency-light demo fallback."""

from __future__ import annotations

import io
from pathlib import Path
from typing import Any

from PIL import Image, ImageFilter, ImageStat

MODEL_PATH = Path(__file__).resolve().parents[2] / "models" / "parcels.pt"


def inspect_image(raw: bytes) -> tuple[Image.Image, dict[str, Any]]:
    """Decode an image and return objective brightness and blur indicators."""
    image = Image.open(io.BytesIO(raw)).convert("RGB")
    grayscale = image.convert("L")
    brightness = float(ImageStat.Stat(grayscale).mean[0])
    edges = grayscale.filter(ImageFilter.FIND_EDGES)
    sharpness = float(ImageStat.Stat(edges).mean[0])
    is_blurry = sharpness < 5.0
    is_too_dark = brightness < 42.0
    return image, {
        "is_blurry": is_blurry,
        "is_too_dark": is_too_dark,
        "sharpness": round(sharpness, 2),
        "brightness": round(brightness, 2),
        "passed": not (is_blurry or is_too_dark),
    }


def detect_parcels(image: Image.Image) -> list[dict[str, Any]]:
    """Run local YOLO weights when available; otherwise return a demo parcel."""
    if MODEL_PATH.is_file():
        try:
            from ultralytics import YOLO  # type: ignore[import-not-found]

            model = YOLO(str(MODEL_PATH))
            prediction = model.predict(image, verbose=False)[0]
            output: list[dict[str, Any]] = []
            for index, box in enumerate(prediction.boxes):
                x1, y1, x2, y2 = (float(value) for value in box.xyxy[0].tolist())
                width, height = image.size
                output.append({
                    "parcel_id": f"P-{104 + index}",
                    "confidence": float(box.conf[0]),
                    "area_m2": max(((x2 - x1) * (y2 - y1)) / 100.0, 1.0),
                    "bbox": [x1 / width, y1 / height, x2 / width, y2 / height],
                    "label": "parcel",
                })
            return output
        except (ImportError, RuntimeError, ValueError) as error:
            raise RuntimeError(f"YOLO weights exist but inference failed: {error}") from error

    width, height = image.size
    return [{
        "parcel_id": "P-104",
        "confidence": 0.93,
        "area_m2": 1210.0,
        "bbox": [0.18, 0.16, 0.79, 0.82],
        "iou": 0.84,
        "label": "parcel",
    }]
