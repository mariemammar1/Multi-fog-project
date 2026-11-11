
import pandas as pd
from pathlib import Path

BASE = Path("UrbanEVDataset/20220901-20230228_zone-cleaned-aggregated")
RAW = Path("UrbanEVDataset/20220901-20230228_station-raw")

zones = pd.read_csv(BASE / "zone-information.csv")
stations = pd.read_csv(RAW / "station_information.csv")

zones["TAZID"] = zones["TAZID"].astype(str).str.strip()
stations["TAZID"] = stations["TAZID"].astype(str).str.strip()

# Vérifier les données sources
print("=" * 60)
print("SOURCE DATA")
print("=" * 60)

print("Number of station records:", len(stations))
print("Unique station IDs:", stations["station_id"].nunique())
print("Number of zone records:", len(zones))
print("Unique zone IDs:", zones["TAZID"].nunique())

# Vérifier les zones non reconnues
zone_ids = set(zones["TAZID"])
station_zone_ids = set(stations["TAZID"])

unmatched = station_zone_ids - zone_ids

print("\n" + "=" * 60)
print("MAPPING DIAGNOSTIC")
print("=" * 60)

print("Distinct station TAZIDs:", len(station_zone_ids))
print("TAZIDs missing from zone information:", len(unmatched))
print("Unmatched TAZIDs:", sorted(unmatched))

unmatched_stations = stations[
    stations["TAZID"].isin(unmatched)
]

print("Number of stations in unmatched zones:",
      len(unmatched_stations))

# Vérifier les valeurs manquantes
print("\nMissing TAZID values:", stations["TAZID"].isna().sum())
print("Empty TAZID values:",
      (stations["TAZID"] == "").sum())

# Recalculer les totaux
counts = stations.groupby("TAZID").size()

print("\n" + "=" * 60)
print("STATION COUNT CHECK")
print("=" * 60)

print("Total stations from source:", counts.sum())
print("Stations mapped to zone metadata:",
      counts[counts.index.isin(zone_ids)].sum())
print("Stations not mapped:",
      counts[~counts.index.isin(zone_ids)].sum())
