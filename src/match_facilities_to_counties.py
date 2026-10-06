from pathlib import Path
import pandas as pd
import geopandas as gpd

project = Path(__file__).resolve().parents[1]
processed = project / "data" / "processed"

boundary_file = (
    project / "data" / "raw" / "cb_2024_us_county_500k.zip"
)
facility_file = processed / "facilities_clean.csv"

for file in [boundary_file, facility_file]:
    if not file.exists():
        raise FileNotFoundError(f"Required file missing: {file}")

print("Reading county boundaries...", flush=True)
counties = gpd.read_file(f"zip://{boundary_file}")

if counties.crs is None:
    raise ValueError("County boundaries have no coordinate system.")

counties = counties[["GEOID", "NAME", "geometry"]].rename(
    columns={
        "GEOID": "county_fips",
        "NAME": "matched_county_name",
    }
)
counties["county_fips"] = (
    counties["county_fips"].astype("string").str.zfill(5)
)

if not counties["county_fips"].is_unique:
    raise ValueError("Duplicate county FIPS codes in boundaries.")

print("Reading facilities...", flush=True)
facilities = pd.read_csv(
    facility_file,
    dtype={"facility_id": str},
).reset_index(drop=True)

if facilities.empty:
    raise ValueError("The clean facility file contains no records.")

if (
    facilities["facility_id"].isna().any()
    or not facilities["facility_id"].is_unique
):
    raise ValueError("Facility IDs must be present and unique.")

for column in ["latitude", "longitude"]:
    facilities[column] = pd.to_numeric(
        facilities[column], errors="raise"
    )

if not (
    facilities["latitude"].between(-90, 90).all()
    and facilities["longitude"].between(-180, 180).all()
):
    raise ValueError("Missing or invalid coordinates.")

# Longitude comes first; latitude comes second.
points = gpd.GeoDataFrame(
    facilities,
    geometry=gpd.points_from_xy(
        facilities["longitude"],
        facilities["latitude"],
    ),
    crs="EPSG:4326",
)

counties = counties.to_crs(points.crs)

print("Matching facilities to counties...", flush=True)
joined = gpd.sjoin(
    points,
    counties,
    how="left",
    predicate="intersects",
)

match_counts = joined.groupby("facility_id")["county_fips"].count()
joined["county_match_count"] = (
    joined["facility_id"].map(match_counts)
)

matched = joined.loc[joined["county_match_count"].eq(1)].copy()
review = joined.loc[joined["county_match_count"].ne(1)].copy()

review["county_review_reason"] = review["county_match_count"].map(
    lambda count: (
        "no_county_match" if count == 0
        else "multiple_county_matches"
    )
)

matched = pd.DataFrame(
    matched.drop(columns=["geometry", "index_right"])
)
review = pd.DataFrame(
    review.drop(columns=["geometry", "index_right"])
)

assert matched["facility_id"].is_unique
assert matched["county_fips"].str.fullmatch(r"\d{5}").all()
assert (
    matched["facility_id"].nunique()
    + review["facility_id"].nunique()
    == len(facilities)
)

matched.to_csv(
    processed / "facilities_with_counties.csv", index=False
)
review.to_csv(
    processed / "facilities_county_review.csv", index=False
)

print("\nInput facilities:", len(facilities))
print("Matched to exactly one county:", len(matched))
print("Facilities needing review:", review["facility_id"].nunique())
print("No county match:", int(match_counts.eq(0).sum()))
print("Multiple county matches:", int(match_counts.gt(1).sum()))

print("\nMatched preview:")
print(
    matched[
        ["facility_name", "county_fips", "matched_county_name"]
    ].head().to_string(index=False)
)

print("\nOutput files saved in:", processed)