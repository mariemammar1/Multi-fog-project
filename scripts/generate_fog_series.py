import csv
from collections import defaultdict
from pathlib import Path

DATASET = Path("UrbanEVDataset/20220901-20230228_zone-cleaned-aggregated/charge_1hour")
PARTITION = Path("territory_partition_final.csv")
OUTPUT = Path("ml-service/data")

# Associer chaque zone à son Fog
with PARTITION.open(newline="") as f:
    partition = {
        row["TAZID"]: row["fog_id"]
        for row in csv.DictReader(f)
    }

# Lire les zones présentes dans le fichier
with (DATASET / "occupancy.csv").open(newline="") as f:
    reader = csv.reader(f)
    header = next(reader)

    fog_columns = defaultdict(list)

    for index, zone in enumerate(header[1:], start=1):
        fog = partition.get(zone)
        if fog in ("fog-a", "fog-b", "fog-c"):
            fog_columns[fog].append(index)

    # Créer un fichier indépendant par Fog
    files = {}
    writers = {}

    try:
        for fog in ("fog-a", "fog-b", "fog-c"):
            files[fog] = (OUTPUT / f"{fog}.csv").open("w", newline="")
            writers[fog] = csv.writer(files[fog])
            writers[fog].writerow(["time", "busy"])

        for row in reader:
            timestamp = row[0]

            for fog in ("fog-a", "fog-b", "fog-c"):
                total_busy = sum(float(row[i]) for i in fog_columns[fog])
                writers[fog].writerow([timestamp, total_busy])

    finally:
        for file in files.values():
            file.close()

for fog in ("fog-a", "fog-b", "fog-c"):
    print(f"{fog}: {len(fog_columns[fog])} zones -> {OUTPUT / (fog + '.csv')}")
