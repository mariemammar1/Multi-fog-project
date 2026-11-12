
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

EXPECTED = {
    "fog_a.db": (524, 6083, 0),
    "fog_b.db": (545, 7403, 58),
    "fog_c.db": (566, 8652, 24),
}

all_station_ids = set()
all_pile_ids = set()

total_stations = 0
total_piles = 0
total_non_reservable = 0

for db_name, (expected_stations, expected_piles, expected_zero) in EXPECTED.items():

    db_path = DATA_DIR / db_name
    fog_id = db_name.replace("_", "-").replace(".db", "")

    print(f"\n--- {fog_id.upper()} ---")

    with sqlite3.connect(db_path) as connection:

        connection.execute("PRAGMA foreign_keys = ON")

        station_ids = {
            row[0]
            for row in connection.execute(
                "SELECT station_id FROM stations"
            )
        }

        pile_ids = {
            row[0]
            for row in connection.execute(
                "SELECT pile_id FROM piles"
            )
        }

        station_count = len(station_ids)
        pile_count = len(pile_ids)

        non_reservable = connection.execute(
            "SELECT COUNT(*) FROM piles WHERE is_reservable = 0"
        ).fetchone()[0]

        wrong_owner = connection.execute(
            "SELECT COUNT(*) FROM stations WHERE fog_id != ?",
            (fog_id,)
        ).fetchone()[0]

        orphan_piles = connection.execute("""
            SELECT COUNT(*)
            FROM piles p
            LEFT JOIN stations s ON p.station_id = s.station_id
            WHERE s.station_id IS NULL
        """).fetchone()[0]

        foreign_key_errors = connection.execute(
            "PRAGMA foreign_key_check"
        ).fetchall()

        print("Stations:", station_count)
        print("Piles:", pile_count)
        print("Non-reservable piles:", non_reservable)
        print("Wrong station owners:", wrong_owner)
        print("Piles without station:", orphan_piles)
        print("Foreign key errors:", len(foreign_key_errors))

        assert station_count == expected_stations
        assert pile_count == expected_piles
        assert non_reservable == expected_zero
        assert wrong_owner == 0
        assert orphan_piles == 0
        assert len(foreign_key_errors) == 0

        assert not (all_station_ids & station_ids), "Duplicate station IDs!"
        assert not (all_pile_ids & pile_ids), "Duplicate pile IDs!"

        all_station_ids.update(station_ids)
        all_pile_ids.update(pile_ids)

        total_stations += station_count
        total_piles += pile_count
        total_non_reservable += non_reservable

print("\n========== GLOBAL RESULT ==========")
print("Total stations:", total_stations)
print("Total piles:", total_piles)
print("Non-reservable piles:", total_non_reservable)
print("Reservable piles:", total_piles - total_non_reservable)

assert total_stations == 1635
assert total_piles == 22138
assert total_non_reservable == 82

print("\nSUCCESS: All three Fog databases are consistent!")
