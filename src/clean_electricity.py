from pathlib import Path
import pandas as pd

project = Path(__file__).resolve().parents[1]
processed = project / "data" / "processed"
source = (
    project / "data" / "raw"
    / "eia_residential_electricity_price_2024_by_state.csv"
)

# Explicit mapping from full state names to postal abbreviations.
state_pairs = """
Alabama|AL
Alaska|AK
Arizona|AZ
Arkansas|AR
California|CA
Colorado|CO
Connecticut|CT
Delaware|DE
District of Columbia|DC
Florida|FL
Georgia|GA
Hawaii|HI
Idaho|ID
Illinois|IL
Indiana|IN
Iowa|IA
Kansas|KS
Kentucky|KY
Louisiana|LA
Maine|ME
Maryland|MD
Massachusetts|MA
Michigan|MI
Minnesota|MN
Mississippi|MS
Missouri|MO
Montana|MT
Nebraska|NE
Nevada|NV
New Hampshire|NH
New Jersey|NJ
New Mexico|NM
New York|NY
North Carolina|NC
North Dakota|ND
Ohio|OH
Oklahoma|OK
Oregon|OR
Pennsylvania|PA
Rhode Island|RI
South Carolina|SC
South Dakota|SD
Tennessee|TN
Texas|TX
Utah|UT
Vermont|VT
Virginia|VA
Washington|WA
West Virginia|WV
Wisconsin|WI
Wyoming|WY
"""

state_map = dict(
    line.split("|") for line in state_pairs.strip().splitlines()
)

df = pd.read_csv(source)
df.columns = df.columns.str.strip()
df["State"] = df["State"].str.strip()
df["Sector"] = df["Sector"].str.strip()

# Remove the national summary, which is not a state.
df = df.loc[df["State"].ne("U.S. Total")].copy()

if not df["Sector"].eq("Residential").all():
    raise ValueError("Unexpected electricity sector.")

df["Year"] = pd.to_numeric(df["Year"], errors="raise")
if not df["Year"].eq(2024).all():
    raise ValueError("Expected only 2024 data.")

df["state"] = df["State"].map(state_map)
if df["state"].isna().any():
    raise ValueError("Unrecognized state names.")

if len(df) != 51 or set(df["state"]) != set(state_map.values()):
    raise ValueError("Expected all 50 states plus Washington, DC.")

if not df["state"].is_unique:
    raise ValueError("Duplicate state records.")

df["residential_price_cents_kwh"] = pd.to_numeric(
    df["Average retail price (cents/kWh)"],
    errors="raise",
)

if not df["residential_price_cents_kwh"].gt(0).all():
    raise ValueError("Missing or nonpositive electricity prices.")

electricity = df[
    ["state", "Year", "residential_price_cents_kwh"]
].rename(columns={"Year": "electricity_year"})

electricity["electricity_source_file"] = source.name
electricity["electricity_geographic_level"] = "state"

counties = pd.read_csv(
    processed / "county_indicators.csv",
    dtype={"county_fips": str},
)

combined = counties.merge(
    electricity,
    on="state",
    how="left",
    validate="many_to_one",
)

if len(combined) != len(counties):
    raise ValueError("County row count changed during the join.")

if combined["residential_price_cents_kwh"].isna().any():
    raise ValueError("Some counties did not receive a state price.")

processed.mkdir(parents=True, exist_ok=True)

electricity.to_csv(
    processed / "electricity_states_2024.csv", index=False
)
combined.to_csv(
    processed / "county_indicators_with_electricity.csv",
    index=False,
)

print("State electricity records:", len(electricity))
print("County rows:", len(combined))
print(
    "Counties missing electricity prices:",
    combined["residential_price_cents_kwh"].isna().sum(),
)
print("\nPreview:")
print(
    combined[
        [
            "county_name",
            "state",
            "listed_facility_count",
            "electricity_year",
            "residential_price_cents_kwh",
        ]
    ].head().to_string(index=False)
)
print("\nSaved electricity_states_2024.csv")
print("Saved county_indicators_with_electricity.csv")