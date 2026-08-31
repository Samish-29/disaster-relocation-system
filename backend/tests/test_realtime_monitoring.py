from backend.realtime.engine import (
    evaluate_safe_zone_status,
    load_assam_district_names,
    normalize_hazard_event,
)


def test_uses_real_assam_district_names_for_monitoring():
    district_names = load_assam_district_names()

    assert len(district_names) >= 10
    assert "Tinsukia" in district_names
    assert "Dibrugarh" in district_names
    assert "Safe Zone A" not in district_names


def test_normalize_hazard_event_sets_severity_and_status():
    payload = {
        "hazard_type": "flood",
        "district": "Dibrugarh",
        "severity": "severe",
        "source": "SACHET",
        "distance_km": 12,
        "warning": "River banks rising rapidly"
    }

    normalized = normalize_hazard_event(payload)

    assert normalized["hazard_type"] == "flood"
    assert normalized["severity_score"] >= 0.7
    assert normalized["status"] in {"watch", "warning", "alert"}
    assert normalized["source"] == "SACHET"


def test_evaluate_safe_zone_status_detects_alert_condition():
    hazard = {
        "hazard_type": "flood",
        "district": "Safe Zone A",
        "severity": "extreme",
        "source": "IMD",
        "distance_km": 4,
        "warning": "Water levels rising near safe zone"
    }

    result = evaluate_safe_zone_status(
        "Safe Zone A",
        hazard,
        threshold_distance_km=10,
        threshold_severity=0.6,
    )

    assert result["status"] == "alert"
    assert result["impact_level"] in {"critical", "high"}
    assert result["triggered"] is True
