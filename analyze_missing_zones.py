

import numpy as np
import pandas as pd
from pathlib import Path

BASE = Path("UrbanEVDataset")
RAW = BASE / "20220901-20230228_station-raw"

stations = pd.read_csv(RAW / "station_information.csv")
partition = pd.read_csv("territory_partition_optimized.csv")

# Identifier les 56 zones absentes de la partition.
missing = (
    stations[~stations["TAZID"].isin(partition["TAZID"])]
    .groupby("TAZID")
    .agg(
        longitude=("longitude", "mean"),
        latitude=("latitude", "mean"),
        station_count=("station_id", "nunique"),
    )
    .reset_index()
)

def haversine(lon1, lat1, lon2, lat2):
    """Distance géographique en kilomètres."""
    radius = 6371

    lon1, lat1, lon2, lat2 = map(
        np.radians, [lon1, lat1, lon2, lat2]
    )

    dlon = lon2 - lon1
    dlat = lat2 - lat1

    a = (
        np.sin(dlat / 2) ** 2
        + np.cos(lat1)
        * np.cos(lat2)
        * np.sin(dlon / 2) ** 2
    )

    return 2 * radius * np.arcsin(np.sqrt(a))


results = []

for _, zone in missing.iterrows():
    distances = {}

    for fog_id in ["fog-a", "fog-b", "fog-c"]:
        fog_zones = partition[partition["fog_id"] == fog_id]

        d = haversine(
            zone["longitude"],
            zone["latitude"],
            fog_zones["longitude"].to_numpy(),
            fog_zones["latitude"].to_numpy(),
        )

        nearest_index = np.argmin(d)

        distances[fog_id] = {
            "distance_km": d[nearest_index],
            "nearest_TAZID": fog_zones.iloc[nearest_index]["TAZID"],
        }

    ordered = sorted(
        distances.items(),
        key=lambda item: item[1]["distance_km"],
    )

    results.append({
        "TAZID": int(zone["TAZID"]),
        "station_count": int(zone["station_count"]),
        "nearest_fog": ordered[0][0],
        "nearest_distance_km": round(
            ordered[0][1]["distance_km"], 2
        ),
        "nearest_existing_TAZID": int(
            ordered[0][1]["nearest_TAZID"]
        ),
        "second_fog": ordered[1][0],
        "second_distance_km": round(
            ordered[1][1]["distance_km"], 2
        ),
        "distance_margin_km": round(
            ordered[1][1]["distance_km"]
            - ordered[0][1]["distance_km"],
            2,
        ),
    })

result = pd.DataFrame(results)

print("\n--- AFFECTATION GEOGRAPHIQUE PROPOSEE ---")
print(result.to_string(index=False))

print("\n--- RESUME PAR FOG ---")
print(
    result.groupby("nearest_fog").agg(
        zones=("TAZID", "count"),
        stations=("station_count", "sum"),
        distance_moyenne_km=("nearest_distance_km", "mean"),
        distance_max_km=("nearest_distance_km", "max"),
    ).round(2).to_string()
)

print("\n--- ZONES LES PLUS ELOIGNEES ---")
print(
    result.nlargest(10, "nearest_distance_km")[
        ["TAZID", "nearest_fog", "nearest_distance_km"]
    ].to_string(index=False)
)

result.to_csv("missing_zones_assignment_candidates.csv", index=False)
print("\nFichier créé : missing_zones_assignment_candidates.csv")
