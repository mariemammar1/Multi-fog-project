
from pathlib import Path
import pandas as pd

BASE = (
    Path("UrbanEVDataset")
    / "20220901-20230228_zone-cleaned-aggregated"
)

zones = pd.read_csv(BASE / "zone-information.csv")
stations = pd.read_csv(BASE / "station_information.csv")

# Find zones with missing or invalid coordinates
invalid = zones[
    zones["longitude"].isna()
    | zones["latitude"].isna()
    | (zones["longitude"] == 0)
    | (zones["latitude"] == 0)
]

print("Total zones:", len(zones))
print("Zones with invalid coordinates:", len(invalid))

for _, zone in invalid.iterrows():
    zone_id = zone["TAZID"]

    zone_stations = stations[
        stations["TAZID"] == zone_id
    ]

    print(f"\nZone: {zone_id}")
    print("Metadata coordinates:",
          zone["longitude"], zone["latitude"])
    print("Number of stations:", len(zone_stations))

    if not zone_stations.empty:
        print("Station-based longitude:",
              zone_stations["longitude"].mean())
        print("Station-based latitude:",
              zone_stations["latitude"].mean())
    else:
        print("WARNING: No station coordinates available!")
