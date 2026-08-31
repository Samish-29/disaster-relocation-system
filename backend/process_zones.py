import geopandas as gpd
import pandas as pd
import os
import re


# ============================================================
# FILE PATHS
# ============================================================

BOUNDARY_FILE = "data/raw/boundaries/assam_districts.geojson"

FLOOD_FILE = "data/processed/floods/assam_flood_district_stats.csv"

EARTHQUAKE_FILE = "data/processed/earthquakes/assam_earthquakes.csv"

POPULATION_FILE = (
    "data/raw/population/2011-IndiaStateDist-0000.xlsx"
)

OUTPUT_FILE = "data/processed/zones/assam_risk_zones.geojson"


# ============================================================
# HELPER: CLEAN DISTRICT NAMES
# ============================================================

def clean_district_name(name):
    """
    Normalize district names so datasets can be joined safely.
    """

    if pd.isna(name):
        return ""

    name = str(name).strip().lower()

    # Remove common punctuation
    name = re.sub(r"[^a-z0-9 ]", "", name)

    # Normalize spaces
    name = re.sub(r"\s+", " ", name)

    # Some historical/current naming differences
    aliases = {
        "kamrup metro": "kamrup metropolitan",
        "kamrup metropolitan": "kamrup metropolitan",

        "sivasagar": "sivasagar",
        "sibsagar": "sivasagar",

        "dibrugarh": "dibrugarh",
        "tinsukia": "tinsukia",

        "karbi anglong": "karbi anglong",
        "west karbi anglong": "west karbi anglong",

        "hojai": "hojai",
        "haila kandi": "hailakandi",
        "hailakandi": "hailakandi",

        "south salmara mancachar": "south salmara mancachar",
        "south salmara mankachar": "south salmara mancachar",
    }

    return aliases.get(name, name)


# ============================================================
# LOAD DISTRICT BOUNDARIES
# ============================================================

print("Loading Assam district boundaries...")

zones = gpd.read_file(BOUNDARY_FILE)

print(f"District polygons: {len(zones)}")

zones["district_key"] = zones["district"].apply(
    clean_district_name
)


# ============================================================
# LOAD FLOOD DATA
# ============================================================

print()
print("Loading flood statistics...")

floods = pd.read_csv(FLOOD_FILE)

print(f"Flood district records: {len(floods)}")

floods["district_key"] = floods["district"].apply(
    clean_district_name
)

# Rename fields to make them explicit
floods = floods.rename(
    columns={
        "flood_events": "flood_events",
        "fatalities": "fatalities",
        "injured": "injured",
        "displaced": "displaced",
    }
)

flood_columns = [
    "district_key",
    "flood_events",
    "fatalities",
    "injured",
    "displaced",
]

floods = floods[flood_columns]


# ============================================================
# LOAD EARTHQUAKE DATA
# ============================================================

print()
print("Loading earthquake data...")

earthquakes = pd.read_csv(EARTHQUAKE_FILE)

print(f"Earthquake records: {len(earthquakes)}")

# Make sure numeric columns are actually numeric
earthquakes["magnitude"] = pd.to_numeric(
    earthquakes["magnitude"],
    errors="coerce"
)

earthquakes["latitude"] = pd.to_numeric(
    earthquakes["latitude"],
    errors="coerce"
)

earthquakes["longitude"] = pd.to_numeric(
    earthquakes["longitude"],
    errors="coerce"
)

# ------------------------------------------------------------
# Assign earthquakes to district polygons
# ------------------------------------------------------------

print("Assigning earthquakes to districts...")

earthquake_points = gpd.GeoDataFrame(
    earthquakes,
    geometry=gpd.points_from_xy(
        earthquakes["longitude"],
        earthquakes["latitude"]
    ),
    crs="EPSG:4326"
)

# Ensure boundaries use same CRS
zones_for_join = zones.to_crs("EPSG:4326")

earthquake_joined = gpd.sjoin(
    earthquake_points,
    zones_for_join[["district", "district_key", "geometry"]],
    how="inner",
    predicate="within"
)

earthquake_stats = (
    earthquake_joined
    .groupby("district_key")
    .agg(
        earthquake_events=("magnitude", "count"),
        max_earthquake_magnitude=("magnitude", "max"),
        avg_earthquake_magnitude=("magnitude", "mean"),
    )
    .reset_index()
)

print(
    f"Earthquakes assigned to districts: "
    f"{len(earthquake_joined)}"
)


# ============================================================
# LOAD CENSUS POPULATION DATA
# ============================================================

print()
print("Loading Census population data...")

population = pd.read_excel(
    POPULATION_FILE
)

print(f"Population rows: {len(population)}")

# Assam = State code 18
population = population[
    population["State"] == 18
]

# We only want district-level records
population = population[
    population["Level"].astype(str).str.upper()
    == "DISTRICT"
]

# We only want the TOTAL row, not Rural + Urban
population = population[
    population["TRU"].astype(str).str.lower()
    == "total"
]

print(
    f"Assam district population records: "
    f"{len(population)}"
)

population["district_key"] = population["Name"].apply(
    clean_district_name
)

population["population"] = pd.to_numeric(
    population["TOT_P"],
    errors="coerce"
)

population = population[
    [
        "district_key",
        "Name",
        "population",
    ]
]


# ============================================================
# MERGE FLOOD DATA
# ============================================================

print()
print("Joining flood statistics...")

zones = zones.merge(
    floods,
    on="district_key",
    how="left"
)


# ============================================================
# MERGE EARTHQUAKE DATA
# ============================================================

print("Joining earthquake statistics...")

zones = zones.merge(
    earthquake_stats,
    on="district_key",
    how="left"
)


# ============================================================
# MERGE POPULATION DATA
# ============================================================

print("Joining Census population...")

zones = zones.merge(
    population[
        [
            "district_key",
            "population",
        ]
    ],
    on="district_key",
    how="left"
)


# ============================================================
# FILL MISSING VALUES
# ============================================================

numeric_columns = [
    "flood_events",
    "fatalities",
    "injured",
    "displaced",
    "earthquake_events",
    "max_earthquake_magnitude",
    "avg_earthquake_magnitude",
    "population",
]

for column in numeric_columns:

    if column in zones.columns:
        zones[column] = pd.to_numeric(
            zones[column],
            errors="coerce"
        ).fillna(0)


# ============================================================
# CALCULATE RISK SCORE
# ============================================================

print()
print("Calculating risk scores...")

# Normalize flood events
max_flood = zones["flood_events"].max()

if max_flood > 0:
    flood_score = (
        zones["flood_events"] / max_flood
    )
else:
    flood_score = 0


# Normalize earthquake activity
max_eq = zones["earthquake_events"].max()

if max_eq > 0:
    earthquake_score = (
        zones["earthquake_events"] / max_eq
    )
else:
    earthquake_score = 0


# Normalize earthquake magnitude
max_mag = zones["max_earthquake_magnitude"].max()

if max_mag > 0:
    magnitude_score = (
        zones["max_earthquake_magnitude"] / max_mag
    )
else:
    magnitude_score = 0


# ------------------------------------------------------------
# Current risk formula
#
# Flood history       = 60%
# Earthquake events   = 25%
# Earthquake magnitude= 15%
# ------------------------------------------------------------

zones["risk_score"] = (
    flood_score * 0.60
    + earthquake_score * 0.25
    + magnitude_score * 0.15
)


# ============================================================
# ASSIGN RISK LEVEL
# ============================================================

def get_risk_level(score):

    if score >= 0.70:
        return "HIGH"

    elif score >= 0.40:
        return "MEDIUM"

    else:
        return "LOW"


zones["risk_level"] = zones["risk_score"].apply(
    get_risk_level
)


# ============================================================
# REMOVE INTERNAL JOIN COLUMN
# ============================================================

zones = zones.drop(
    columns=["district_key"],
    errors="ignore"
)


# ============================================================
# SAVE GEOJSON
# ============================================================

print()
print("Saving Assam risk zones...")

os.makedirs(
    os.path.dirname(OUTPUT_FILE),
    exist_ok=True
)

zones.to_file(
    OUTPUT_FILE,
    driver="GeoJSON"
)


# ============================================================
# SUMMARY
# ============================================================

print()
print("=" * 50)
print("ASSAM RISK ZONES CREATED")
print("=" * 50)

print(
    f"District zones: {len(zones)}"
)

print()
print("Risk distribution:")

print(
    zones["risk_level"].value_counts()
)

print()
print("Population matching:")

population_matches = (
    zones["population"] > 0
).sum()

print(
    f"Districts with population data: "
    f"{population_matches}/{len(zones)}"
)

print()
print("Top districts by risk:")

display_columns = [
    "district",
    "population",
    "flood_events",
    "earthquake_events",
    "max_earthquake_magnitude",
    "risk_score",
    "risk_level",
]

print(
    zones[
        display_columns
    ]
    .sort_values(
        "risk_score",
        ascending=False
    )
    .head(10)
    .to_string(index=False)
)

print()
print(f"Saved to: {OUTPUT_FILE}")