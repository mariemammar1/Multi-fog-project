
from pathlib import Path
import math

import networkx as nx
import pandas as pd


# --------------------------------------------------
# 1. Dataset paths
# --------------------------------------------------

BASE = (
    Path("UrbanEVDataset")
    / "20220901-20230228_zone-cleaned-aggregated"
)

adj_file = BASE / "adj.csv"
stations_file = BASE / "station_information.csv"
zones_file = BASE / "zone-information.csv"


# --------------------------------------------------
# 2. Helper functions
# --------------------------------------------------

def normalize_id(value):
    """Convert IDs such as 348.0 and '348' to '348'."""
    return str(int(float(value)))


def haversine(lon1, lat1, lon2, lat2):
    """Geographical straight-line distance in meters."""
    radius = 6_371_000

    lon1, lat1, lon2, lat2 = map(
        math.radians, [lon1, lat1, lon2, lat2]
    )

    dlon = lon2 - lon1
    dlat = lat2 - lat1

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1)
        * math.cos(lat2)
        * math.sin(dlon / 2) ** 2
    )

    return 2 * radius * math.asin(math.sqrt(a))


# --------------------------------------------------
# 3. Load data
# --------------------------------------------------

stations = pd.read_csv(stations_file)
zones = pd.read_csv(zones_file)
adj = pd.read_csv(adj_file)

stations["TAZID"] = stations["TAZID"].apply(normalize_id)
zones["TAZID"] = zones["TAZID"].apply(normalize_id)

adj.columns = [normalize_id(c) for c in adj.columns]

zone_ids = list(adj.columns)

if len(zone_ids) != len(adj):
    raise ValueError("Adjacency matrix is not square.")

if len(set(zone_ids)) != len(zone_ids):
    raise ValueError("Duplicate zone IDs in adjacency matrix.")

adj.index = zone_ids

if set(zone_ids) != set(zones["TAZID"]):
    raise ValueError("Zone IDs do not match zone metadata.")

# Number of stations per zone
station_counts = (
    stations.groupby("TAZID")
    .size()
    .to_dict()
)

# Geographic coordinates
coordinates = {}

for _, zone in zones.iterrows():
    zone_id = zone["TAZID"]

    lon = zone["longitude"]
    lat = zone["latitude"]

    # Correct zone 348 using its station coordinates
    if (
        pd.isna(lon)
        or pd.isna(lat)
        or lon == 0
        or lat == 0
    ):
        zone_stations = stations[
            stations["TAZID"] == zone_id
        ]

        if zone_stations.empty:
            raise ValueError(
                f"No valid coordinates for zone {zone_id}"
            )

        lon = zone_stations["longitude"].mean()
        lat = zone_stations["latitude"].mean()

        print(f"Corrected coordinates for zone {zone_id}")

    coordinates[zone_id] = (float(lon), float(lat))


# --------------------------------------------------
# 4. Build the real adjacency graph
# --------------------------------------------------

graph = nx.Graph()
graph.add_nodes_from(zone_ids)

matrix = adj.to_numpy(dtype=int)

for i in range(len(zone_ids)):
    for j in range(i + 1, len(zone_ids)):

        # OR preserves one-way adjacency relationships
        if matrix[i, j] == 1 or matrix[j, i] == 1:
            graph.add_edge(zone_ids[i], zone_ids[j])


components = sorted(
    nx.connected_components(graph),
    key=len,
    reverse=True
)

main_component = set(components[0])

print("\n========== GRAPH ==========")
print("Zones:", graph.number_of_nodes())
print("Edges:", graph.number_of_edges())
print("Connected components:", len(components))
print("Main component zones:", len(main_component))

main_stations = sum(
    station_counts.get(z, 0)
    for z in main_component
)

print("Stations in main component:", main_stations)

if len(main_component) != 264 or main_stations != 1320:
    raise ValueError(
        "Unexpected dataset structure. Check the input files."
    )


# --------------------------------------------------
# 5. Choose three geographically distant seeds
# --------------------------------------------------

# First seed: zone closest to the geographical center
center_lon = sum(
    coordinates[z][0] for z in main_component
) / len(main_component)

center_lat = sum(
    coordinates[z][1] for z in main_component
) / len(main_component)


def distance_to_seed(zone_a, zone_b):
    lon1, lat1 = coordinates[zone_a]
    lon2, lat2 = coordinates[zone_b]

    return haversine(lon1, lat1, lon2, lat2)


first_seed = min(
    main_component,
    key=lambda z: haversine(
        center_lon,
        center_lat,
        coordinates[z][0],
        coordinates[z][1]
    )
)

seeds = [first_seed]

# Farthest-point selection for the other two seeds
while len(seeds) < 3:
    remaining = main_component - set(seeds)

    next_seed = max(
        remaining,
        key=lambda candidate: min(
            distance_to_seed(candidate, seed)
            for seed in seeds
        )
    )

    seeds.append(next_seed)


print("\n========== INITIAL SEEDS ==========")

for name, seed in zip(["fog-a", "fog-b", "fog-c"], seeds):
    print(
        name,
        "| zone:", seed,
        "| stations:", station_counts.get(seed, 0),
        "| coordinates:", coordinates[seed]
    )


# --------------------------------------------------
# 6. Grow three connected territories
# --------------------------------------------------


# --------------------------------------------------
# 6. Grow three connected territories - VERSION 2
# --------------------------------------------------

territories = {
    "fog-a": {seeds[0]},
    "fog-b": {seeds[1]},
    "fog-c": {seeds[2]}
}

loads = {
    name: station_counts.get(seed, 0)
    for name, seed in zip(territories, seeds)
}

target = main_stations / 3

# Distance penalty: favors compact territories
DISTANCE_WEIGHT = 25
DISTANCE_SCALE = 10_000


while sum(
    len(zones_set) for zones_set in territories.values()
) < len(main_component):

    assigned = set().union(*territories.values())

    best_choice = None
    best_score = float("inf")

    # Examine every possible territory/frontier assignment
    for name, owned_zones in territories.items():

        frontier = set()

        for zone in owned_zones:
            frontier.update(graph.neighbors(zone))

        frontier &= main_component
        frontier -= assigned

        for candidate in frontier:

            candidate_count = station_counts.get(candidate, 0)

            current_load = loads[name]
            projected_load = current_load + candidate_count

            # Change in global load imbalance
            balance_delta = (
                (projected_load - target) ** 2
                - (current_load - target) ** 2
            )

            # Distance to the nearest zone in this territory
            geographic_distance = min(
                distance_to_seed(candidate, owned)
                for owned in owned_zones
            )

            distance_penalty = (
                DISTANCE_WEIGHT
                * (geographic_distance / DISTANCE_SCALE) ** 2
            )

            score = balance_delta + distance_penalty

            if score < best_score:
                best_score = score
                best_choice = (name, candidate)

    if best_choice is None:
        raise RuntimeError(
            "No available frontier zone. Connectivity issue."
        )

    selected_name, selected_zone = best_choice

    territories[selected_name].add(selected_zone)

    loads[selected_name] += station_counts.get(
        selected_zone, 0
    )

    # Stop if all zones have been assigned
    if sum(len(t) for t in territories.values()) == len(main_component):
        break

    # Progress information
    total_assigned = sum(
        len(t) for t in territories.values()
    )

    if total_assigned % 25 == 0:
        print(
            f"Progress: {total_assigned}/"
            f"{len(main_component)} zones | "
            f"Loads: {loads}"
        )



# --------------------------------------------------
# 7. Validate and export
# --------------------------------------------------

rows = []

for name, owned_zones in territories.items():

    for zone_id in owned_zones:
        rows.append({
            "fog_id": name,
            "TAZID": zone_id,
            "station_count": station_counts.get(zone_id, 0),
            "longitude": coordinates[zone_id][0],
            "latitude": coordinates[zone_id][1]
        })

# Keep small components separate
for component_number, component in enumerate(components[1:], start=2):

    for zone_id in component:
        rows.append({
            "fog_id": f"UNASSIGNED_COMPONENT_{component_number}",
            "TAZID": zone_id,
            "station_count": station_counts.get(zone_id, 0),
            "longitude": coordinates[zone_id][0],
            "latitude": coordinates[zone_id][1]
        })


result = pd.DataFrame(rows)

output_file = Path("territory_partition.csv")
result.to_csv(output_file, index=False)

print("\n========== TERRITORY RESULTS ==========")

for name in territories:
    subset = result[result["fog_id"] == name]

    print(f"\n{name}")
    print("Zones:", len(subset))
    print("Stations:", int(subset["station_count"].sum()))

print("\nUnassigned small components:")
print(
    result[
        result["fog_id"].str.startswith("UNASSIGNED")
    ]["station_count"].sum(),
    "stations"
)

print("\nTotal zones:", len(result))
print("Total stations:", int(result["station_count"].sum()))

print("\nExported:", output_file)
