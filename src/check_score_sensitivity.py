from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
folder = ROOT / "data" / "processed"

df = pd.read_csv(
    folder / "county_screening_scores.csv",
    dtype={"county_fips": str},
)
df = df[df["screening_status"].eq("draft_scored")].copy()

columns = [
    "poverty_percentile",
    "electricity_price_percentile",
    "water_stress_percentile",
]

weights = {
    "equal": [1/3, 1/3, 1/3],
    "poverty_focus": [0.50, 0.25, 0.25],
    "electricity_focus": [0.25, 0.50, 0.25],
    "water_focus": [0.25, 0.25, 0.50],
}

if df.empty or df[columns].isna().any().any():
    raise ValueError("Eligible counties must have complete percentiles.")

for name, values in weights.items():
    df[f"{name}_score"] = (
        df[columns].mul(values, axis="columns").sum(axis=1) * 100
    )
    df[f"{name}_rank"] = df[f"{name}_score"].rank(
        ascending=False, method="min"
    )

baseline_top = set(
    df.nlargest(10, "equal_score")["county_fips"]
)

print(f"Counties assessed: {len(df)}")
for name in weights:
    top = set(df.nlargest(10, f"{name}_score")["county_fips"])
    correlation = df["equal_rank"].corr(df[f"{name}_rank"])
    print(
        f"{name}: rank correlation={correlation:.3f}; "
        f"top-10 overlap={len(top & baseline_top)}/10"
    )

rank_columns = [f"{name}_rank" for name in weights]
df["rank_range"] = (
    df[rank_columns].max(axis=1) - df[rank_columns].min(axis=1)
)

print("\nLargest ranking changes across scenarios:")
print(
    df.nlargest(10, "rank_range")[
        ["county_name", "state", *rank_columns, "rank_range"]
    ].to_string(index=False)
)

df.to_csv(folder / "county_score_sensitivity.csv", index=False)
print("\nSaved: county_score_sensitivity.csv")