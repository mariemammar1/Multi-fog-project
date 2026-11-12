
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt

# 1. Paths
BASE = Path("UrbanEVDataset") / "20220901-20230228_zone-cleaned-aggregated"

PARTITION_FILE = Path("territory_partition_optimized.csv")
ZONE_FILE = BASE / "zone-information.csv"

# 2. Load data
partition = pd.read_csv(PARTITION_FILE)
zones = pd.read_csv(ZONE_FILE)

# 3. Normalize zone IDs
partition["TAZID"] = partition["TAZID"].astype(str)
zones["TAZID"] = zones["TAZID"].astype(str)

# 4. Merge partition with geographic coordinates
data = partition.merge(
    zones[["TAZID", "longitude", "latitude"]],
    on="TAZID",
    how="left",
    suffixes=("", "_dataset")
)

# 5. Check missing coordinates
missing = data[["longitude", "latitude"]].isna().any(axis=1).sum()
print(f"Zones without coordinates: {missing}")

# 6. Draw the map
fig, ax = plt.subplots(figsize=(12, 9))

colors = {
    "fog-a": "royalblue",
    "fog-b": "darkorange",
    "fog-c": "seagreen",
}

for fog_id, color in colors.items():
    subset = data[data["fog_id"] == fog_id]

    ax.scatter(
        subset["longitude"],
        subset["latitude"],
        c=color,
        label=f"{fog_id} ({subset['station_count'].sum()} stations)",
        s=20 + subset["station_count"] * 2,
        alpha=0.7,
        edgecolors="black",
        linewidths=0.3,
    )

ax.set_title("Geographical Distribution of the 3 Fog Territories")
ax.set_xlabel("Longitude")
ax.set_ylabel("Latitude")
ax.legend(title="Fog Territories")
ax.grid(True, alpha=0.3)

ax.set_aspect("equal", adjustable="datalim")

plt.tight_layout()
plt.savefig("territory_map.png", dpi=300)
plt.show()

# 7. Display territory statistics
print("\nTerritory statistics:")
print(
    data.groupby("fog_id").agg(
        zones=("TAZID", "count"),
        stations=("station_count", "sum"),
    )
)
