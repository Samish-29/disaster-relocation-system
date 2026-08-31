import asyncio
from typing import Any, Dict, List

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.realtime.engine import (
    build_demo_realtime_update,
    evaluate_safe_zone_status,
    load_demo_event_feed,
    load_demo_safe_zone_names,
    normalize_hazard_event,
)

router = APIRouter(prefix="/api/realtime")


@router.get("/health")
def realtime_health() -> Dict[str, Any]:
    return {
        "status": "ok",
        "mode": "near-real-time",
        "description": "Multi-hazard monitoring and safe-zone status evaluation is active.",
    }


@router.get("/hazards")
def get_hazard_feed() -> Dict[str, Any]:
    return {
        "source": "demo",
        "mode": "near-real-time",
        "events": load_demo_event_feed(),
    }


@router.get("/safe-zone-status")
def get_safe_zone_status() -> Dict[str, Any]:
    return build_demo_realtime_update()


@router.post("/hazard")
def ingest_hazard(event: Dict[str, Any]) -> Dict[str, Any]:
    normalized_event = normalize_hazard_event(event)
    safe_zones = load_demo_safe_zone_names()
    statuses = [
        evaluate_safe_zone_status(zone, normalized_event, threshold_distance_km=15.0, threshold_severity=0.6)
        for zone in safe_zones
    ]
    return {
        "status": "accepted",
        "mode": "near-real-time",
        "hazard": normalized_event,
        "safe_zone_updates": statuses,
    }


@router.websocket("/ws")
async def realtime_ws(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            payload = build_demo_realtime_update()
            await websocket.send_json({
                "type": "realtime_update",
                "mode": "near-real-time",
                "payload": payload,
            })
            await asyncio.sleep(12)
    except WebSocketDisconnect:
        return
