# -*- coding: utf-8 -*-
import pandas as pd

base = "UrbanEVDataset/20220901-20230228_zone-cleaned-aggregated"

# Load geographical metadata
zones = pd.read_csv(f"{base}/zone-information.csv")
stations = pd.read_csv(f"{base}/station_information.csv")

# Read only the CSV header (not the complete dataset)
volume = pd.read_csv(
    f"{base}/charge_5min/volume.csv",
    nrows=0
)

temporal_ids = set(volume.columns[1:].astype(str))
metadata_ids = set(zones["TAZID"].astype(str))
station_ids = set(stations["TAZID"].astype(str))

print("\n========== ZONE MAPPING ==========")
print("Temporal zones:", len(temporal_ids))
print("Metadata zones:", len(metadata_ids))
print("Zones with metadata:", len(temporal_ids & metadata_ids))
print("Zones without metadata:", sorted(temporal_ids - metadata_ids))
print("Metadata zones without temporal data:", sorted(metadata_ids - temporal_ids))

print("\n========== STATION MAPPING ==========")
print("Total stations:", len(stations))
print("Zones containing stations:", len(station_ids))
print("Stations without temporal zone:", len(station_ids - temporal_ids))

print("\n========== GEOGRAPHICAL INFORMATION ==========")
print("Longitude range:", zones["longitude"].min(), "-", zones["longitude"].max())
print("Latitude range:", zones["latitude"].min(), "-", zones["latitude"].max())

print("\n========== STATIONS PER ZONE ==========")
counts = stations.groupby("TAZID")["station_id"].count()
print(counts.describe())

print("\nTop 10 zones by station count:")
print(counts.sort_values(ascending=False).head(10))

print("\n========== DUPLICATES ==========")
print("Duplicate zone IDs:", zones["TAZID"].duplicated().sum())
print("Duplicate station IDs:", stations["station_id"].duplicated().sum())