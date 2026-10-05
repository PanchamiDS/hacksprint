"""Decision-engine rule coverage."""

from api.app.decision import decide_parcel, summarize
from api.app.schemas import Detection, ImageQA


def detection(**overrides: object) -> Detection:
    values: dict[str, object] = {"parcel_id": "P-104", "confidence": 0.93, "area_m2": 1210.0, "iou": 0.84}
    values.update(overrides)
    return Detection(**values)


GIS = {"parcel_id": "P-104", "area_m2": 1180.0, "iou": 0.84}


def test_blurry_image_routes_to_resurvey() -> None:
    result = decide_parcel(detection(), ImageQA(is_blurry=True), GIS)
    assert result["action"] == "RESURVEY"
    assert "blurry" in result["reasons"][0]


def test_dark_image_routes_to_resurvey() -> None:
    assert decide_parcel(detection(), ImageQA(is_too_dark=True), GIS)["action"] == "RESURVEY"


def test_failed_qa_routes_to_resurvey() -> None:
    assert decide_parcel(detection(), ImageQA(passed=False), GIS)["action"] == "RESURVEY"


def test_low_confidence_routes_to_resurvey() -> None:
    result = decide_parcel(detection(confidence=0.59), ImageQA(), GIS)
    assert result["action"] == "RESURVEY"
    assert "below the 60%" in result["reasons"][0]


def test_strong_match_is_approved() -> None:
    result = decide_parcel(detection(), ImageQA(), GIS)
    assert result["action"] == "APPROVE"
    assert len(result["reasons"]) == 3


def test_missing_gis_record_is_flagged() -> None:
    result = decide_parcel(detection(parcel_id="P-999"), ImageQA(), None)
    assert result["action"] == "FLAG"
    assert "No GIS reference" in result["reasons"][0]


def test_low_iou_is_flagged() -> None:
    result = decide_parcel(detection(iou=0.69), ImageQA(), GIS)
    assert result["action"] == "FLAG"
    assert any("overlap is low" in reason for reason in result["reasons"])


def test_area_mismatch_over_25_percent_is_flagged() -> None:
    result = decide_parcel(detection(area_m2=1500), ImageQA(), GIS)
    assert result["action"] == "FLAG"
    assert any("differs from GIS" in reason for reason in result["reasons"])


def test_medium_confidence_requires_review() -> None:
    result = decide_parcel(detection(confidence=0.75), ImageQA(), GIS)
    assert result["action"] == "FLAG"
    assert any("below the 85%" in reason for reason in result["reasons"])


def test_batch_routes_and_calculates_automation_rate() -> None:
    summary = summarize([{"action": "APPROVE"}, {"action": "FLAG"}])
    assert summary["automation_rate"] == 50.0
    assert summary["batch_action"] == "review"


def test_all_resurvey_batch_routes_to_resurvey() -> None:
    assert summarize([{"action": "RESURVEY"}])["batch_action"] == "resurvey"
