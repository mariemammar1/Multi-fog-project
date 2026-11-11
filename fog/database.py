
import sqlite3

from fog.settings import DB_PATH, DATA_DIR


def init_db():
    """
    Initialize the local database of the current Fog.

    Each Fog owns its stations, piles and reservations.
    Historical station and pile information is imported
    separately from the UrbanEV dataset.
    """

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(DB_PATH) as connection:

        connection.execute("PRAGMA foreign_keys = ON")

        # Detect and remove the previous synthetic schema.
        # The original databases have already been backed up.
        existing_columns = {
            row[1]
            for row in connection.execute(
                "PRAGMA table_info(stations)"
            ).fetchall()
        }

        if existing_columns and "zone" in existing_columns:
            connection.execute("DROP TABLE IF EXISTS reservations")
            connection.execute("DROP TABLE IF EXISTS piles")
            connection.execute("DROP TABLE IF EXISTS stations")

        # Static geographical information about charging stations.
        connection.execute("""
            CREATE TABLE IF NOT EXISTS stations (
                station_id TEXT PRIMARY KEY,
                longitude REAL NOT NULL,
                latitude REAL NOT NULL,
                slow_count INTEGER NOT NULL DEFAULT 0,
                fast_count INTEGER NOT NULL DEFAULT 0,
                charge_count INTEGER NOT NULL DEFAULT 0,
                tazid TEXT,
                fog_id TEXT NOT NULL
            )
        """)

        # Individual charging piles belonging to a station.
        # Status is simulated; it is not provided by UrbanEV.
        connection.execute("""
            CREATE TABLE IF NOT EXISTS piles (
                pile_id TEXT PRIMARY KEY,
                station_id TEXT NOT NULL,
                power_kw REAL NOT NULL CHECK (power_kw >= 0),
                pile_type TEXT NOT NULL CHECK (
                    pile_type IN ('AC', 'DC')
                ),
                status TEXT NOT NULL DEFAULT 'AVAILABLE'
                    CHECK (
                        status IN (
                            'AVAILABLE',
                            'OCCUPIED',
                            'OUT_OF_SERVICE'
                        )
                    ),
                is_reservable INTEGER NOT NULL DEFAULT 1
                    CHECK (is_reservable IN (0, 1)),
                FOREIGN KEY (station_id)
                    REFERENCES stations(station_id)
                    ON DELETE CASCADE
            )
        """)

        # Reservations target individual piles, not whole stations.
        connection.execute("""
            CREATE TABLE IF NOT EXISTS reservations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                hold_id TEXT NOT NULL,
                request_id TEXT NOT NULL,
                origin_fog TEXT NOT NULL,
                pile_id TEXT NOT NULL,
                status TEXT NOT NULL CHECK (
                    status IN (
                        'HOLD',
                        'CONFIRMED',
                        'CANCELLED',
                        'EXPIRED'
                    )
                ),
                expires_at TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (pile_id)
                    REFERENCES piles(pile_id)
            )
        """)

        # One pile cannot have two active reservations.
        connection.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS
            unique_active_pile_reservation
            ON reservations(pile_id)
            WHERE status IN ('HOLD', 'CONFIRMED')
        """)

        # Useful indexes for station and pile queries.
        connection.execute("""
            CREATE INDEX IF NOT EXISTS
            idx_piles_station
            ON piles(station_id)
        """)

        connection.execute("""
            CREATE INDEX IF NOT EXISTS
            idx_piles_status
            ON piles(status, is_reservable)
        """)

        connection.commit()
