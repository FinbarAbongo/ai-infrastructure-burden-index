from pathlib import Path
import pandas as pd

project = Path(__file__).resolve().parents[1]
source = project / "data" / "raw" / "est24all.xls"

# Excel row 4 is Python header index 3.
df = pd.read_excel(source, header=3, dtype=str, na_values=["."])

# Keep rows with valid geographic codes and exclude summary rows.
state = df["State FIPS Code"].str.strip()
county = df["County FIPS Code"].str.strip()

valid = (
    state.str.fullmatch(r"\d{2}", na=False)
    & county.str.fullmatch(r"\d{3}", na=False)
    & county.ne("000")
)

counties = df.loc[valid].copy()

clean = pd.DataFrame({
    "county_fips": state.loc[valid] + county.loc[valid],
    "year": 2024,
    "state": counties["Postal Code"],
    "county_name": counties["Name"],
    "poverty_count": pd.to_numeric(
        counties["Poverty Estimate, All Ages"], errors="raise"
    ),
    "poverty_rate": pd.to_numeric(
        counties["Poverty Percent, All Ages"], errors="raise"
    ),
    "median_household_income": pd.to_numeric(
        counties["Median Household Income"], errors="raise"
    ),
})

if clean.empty:
    raise ValueError("No county records found.")

if clean["county_fips"].duplicated().any():
    raise ValueError("Duplicate county FIPS codes found.")

if not clean["poverty_rate"].dropna().between(0, 100).all():
    raise ValueError("Poverty rates must be between 0 and 100.")

output_folder = project / "data" / "processed"
output_folder.mkdir(parents=True, exist_ok=True)

output = output_folder / "saipe_counties_2024.csv"
clean.to_csv(output, index=False)

print("County records:", len(clean))
print("\nMissing values:")
print(clean.isna().sum())
print("\nPreview:")
print(clean.head().to_string(index=False))
print("\nSaved to:", output)

estimate_columns = [
    "poverty_count",
    "poverty_rate",
    "median_household_income",
]

missing_rows = clean[
    clean[estimate_columns].isna().any(axis=1)
]

print("\nRecords with missing estimates:")
print(missing_rows.to_string(index=False))