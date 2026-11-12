
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# Fichiers sources
raw_dir = (
    BASE_DIR
    / "UrbanEVDataset"
    / "20220901-20230228_station-raw"
)

stations = pd.read_csv(raw_dir / "station_information.csv")
partition = pd.read_csv("territory_partition_extended.csv")

# Recalculer le nombre réel de stations par zone
real_counts = (
    stations.groupby("TAZID")["station_id"]
    .nunique()
    .rename("station_count_real")
    .reset_index()
)

# Associer les vrais compteurs aux zones
corrected = partition.drop(columns=["station_count"]).merge(
    real_counts,
    on="TAZID",
    how="left",
    validate="one_to_one"
)

# Vérifications
assert corrected["station_count_real"].notna().all()
assert corrected["TAZID"].nunique() == 331
assert corrected["station_count_real"].sum() == stations["station_id"].nunique()

corrected = corrected.rename(
    columns={"station_count_real": "station_count"}
)

# Sauvegarder sans écraser l'ancien fichier
output = BASE_DIR / "territory_partition_final.csv"
corrected.to_csv(output, index=False)

print("Partition corrigée :", output.name)
print("Nombre de zones :", corrected["TAZID"].nunique())
print("Nombre total de stations :", corrected["station_count"].sum())

print("\nRépartition finale :")
print(
    corrected.groupby("fog_id").agg(
        zones=("TAZID", "nunique"),
        stations=("station_count", "sum")
    )
)
