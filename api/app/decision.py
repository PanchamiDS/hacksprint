"""Explainable parcel decision rules used by both the API and tests."""

from __future__ import annotations

from typing import Any

from .schemas import Action, Detection, ImageQA


def decide_parcel(
    detection: Detection,
    image_qa: ImageQA,
    gis_record: dict[str, Any] | None,
) -> dict[str, Any]:
    """Apply deterministic QA, confidence, GIS overlap, and area rules."""
    reasons: list[str] = []
    mismatch: float | None = None
    iou: float | None = detection.iou
    action: Action

    if image_qa.is_blurry or image_qa.is_too_dark or not image_qa.passed:
        if image_qa.is_blurry:
            reasons.append("Image is too blurry for reliable parcel mapping.")
        if image_qa.is_too_dark:
            reasons.append("Image is too dark for reliable parcel mapping.")
        if not image_qa.passed and not reasons:
            reasons.append("Image quality checks did not pass.")
        return _result(detection, "RESURVEY", reasons, iou, mismatch)

    if detection.confidence < 0.60:
        reasons.append(f"Model confidence {detection.confidence:.0%} is below the 60% minimum.")
        return _result(detection, "RESURVEY", reasons, iou, mismatch)

    if gis_record is None:
        reasons.append(f"No GIS reference record was found for parcel {detection.parcel_id}.")
        return _result(detection, "FLAG", reasons, iou, mismatch)

    if iou is None:
        raw_iou = gis_record.get("iou")
        iou = float(raw_iou) if raw_iou is not None else None

    gis_area = float(gis_record.get("area_m2", 0.0))
    if gis_area > 0:
        mismatch = abs(detection.area_m2 - gis_area) / gis_area * 100.0

    if iou is None:
        reasons.append("GIS overlap could not be calculated; manual review is required.")
        return _result(detection, "FLAG", reasons, iou, mismatch)

    if detection.confidence >= 0.85 and iou >= 0.70 and mismatch is not None and mismatch <= 25.0:
        reasons.extend([
            f"Model confidence is high ({detection.confidence:.0%} ≥ 85%).",
            f"GIS overlap is strong (IoU {iou:.2f} ≥ 0.70).",
            f"Area agrees with GIS within tolerance ({mismatch:.1f}% mismatch).",
        ])
        action = "APPROVE"
        return _result(detection, action, reasons, iou, mismatch)

    if iou < 0.70:
        reasons.append(f"GIS overlap is low (IoU {iou:.2f} < 0.70).")
    if mismatch is None:
        reasons.append("GIS reference is missing a usable parcel area.")
    elif mismatch > 25.0:
        reasons.append(f"Detected area differs from GIS by {mismatch:.1f}% (limit 25%).")
    if detection.confidence < 0.85:
        reasons.append(f"Confidence {detection.confidence:.0%} is below the 85% auto-approval threshold.")
    if not reasons:
        reasons.append("The parcel did not meet every automatic approval condition.")
    return _result(detection, "FLAG", reasons, iou, mismatch)


def summarize(decisions: list[dict[str, Any]]) -> dict[str, int | float | str]:
    """Summarize a batch and choose its downstream workflow route."""
    counts = {action: sum(item["action"] == action for item in decisions) for action in ("APPROVE", "FLAG", "RESURVEY")}
    total = len(decisions)
    automation_rate = round(counts["APPROVE"] / total * 100.0, 1) if total else 0.0
    if total and counts["RESURVEY"] == total:
        batch_action = "resurvey"
    elif counts["FLAG"] or counts["RESURVEY"]:
        batch_action = "review"
    else:
        batch_action = "auto_publish"
    return {
        "total": total,
        "approved": counts["APPROVE"],
        "flagged": counts["FLAG"],
        "resurvey": counts["RESURVEY"],
        "automation_rate": automation_rate,
        "batch_action": batch_action,
    }


def _result(
    detection: Detection,
    action: Action,
    reasons: list[str],
    iou: float | None,
    mismatch: float | None,
) -> dict[str, Any]:
    return {
        "parcel_id": detection.parcel_id,
        "action": action,
        "confidence": detection.confidence,
        "iou": iou,
        "area_mismatch_pct": round(mismatch, 2) if mismatch is not None else None,
        "reasons": reasons,
        "detection": detection,
    }
