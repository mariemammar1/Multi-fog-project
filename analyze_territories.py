
import pandas as pd
import networkx as nx
from pathlib import Path

BASE = Path("UrbanEVDataset/20220901-20230228_zone-cleaned-aggregated")
RAW = Path(
    "UrbanEVDataset/20220901-20230228_zone-cleaned-aggregated"
)

# 1. Charger les zones et leurs coordonnées
zones_df = pd.read_csv(BASE / "zone-information.csv")
zones_df["TAZID"] = zones_df["TAZID"].astype(str)

# Corriger le centroïde invalide de la zone 348
stations_df = pd.read_csv(RAW / "station_information.csv")
stations_df["TAZID"] = stations_df["TAZID"].astype(str)

zone_348 = stations_df[stations_df["TAZID"] == "348"]

zones_df.loc[zones_df["TAZID"] == "348", "longitude"] = (
    zone_348["longitude"].mean()
)
zones_df.loc[zones_df["TAZID"] == "348", "latitude"] = (
    zone_348["latitude"].mean()
)

# 2. Calculer le nombre de stations par zone
counts = stations_df.groupby("TAZID").size()

zones_df["station_count"] = (
    zones_df["TAZID"].map(counts).fillna(0).astype(int)
)

# 3. Construire le graphe d'adjacence OR
adj_df = pd.read_csv(BASE / "adj.csv")
zone_ids = adj_df.columns.astype(str).tolist()
A = adj_df.to_numpy(dtype=int)

G = nx.Graph()
G.add_nodes_from(zone_ids)

for i in range(len(zone_ids)):
    for j in range(i + 1, len(zone_ids)):
        if A[i, j] == 1 or A[j, i] == 1:
            G.add_edge(zone_ids[i], zone_ids[j])

components = sorted(
    nx.connected_components(G),
    key=len,
    reverse=True
)

main_zones = set(components[0])

# 4. Créer le tableau de synthèse
zones_df["component"] = zones_df["TAZID"].apply(
    lambda z: next(
        i + 1 for i, comp in enumerate(components) if z in comp
    )
)

zones_df["is_main_component"] = (
    zones_df["TAZID"].isin(main_zones)
)

print("TOTAL STATIONS:", zones_df["station_count"].sum())
print("TOTAL ZONES:", len(zones_df))

print("\nMAIN COMPONENT:")
main = zones_df[zones_df["is_main_component"]]

print("Zones:", len(main))
print("Stations:", main["station_count"].sum())

print("\nSTATION DISTRIBUTION:")
print(main["station_count"].describe())

print("\nGEOGRAPHICAL BOUNDS:")
print("Longitude:", main["longitude"].min(), "to", main["longitude"].max())
print("Latitude:", main["latitude"].min(), "to", main["latitude"].max())

# 5. Sauvegarder une copie de travail
output = Path("territory_analysis.csv")
zones_df.to_csv(output, index=False)

print("\nFile generated:", output)
