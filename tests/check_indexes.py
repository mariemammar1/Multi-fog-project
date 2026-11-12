
import sqlite3
from pathlib import Path

databases = [
    Path("data/fog_a.db"),
    Path("data/fog_b.db"),
    Path("data/fog_c.db"),
]

expected_index = "unique_active_station_reservation"

for db_path in databases:
    print(f"\nChecking: {db_path}")

    if not db_path.exists():
        print("ERROR: Database not found!")
        continue

    with sqlite3.connect(db_path) as connection:
        indexes = connection.execute("""
            SELECT name, sql
            FROM sqlite_master
            WHERE type = 'index'
              AND name = ?
        """, (expected_index,)).fetchall()

        if indexes:
            print("SUCCESS: New index exists.")
            print(indexes[0][1])
        else:
            print("ERROR: New index is missing!")
