
import pandas as pd
import networkx as nx
from pathlib import Path


# ============================================================
# 1. CONFIGURATION
# ============================================================

BASE = Path(
    "UrbanEVDataset/20220901-20230228_zone-cleaned-aggregated"
)


# ============================================================
# 2. CHARGEMENT DES DONNEES
# ============================================================

print("=" * 65)
print("LOADING URBANEV DATASET")
print("=" * 65)

zones = pd.read_csv(BASE / "zone-information.csv")
stations = pd.read_csv(BASE / "station_information.csv")

# Ne pas utiliser index_col=0 :
# la première colonne contient les valeurs de la matrice.
adj = pd.read_csv(BASE / "adj.csv")

print("Zones loaded:", len(zones))
print("Stations loaded:", len(stations))


# ============================================================
# 3. PREPARATION DE LA MATRICE D'ADJACENCE
# ============================================================

print("\n" + "=" * 65)
print("PREPARING ADJACENCY MATRIX")
print("=" * 65)

# Les colonnes représentent les identifiants des zones.
adj.columns = adj.columns.astype(str)

# Vérifier la dimension de la matrice.
print("Shape:", adj.shape)
print("Duplicate columns:", adj.columns.duplicated().sum())

if adj.shape[0] != adj.shape[1]:
    raise ValueError("La matrice d'adjacence n'est pas carree.")

if not adj.columns.is_unique:
    raise ValueError("Les identifiants des zones sont dupliques.")

# La première colonne du CSV contient les valeurs de la matrice.
# On utilise les identifiants des colonnes comme index des lignes.
zone_ids = list(adj.columns)
adj.index = zone_ids

print("Matrix shape:", adj.shape)
print("Number of zone IDs:", len(zone_ids))
print("Unique zone IDs:", len(set(zone_ids)))
print("Index unique:", adj.index.is_unique)
print("Columns unique:", adj.columns.is_unique)

# Conversion en matrice numérique.
matrix = adj.to_numpy(dtype=int)


# ============================================================
# 4. CONSTRUCTION DU GRAPHE GEOGRAPHIQUE
# ============================================================

print("\n" + "=" * 65)
print("BUILDING GEOGRAPHICAL GRAPH")
print("=" * 65)

G = nx.Graph()

# Chaque zone représente un noeud.
G.add_nodes_from(zone_ids)

# Une relation est conservée si elle existe dans au moins
# un des deux sens (OR).
# La diagonale est ignorée.
for i in range(len(zone_ids)):
    for j in range(i + 1, len(zone_ids)):

        if matrix[i, j] == 1 or matrix[j, i] == 1:
            G.add_edge(zone_ids[i], zone_ids[j])

print("Graph nodes:", G.number_of_nodes())
print("Graph edges:", G.number_of_edges())


# ============================================================
# 5. CALCUL DU NOMBRE DE STATIONS PAR ZONE
# ============================================================

print("\n" + "=" * 65)
print("CALCULATING STATIONS PER ZONE")
print("=" * 65)

zones["TAZID"] = zones["TAZID"].astype(str)
stations["TAZID"] = stations["TAZID"].astype(str)

station_counts = stations.groupby("TAZID").size()

zones["station_count"] = (
    zones["TAZID"]
    .map(station_counts)
    .fillna(0)
    .astype(int)
)

print("Total stations:", zones["station_count"].sum())
print("Total zones:", len(zones))


# ============================================================
# 6. IDENTIFICATION DES COMPOSANTES CONNEXES
# ============================================================

print("\n" + "=" * 65)
print("CONNECTED COMPONENTS ANALYSIS")
print("=" * 65)

components = sorted(
    nx.connected_components(G),
    key=len,
    reverse=True
)

print("Number of connected components:", len(components))


# ============================================================
# 7. AFFICHAGE DES RESULTATS
# ============================================================

for i, component in enumerate(components, start=1):

    component_data = zones[
        zones["TAZID"].isin(component)
    ].copy()

    component_data = component_data.sort_values("TAZID")

    total_stations = component_data["station_count"].sum()

    print("\n" + "=" * 65)
    print(f"COMPONENT {i}")
    print("=" * 65)

    print("Number of zones:", len(component))
    print("Number of stations:", total_stations)

    print("\nZone details:")

    print(
        component_data[
            [
                "TAZID",
                "longitude",
                "latitude",
                "station_count"
            ]
        ].to_string(index=False)
    )


# ============================================================
# 8. STATISTIQUES GLOBALES
# ============================================================

print("\n" + "=" * 65)
print("GLOBAL SUMMARY")
print("=" * 65)

print("Total zones in graph:", G.number_of_nodes())
print("Total edges:", G.number_of_edges())
print("Connected components:", len(components))

print("Total stations:", zones["station_count"].sum())

print(
    "Zones in largest component:",
    len(components[0])
)

print(
    "Stations in largest component:",
    zones[
        zones["TAZID"].isin(components[0])
    ]["station_count"].sum()
)

print("\nAnalysis completed successfully.")
