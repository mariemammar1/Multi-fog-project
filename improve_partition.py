
from pathlib import Path

import networkx as nx
import pandas as pd

# =====================================================
# 1. CONFIGURATION
# =====================================================

BASE = (
    Path("UrbanEVDataset")
    / "20220901-20230228_zone-cleaned-aggregated"
)

INPUT_FILE = Path("territory_partition.csv")
OUTPUT_FILE = Path("territory_partition_optimized.csv")

FOGS = ["fog-a", "fog-b", "fog-c"]

BALANCE_WEIGHT = 0.80
COMPACTNESS_WEIGHT = 0.20

MAX_ITERATIONS = 200
MIN_IMPROVEMENT = 1e-9


def normalize_id(value):
    return str(int(float(value)))


# =====================================================
# 2. LOAD DATA
# =====================================================

print("Loading dataset...")

adjacency = pd.read_csv(BASE / "adj.csv")
distance = pd.read_csv(BASE / "distance.csv")
partition = pd.read_csv(INPUT_FILE)

adjacency.columns = [normalize_id(c) for c in adjacency.columns]
adjacency.index = adjacency.columns

distance.columns = [normalize_id(c) for c in distance.columns]
distance.index = distance.columns

partition["TAZID"] = partition["TAZID"].apply(normalize_id)
partition["station_count"] = partition["station_count"].astype(int)

# Keep only the zones assigned to the three Fog nodes.
assigned = partition[
    partition["fog_id"].isin(FOGS)
].copy()

# =====================================================
# 3. BUILD ADJACENCY GRAPH
# =====================================================

print("Building geographic graph...")

zone_ids = list(adjacency.columns)
matrix = adjacency.to_numpy(dtype=int)

graph = nx.Graph()
graph.add_nodes_from(zone_ids)

for i in range(len(zone_ids)):
    for j in range(i + 1, len(zone_ids)):
        if matrix[i, j] == 1 or matrix[j, i] == 1:
            graph.add_edge(zone_ids[i], zone_ids[j])

# =====================================================
# 4. BUILD TERRITORIES
# =====================================================

territories = {
    fog: set(
        assigned.loc[assigned["fog_id"] == fog, "TAZID"]
    )
    for fog in FOGS
}

counts = (
    assigned.set_index("TAZID")["station_count"].to_dict()
)

# Check that every assigned zone exists in both matrices.
assigned_zones = set().union(*territories.values())

if not assigned_zones.issubset(set(zone_ids)):
    raise ValueError("Some assigned zones are missing from adjacency.csv")

if not assigned_zones.issubset(set(distance.index)):
    raise ValueError("Some assigned zones are missing from distance.csv")

# Initial connectivity check.
for fog in FOGS:
    if not territories[fog]:
        raise ValueError(f"{fog} has no assigned zones.")

    if not nx.is_connected(graph.subgraph(territories[fog])):
        raise ValueError(f"{fog} is not initially connected.")

# =====================================================
# 5. METRICS
# =====================================================

total_stations = sum(counts.values())
target = total_stations / len(FOGS)


def calculate_loads(current_territories):
    return {
        fog: sum(counts[z] for z in current_territories[fog])
        for fog in FOGS
    }


def calculate_balance(current_territories):
    loads = calculate_loads(current_territories)

    return sum(
        ((loads[fog] - target) / target) ** 2
        for fog in FOGS
    )


def calculate_compactness(current_territories):
    values = {}

    for fog in FOGS:
        zones = sorted(current_territories[fog])

        numerator = 0.0
        denominator = 0.0

        for i in range(len(zones)):
            for j in range(i + 1, len(zones)):
                a = zones[i]
                b = zones[j]

                weight = counts[a] * counts[b]
                d = float(distance.loc[a, b])

                numerator += weight * d
                denominator += weight

        values[fog] = (
            numerator / denominator
            if denominator > 0
            else 0.0
        )

    return values


def calculate_objective(current_territories):
    balance = calculate_balance(current_territories)

    compactness_values = calculate_compactness(
        current_territories
    )

    average_compactness = sum(
        compactness_values.values()
    ) / len(FOGS)

    normalized_balance = (
        balance / initial_balance
        if initial_balance > 0
        else 0.0
    )

    normalized_compactness = (
        average_compactness / initial_compactness
        if initial_compactness > 0
        else 0.0
    )

    score = (
        BALANCE_WEIGHT * normalized_balance
        + COMPACTNESS_WEIGHT * normalized_compactness
    )

    return score


# =====================================================
# 6. INITIAL BASELINE
# =====================================================

initial_loads = calculate_loads(territories)
initial_balance = calculate_balance(territories)

initial_compactness_values = calculate_compactness(
    territories
)

initial_compactness = sum(
    initial_compactness_values.values()
) / len(FOGS)

if initial_balance <= 0 or initial_compactness <= 0:
    raise ValueError("Invalid initial metrics for normalization.")

current_score = calculate_objective(territories)

print("\n========== INITIAL STATE ==========")
print("Target:", target)
print("Loads:", initial_loads)
print("Balance:", initial_balance)
print("Compactness:", initial_compactness)
print("Objective:", current_score)

# =====================================================
# 7. ITERATIVE LOCAL SEARCH
# =====================================================

print("\n========== OPTIMIZATION ==========")

history = []

for iteration in range(1, MAX_ITERATIONS + 1):

    best_move = None
    best_score = current_score

    # Explore all possible single-zone transfers.
    for source in FOGS:

        for zone in sorted(territories[source]):

            remaining_source = territories[source] - {zone}

            # Source must remain connected.
            if not remaining_source:
                continue

            if not nx.is_connected(
                graph.subgraph(remaining_source)
            ):
                continue

            neighbors = set(graph.neighbors(zone))

            for destination in FOGS:

                if destination == source:
                    continue

                # Destination must touch the transferred zone.
                if not (neighbors & territories[destination]):
                    continue

                # Test the new destination territory.
                new_destination = territories[destination] | {zone}

                if not nx.is_connected(
                    graph.subgraph(new_destination)
                ):
                    continue

                # Evaluate the hypothetical partition.
                candidate = {
                    fog: set(zones)
                    for fog, zones in territories.items()
                }

                candidate[source].remove(zone)
                candidate[destination].add(zone)

                candidate_score = calculate_objective(candidate)

                if candidate_score < best_score - MIN_IMPROVEMENT:
                    best_score = candidate_score

                    best_move = {
                        "zone": zone,
                        "source": source,
                        "destination": destination,
                        "score": candidate_score,
                    }

    # No improving move: local optimum reached.
    if best_move is None:
        print("No improving transfer found.")
        break

    # Apply the best move.
    zone = best_move["zone"]
    source = best_move["source"]
    destination = best_move["destination"]

    territories[source].remove(zone)
    territories[destination].add(zone)

    current_score = best_score

    loads = calculate_loads(territories)

    history.append({
        "iteration": iteration,
        "zone": zone,
        "source": source,
        "destination": destination,
        "score": current_score,
        "loads": loads.copy(),
    })

    print(
        f"Iteration {iteration}: "
        f"Zone {zone}, {source} -> {destination}, "
        f"score={current_score:.6f}, loads={loads}"
    )

else:
    print("Maximum iteration limit reached.")

# =====================================================
# 8. FINAL VALIDATION
# =====================================================

print("\n========== FINAL VALIDATION ==========")

for fog in FOGS:
    components = nx.number_connected_components(
        graph.subgraph(territories[fog])
    )

    print(
        f"{fog}: "
        f"{len(territories[fog])} zones, "
        f"{calculate_loads(territories)[fog]} stations, "
        f"{components} component(s)"
    )

final_balance = calculate_balance(territories)
final_compactness_values = calculate_compactness(territories)

final_average_compactness = sum(
    final_compactness_values.values()
) / len(FOGS)

print("\nInitial balance:", initial_balance)
print("Final balance:", final_balance)

print("Initial compactness:", initial_compactness)
print("Final compactness:", final_average_compactness)

print("Initial objective:", 1.0)
print("Final objective:", current_score)

# =====================================================
# 9. SAVE NEW PARTITION
# =====================================================

new_assignments = {}

for fog in FOGS:
    for zone in territories[fog]:
        new_assignments[zone] = fog

# Preserve unassigned zones and all original columns.
optimized_partition = partition.copy()

mask = optimized_partition["TAZID"].isin(new_assignments)

optimized_partition.loc[mask, "fog_id"] = (
    optimized_partition.loc[mask, "TAZID"]
    .map(new_assignments)
)

optimized_partition.to_csv(
    OUTPUT_FILE,
    index=False
)

print("\nOptimized partition saved to:", OUTPUT_FILE)
print("Original partition was not modified.")
print("Total accepted transfers:", len(history))
