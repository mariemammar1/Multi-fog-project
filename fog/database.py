import sqlite3

from fog.settings import DB_PATH, DATA_DIR, FOG_ZONE, STATION_PREFIX


def init_db():
    """
    Initialize the local database of the current Fog.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(DB_PATH) as connection:

        connection.execute("""
            CREATE TABLE IF NOT EXISTS stations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                station_id TEXT NOT NULL UNIQUE,
                zone TEXT NOT NULL,
                status TEXT NOT NULL CHECK (
                    status IN (
                        'AVAILABLE',
                        'OCCUPIED',
                        'OUT_OF_SERVICE'
                    )
                ),
                power_kw REAL NOT NULL CHECK (power_kw > 0),
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        initial_stations = [
            (
                f"{STATION_PREFIX}-01",
                FOG_ZONE,
                "AVAILABLE",
                22.0
            ),
            (
                f"{STATION_PREFIX}-02",
                FOG_ZONE,
                "OCCUPIED",
                22.0
            ),
        ]

        connection.executemany("""
            INSERT OR IGNORE INTO stations
                (station_id, zone, status, power_kw)
            VALUES (?, ?, ?, ?)
        """, initial_stations)

        connection.commit()