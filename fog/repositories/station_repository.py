import sqlite3

from fog.database import DB_PATH


def get_all_stations():
    """
    Retrieve all stations owned by this Fog,
    including their active reservation information.
    """
    with sqlite3.connect(DB_PATH) as connection:
        connection.row_factory = sqlite3.Row

        rows = connection.execute("""
            SELECT
                s.station_id,
                s.zone,
                s.status,
                s.power_kw,
                s.created_at,

                (
                    SELECT r.status
                    FROM reservations r
                    WHERE r.station_id = s.station_id
                      AND (
                          r.status = 'CONFIRMED'
                          OR (
                              r.status = 'HOLD'
                              AND julianday(r.expires_at) > julianday('now')
                          )
                      )
                    ORDER BY
                        CASE r.status
                            WHEN 'CONFIRMED' THEN 1
                            WHEN 'HOLD' THEN 2
                        END
                    LIMIT 1
                ) AS reservation_status,

                CASE
                    WHEN s.status != 'AVAILABLE' THEN 0
                    WHEN EXISTS (
                        SELECT 1
                        FROM reservations r
                        WHERE r.station_id = s.station_id
                          AND (
                              r.status = 'CONFIRMED'
                              OR (
                                  r.status = 'HOLD'
                                  AND julianday(r.expires_at) > julianday('now')
                              )
                          )
                    ) THEN 0
                    ELSE 1
                END AS is_reservable

            FROM stations s
            ORDER BY s.station_id
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
    Calculate the real local station capacity.

    A station is available only if:
    - Its physical status is AVAILABLE.
    - It has no active HOLD or CONFIRMED reservation.
    """
    with sqlite3.connect(DB_PATH) as connection:
        connection.row_factory = sqlite3.Row

        row = connection.execute("""
            SELECT
                COUNT(*) AS total_stations,

                SUM(
                    CASE
                        WHEN s.status = 'AVAILABLE'
                        AND NOT EXISTS (
                            SELECT 1
                            FROM reservations r
                            WHERE r.station_id = s.station_id
                              AND (
                                  r.status = 'CONFIRMED'
                                  OR (
                                      r.status = 'HOLD'
                                      AND julianday(r.expires_at) > julianday('now')
                                  )
                              )
                        )
                        THEN 1 ELSE 0
                    END
                ) AS available_stations,

                SUM(
                    CASE WHEN s.status = 'OCCUPIED'
                    THEN 1 ELSE 0 END
                ) AS occupied_stations,

                SUM(
                    CASE WHEN s.status = 'OUT_OF_SERVICE'
                    THEN 1 ELSE 0 END
                ) AS out_of_service_stations,

                COALESCE(
                    SUM(
                        CASE
                            WHEN s.status = 'AVAILABLE'
                            AND NOT EXISTS (
                                SELECT 1
                                FROM reservations r
                                WHERE r.station_id = s.station_id
                                  AND (
                                      r.status = 'CONFIRMED'
                                      OR (
                                          r.status = 'HOLD'
                                          AND julianday(r.expires_at) > julianday('now')
                                      )
                                  )
                            )
                            THEN s.power_kw ELSE 0
                        END
                    ),
                    0
                ) AS available_power_kw

            FROM stations s
        """).fetchone()

        return dict(row)
