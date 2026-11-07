from pathlib import Path
import sqlite3


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "fog_a.db"


def init_db():
    """
    Create the local database and initialize the stations table.
    Insert initial stations only if they do not already exist.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(DB_PATH) as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS stations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                station_id TEXT NOT NULL UNIQUE,
                zone TEXT NOT NULL,
                status TEXT NOT NULL CHECK (
                    status IN ('AVAILABLE', 'OCCUPIED', 'OUT_OF_SERVICE')
                ),
                power_kw REAL NOT NULL CHECK (power_kw > 0),
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        initial_stations = [
            ("A-01", "university", "AVAILABLE", 22.0),
            ("A-02", "university", "OCCUPIED", 22.0),
        ]

        connection.executemany("""
            INSERT OR IGNORE INTO stations
                (station_id, zone, status, power_kw)
            VALUES (?, ?, ?, ?)
        """, initial_stations)

        connection.commit()