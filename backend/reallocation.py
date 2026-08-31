from __future__ import annotations

from typing import Any, Dict, List, Optional

DEFAULT_WEIGHTS = {
    "risk_score": 0.25,
    "distance": 0.20,
    "road_accessibility": 0.15,
    "medical_facilities": 0.10,
    "food_water": 0.10,
    "infrastructure": 0.10,
    "travel_time": 0.05,
    "capacity": 0.05,
}

RESOURCE_REQUIREMENTS = {
    "food_kg_per_person_per_day": 0.75,
    "water_liters_per_person_per_day": 4.5,
    "medical_capacity_per_person": 0.12,
    "shelter_space_per_person": 0.32,
    "toilets_per_person": 0.03,
    "electricity_kwh_per_person_per_day": 0.85,
    "emergency_personnel_per_1000": 0.8,
}


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _normalize_zone(zone: Dict[str, Any]) -> Dict[str, Any]:
    name = zone.get("district") or zone.get("name") or "Unknown Safe Zone"
    capacity = _as_float(zone.get("capacity"), 0.0)
    current_population = _as_float(zone.get("current_population"), zone.get("population", 0.0))
    available_capacity = max(0.0, capacity - current_population)

    normalized = dict(zone)
    normalized["name"] = name
    normalized["district"] = name
    normalized["capacity"] = capacity
    normalized["current_population"] = current_population
    normalized["available_capacity"] = available_capacity
    normalized["risk_score"] = _as_float(zone.get("risk_score"), 0.0)
    normalized["distance_km"] = _as_float(zone.get("distance_km"), 0.0)
    normalized["travel_time_minutes"] = _as_float(zone.get("travel_time_minutes"), 0.0)
    normalized["road_accessibility"] = _as_float(zone.get("road_accessibility"), 0.6)
    normalized["medical_facilities"] = _as_float(zone.get("medical_facilities"), 0.6)
    normalized["food_water"] = _as_float(zone.get("food_water"), 0.6)
    normalized["infrastructure_score"] = _as_float(zone.get("infrastructure_score"), 0.6)
    normalized["risk_level"] = zone.get("risk_level") or (
        "HIGH" if normalized["risk_score"] >= 0.7 else "MEDIUM" if normalized["risk_score"] >= 0.4 else "LOW"
    )

    if capacity <= 0 and current_population > 0:
        normalized["capacity"] = max(1000.0, current_population * 1.5)
        normalized["available_capacity"] = max(0.0, normalized["capacity"] - current_population)

    return normalized


def _suitability_score(zone: Dict[str, Any], weights: Optional[Dict[str, float]] = None) -> float:
    weights = weights or DEFAULT_WEIGHTS
    risk_score = 1.0 - min(max(zone["risk_score"], 0.0), 1.0)
    distance_score = 1.0 - min(zone["distance_km"] / 200.0, 1.0)
    road_score = clamp(zone["road_accessibility"], 0.0, 1.0)
    medical_score = clamp(zone["medical_facilities"], 0.0, 1.0)
    food_water_score = clamp(zone["food_water"], 0.0, 1.0)
    infrastructure_score = clamp(zone["infrastructure_score"], 0.0, 1.0)
    travel_score = 1.0 - min(zone["travel_time_minutes"] / 300.0, 1.0)
    capacity_score = 1.0 if zone["capacity"] <= 0 else min(zone["available_capacity"] / zone["capacity"], 1.0)

    overall = (
        risk_score * weights.get("risk_score", 0.25)
        + distance_score * weights.get("distance", 0.20)
        + road_score * weights.get("road_accessibility", 0.15)
        + medical_score * weights.get("medical_facilities", 0.10)
        + food_water_score * weights.get("food_water", 0.10)
        + infrastructure_score * weights.get("infrastructure", 0.10)
        + travel_score * weights.get("travel_time", 0.05)
        + capacity_score * weights.get("capacity", 0.05)
    )
    return max(0.0, min(1.0, overall))


def rank_safe_zones(safe_zones: List[Dict[str, Any]], weights: Optional[Dict[str, float]] = None) -> List[Dict[str, Any]]:
    ranked = []
    for zone in safe_zones:
        normalized_zone = _normalize_zone(zone)
        suitability = _suitability_score(normalized_zone, weights)
        normalized_zone["overall_suitability_score"] = round(suitability * 100, 2)
        ranked.append(normalized_zone)
    ranked.sort(key=lambda z: z["overall_suitability_score"], reverse=True)
    return ranked


def allocate_population(red_zone_population: float, safe_zones: List[Dict[str, Any]], weights: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
    remaining_population = max(0.0, float(red_zone_population))
    ranked_safe_zones = rank_safe_zones(safe_zones, weights)
    total_available_capacity = sum(max(0.0, zone["available_capacity"]) for zone in ranked_safe_zones)
    allocations = []

    if total_available_capacity <= 0:
        return {
            "total_affected_population": round(remaining_population, 2),
            "total_available_capacity": round(total_available_capacity, 2),
            "total_allocated": 0.0,
            "remaining_population": round(remaining_population, 2),
            "insufficient_capacity": True,
            "allocations": [],
            "warning": "Insufficient Safe Zone Capacity",
        }

    for zone in ranked_safe_zones:
        if remaining_population <= 0:
            break
        available = max(0.0, zone["available_capacity"])
        assigned = min(available, remaining_population)
        if assigned <= 0:
            continue
        allocations.append({
            "safe_zone": zone["district"],
            "name": zone["name"],
            "assigned_population": round(assigned, 2),
            "available_capacity": round(available, 2),
            "capacity_remaining_after_allocation": round(max(0.0, available - assigned), 2),
            "overall_suitability_score": zone["overall_suitability_score"],
            "risk_score": zone["risk_score"],
            "road_accessibility": zone["road_accessibility"],
            "travel_time_minutes": zone["travel_time_minutes"],
            "allocation_percentage": round((assigned / max(float(red_zone_population), 1.0)) * 100, 2),
        })
        remaining_population -= assigned

    total_allocated = sum(item["assigned_population"] for item in allocations)
    insufficient_capacity = total_allocated < float(red_zone_population)

    return {
        "total_affected_population": round(float(red_zone_population), 2),
        "total_available_capacity": round(total_available_capacity, 2),
        "total_allocated": round(total_allocated, 2),
        "remaining_population": round(max(0.0, float(red_zone_population) - total_allocated), 2),
        "insufficient_capacity": insufficient_capacity,
        "warning": "Insufficient Safe Zone Capacity" if insufficient_capacity else None,
        "allocations": allocations,
    }


def calculate_resource_requirements(population_assigned: float, safe_zone: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    assigned_population = max(0.0, float(population_assigned))
    safe_zone_name = (safe_zone or {}).get("district") or (safe_zone or {}).get("name") or "Safe Zone"
    return {
        "safe_zone": safe_zone_name,
        "population_assigned": round(assigned_population, 2),
        "food_required_kg_per_day": round(assigned_population * RESOURCE_REQUIREMENTS["food_kg_per_person_per_day"], 2),
        "water_required_liters_per_day": round(assigned_population * RESOURCE_REQUIREMENTS["water_liters_per_person_per_day"], 2),
        "medical_capacity_required": round(assigned_population * RESOURCE_REQUIREMENTS["medical_capacity_per_person"], 2),
        "shelter_required_spaces": round(assigned_population * RESOURCE_REQUIREMENTS["shelter_space_per_person"], 2),
        "toilets_required": round(assigned_population * RESOURCE_REQUIREMENTS["toilets_per_person"], 2),
        "electricity_required_kwh_per_day": round(assigned_population * RESOURCE_REQUIREMENTS["electricity_kwh_per_person_per_day"], 2),
        "emergency_personnel_required": round((assigned_population / 1000.0) * RESOURCE_REQUIREMENTS["emergency_personnel_per_1000"], 2),
    }


def build_evacuation_routes(red_zone_population: float, safe_zone_allocations: List[Dict[str, Any]], red_zone_name: str) -> List[Dict[str, Any]]:
    routes = []
    for index, allocation in enumerate(safe_zone_allocations, start=1):
        zone_name = allocation["safe_zone"]
        base_distance = 25 + (index * 12)
        base_time = 40 + (index * 15)
        route_risk = round(min(0.95, 0.35 + (index * 0.12)), 2)
        primary = {
            "red_zone": red_zone_name,
            "safe_zone": zone_name,
            "route_type": "Primary",
            "distance_km": round(base_distance, 2),
            "estimated_travel_time_minutes": round(base_time, 2),
            "route_risk_score": route_risk,
            "road_condition": "Good" if route_risk < 0.5 else "Moderate",
            "people_assigned": round(allocation["assigned_population"], 2),
        }
        alternative = {
            "red_zone": red_zone_name,
            "safe_zone": zone_name,
            "route_type": "Alternative",
            "distance_km": round(base_distance * 1.15, 2),
            "estimated_travel_time_minutes": round(base_time * 1.12, 2),
            "route_risk_score": round(min(0.98, route_risk + 0.12), 2),
            "road_condition": "Fair" if route_risk < 0.75 else "High Risk",
            "people_assigned": round(allocation["assigned_population"], 2),
        }
        routes.extend([primary, alternative])
    return routes
