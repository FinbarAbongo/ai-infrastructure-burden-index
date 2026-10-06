from pathlib import Path
import pandas as pd

project_folder = Path(__file__).resolve().parents[1]
raw_folder = project_folder / "data" / "raw"

files = [
    file for file in raw_folder.iterdir()
    if file.suffix.lower() in {".xls", ".xlsx"}
    and not file.name.startswith("~$")
]

if len(files) != 1:
    raise ValueError(
        f"Expected one Excel dataset in data/raw. Found: "
        f"{[file.name for file in files]}"
    )

workbook = pd.ExcelFile(files[0])

print("File:", files[0].name)
print("Sheets:", workbook.sheet_names)

preview = pd.read_excel(
    workbook,
    sheet_name=0,
    header=None,
    nrows=15,
    dtype=str,
)

print("\nFirst 15 rows:")
print(preview.to_string(index=False, header=False))