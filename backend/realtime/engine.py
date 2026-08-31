from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


SEVERITY_MAP = {
    "normal": 0.15,
    "watch": 0.35,
    "advisory": 0.5,
    "warning": 0.7,
    "severe": 0.8,
    "extreme": 0.96,
}

HAZARD_TYPE_WEIGHTS = {
    "flood": 1.0,
    "earthquake": 1.1,
    "storm": 0.9,
    "cyclone": 1.15,
    "landslide": 0.85,
    "heat": 0.6,
    "fire": 0.8,
    "unknown": 0.5,
}


def normalize_hazard_event(event: Dict[str, Any]) -> Dict[str, Any]:
    hazard_type = str((event or {}).get("hazard_type") or (event or {}).get("type") or "unknown").lower()
    source = str((event or {}).get("source") or "manual").upper()
    raw_severity = str((event or {}).get("severity") or "watch").lower()
    severity_score = float((event or {}).get("severity_score") or SEVERITY_MAP.get(raw_severity, SEVERITY_MAP["watch"]))
    distance_km = float((event or {}).get("distance_km") or 0.0)
    warning = str((event or {}).get("warning") or (event or {}).get("message") or "Hazard event reported").strip()
    now = datetime.now(timezone.utc).isoformat()

    status = "watch"
    if severity_score >= 0.85:
        status = "alert"
    elif severity_score >= 0.6:
        status = "warning"
    elif severity_score >= 0.35:
        status = "watch"

    normalized = {
        "hazard_type": hazard_type,
        "source": source,
        "severity": raw_severity,
        "severity_score": round(clamp(severity_score, 0.0, 1.0), 3),
        "distance_km": distance_km,
        "warning": warning,
        "status": status,
        "timestamp": now,
    }

    normalized["risk_weight"] = round(
        clamp(
            (HAZARD_TYPE_WEIGHTS.get(hazard_type, 0.5) * normalized["severity_score"])
            + (0.2 if distance_km <= 25 else 0.0),
            0.0,
            1.0,
        ),
        3,
    )

    return normalized


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def evaluate_safe_zone_status(
    safe_zone_name: str,
    hazard_event: Dict[str, Any],
    threshold_distance_km: float = 15.0,
    threshold_severity: float = 0.6,
) -> Dict[str, Any]:
    normalized = normalize_hazard_event(hazard_event)
    is_near = normalized["distance_km"] <= threshold_distance_km
    is_severe = normalized["severity_score"] >= threshold_severity
    triggered = is_near and is_severe

    if triggered and normalized["severity_score"] >= 0.85:
        status = "alert"
        impact_level = "critical"
    elif triggered:
        status = "warning"
        impact_level = "high"
    elif is_near or is_severe:
        status = "watch"
        impact_level = "medium"
    else:
        status = "stable"
        impact_level = "low"

    return {
        "safe_zone": safe_zone_name,
        "hazard_type": normalized["hazard_type"],
        "status": status,
        "impact_level": impact_level,
        "severity_score": normalized["severity_score"],
        "distance_km": normalized["distance_km"],
        "source": normalized["source"],
        "warning": normalized["warning"],
        "triggered": triggered,
        "timestamp": normalized["timestamp"],
    }


def monitor_hazard_events(
    events: Iterable[Dict[str, Any]],
    safe_zones: Iterable[str],
    threshold_distance_km: float = 15.0,
    threshold_severity: float = 0.6,
) -> List[Dict[str, Any]]:
    safe_zone_names = list(safe_zones)
    monitored = []

    for event in events:
        normalized = normalize_hazard_event(event)
        for safe_zone_name in safe_zone_names:
            monitored.append(
                evaluate_safe_zone_status(
                    safe_zone_name,
                    normalized,
                    threshold_distance_km=threshold_distance_km,
                    threshold_severity=threshold_severity,
                )
            )

    return monitored


def get_realtime_status_snapshot(
    safe_zones: Iterable[str],
    hazard_events: Optional[Iterable[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    hazard_events = list(hazard_events or [])
    statuses = []

    for safe_zone_name in safe_zones:
        zone_status = {
            "safe_zone": safe_zone_name,
            "status": "stable",
            "active_hazards": [],
            "alert_count": 0,
        }
        for event in hazard_events:
            evaluation = evaluate_safe_zone_status(
                safe_zone_name,
                event,
                threshold_distance_km=15.0,
                threshold_severity=0.6,
            )
            if evaluation["triggered"]:
                zone_status["active_hazards"].append(evaluation)
                zone_status["alert_count"] += 1
                if evaluation["status"] in {"warning", "alert"}:
                    zone_status["status"] = evaluation["status"]
        statuses.append(zone_status)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "safe_zones": statuses,
    }


def load_demo_event_feed() -> List[Dict[str, Any]]:
    return [
        {
            "hazard_type": "flood",
            "district": "Dibrugarh",
            "severity": "warning",
            "source": "SACHET",
            "distance_km": 6,
            "warning": "River levels rising near a safe-zone corridor.",
        },
        {
            "hazard_type": "storm",
            "district": "Tezpur",
            "severity": "severe",
            "source": "IMD",
            "distance_km": 14,
            "warning": "Wind gusts and downpours impacting roads.",
        },
    ]


def load_assam_district_names() -> List[str]:
    zones_file = Path(__file__).resolve().parents[2] / "data" / "processed" / "zones" / "assam_risk_zones.geojson"
    if not zones_file.exists():
        return ["Tinsukia", "Dibrugarh", "Sivasagar", "Jorhat", "Golaghat", "Nagaon", "Kamrup", "Dhubri", "Barpeta", "Darrang"]

    try:
        with zones_file.open("r", encoding="utf-8") as f:
            data = json.load(f)
        districts = []
        for feature in data.get("features", []):
            district_name = (feature.get("properties") or {}).get("district")
            if district_name:
                districts.append(str(district_name))
        return districts or ["Tinsukia", "Dibrugarh", "Sivasagar", "Jorhat", "Golaghat", "Nagaon", "Kamrup", "Dhubri", "Barpeta", "Darrang"]
    except (TypeError, ValueError, OSError):
        return ["Tinsukia", "Dibrugarh", "Sivasagar", "Jorhat", "Golaghat", "Nagaon", "Kamrup", "Dhubri", "Barpeta", "Darrang"]


def load_demo_safe_zone_names() -> List[str]:
    return load_assam_district_names()


def build_demo_realtime_update() -> Dict[str, Any]:
    return get_realtime_status_snapshot(
        load_demo_safe_zone_names(),
        load_demo_event_feed(),
    )
