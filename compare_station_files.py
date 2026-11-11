
import pandas as pd
from pathlib import Path

RAW = Path("UrbanEVDataset/20220901-20230228_station-raw")
CLEAN = Path("UrbanEVDataset/20220901-20230228_zone-cleaned-aggregated")

files = {
    "RAW": RAW / "station_information.csv",
    "CLEANED": CLEAN / "station_information.csv",
}

for name, path in files.items():
    print("\n" + "=" * 65)
    print(name, "-", path)

    if not path.exists():
        print("FILE NOT FOUND")
        continue

    df = pd.read_csv(path)

    print("Shape:", df.shape)
    print("Columns:", df.columns.tolist())
    print("First 5 rows:")
    print(df.head().to_string(index=False))

    if "TAZID" in df.columns:
        print("Unique TAZIDs:", df["TAZID"].nunique())
        print("Missing TAZIDs:", df["TAZID"].isna().sum())
        print("Stations per TAZID:")
        print(df.groupby("TAZID").size().describe())
