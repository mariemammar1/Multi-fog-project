import sqlite3

from fog.database import DB_PATH


def get_all_stations():
    """
    Retrieve all stations owned by this Fog Node.
    """
    with sqlite3.connect(DB_PATH) as connection:
        connection.row_factory = sqlite3.Row

        rows = connection.execute("""
            SELECT station_id, zone, status, power_kw, created_at
            FROM stations
            ORDER BY station_id
        """).fetchall()

        return [dict(row) for row in rows]


def update_station_status(station_id: str, new_status: str):
    """
    Update the status of a station owned by this Fog.
    """
    with sqlite3.connect(DB_PATH) as connection:
        cursor = connection.execute("""
            UPDATE stations
            SET status = ?
            WHERE station_id = ?
        """, (new_status, station_id))

        connection.commit()

        return cursor.rowcount > 0


def get_station_capacity():
    """
    Calculate the local station capacity of this Fog.
    """
    with sqlite3.connect(DB_PATH) as connection:
        connection.row_factory = sqlite3.Row

        row = connection.execute("""
            SELECT
                COUNT(*) AS total_stations,
                SUM(CASE WHEN status = 'AVAILABLE' THEN 1 ELSE 0 END)
                    AS available_stations,
                SUM(CASE WHEN status = 'OCCUPIED' THEN 1 ELSE 0 END)
                    AS occupied_stations,
                SUM(CASE WHEN status = 'OUT_OF_SERVICE' THEN 1 ELSE 0 END)
                    AS out_of_service_stations,
                COALESCE(
                    SUM(CASE WHEN status = 'AVAILABLE' THEN power_kw ELSE 0 END),
                    0
                ) AS available_power_kw
            FROM stations
        """).fetchone()

        return dict(row)