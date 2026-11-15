import sqlite3

from fog.settings import DB_PATH, FOG_ZONE


def get_all_stations():
    """
    Retrieve all stations owned by this Fog,
    including their aggregated pile availability and real geographic data.
    """
    with sqlite3.connect(DB_PATH) as connection:
        connection.row_factory = sqlite3.Row

        rows = connection.execute("""
            WITH pile_stats AS (
                SELECT
                    p.station_id,
                    COUNT(*) AS total_piles,
                    SUM(
                        CASE
                            WHEN p.status = 'AVAILABLE'
                             AND p.is_reservable = 1
                             AND NOT EXISTS (
                                SELECT 1
                                FROM reservations r
                                WHERE r.pile_id = p.pile_id
                                  AND (
                                      r.status IN ('CONFIRMED', 'ACTIVE')
                                      OR (
                                          r.status = 'HOLD'
                                          AND julianday(r.expires_at) > julianday('now')
                                      )
                                  )
                             )
                            THEN 1 ELSE 0
                        END
                    ) AS available_piles,
                    SUM(CASE WHEN p.status = 'OCCUPIED' THEN 1 ELSE 0 END) AS occupied_piles,
                    SUM(CASE WHEN p.status = 'OUT_OF_SERVICE' THEN 1 ELSE 0 END) AS out_of_service_piles,
                    MAX(p.power_kw) AS max_power_kw,
                    SUM(p.power_kw) AS total_power_kw
                FROM piles p
                GROUP BY p.station_id
            )
            SELECT
                s.station_id,
                ? AS zone,
                s.fog_id,
                s.longitude,
                s.latitude,
                s.slow_count,
                s.fast_count,
                s.charge_count,
                s.tazid,
                COALESCE(ps.total_piles, 0) AS total_piles,
                COALESCE(ps.available_piles, 0) AS available_piles,
                COALESCE(ps.occupied_piles, 0) AS occupied_piles,
                COALESCE(ps.out_of_service_piles, 0) AS out_of_service_piles,
                COALESCE(ps.max_power_kw, 22.0) AS power_kw,
                COALESCE(ps.total_power_kw, 0.0) AS total_power_kw,
                NULL AS created_at,
                NULL AS reservation_status,
                CASE
                    WHEN COALESCE(ps.available_piles, 0) > 0 THEN 'AVAILABLE'
                    WHEN COALESCE(ps.occupied_piles, 0) > 0 THEN 'OCCUPIED'
                    ELSE 'OUT_OF_SERVICE'
                END AS status,
                CASE
                    WHEN COALESCE(ps.available_piles, 0) > 0 THEN 1
                    ELSE 0
                END AS is_reservable
            FROM stations s
            LEFT JOIN pile_stats ps ON ps.station_id = s.station_id
            ORDER BY s.station_id
        """, (FOG_ZONE,)).fetchall()

        return [dict(row) for row in rows]


def update_station_status(station_id: str, new_status: str):
    """
    Update the status of all piles of a station owned by this Fog.
    """
    with sqlite3.connect(DB_PATH) as connection:
        cursor = connection.execute("""
            UPDATE piles
            SET status = ?
            WHERE station_id = ?
        """, (new_status, station_id))

        connection.commit()
        return cursor.rowcount > 0


def get_station_capacity():
    with sqlite3.connect(DB_PATH) as connection:
        connection.row_factory = sqlite3.Row

        row = connection.execute("""
            WITH pile_stats AS (
                SELECT
                    p.station_id,
                    COUNT(*) AS total_piles,
                    SUM(
                        CASE
                            WHEN p.status = 'AVAILABLE'
                             AND p.is_reservable = 1
                             AND NOT EXISTS (
                                SELECT 1
                                FROM reservations r
                                WHERE r.pile_id = p.pile_id
                                  AND (
                                      r.status IN ('CONFIRMED', 'ACTIVE')
                                      OR (
                                          r.status = 'HOLD'
                                          AND julianday(r.expires_at) > julianday('now')
                                      )
                                  )
                             )
                            THEN 1 ELSE 0
                        END
                    ) AS available_piles,
                    SUM(CASE WHEN p.status = 'OCCUPIED' THEN 1 ELSE 0 END) AS occupied_piles,
                    SUM(CASE WHEN p.status = 'OUT_OF_SERVICE' THEN 1 ELSE 0 END) AS out_of_service_piles,
                    SUM(
                        CASE
                            WHEN p.status = 'AVAILABLE'
                             AND p.is_reservable = 1
                             AND NOT EXISTS (
                                SELECT 1
                                FROM reservations r
                                WHERE r.pile_id = p.pile_id
                                  AND (
                                      r.status IN ('CONFIRMED', 'ACTIVE')
                                      OR (
                                          r.status = 'HOLD'
                                          AND julianday(r.expires_at) > julianday('now')
                                      )
                                  )
                             )
                            THEN p.power_kw ELSE 0
                        END
                    ) AS available_power_kw
                FROM piles p
                GROUP BY p.station_id
            )
            SELECT
                COUNT(*) AS total_stations,
                SUM(CASE WHEN ps.available_piles > 0 THEN 1 ELSE 0 END) AS available_stations,
                SUM(CASE WHEN ps.occupied_piles = ps.total_piles THEN 1 ELSE 0 END) AS occupied_stations,
                SUM(CASE WHEN ps.out_of_service_piles = ps.total_piles THEN 1 ELSE 0 END) AS out_of_service_stations,
                COALESCE(SUM(ps.total_piles), 0) AS total_piles,
                COALESCE(SUM(ps.available_piles), 0) AS available_piles,
                COALESCE(SUM(ps.occupied_piles), 0) AS occupied_piles,
                COALESCE(SUM(ps.out_of_service_piles), 0) AS out_of_service_piles,
                COALESCE(SUM(ps.available_power_kw), 0) AS available_power_kw
            FROM stations s
            LEFT JOIN pile_stats ps ON ps.station_id = s.station_id
        """).fetchone()

        return dict(row)
