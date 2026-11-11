
from pathlib import Path
import pandas as pd

BASE = (
    Path("UrbanEVDataset")
    / "20220901-20230228_zone-cleaned-aggregated"
)

stations_file = BASE / "station_information.csv"
zones_file = BASE / "zone-information.csv"

stations = pd.read_csv(stations_file)
zones = pd.read_csv(zones_file)

# Normalize zone IDs to strings for reliable comparison
stations["TAZID"] = stations["TAZID"].astype(str)
zones["TAZID"] = zones["TAZID"].astype(str)

zone_id = "348"

print("========== CLEANED: STATIONS IN ZONE 348 ==========")

zone_stations = stations[stations["TAZID"] == zone_id]

print("Number of stations:", len(zone_stations))
print(zone_stations.to_string(index=False))

if not zone_stations.empty:
    print("\n========== RECALCULATED CENTROID ==========")
    print("Longitude:", zone_stations["longitude"].mean())
    print("Latitude:", zone_stations["latitude"].mean())

print("\n========== ZONE METADATA ==========")

zone_info = zones[zones["TAZID"] == zone_id]
print(zone_info.to_string(index=False))
