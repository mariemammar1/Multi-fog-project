import sqlite3
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fog.settings import DB_PATH


def create_hold(request):
    """
    Atomically reserve the required available stations
    in this Fog's local database.
    """

    now = datetime.now(timezone.utc)
    now_text = now.isoformat(timespec="seconds")

    expires_at = (
        now + timedelta(seconds=request.ttl_seconds)
    ).isoformat(timespec="seconds")

    with sqlite3.connect(DB_PATH, timeout=10) as connection:
        connection.row_factory = sqlite3.Row

        # Prevent concurrent transactions from selecting
        # the same available stations.
        connection.execute("BEGIN IMMEDIATE")

        # Expire old temporary reservations.
        connection.execute("""
            UPDATE reservations
            SET status = 'EXPIRED'
            WHERE status = 'HOLD'
              AND expires_at <= ?
        """, (now_text,))

        # Idempotency: if this request already has an active HOLD,
        # return the existing reservation instead of creating another.
        existing = connection.execute("""
            SELECT hold_id, request_id, origin_fog,
                   station_id, expires_at
            FROM reservations
            WHERE request_id = ?
              AND status = 'HOLD'
            ORDER BY station_id
        """, (request.request_id,)).fetchall()

        if existing:
            return {
                "hold_id": existing[0]["hold_id"],
                "request_id": request.request_id,
                "origin_fog": existing[0]["origin_fog"],
                "station_ids": [row["station_id"] for row in existing],
                "expires_at": existing[0]["expires_at"]
            }

        # Find stations not already reserved by an active HOLD.
        available = connection.execute("""
            SELECT s.station_id, s.power_kw
            FROM stations s
            WHERE s.status = 'AVAILABLE'
              AND NOT EXISTS (
                  SELECT 1
                  FROM reservations r
                  WHERE r.station_id = s.station_id
                    AND r.status = 'HOLD'
              )
            ORDER BY s.power_kw DESC, s.station_id
        """).fetchall()

        selected = []
        total_power = 0.0

        for station in available:
            if len(selected) >= request.required_stations:
                break

            selected.append(station)
            total_power += station["power_kw"]

        # Do not create a reservation if the requirements
        # cannot be satisfied.
        if (
            len(selected) < request.required_stations
            or total_power < request.required_power_kw
        ):
            return None

        hold_id = str(uuid4())

        for station in selected:
            connection.execute("""
                INSERT INTO reservations (
                    hold_id, request_id, origin_fog,
                    station_id, status, expires_at
                )
                VALUES (?, ?, ?, ?, 'HOLD', ?)
            """, (
                hold_id,
                request.request_id,
                request.origin_fog,
                station["station_id"],
                expires_at
            ))

        return {
            "hold_id": hold_id,
            "request_id": request.request_id,
            "origin_fog": request.origin_fog,
            "station_ids": [station["station_id"] for station in selected],
            "expires_at": expires_at
        }
def confirm_hold(hold_id):
    """
    Confirm an existing temporary reservation.
    An expired or cancelled reservation cannot be confirmed.
    """

    now = datetime.now(timezone.utc)
    now_text = now.isoformat(timespec="seconds")

    with sqlite3.connect(DB_PATH, timeout=10) as connection:
        connection.row_factory = sqlite3.Row
        connection.execute("BEGIN IMMEDIATE")

        reservations = connection.execute("""
            SELECT hold_id, request_id, origin_fog,
                   station_id, status, expires_at
            FROM reservations
            WHERE hold_id = ?
            ORDER BY station_id
        """, (hold_id,)).fetchall()

        if not reservations:
            return None

        # Idempotency: an already confirmed reservation
        # returns the same result.
        if all(row["status"] == "CONFIRMED" for row in reservations):
            return {
                "hold_id": hold_id,
                "request_id": reservations[0]["request_id"],
                "origin_fog": reservations[0]["origin_fog"],
                "station_ids": [
                    row["station_id"] for row in reservations
                ]
            }

        # All stations must still be on HOLD.
        if not all(row["status"] == "HOLD" for row in reservations):
            return None

        # Check expiration.
        if any(row["expires_at"] <= now_text for row in reservations):
            connection.execute("""
                UPDATE reservations
                SET status = 'EXPIRED'
                WHERE hold_id = ? AND status = 'HOLD'
            """, (hold_id,))
            return None

        # Confirm all stations belonging to this HOLD.
        connection.execute("""
            UPDATE reservations
            SET status = 'CONFIRMED'
            WHERE hold_id = ? AND status = 'HOLD'
        """, (hold_id,))

        return {
            "hold_id": hold_id,
            "request_id": reservations[0]["request_id"],
            "origin_fog": reservations[0]["origin_fog"],
            "station_ids": [
                row["station_id"] for row in reservations
            ]
        }