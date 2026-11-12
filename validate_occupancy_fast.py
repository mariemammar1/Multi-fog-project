
import csv
import time
from pathlib import Path
from array import array
from collections import defaultdict

START = time.time()

BASE = Path("UrbanEVDataset")
ZONE_DIR = BASE / "20220901-20230228_zone-cleaned-aggregated"
RAW_DIR = BASE / "20220901-20230228_station-raw" / "charge_5min"

OCCUPANCY_FILE = ZONE_DIR / "charge_5min" / "occupancy.csv"
STATION_INFO_FILE = ZONE_DIR / "station_information.csv"


def normalize_id(value):
    return str(int(float(value)))


print("1. Lecture des informations des stations...", flush=True)

# Associer chaque zone à ses stations
stations_by_zone = defaultdict(list)

with open(STATION_INFO_FILE, "r", newline="", encoding="utf-8-sig") as f:
    reader = csv.DictReader(f)

    for row in reader:
        station_id = normalize_id(row["station_id"])
        zone_id = normalize_id(row["TAZID"])
        stations_by_zone[zone_id].append(station_id)

print(f"Stations identifiées : {sum(map(len, stations_by_zone.values()))}")
print(f"Zones identifiées : {len(stations_by_zone)}")


print("\n2. Lecture des occupations de référence...", flush=True)

# Charger les timestamps et les occupations attendues
with open(OCCUPANCY_FILE, "r", newline="", encoding="utf-8-sig") as f:
    reader = csv.reader(f)

    header = next(reader)
    zone_ids = [normalize_id(z) for z in header[1:]]

    times = []
    expected = {
        zone: array("i")
        for zone in zone_ids
    }

    for row in reader:
        if not row:
            continue

        times.append(row[0])

        for zone, value in zip(zone_ids, row[1:]):
            expected[zone].append(int(float(value or 0)))

number_of_times = len(times)

print(f"Zones : {len(zone_ids)}")
print(f"Timestamps : {number_of_times}")
print(f"Valeurs de référence chargées.", flush=True)


print("\n3. Reconstruction des occupations depuis les stations...", flush=True)

# Une seule liste compacte par zone
actual = {
    zone: array("i", [0]) * number_of_times
    for zone in zone_ids
}

processed = 0
missing_files = []
time_index = {timestamp: i for i, timestamp in enumerate(times)}

total_stations = sum(len(s) for s in stations_by_zone.values())

for zone_id, station_ids in stations_by_zone.items():

    if zone_id not in actual:
        continue

    zone_values = actual[zone_id]

    for station_id in station_ids:

        file_path = RAW_DIR / f"{station_id}.csv"

        if not file_path.exists():
            missing_files.append(station_id)
            continue

        last_busy = 0
        sequential_idx = 0

        with open(file_path, "r", newline="", encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            raw_header = next(reader, None)

            if not raw_header:
                continue

            time_col = raw_header.index("time")
            busy_col = raw_header.index("busy")

            for row in reader:

                if len(row) <= max(time_col, busy_col):
                    continue

                timestamp = row[time_col]

                # Chemin rapide : timestamps dans le même ordre
                if (
                    sequential_idx < number_of_times
                    and timestamp == times[sequential_idx]
                ):
                    idx = sequential_idx
                    sequential_idx += 1

                else:
                    # Fallback si les timestamps ne sont pas alignés
                    idx = time_index.get(timestamp)

                    if idx is None:
                        continue

                    sequential_idx = idx + 1

                busy_value = row[busy_col].strip()

                # Forward fill : conserver la dernière valeur connue
                if busy_value:
                    last_busy = int(float(busy_value))

                zone_values[idx] += last_busy

        processed += 1

        if processed % 50 == 0:
            elapsed = time.time() - START
            print(
                f"Stations traitées : {processed}/{total_stations} "
                f"({processed / total_stations * 100:.1f}%) "
                f"| Temps : {elapsed:.1f}s",
                flush=True
            )


print("\n4. Comparaison avec occupancy.csv...", flush=True)

total_differences = 0
zones_with_differences = 0

for zone in zone_ids:

    if zone not in actual:
        continue

    expected_values = expected[zone]
    actual_values = actual[zone]

    differences = 0
    first_differences = []
    max_difference = 0

    for i in range(number_of_times):
        expected_value = expected_values[i]
        actual_value = actual_values[i]

        if expected_value != actual_value:
            differences += 1

            diff = abs(expected_value - actual_value)
            max_difference = max(max_difference, diff)

            if len(first_differences) < 5:
                first_differences.append({
                    "time": times[i],
                    "expected": expected_value,
                    "calculated": actual_value
                })

    total_differences += differences

    if differences > 0:
        zones_with_differences += 1

        print(
            f"\nZone {zone} : {differences}/{number_of_times} "
            f"différences | écart max : {max_difference}"
        )

        for item in first_differences:
            print(
                f"  {item['time']} | "
                f"attendu={item['expected']} | "
                f"calculé={item['calculated']}"
            )

print("\n========== RÉSULTAT FINAL ==========")
print(f"Stations traitées : {processed}/{total_stations}")
print(f"Fichiers manquants : {len(missing_files)}")
print(f"Zones avec différences : {zones_with_differences}")
print(f"Nombre total de différences : {total_differences}")

if total_differences == 0:
    print("VALIDATION RÉUSSIE : toutes les valeurs correspondent.")
else:
    print("VALIDATION INCOMPLÈTE : certaines valeurs ne correspondent pas.")

print(f"Temps total : {time.time() - START:.2f} secondes")
