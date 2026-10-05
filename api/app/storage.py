"""Small storage adapter: PostGIS in Compose, in-memory records for local tests."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any

DATABASE_URL = os.getenv("DATABASE_URL", "")

# Seed data keeps the dashboard useful before PostGIS is started.
GIS_RECORDS: dict[str, dict[str, Any]] = {
    "P-104": {"parcel_id": "P-104", "area_m2": 1180.0, "iou": 0.84, "lat": 12.9716, "lon": 77.5946, "status": "mapped"},
    "P-105": {"parcel_id": "P-105", "area_m2": 960.0, "iou": 0.68, "lat": 12.9741, "lon": 77.5982, "status": "mapped"},
    "P-106": {"parcel_id": "P-106", "area_m2": 1430.0, "iou": 0.58, "lat": 12.9689, "lon": 77.6011, "status": "mapped"},
}
DECISIONS: list[dict[str, Any]] = []
NOTIFICATIONS: list[dict[str, Any]] = []


def get_gis_record(parcel_id: str) -> dict[str, Any] | None:
    """Return a GIS reference row from PostGIS or the local seed catalog."""
    if DATABASE_URL:
        try:
            import psycopg

            with psycopg.connect(DATABASE_URL) as connection:
                row = connection.execute(
                    "SELECT parcel_id, area_m2, ST_Y(centroid), ST_X(centroid) FROM parcels WHERE parcel_id = %s",
                    (parcel_id,),
                ).fetchone()
            if row:
                return {"parcel_id": row[0], "area_m2": float(row[1]), "lat": float(row[2]), "lon": float(row[3]), "iou": None}
        except (ImportError, OSError):
            pass
    return GIS_RECORDS.get(parcel_id)


def save_decisions(batch_id: str, decisions: list[dict[str, Any]]) -> None:
    """Persist decisions to PostGIS when available and always retain local history."""
    timestamp = datetime.now(timezone.utc).isoformat()
    for item in decisions:
        row = {**item, "batch_id": batch_id, "created_at": timestamp}
        DECISIONS.insert(0, row)
        if DATABASE_URL:
            try:
                import psycopg

                with psycopg.connect(DATABASE_URL) as connection:
                    connection.execute(
                        "INSERT INTO decisions (batch_id, parcel_id, action, confidence, iou, area_mismatch_pct, reasons, payload) "
                        "VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb)",
                        (batch_id, item["parcel_id"], item["action"], item["confidence"], item["iou"],
                         item["area_mismatch_pct"], json.dumps(item["reasons"]), json.dumps(item, default=str)),
                    )
            except (ImportError, OSError):
                pass


def list_records(limit: int = 100) -> list[dict[str, Any]]:
    """Return newest decisions, preferring the database when configured."""
    if DATABASE_URL:
        try:
            import psycopg

            with psycopg.connect(DATABASE_URL) as connection:
                rows = connection.execute(
                    "SELECT batch_id, parcel_id, action, confidence, iou, area_mismatch_pct, reasons, created_at "
                    "FROM decisions ORDER BY created_at DESC LIMIT %s", (limit,),
                ).fetchall()
            if rows:
                return [{"batch_id": row[0], "parcel_id": row[1], "action": row[2], "confidence": row[3],
                         "iou": row[4], "area_mismatch_pct": row[5], "reasons": row[6], "created_at": row[7].isoformat()} for row in rows]
        except (ImportError, OSError):
            pass
    return DECISIONS[:limit]


def save_notification(notification: dict[str, Any]) -> dict[str, Any]:
    """Record a notification request for the Slack/email integration boundary."""
    item = {**notification, "created_at": datetime.now(timezone.utc).isoformat(), "status": "queued"}
    NOTIFICATIONS.insert(0, item)
    return item
