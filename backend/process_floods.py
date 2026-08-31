import pandas as pd
from pathlib import Path

INPUT_FILE = Path("data/raw/floods/India_Flood_Inventory_v3.csv")
OUTPUT_DIR = Path("data/processed/floods")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

print("Loading flood dataset...")

df = pd.read_csv(INPUT_FILE)

# -----------------------------------
# Select Assam
# -----------------------------------

assam = df[
    df["State"]
    .astype(str)
    .str.strip()
    .str.lower()
    == "assam"
].copy()

print(f"Total Assam records: {len(assam)}")

# -----------------------------------
# Keep useful columns
# -----------------------------------

columns = [
    "Start Date",
    "End Date",
    "Districts",
    "Human fatality",
    "Human injured",
    "Human Displaced",
]

assam = assam[columns].copy()

# -----------------------------------
# Clean district field
# -----------------------------------

assam["Districts"] = (
    assam["Districts"]
    .astype(str)
    .str.replace("NaN", "", regex=False)
    .str.strip()
)

# Remove records without districts
assam = assam[assam["Districts"] != ""]

print(f"Records with district information: {len(assam)}")

# -----------------------------------
# Split multi-district events
# -----------------------------------

assam["Districts"] = assam["Districts"].str.split(",")

exploded = assam.explode("Districts")

exploded["Districts"] = (
    exploded["Districts"]
    .astype(str)
    .str.strip()
)

# Remove empty district names
exploded = exploded[
    exploded["Districts"] != ""
]

# -----------------------------------
# Convert impact fields to numbers
# -----------------------------------

for column in [
    "Human fatality",
    "Human injured",
    "Human Displaced"
]:
    exploded[column] = pd.to_numeric(
        exploded[column],
        errors="coerce"
    ).fillna(0)

# -----------------------------------
# Create district statistics
# -----------------------------------

district_stats = (
    exploded
    .groupby("Districts")
    .agg(
        flood_events=("Districts", "size"),
        fatalities=("Human fatality", "sum"),
        injured=("Human injured", "sum"),
        displaced=("Human Displaced", "sum")
    )
    .reset_index()
)

# Rename district column
district_stats = district_stats.rename(
    columns={"Districts": "district"}
)

# -----------------------------------
# Sort by flood events
# -----------------------------------

district_stats = district_stats.sort_values(
    "flood_events",
    ascending=False
)

# -----------------------------------
# Save
# -----------------------------------

output_file = (
    OUTPUT_DIR /
    "assam_flood_district_stats.csv"
)

district_stats.to_csv(
    output_file,
    index=False
)

print()
print("======================================")
print("ASSAM FLOOD PROCESSING COMPLETE")
print("======================================")

print(f"Unique districts found: {len(district_stats)}")

print()
print("Top 15 districts by historical flood events:")
print(
    district_stats
    .head(15)
    .to_string(index=False)
)

print()
print(f"Saved to: {output_file}")