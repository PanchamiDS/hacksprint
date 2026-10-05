"""Submit the generated demo tile to a running DrishtiX API."""

from __future__ import annotations

import json
import time
import uuid
from urllib.error import HTTPError, URLError
from pathlib import Path
from urllib.request import Request, urlopen

API = "http://localhost:8000"
IMAGE = Path(__file__).resolve().parents[1] / "sample_data" / "sample_tile.jpg"


def post_json(path: str, payload: dict[str, object]) -> dict[str, object]:
    """Send a JSON request using the standard library only."""
    body = json.dumps(payload).encode("utf-8")
    request = Request(f"{API}{path}", data=body, headers={"Content-Type": "application/json"}, method="POST")
    with urlopen(request, timeout=45) as response:
        return json.load(response)


def main() -> None:
    if not IMAGE.exists():
        raise SystemExit("Sample image is missing. Run `make sample` first.")
    for attempt in range(30):
        try:
            with urlopen(f"{API}/health", timeout=2):
                break
        except (URLError, TimeoutError):
            if attempt == 29:
                raise SystemExit("API did not become ready. Check `docker compose logs api`.")
            time.sleep(1)

    boundary = f"----DrishtiX{uuid.uuid4().hex}"
    image_bytes = IMAGE.read_bytes()
    multipart = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{IMAGE.name}"\r\n'
        "Content-Type: image/jpeg\r\n\r\n"
    ).encode("utf-8") + image_bytes + f"\r\n--{boundary}--\r\n".encode("utf-8")
    detect_request = Request(f"{API}/detect", data=multipart, headers={"Content-Type": f"multipart/form-data; boundary={boundary}"}, method="POST")
    try:
        with urlopen(detect_request, timeout=45) as response:
            payload = json.load(response)
        result = post_json("/decide", {
            "batch_id": payload["batch_id"],
            "image_qa": payload["image_qa"],
            "detections": payload["detections"],
        })
        if result["decisions"] and result["decisions"][0]["action"] != "APPROVE":
            decision = result["decisions"][0]
            post_json("/notify", {"parcel_id": decision["parcel_id"], "action": decision["action"], "message": " ".join(decision["reasons"]), "batch_id": result["batch_id"]})
    except (HTTPError, URLError, TimeoutError) as error:
        raise SystemExit(f"API request failed: {error}. Is `docker compose up` running?") from error
    print(json.dumps(result, indent=2))
    print("\nDashboard: http://localhost:8000")
    print("n8n editor: http://localhost:5678")


if __name__ == "__main__":
    main()
