from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import geopandas as gpd
import os

from backend.population_reallocation_api import router as reallocation_router
from backend.realtime.router import router as realtime_router


app = FastAPI(
    title="Disaster Relocation System",
    description="Assam disaster risk API",
    version="1.0.1"
)

# Allow a future frontend to communicate with the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(reallocation_router)
app.include_router(realtime_router)


ZONES_FILE = "data/processed/zones/assam_risk_zones.geojson"


def load_zones():
    if not os.path.exists(ZONES_FILE):
        raise FileNotFoundError(
            f"Zone dataset not found: {ZONES_FILE}"
        )

    return gpd.read_file(ZONES_FILE)


@app.get("/")
def root():
    return {
        "message": "Disaster Relocation System API",
        "status": "running"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy"
    }


@app.get("/zones")
def get_zones():
    zones = load_zones()

    # Convert GeoDataFrame to GeoJSON
    return zones.to_json()


@app.get("/zones/{district}")
def get_zone(district: str):
    zones = load_zones()

    matches = zones[
        zones["district"].str.lower() == district.lower()
    ]

    if matches.empty:
        raise HTTPException(
            status_code=404,
            detail=f"District '{district}' not found"
        )

    return matches.to_json()


@app.get("/stats")
def get_stats():
    zones = load_zones()

    return {
        "districts": len(zones),
        "high_risk": int(
            (zones["risk_level"] == "HIGH").sum()
        ),
        "medium_risk": int(
            (zones["risk_level"] == "MEDIUM").sum()
        ),
        "low_risk": int(
            (zones["risk_level"] == "LOW").sum()
        )
    }
