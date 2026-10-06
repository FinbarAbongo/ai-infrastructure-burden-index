from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"

counties = pd.read_csv(
    PROCESSED / "county_indicators_with_electricity.csv",
    dtype={"county_fips": str},
)
facilities = pd.read_csv(
    PROCESSED / "facilities_with_water_stress.csv",
    dtype={"facility_id": str, "county_fips": str},
)

if not counties["county_fips"].is_unique:
    raise ValueError("County FIPS must be unique.")
if not facilities["facility_id"].is_unique:
    raise ValueError("Facility IDs must be unique.")
if not facilities["county_fips"].isin(counties["county_fips"]).all():
    raise ValueError("Water-stress records contain counties outside scope.")

facilities["bws_score"] = pd.to_numeric(
    facilities["bws_score"], errors="raise"
)
if not facilities["bws_score"].between(0, 5).all():
    raise ValueError("Water-stress scores must be between 0 and 5.")

summary = (
    facilities.groupby("county_fips", as_index=False)
    .agg(
        water_stress_facility_count=("facility_id", "nunique"),
        mean_facility_water_stress_score=("bws_score", "mean"),
    )
)

result = counties.merge(
    summary,
    on="county_fips",
    how="left",
    validate="one_to_one",
)

result["water_stress_facility_count"] = (
    result["water_stress_facility_count"].fillna(0).astype(int)
)

total = result["listed_facility_count"]
usable = result["water_stress_facility_count"]

if (usable > total).any():
    raise ValueError("Usable matches exceed listed facility counts.")

# Coverage is undefined for counties with no listed facilities.
result["water_stress_coverage_pct"] = (
    usable.div(total.where(total.gt(0))) * 100
)
result["water_stress_review_count"] = total - usable

result["water_stress_summary_status"] = "no_listed_facilities"
result.loc[
    total.gt(0) & usable.eq(0), "water_stress_summary_status"
] = "no_usable_water_stress"
result.loc[
    usable.gt(0) & usable.lt(total), "water_stress_summary_status"
] = "partial_coverage"
result.loc[
    total.gt(0) & usable.eq(total), "water_stress_summary_status"
] = "complete_coverage"

result["water_stress_source"] = "WRI Aqueduct 4.0 baseline_annual"

assert len(result) == len(counties)
assert usable.sum() == len(facilities)

output = PROCESSED / "county_indicators_with_water_stress.csv"
result.to_csv(output, index=False)

print(f"County rows: {len(result)}")
print(f"Facilities with usable water stress: {usable.sum()}")
print(f"Facilities requiring review: {(total - usable).sum()}")
print("\nCounty coverage:")
print(result["water_stress_summary_status"].value_counts().to_string())

print("\nPreview of counties with listed facilities:")
print(
    result.loc[
        total.gt(0),
        [
            "county_name",
            "state",
            "listed_facility_count",
            "mean_facility_water_stress_score",
            "water_stress_coverage_pct",
        ],
    ].head(10).to_string(index=False)
)

print(f"\nSaved: {output.name}")

