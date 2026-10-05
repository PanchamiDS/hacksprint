"""FastAPI application for the DrishtiX Flow parcel review pipeline."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .decision import decide_parcel, summarize
from .detector import detect_parcels, inspect_image
from .schemas import DecisionRequest, DecisionResponse, NotificationRequest
from .storage import get_gis_record, list_records, save_decisions, save_notification

app = FastAPI(title="DrishtiX Flow API", version="1.0.0", description="Explainable drone parcel mapping decisions.")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
WEB_ROOT = Path(__file__).resolve().parents[2] / "web"
SAMPLE_ROOT = Path(__file__).resolve().parents[2] / "sample_data"
app.mount("/sample_data", StaticFiles(directory=SAMPLE_ROOT), name="sample_data")


@app.get("/", include_in_schema=False)
def dashboard() -> FileResponse:
    """Serve the single-file operations dashboard."""
    return FileResponse(WEB_ROOT / "index.html")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "drishtix-flow-api"}


@app.post("/detect")
async def detect(file: UploadFile = File(...)) -> dict[str, object]:
    """Run image QA and parcel detection for an uploaded drone tile."""
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=415, detail="Upload a supported image file.")
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Uploaded image is empty.")
    try:
        image, qa = inspect_image(raw)
        detections = detect_parcels(image)
    except Exception as error:
        raise HTTPException(status_code=400, detail=f"Could not process image: {error}") from error
    return {"batch_id": str(uuid4()), "filename": file.filename or "drone-tile", "image_qa": qa, "detections": detections,
            "image_size": {"width": image.width, "height": image.height}}


@app.post("/decide", response_model=DecisionResponse)
def decide(request: DecisionRequest) -> DecisionResponse:
    """Evaluate detections and persist the explainable decision trail."""
    batch_id = request.batch_id or str(uuid4())
    decisions = []
    for detection in request.detections:
        item = decide_parcel(detection, request.image_qa, get_gis_record(detection.parcel_id))
        decisions.append(item)
    save_decisions(batch_id, decisions)
    return DecisionResponse(batch_id=batch_id, decisions=decisions, summary=summarize(decisions))


@app.get("/records")
def records(limit: int = Query(default=100, ge=1, le=500)) -> dict[str, object]:
    """Return the decision history and GIS parcel catalog for the map and table."""
    return {"records": list_records(limit), "parcels": list(get_parcel_catalog().values())}


def get_parcel_catalog() -> dict[str, dict[str, object]]:
    """Expose seed GIS rows, augmented with latest decision action."""
    from .storage import GIS_RECORDS

    catalog = {key: dict(value) for key, value in GIS_RECORDS.items()}
    for row in list_records(500):
        parcel = catalog.get(row["parcel_id"])
        if parcel is not None:
            parcel["action"] = row["action"]
    return catalog


@app.post("/notify")
def notify(request: NotificationRequest) -> dict[str, object]:
    """Queue a surveyor notification (provider-ready Slack/email boundary)."""
    return save_notification(request.model_dump())
