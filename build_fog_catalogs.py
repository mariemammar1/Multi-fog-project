
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

RAW_DIR = (
    BASE_DIR
    / "UrbanEVDataset"
    / "20220901-20230228_station-raw"
)

# Charger les sources
stations = pd.read_csv(RAW_DIR / "station_information.csv")
piles = pd.read_csv(RAW_DIR / "pile_rated_power.csv")
partition = pd.read_csv("territory_partition_final.csv")

# Vérifier l'unicité des identifiants
assert stations["station_id"].is_unique
assert piles["pile_id"].is_unique
assert partition["TAZID"].is_unique

# Associer chaque station à son Fog propriétaire
stations_catalog = stations.merge(
    partition[["TAZID", "fog_id"]],
    on="TAZID",
    how="left",
    validate="many_to_one"
)

assert stations_catalog["fog_id"].notna().all()
assert len(stations_catalog) == 1682

# Ajouter le Fog propriétaire à chaque pile
piles_catalog = piles.merge(
    stations_catalog[["station_id", "fog_id"]],
    on="station_id",
    how="left",
    validate="many_to_one"
)

assert piles_catalog["fog_id"].notna().all()
assert len(piles_catalog) == 22650

# Sauvegarder les deux catalogues
stations_catalog.to_csv(
    BASE_DIR / "stations_catalog.csv",
    index=False
)

piles_catalog.to_csv(
    BASE_DIR / "piles_catalog.csv",
    index=False
)

# Statistiques
print("\n--- STATIONS PAR FOG ---")
print(
    stations_catalog.groupby("fog_id").agg(
        stations=("station_id", "nunique")
    )
)

print("\n--- PILES PAR FOG ---")
print(
    piles_catalog.groupby("fog_id").agg(
        piles=("pile_id", "nunique"),
        puissance_totale_kw=("power", "sum")
    )
)

print("\n--- STATIONS SANS PILES ---")
stations_with_piles = set(piles["station_id"])

without_piles = stations_catalog[
    ~stations_catalog["station_id"].isin(stations_with_piles)
]

print("Total :", len(without_piles))
print(without_piles.groupby("fog_id").size())

print("\nCatalogues créés avec succès.")
