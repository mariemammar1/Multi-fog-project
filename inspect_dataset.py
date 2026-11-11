# -*- coding: utf-8 -*-
import pandas as pd

base = "UrbanEVDataset/20220901-20230228_zone-cleaned-aggregated"

files = [
    "charge_5min/volume.csv",
    "charge_5min/occupancy.csv",
    "charge_1hour/volume.csv",
    "charge_1hour/occupancy.csv",
    "zone-information.csv",
    "station_information.csv"
]

for name in files:
    path = f"{base}/{name}"

    print("\n" + "=" * 65)
    print("FILE:", name)

    df = pd.read_csv(path, nrows=5)

    print("Number of columns:", len(df.columns))
    print("First columns:", df.columns[:12].tolist())
    print("Sample dimensions:", df.shape)
    print("\nFirst rows:")

    print(df.iloc[:3, :min(6, len(df.columns))].to_string(index=False))
