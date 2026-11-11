
from pathlib import Path

import pandas as pd
import networkx as nx

BASE = (
    Path("UrbanEVDataset")
    / "20220901-20230228_zone-cleaned-aggregated"
)

# 1. Load data
distance = pd.read_csv(BASE / "distance.csv")
adjacency = pd.read_csv(BASE / "adj.csv")
partition = pd.read_csv("territory_partition.csv")


def normalize_id(value):
    return str(int(float(value)))


# 2. Restore zone IDs as row indexes
distance.columns = [normalize_id(c) for c in distance.columns]
distance.index = distance.columns

adjacency.columns = [normalize_id(c) for c in adjacency.columns]
adjacency.index = adjacency.columns

partition["TAZID"] = partition["TAZID"].apply(normalize_id)

# 3. Build the geographic graph
zone_ids = list(adjacency.columns)
matrix = adjacency.to_numpy(dtype=int)

graph = nx.Graph()
graph.add_nodes_from(zone_ids)

for i in range(len(zone_ids)):
    for j in range(i + 1, len(zone_ids)):
        if matrix[i, j] == 1 or matrix[j, i] == 1:
            graph.add_edge(zone_ids[i], zone_ids[j])

# 4. Calculate territory metrics
territories = {
    fog: group.set_index("TAZID")["station_count"].to_dict()
    for fog, group in partition.groupby("fog_id")
    if fog in ["fog-a", "fog-b", "fog-c"]
}

loads = {
    fog: sum(zones.values())
    for fog, zones in territories.items()
}

target = sum(loads.values()) / 3

balance_score = sum(
    ((load - target) / target) ** 2
    for load in loads.values()
)

print("========== BALANCE ==========")
print(f"Target: {target:.2f}")

for fog, load in loads.items():
    print(f"{fog}: {load} stations")

print(f"Balance score: {balance_score:.6f}")

print("\n========== COMPACTNESS ==========")

compactness_values = []

for fog, zones in territories.items():
    zone_list = list(zones.keys())

    numerator = 0.0
    denominator = 0.0

    for i in range(len(zone_list)):
        for j in range(i + 1, len(zone_list)):
            a = zone_list[i]
            b = zone_list[j]

            weight = zones[a] * zones[b]
            d = float(distance.loc[a, b])

            numerator += weight * d
            denominator += weight

    compactness = (
        numerator / denominator
        if denominator > 0
        else 0.0
    )

    compactness_values.append(compactness)

    print(f"{fog}: {compactness:.2f} meters")

print(
    "Average compactness:",
    f"{sum(compactness_values) / len(compactness_values):.2f} meters"
)

print("\n========== CONNECTIVITY ==========")

for fog, zones in territories.items():
    components = nx.number_connected_components(
        graph.subgraph(zones.keys())
    )

    print(f"{fog}: {components} connected component(s)")

print("\nEvaluation completed.")
