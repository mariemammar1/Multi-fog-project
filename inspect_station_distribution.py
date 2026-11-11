
from pathlib import Path
import pandas as pd

BASE = (
    Path("UrbanEVDataset")
    / "20220901-20230228_zone-cleaned-aggregated"
)

stations = pd.read_csv(BASE / "station_information.csv")
partition = pd.read_csv("territory_partition.csv")

stations_per_zone = (
    stations.groupby("TAZID")
    .size()
    .rename("station_count")
    .reset_index()
)

# Only the 264 zones assigned to the three Fog nodes
main_zones = partition[
    partition["fog_id"].isin(["fog-a", "fog-b", "fog-c"])
]

print("========== STATION DISTRIBUTION ==========")

print(
    main_zones["station_count"].describe(
        percentiles=[0.25, 0.50, 0.75, 0.90, 0.95]
    ).to_string()
)

print("\n========== 15 DENSEST ZONES ==========")

print(
    main_zones.sort_values(
        "station_count", ascending=False
    )[["TAZID", "station_count", "fog_id"]]
    .head(15)
    .to_string(index=False)
)

print("\n========== 15 LEAST DENSE ZONES ==========")

print(
    main_zones.sort_values(
        "station_count"
    )[["TAZID", "station_count", "fog_id"]]
    .head(15)
    .to_string(index=False)
)

