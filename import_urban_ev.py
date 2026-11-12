
import csv
import sqlite3
from pathlib import Path

from fog.settings import DB_PATH, FOG_ID


BASE_DIR = Path(__file__).resolve().parent

STATIONS_FILE = BASE_DIR / "stations_catalog.csv"
PILES_FILE = BASE_DIR / "piles_catalog.csv"


def normalize_id(value):
    """Convert numeric CSV identifiers to consistent strings."""
    return str(int(float(value)))


def import_urban_ev():
    if FOG_ID not in {"fog-a", "fog-b", "fog-c"}:
        raise ValueError(f"Unknown Fog ID: {FOG_ID}")

    if not STATIONS_FILE.exists() or not PILES_FILE.exists():
        raise FileNotFoundError("UrbanEV catalog files are missing.")

    # Read only stations owned by the current Fog.
    with open(STATIONS_FILE, newline="", encoding="utf-8") as file:
        stations = [
            row for row in csv.DictReader(file)
            if row["fog_id"].strip() == FOG_ID
        ]

    # Read only piles owned by the current Fog.
    with open(PILES_FILE, newline="", encoding="utf-8") as file:
        piles = [
            row for row in csv.DictReader(file)
            if row["fog_id"].strip() == FOG_ID
        ]

    if not stations:
        raise ValueError(f"No stations found for {FOG_ID}.")

    station_ids = {
        normalize_id(row["station_id"])
        for row in stations
    }

    # Every imported pile must belong to an imported station.
    for pile in piles:
        if normalize_id(pile["station_id"]) not in station_ids:
            raise ValueError(
                f"Pile {pile['pile_id']} has no station in {FOG_ID}."
            )

    with sqlite3.connect(DB_PATH) as connection:
        connection.execute("PRAGMA foreign_keys = ON")

        # Verify that the new database schema is present.
        station_columns = {
            row[1]
            for row in connection.execute(
                "PRAGMA table_info(stations)"
            )
        }
        pile_columns = {
            row[1]
            for row in connection.execute(
                "PRAGMA table_info(piles)"
            )
        }

        if "longitude" not in station_columns or "tazid" not in station_columns:
            raise RuntimeError("The stations table has an incorrect schema.")

        if "power_kw" not in pile_columns or "pile_type" not in pile_columns:
            raise RuntimeError("The piles table has an incorrect schema.")

        # Insert stations first because piles reference them.
        connection.executemany(
            """
            INSERT OR IGNORE INTO stations (
                station_id,
                longitude,
                latitude,
                slow_count,
                fast_count,
                charge_count,
                tazid,
                fog_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    normalize_id(row["station_id"]),
                    float(row["longitude"]),
                    float(row["latitude"]),
                    int(row["slow_count"]),
                    int(row["fast_count"]),
                    int(row["charge_count"]),
                    row["TAZID"] or None,
                    FOG_ID,
                )
                for row in stations
            ],
        )

        # Insert individual charging piles.
        connection.executemany(
            """
            INSERT OR IGNORE INTO piles (
                pile_id,
                station_id,
                power_kw,
                pile_type,
                status,
                is_reservable
            )
            VALUES (?, ?, ?, ?, 'AVAILABLE', ?)
            """,
            [
                (
                    normalize_id(row["pile_id"]),
                    normalize_id(row["station_id"]),
                    float(row["power"]),
                    row["pileType"].strip().upper(),
                    int(float(row["power"]) > 0),
                )
                for row in piles
            ],
        )

        connection.commit()

        station_count = connection.execute(
            "SELECT COUNT(*) FROM stations"
        ).fetchone()[0]

        pile_count = connection.execute(
            "SELECT COUNT(*) FROM piles"
        ).fetchone()[0]

        reservable_count = connection.execute(
            "SELECT COUNT(*) FROM piles WHERE is_reservable = 1"
        ).fetchone()[0]

    print(f"\nImport completed for {FOG_ID}")
    print(f"Database: {DB_PATH}")
    print(f"Stations in catalog: {len(stations)}")
    print(f"Piles in catalog: {len(piles)}")
    print(f"Stations in database: {station_count}")
    print(f"Piles in database: {pile_count}")
    print(f"Reservable piles: {reservable_count}")


if __name__ == "__main__":
    import_urban_ev()
