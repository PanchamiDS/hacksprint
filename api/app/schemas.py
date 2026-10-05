"""Typed request and response models for the DrishtiX API."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Action = Literal["APPROVE", "FLAG", "RESURVEY"]


class ImageQA(BaseModel):
    is_blurry: bool = False
    is_too_dark: bool = False
    sharpness: float = 0.0
    brightness: float = 0.0
    passed: bool = True


class Detection(BaseModel):
    parcel_id: str = "P-104"
    confidence: float = Field(ge=0.0, le=1.0)
    area_m2: float = Field(gt=0.0)
    bbox: list[float] = Field(default_factory=list)
    iou: float | None = Field(default=None, ge=0.0, le=1.0)
    label: str = "parcel"


class DecisionRequest(BaseModel):
    detections: list[Detection] = Field(default_factory=list)
    image_qa: ImageQA = Field(default_factory=ImageQA)
    batch_id: str | None = None


class DecisionItem(BaseModel):
    parcel_id: str
    action: Action
    confidence: float
    iou: float | None = None
    area_mismatch_pct: float | None = None
    reasons: list[str]
    detection: Detection


class DecisionResponse(BaseModel):
    batch_id: str
    decisions: list[DecisionItem]
    summary: dict[str, int | float | str]


class NotificationRequest(BaseModel):
    parcel_id: str
    action: Action
    message: str
    channel: str = "surveyor"
    batch_id: str | None = None
