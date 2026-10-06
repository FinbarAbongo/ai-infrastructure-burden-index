from pathlib import Path

import geopandas as gpd
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
DATABASE = (
    ROOT
    / "data/raw/aqueduct"
    / "Aqueduct40_waterrisk_download_Y2023M07D05"
    / "GDB/Aq40_Y2023D07M05.gdb"
)

FACILITIES_FILE = PROCESSED / "facilities_with_counties.csv"
COUNTIES_FILE = PROCESSED / "county_indicators_with_electricity.csv"

for path in [DATABASE, FACILITIES_FILE, COUNTIES_FILE]:
    if not path.exists():
        raise FileNotFoundError(f"Required file missing: {path}")

counties = pd.read_csv(COUNTIES_FILE, dtype={"county_fips": str})
facilities = pd.read_csv(
    FACILITIES_FILE,
    dtype={"facility_id": str, "county_fips": str},
)

# Keep the same county scope as the existing comparison table.
facilities = facilities[
    facilities["county_fips"].isin(counties["county_fips"])
].copy()

if facilities.empty:
    raise ValueError("No facilities remain in the county comparison scope.")

if facilities["facility_id"].isna().any():
    raise ValueError("Missing facility IDs.")
if facilities["facility_id"].duplicated().any():
    raise ValueError("Facility IDs must be unique.")

for column in ["longitude", "latitude"]:
    facilities[column] = pd.to_numeric(
        facilities[column], errors="raise"
    )

valid_coordinates = (
    facilities["longitude"].between(-180, 180)
    & facilities["latitude"].between(-90, 90)
)
if not valid_coordinates.all():
    raise ValueError("Facilities contain missing or invalid coordinates.")

points = gpd.GeoDataFrame(
    facilities,
    geometry=gpd.points_from_xy(
        facilities["longitude"], facilities["latitude"]
    ),
    crs="EPSG:4326",
)

print("Reading baseline annual water-risk polygons...", flush=True)

fields = [
    "string_id", "bws_raw", "bws_score", "bws_cat", "bws_label"
]
water = gpd.read_file(
    DATABASE,
    layer="baseline_annual",
    engine="pyogrio",
    columns=fields,
)

if water.crs is None:
    raise ValueError("Water-risk dataset has no coordinate system.")

water = water.to_crs(points.crs)


# Preserve an audit of invalid polygons before repairing them.
needs_repair = (
    water.geometry.notna()
    & ~water.geometry.is_empty
    & ~water.geometry.is_valid
)

repair_log = pd.DataFrame(
    water.loc[needs_repair].drop(columns="geometry")
).copy()
repair_log["original_geometry_wkt"] = (
    water.loc[needs_repair].geometry.to_wkt()
)

water.loc[needs_repair, "geometry"] = (
    water.loc[needs_repair].geometry.make_valid()
)

repair_log["repaired_geometry_wkt"] = (
    water.loc[needs_repair].geometry.to_wkt()
)
repair_log["valid_after_repair"] = (
    water.loc[needs_repair].geometry.is_valid
)

PROCESSED.mkdir(parents=True, exist_ok=True)
repair_log.to_csv(
    PROCESSED / "aqueduct_geometry_repairs.csv",
    index=False,
)
print(f"Source polygons repaired: {len(repair_log)}", flush=True)

missing_geometry = water.geometry.isna()
empty_geometry = water.geometry.is_empty
invalid_geometry = (
    ~missing_geometry
    & ~empty_geometry
    & ~water.geometry.is_valid
)

geometry_problem = (
    missing_geometry | empty_geometry | invalid_geometry
)

polygon_review = water.loc[geometry_problem].copy()
polygon_review["review_reason"] = ""

polygon_review.loc[
    missing_geometry[geometry_problem], "review_reason"
] = "missing_geometry"

polygon_review.loc[
    empty_geometry[geometry_problem], "review_reason"
] = "empty_geometry"

polygon_review.loc[
    invalid_geometry[geometry_problem], "review_reason"
] = "invalid_geometry"

PROCESSED.mkdir(parents=True, exist_ok=True)

# Keep attributes and geometry text for inspection.
polygon_review["geometry_wkt"] = polygon_review.geometry.to_wkt()
pd.DataFrame(
    polygon_review.drop(columns="geometry")
).to_csv(
    PROCESSED / "aqueduct_polygon_review.csv",
    index=False,
)

print(f"Water polygons loaded: {len(water)}", flush=True)
print(
    f"Water polygons requiring review: {len(polygon_review)}",
    flush=True,
)

water = water.loc[~geometry_problem].copy()

if water.empty:
    raise ValueError("No usable water polygons remain.")

print(f"Usable water polygons: {len(water)}", flush=True)

water = water.rename(columns={"string_id": "aqueduct_polygon_id"})

print("Matching facilities to water-risk polygons...", flush=True)

joined = gpd.sjoin(
    points,
    water,
    how="left",
    predicate="intersects",
)

# Zero matches and multiple matches both require review.
match_counts = joined.groupby("facility_id")["index_right"].count()
joined["water_polygon_match_count"] = (
    joined["facility_id"].map(match_counts).astype(int)
)

for column in ["bws_score", "bws_cat"]:
    joined[column] = pd.to_numeric(joined[column], errors="coerce")

joined["review_reason"] = ""

no_match = joined["water_polygon_match_count"].eq(0)
multiple = joined["water_polygon_match_count"].gt(1)
single = joined["water_polygon_match_count"].eq(1)

usable_score = (
    joined["bws_score"].between(0, 5)
    & joined["bws_cat"].between(0, 4)
)

joined.loc[no_match, "review_reason"] = "no_water_polygon_match"
joined.loc[multiple, "review_reason"] = "multiple_water_polygon_matches"
joined.loc[single & ~usable_score, "review_reason"] = (
    "missing_or_special_water_stress_value"
)

joined["aqueduct_version"] = "4.0"
joined["aqueduct_layer"] = "baseline_annual"
joined["aqueduct_source_file"] = str(DATABASE.relative_to(ROOT))

table = pd.DataFrame(joined.drop(columns=["geometry", "index_right"]))
clean = table[table["review_reason"].eq("")].copy()
review = table[table["review_reason"].ne("")].copy()

assert clean["facility_id"].is_unique
assert clean["bws_score"].between(0, 5).all()
assert (
    len(clean) + review["facility_id"].nunique()
    == len(facilities)
)

PROCESSED.mkdir(parents=True, exist_ok=True)
clean.to_csv(PROCESSED / "facilities_with_water_stress.csv", index=False)
review.to_csv(PROCESSED / "facilities_water_stress_review.csv", index=False)

print(f"\nFacilities in comparison scope: {len(facilities)}")
print(f"Facilities with one usable water-stress match: {len(clean)}")
print(f"Facilities requiring review: {review['facility_id'].nunique()}")

if not review.empty:
    print("\nReview reasons (unique facilities):")
    print(
        review.groupby("review_reason")["facility_id"]
        .nunique()
        .to_string()
    )

print("\nClean preview:")
print(
    clean[
        [
            "facility_name", "county_fips",
            "bws_score", "bws_label"
        ]
    ].head().to_string(index=False)
)

print("\nSaved facilities_with_water_stress.csv")
print("Saved facilities_water_stress_review.csv")