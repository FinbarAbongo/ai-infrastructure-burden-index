import json
from pathlib import Path
from urllib.request import Request, urlopen
from datetime import datetime, timezone

project = Path(__file__).resolve().parents[1]
raw_folder = project / "data" / "raw"
raw_folder.mkdir(parents=True, exist_ok=True)

url = "https://www.peeringdb.com/api/fac?country=US&depth=0"
request = Request(
    url,
    headers={"Accept": "application/json"},
)

with urlopen(request, timeout=60) as response:
    payload = json.load(response)

facilities = payload.get("data", [])

if not facilities:
    raise ValueError("No facilities returned. Check the API response.")

timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
output = raw_folder / f"peeringdb_us_facilities_{timestamp}.json"

with output.open("w", encoding="utf-8") as file:
    json.dump(payload, file, indent=2)

print("Retrieved at UTC:", timestamp)
print("Source:", url)
print("Facility records:", len(facilities))
print("Response metadata:", payload.get("meta", {}))
print("\nFirst facility:")
print(json.dumps(facilities[0], indent=2))
print("\nSaved to:", output)