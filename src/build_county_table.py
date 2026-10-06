from pathlib import Path
import pandas as pd

project = Path(__file__).resolve().parents[1]
processed = project / "data" / "processed"

saipe = pd.read_csv(
    processed / "saipe_counties_2024.csv",
    dtype={"county_fips": str},
).rename(columns={"year": "saipe_year"})

facilities = pd.read_csv(
    processed / "facilities_with_counties.csv",
    dtype={"county_fips": str, "facility_id": str},
)

if not saipe["county_fips"].is_unique:
    raise ValueError("Duplicate counties in SAIPE.")

if not facilities["facility_id"].is_unique:
    raise ValueError("Duplicate facility IDs.")

# Check that every matched county exists in our SAIPE table.
# Preserve records outside the SAIPE geographic coverage.
outside_scope = facilities.loc[
    ~facilities["county_fips"].isin(saipe["county_fips"])
].copy()

# Only the identified Puerto Rico mismatch is expected.
unexpected = outside_scope.loc[
    ~outside_scope["county_fips"].str.startswith("72", na=False)
]

if not unexpected.empty:
    raise ValueError(
        "Unexpected county mismatch. Inspect county FIPS codes."
    )

outside_scope.to_csv(
    processed / "facilities_outside_saipe_scope.csv",
    index=False,
)

print("Facility records before scope filter:", len(facilities))
print("Puerto Rico records saved separately:", len(outside_scope))

facilities = facilities.loc[
    facilities["county_fips"].isin(saipe["county_fips"])
].copy()

counts = (
    facilities.groupby("county_fips")["facility_id"]
    .nunique()
    .rename("listed_facility_count")
    .reset_index()
)

combined = saipe.merge(
    counts,
    on="county_fips",
    how="left",
    validate="one_to_one",
)

combined["listed_facility_count"] = (
    combined["listed_facility_count"].fillna(0).astype(int)
)

# Preserve the facility snapshot reference separately from SAIPE year.
sources = facilities["source_file"].dropna().unique()
if len(sources) != 1:
    raise ValueError("Expected one facility source snapshot.")

combined["facility_source_file"] = sources[0]

assert len(combined) == len(saipe)
assert combined["listed_facility_count"].sum() == len(facilities)

output = processed / "county_indicators.csv"
combined.to_csv(output, index=False)

print("County rows:", len(combined))
print("Matched facility records:", combined["listed_facility_count"].sum())
print(
    "Counties with listed facilities:",
    combined["listed_facility_count"].gt(0).sum(),
)
print("\nTop 10 counties by listed record count:")
print(
    combined.nlargest(10, "listed_facility_count")[
        ["county_fips", "county_name", "state", "listed_facility_count"]
    ].to_string(index=False)
)
print("\nSaved to:", output)