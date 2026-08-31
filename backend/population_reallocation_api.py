from __future__ import annotations

from typing import Dict, List, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from backend.reallocation import (
    allocate_population,
    build_evacuation_routes,
    calculate_resource_requirements,
    rank_safe_zones,
)

router = APIRouter(prefix="/api/population-reallocation")


class ZoneInput(BaseModel):
    district: str = Field(...)
    name: Optional[str] = None
    population: float = 0.0
    risk_level: Optional[str] = "LOW"
    risk_score: float = 0.0
    capacity: float = 0.0
    current_population: float = 0.0
    distance_km: float = 0.0
    travel_time_minutes: float = 0.0
    road_accessibility: float = 0.6
    medical_facilities: float = 0.6
    food_water: float = 0.6
    infrastructure_score: float = 0.6


class AnalyzeRequest(BaseModel):
    red_zone_name: str
    red_zone_population: float
    safe_zones: List[ZoneInput]
    weights: Optional[Dict[str, float]] = None


@router.get("/health")
def health():
    return {"status": "ok"}


@router.post("/analyze")
def analyze_reallocation(payload: AnalyzeRequest):
    safe_zone_data = [zone.model_dump() for zone in payload.safe_zones]
    ranked = rank_safe_zones(safe_zone_data, payload.weights)
    allocation = allocate_population(payload.red_zone_population, ranked, payload.weights)
    return {
        "red_zone": payload.red_zone_name,
        "total_affected_population": payload.red_zone_population,
        "safe_zone_ranking": ranked,
        "allocation": allocation,
        "routes": build_evacuation_routes(payload.red_zone_population, allocation["allocations"], payload.red_zone_name),
        "warnings": allocation.get("warning"),
    }


@router.post("/allocate")
def allocate_relocation(payload: AnalyzeRequest):
    safe_zone_data = [zone.model_dump() for zone in payload.safe_zones]
    ranked = rank_safe_zones(safe_zone_data, payload.weights)
    allocation = allocate_population(payload.red_zone_population, ranked, payload.weights)
    return {
        "red_zone": payload.red_zone_name,
        "allocations": allocation,
        "routes": build_evacuation_routes(payload.red_zone_population, allocation["allocations"], payload.red_zone_name),
    }


@router.get("/safe-zones")
def get_safe_zones():
    return {
        "safe_zones": [
            {
                "district": "Safe Zone A",
                "capacity": 7000,
                "current_population": 2000,
                "available_capacity": 5000,
                "risk_score": 0.2,
                "road_accessibility": 0.9,
                "medical_facilities": 0.8,
                "food_water": 0.7,
                "infrastructure_score": 0.8,
                "distance_km": 26,
                "travel_time_minutes": 45,
            },
            {
                "district": "Safe Zone B",
                "capacity": 6000,
                "current_population": 3500,
                "available_capacity": 2500,
                "risk_score": 0.3,
                "road_accessibility": 0.85,
                "medical_facilities": 0.6,
                "food_water": 0.8,
                "infrastructure_score": 0.7,
                "distance_km": 38,
                "travel_time_minutes": 60,
            },
            {
                "district": "Safe Zone C",
                "capacity": 5000,
                "current_population": 1200,
                "available_capacity": 3800,
                "risk_score": 0.5,
                "road_accessibility": 0.7,
                "medical_facilities": 0.9,
                "food_water": 0.5,
                "infrastructure_score": 0.6,
                "distance_km": 54,
                "travel_time_minutes": 75,
            },
            {
                "district": "Safe Zone D",
                "capacity": 8000,
                "current_population": 4000,
                "available_capacity": 4000,
                "risk_score": 0.4,
                "road_accessibility": 0.8,
                "medical_facilities": 0.7,
                "food_water": 0.9,
                "infrastructure_score": 0.9,
                "distance_km": 71,
                "travel_time_minutes": 90,
            },
        ]
    }


@router.get("/red-zones/population")
def get_red_zone_population():
    return {
        "red_zones": [
            {
                "district": "Red Zone A",
                "population": 20000,
                "risk_level": "HIGH",
                "people_requiring_relocation": 20000,
                "available_evacuation_points": 3,
                "roads": ["NH 27", "State Highway 3"],
            }
        ]
    }


@router.get("/evacuation-routes")
def get_evacuation_routes():
    return {
        "routes": [
            {
                "red_zone": "Red Zone A",
                "safe_zone": "Safe Zone A",
                "primary_route": {"distance_km": 26, "travel_time_minutes": 45, "route_risk_score": 0.35},
                "alternative_route": {"distance_km": 30, "travel_time_minutes": 52, "route_risk_score": 0.52},
                "people_assigned": 7000,
            }
        ]
    }


@router.get("/resource-requirements")
def get_resource_requirements():
    return {
        "safe_zone_resources": [
            {
                "safe_zone": "Safe Zone A",
                "population_assigned": 7000,
                **calculate_resource_requirements(7000, {"district": "Safe Zone A"}),
            },
            {
                "safe_zone": "Safe Zone B",
                "population_assigned": 6000,
                **calculate_resource_requirements(6000, {"district": "Safe Zone B"}),
            },
        ]
    }
