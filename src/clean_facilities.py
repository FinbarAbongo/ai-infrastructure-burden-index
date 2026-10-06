import json
from pathlib import Path
import pandas as pd

project = Path(__file__).resolve().parents[1]
raw_folder = project / "data" / "raw"
output_folder = project / "data" / "processed"
output_folder.mkdir(parents=True, exist_ok=True)

# Timestamped filenames sort chronologically.
files = sorted(raw_folder.glob("peeringdb_us_facilities_*.json"))

if not files:
    raise FileNotFoundError(
        "No facility JSON found in data/raw. "
        "Run download_facilities.py first."
    )

source = files[-1]

with source.open(encoding="utf-8") as file:
    payload = json.load(file)

records = payload.get("data")

if not isinstance(records, list) or not records:
    raise ValueError("The JSON does not contain a nonempty data list.")

raw = pd.DataFrame(records)

# Missing fields remain missing rather than causing a crash.
fields = {
    "id": "facility_id",
    "name": "facility_name",
    "country": "country",
    "state": "state",
    "city": "city",
    "address1": "address",
    "address2": "address_line_2",
    "latitude": "latitude",
    "longitude": "longitude",
    "status": "status",
}

df = raw.reindex(columns=list(fields)).rename(columns=fields)

text_columns = [
    "facility_id", "facility_name", "country", "state", "city",
    "address", "address_line_2", "status",
]

for column in text_columns:
    df[column] = df[column].astype("string").str.strip()
    df[column] = df[column].replace("", pd.NA)

# Preserve original coordinate values for diagnosing problems.
df["latitude_original"] = df["latitude"]
df["longitude_original"] = df["longitude"]

for column in ["latitude", "longitude"]:
    df[column] = pd.to_numeric(df[column], errors="coerce")

# Accumulate every reason a record needs review.
reasons = [[] for _ in range(len(df))]

def flag(mask, reason):
    for index in df.index[mask.fillna(False)]:
        reasons[index].append(reason)

flag(df["facility_id"].isna(), "missing_id")
flag(
    df["facility_id"].notna()
    & df["facility_id"].duplicated(keep=False),
    "duplicate_id",
)
flag(df["facility_name"].isna(), "missing_name")
flag(df["country"].fillna("").ne("US"), "country_not_US")
flag(df["status"].fillna("").ne("ok"), "status_not_ok")

flag(
    df["latitude"].isna() | df["longitude"].isna(),
    "missing_or_nonnumeric_coordinates",
)
flag(
    df["latitude"].notna() & ~df["latitude"].between(-90, 90),
    "latitude_out_of_range",
)
flag(
    df["longitude"].notna() & ~df["longitude"].between(-180, 180),
    "longitude_out_of_range",
)
flag(
    df["latitude"].eq(0) & df["longitude"].eq(0),
    "zero_coordinate_pair",
)

df["review_reason"] = ["; ".join(items) for items in reasons]
df["source_file"] = source.name

clean = df.loc[df["review_reason"].eq("")].copy()
review = df.loc[df["review_reason"].ne("")].copy()

assert clean["facility_id"].is_unique
assert clean["facility_id"].notna().all()
assert clean["latitude"].between(-90, 90).all()
assert clean["longitude"].between(-180, 180).all()
assert len(clean) + len(review) == len(df)

clean.to_csv(output_folder / "facilities_clean.csv", index=False)
review.to_csv(output_folder / "facilities_review.csv", index=False)

print("Source file:", source.name)
print("Downloaded records:", len(df))
print("Retained records:", len(clean))
print("Flagged records:", len(review))

print("\nReview reasons:")
if review.empty:
    print("None")
else:
    print(review["review_reason"].value_counts().to_string())

print("\nClean preview:")
print(
    clean[
        ["facility_id", "facility_name", "state", "latitude", "longitude"]
    ].head().to_string(index=False)
)

print("\nSaved:")
print(output_folder / "facilities_clean.csv")
print(output_folder / "facilities_review.csv")