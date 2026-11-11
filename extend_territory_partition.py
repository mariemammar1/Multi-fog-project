
import numpy as np
import pandas as pd
from pathlib import Path

BASE = Path("UrbanEVDataset")
RAW = BASE / "20220901-20230228_station-raw"

partition = pd.read_csv("territory_partition_optimized.csv")
stations = pd.read_csv(RAW / "station_information.csv")

def haversine(lon1, lat1, lon2, lat2):
    radius = 6371.0

    lon1, lat1, lon2, lat2 = map(
        np.radians, [lon1, lat1, lon2, lat2]
    )

    dlon = lon2 - lon1
    dlat = lat2 - lat1

    a = (
        np.sin(dlat / 2) ** 2
        + np.cos(lat1) * np.cos(lat2)
        * np.sin(dlon / 2) ** 2
    )

    return 2 * radius * np.arcsin(np.sqrt(a))


# Préparer les zones déjà partitionnées.
original = partition.copy()

original["assignment_method"] = "graph_partition"
original["adjacency_known"] = True
original["nearest_distance_km"] = np.nan
original["second_fog"] = None
original["second_distance_km"] = np.nan
original["distance_margin_km"] = np.nan
original["review_required"] = False

# Identifier les zones absentes.
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

additional = []

for _, zone in missing.iterrows():
    distances = {}

    for fog_id in ["fog-a", "fog-b", "fog-c"]:
        fog_zones = partition[
            partition["fog_id"] == fog_id
        ]

        d = haversine(
            zone["longitude"],
            zone["latitude"],
            fog_zones["longitude"].to_numpy(),
            fog_zones["latitude"].to_numpy(),
        )

        index = np.argmin(d)

        distances[fog_id] = {
            "distance": float(d[index]),
            "nearest_tazid": int(
                fog_zones.iloc[index]["TAZID"]
            ),
        }

    ordered = sorted(
        distances.items(),
        key=lambda item: item[1]["distance"],
    )

    nearest_fog, nearest = ordered[0]
    second_fog, second = ordered[1]

    distance = nearest["distance"]
    margin = second["distance"] - distance

    additional.append({
        "fog_id": nearest_fog,
        "TAZID": int(zone["TAZID"]),
        "station_count": int(zone["station_count"]),
        "longitude": zone["longitude"],
        "latitude": zone["latitude"],
        "assignment_method": "nearest_zone_spatial",
        "adjacency_known": False,
        "nearest_distance_km": round(distance, 2),
        "second_fog": second_fog,
        "second_distance_km": round(
            second["distance"], 2
        ),
        "distance_margin_km": round(margin, 2),
        "review_required": (
            distance > 5 or margin < 0.5
        ),
    })

extended = pd.concat(
    [original, pd.DataFrame(additional)],
    ignore_index=True,
)

extended.to_csv(
    "territory_partition_extended.csv",
    index=False,
)

print("\n--- PARTITION ETENDUE ---")
print("Nombre de zones:", len(extended))
print("Zones originales:", len(original))
print("Zones supplémentaires:", len(additional))

print("\n--- REPARTITION PAR FOG ---")
print(
    extended.groupby("fog_id").agg(
        zones=("TAZID", "count"),
        stations=("station_count", "sum"),
    ).to_string()
)

print("\n--- AFFECTATIONS A VERIFIER ---")
print(
    extended[extended["review_required"]][
        [
            "TAZID",
            "fog_id",
            "nearest_distance_km",
            "distance_margin_km",
        ]
    ].to_string(index=False)
)

print("\nFichier créé : territory_partition_extended.csv")
