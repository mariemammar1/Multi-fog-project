
from pathlib import Path

import networkx as nx
import pandas as pd

BASE = (
    Path("UrbanEVDataset")
    / "20220901-20230228_zone-cleaned-aggregated"
)

adj = pd.read_csv(BASE / "adj.csv")
partition = pd.read_csv("territory_partition.csv")

def normalize_id(value):
    return str(int(float(value)))

adj.columns = [normalize_id(c) for c in adj.columns]
zone_ids = list(adj.columns)
adj.index = zone_ids

graph = nx.Graph()
graph.add_nodes_from(zone_ids)

matrix = adj.to_numpy(dtype=int)

for i in range(len(zone_ids)):
    for j in range(i + 1, len(zone_ids)):
        if matrix[i, j] == 1 or matrix[j, i] == 1:
            graph.add_edge(zone_ids[i], zone_ids[j])

partition["TAZID"] = partition["TAZID"].apply(normalize_id)

partition = partition[
    partition["fog_id"].isin(["fog-a", "fog-b", "fog-c"])
].copy()

territories = {
    fog: set(group["TAZID"])
    for fog, group in partition.groupby("fog_id")
}

counts = (
    partition.set_index("TAZID")["station_count"].to_dict()
)

loads = {
    fog: sum(counts[z] for z in zones)
    for fog, zones in territories.items()
}

target = sum(loads.values()) / 3

def objective(values):
    return sum((value - target) ** 2 for value in values.values())

print("========== CURRENT LOADS ==========")
for fog, load in loads.items():
    print(f"{fog}: {load}")

print("\n========== CONNECTIVITY ==========")
for fog, zones in territories.items():
    subgraph = graph.subgraph(zones)
    components = list(nx.connected_components(subgraph))
    print(f"{fog}: {len(components)} connected component(s)")

print("\n========== POSSIBLE SINGLE-ZONE TRANSFERS ==========")

current_objective = objective(loads)
candidates = []

for source in territories:
    for zone in territories[source]:

        # Source must remain connected after removing this zone
        remaining = territories[source] - {zone}

        if not remaining:
            continue

        if not nx.is_connected(graph.subgraph(remaining)):
            continue

        # Destination must be adjacent to the transferred zone
        neighbors = set(graph.neighbors(zone))

        for destination in territories:
            if destination == source:
                continue

            if not (neighbors & territories[destination]):
                continue

            station_count = counts[zone]

            new_loads = loads.copy()
            new_loads[source] -= station_count
            new_loads[destination] += station_count

            improvement = (
                current_objective - objective(new_loads)
            )

            if improvement > 0:
                candidates.append({
                    "zone": zone,
                    "stations": station_count,
                    "from": source,
                    "to": destination,
                    "new_source_load": new_loads[source],
                    "new_destination_load": new_loads[destination],
                    "improvement": improvement
                })

candidates.sort(
    key=lambda item: item["improvement"],
    reverse=True
)

print("Number of improving transfers:", len(candidates))

for candidate in candidates[:15]:
    print(candidate)
