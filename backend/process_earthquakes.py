import pandas as pd
import os
import re

INPUT_FILE = "data/raw/earthquakes/ncs_earthquakes.xlsx"
OUTPUT_FILE = "data/processed/earthquakes/assam_earthquakes.csv"

print("Loading earthquake dataset...")

# NCS Excel file has the actual headers on row 2
df = pd.read_excel(INPUT_FILE, header=1)

print(f"Total earthquake records: {len(df)}")

# Clean column names
df.columns = df.columns.astype(str).str.strip()

print("Columns found:")
print(df.columns.tolist())

# Convert coordinates to numbers
df["Lat"] = pd.to_numeric(df["Lat"], errors="coerce")
df["Long"] = pd.to_numeric(df["Long"], errors="coerce")

# Convert depth
df["Depth"] = pd.to_numeric(df["Depth"], errors="coerce")

# Extract numeric magnitude
df["Magnitude"] = (
    df["Magnitude"]
    .astype(str)
    .str.extract(r"(\d+(?:\.\d+)?)")[0]
)

df["Magnitude"] = pd.to_numeric(df["Magnitude"], errors="coerce")

# Assam approximate bounding box
ASSAM_MIN_LAT = 24.0
ASSAM_MAX_LAT = 28.5
ASSAM_MIN_LON = 89.5
ASSAM_MAX_LON = 96.0

# Select earthquakes geographically inside/near Assam
assam = df[
    (df["Lat"] >= ASSAM_MIN_LAT)
    & (df["Lat"] <= ASSAM_MAX_LAT)
    & (df["Long"] >= ASSAM_MIN_LON)
    & (df["Long"] <= ASSAM_MAX_LON)
].copy()

print(f"Earthquakes inside Assam region: {len(assam)}")

# Rename columns for our application
assam = assam.rename(
    columns={
        "Origin Time": "date",
        "Lat": "latitude",
        "Long": "longitude",
        "Depth": "depth_km",
        "Magnitude": "magnitude",
        "Location": "location",
    }
)

# Keep only what our application needs
assam = assam[
    [
        "date",
        "latitude",
        "longitude",
        "depth_km",
        "magnitude",
        "location",
    ]
]

# Add an ID
assam.insert(0, "id", range(1, len(assam) + 1))

# Make sure output directory exists
os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)

# Save
assam.to_csv(OUTPUT_FILE, index=False)

print()
print("========================================")
print("EARTHQUAKE PROCESSING COMPLETE")
print("========================================")
print(f"Records saved: {len(assam)}")
print()
print("First 10 records:")
print(assam.head(10).to_string(index=False))
print()
print(f"Saved to: {OUTPUT_FILE}")