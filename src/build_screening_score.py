from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"

df = pd.read_csv(
    PROCESSED / "county_indicators_with_water_stress.csv",
    dtype={"county_fips": str},
)

components = {
    "poverty_rate": "poverty_percentile",
    "residential_price_cents_kwh": "electricity_price_percentile",
    "mean_facility_water_stress_score": "water_stress_percentile",
}

if not df["county_fips"].is_unique:
    raise ValueError("County FIPS must be unique.")

for column in components:
    df[column] = pd.to_numeric(df[column], errors="raise")

# Score only counties with listed facilities, complete water
# coverage, and all three component values.
eligible = (
    df["listed_facility_count"].gt(0)
    & df["water_stress_summary_status"].eq("complete_coverage")
    & df[list(components)].notna().all(axis=1)
)

if eligible.sum() < 2:
    raise ValueError("Too few eligible counties to calculate percentiles.")

# Higher values receive higher percentiles.
# Equal values receive the same average rank.
for source, output in components.items():
    df[output] = float("nan")
    df.loc[eligible, output] = (
        df.loc[eligible, source].rank(method="average", pct=True)
    )

percentile_columns = list(components.values())

df["screening_score"] = float("nan")
df.loc[eligible, "screening_score"] = (
    df.loc[eligible, percentile_columns].mean(axis=1) * 100
)

df["screening_rank"] = (
    df["screening_score"]
    .rank(method="min", ascending=False)
    .astype("Int64")
)

df["screening_status"] = "not_eligible"
df.loc[eligible, "screening_status"] = "draft_scored"
df["screening_reference_counties"] = int(eligible.sum())
df["screening_method"] = "Equal-weight mean of three percentile ranks"
df["electricity_source_verified"] = False

assert df.loc[eligible, "screening_score"].between(0, 100).all()
assert df.loc[~eligible, "screening_score"].isna().all()

output = PROCESSED / "county_screening_scores.csv"
df.to_csv(output, index=False)

print(f"County rows retained: {len(df)}")
print(f"Counties scored: {eligible.sum()}")
print(f"Counties unscored: {(~eligible).sum()}")

print("\nTop 10 draft screening scores:")
print(
    df.loc[eligible]
    .sort_values("screening_score", ascending=False)[
        [
            "county_name",
            "state",
            "listed_facility_count",
            "poverty_rate",
            "residential_price_cents_kwh",
            "mean_facility_water_stress_score",
            "screening_score",
        ]
    ]
    .head(10)
    .round(2)
    .to_string(index=False)
)

print(f"\nSaved: {output.name}")
print("DRAFT: electricity source verification remains outstanding.")