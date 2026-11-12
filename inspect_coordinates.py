import pandas as pd

base = "UrbanEVDataset/20220901-20230228_zone-cleaned-aggregated"

zones = pd.read_csv(f"{base}/zone-information.csv")
stations = pd.read_csv(f"{base}/station_information.csv")

# Check invalid coordinates
invalid_zones = zones[
    (zones["longitude"] == 0) |
    (zones["latitude"] == 0)
]

invalid_stations = stations[
    (stations["longitude"] == 0) |
    (stations["latitude"] == 0)
]

print("========== INVALID ZONES ==========")
print("Number:", len(invalid_zones))
print(invalid_zones.to_string(index=False))

print("\n========== INVALID STATIONS ==========")
print("Number:", len(invalid_stations))
print(invalid_stations.head(20).to_string(index=False))

print("\n========== VALID ZONE COORDINATES ==========")
valid = zones[
    (zones["longitude"] != 0) &
    (zones["latitude"] != 0)
]

print("Valid zones:", len(valid))
print("Longitude:", valid["longitude"].min(), "-", valid["longitude"].max())
print("Latitude:", valid["latitude"].min(), "-", valid["latitude"].max())

print("\n========== ZONES WITH MOST STATIONS ==========")
print(
    stations.groupby("TAZID").size()
    .sort_values(ascending=False)
    .head(10)
)