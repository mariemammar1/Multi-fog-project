
import sqlite3
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fog.settings import DB_PATH


def create_hold(request):
    """
    Atomically reserve the required available piles
    in this Fog's local database.
    """

    now = datetime.now(timezone.utc)
    now_text = now.isoformat(timespec="seconds")

    expires_at = (
        now + timedelta(seconds=request.ttl_seconds)
    ).isoformat(timespec="seconds")

    with sqlite3.connect(DB_PATH, timeout=10) as connection:
        connection.row_factory = sqlite3.Row

        # Lock the database to prevent concurrent reservations.
        connection.execute("BEGIN IMMEDIATE")

        # Expire temporary reservations whose TTL has elapsed.
        connection.execute("""
            UPDATE reservations
            SET status = 'EXPIRED'
            WHERE status = 'HOLD'
              AND julianday(expires_at) <= julianday(?)
        """, (now_text,))

        # Prevent a repeated request from creating another HOLD.
        existing = connection.execute("""
            SELECT hold_id, request_id, origin_fog,
                   pile_id, expires_at, status
            FROM reservations
            WHERE request_id = ?
              AND origin_fog = ?
              AND status IN ('HOLD', 'CONFIRMED')
            ORDER BY pile_id
        """, (request.request_id, request.origin_fog)).fetchall()

        if existing:
            # An existing confirmed request must not reserve again.
            if existing[0]["status"] == "CONFIRMED":
                return None

            return {
                "hold_id": existing[0]["hold_id"],
                "request_id": request.request_id,
                "origin_fog": request.origin_fog,
                "pile_ids": [row["pile_id"] for row in existing],
                "expires_at": existing[0]["expires_at"]
            }

        # Find available and reservable piles.
        available = connection.execute("""
            SELECT p.pile_id, p.power_kw
            FROM piles p
            WHERE p.status = 'AVAILABLE'
              AND p.is_reservable = 1
              AND NOT EXISTS (
                  SELECT 1
                  FROM reservations r
                  WHERE r.pile_id = p.pile_id
                    AND (
                        r.status = 'CONFIRMED'
                        OR (
                            r.status = 'HOLD'
                            AND julianday(r.expires_at) > julianday(?)
                        )
                    )
              )
            ORDER BY p.power_kw DESC, p.pile_id
        """, (now_text,)).fetchall()

        selected = []
        total_power = 0.0

        for pile in available:
            if len(selected) >= request.required_piles:
                break

            selected.append(pile)
            total_power += pile["power_kw"]

        # Check both the required number of piles and power.
        if (
            len(selected) < request.required_piles
            or total_power < request.required_power_kw
        ):
            return None

        hold_id = str(uuid4())

        for pile in selected:
            connection.execute("""
                INSERT INTO reservations (
                    hold_id,
                    request_id,
                    origin_fog,
                    pile_id,
                    status,
                    expires_at
                )
                VALUES (?, ?, ?, ?, 'HOLD', ?)
            """, (
                hold_id,
                request.request_id,
                request.origin_fog,
                pile["pile_id"],
                expires_at
            ))

        return {
            "hold_id": hold_id,
            "request_id": request.request_id,
            "origin_fog": request.origin_fog,
            "pile_ids": [pile["pile_id"] for pile in selected],
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
                   pile_id, status, expires_at
            FROM reservations
            WHERE hold_id = ?
            ORDER BY pile_id
        """, (hold_id,)).fetchall()

        if not reservations:
            return None

        if all(row["status"] == "CONFIRMED" for row in reservations):
            return {
                "hold_id": hold_id,
                "request_id": reservations[0]["request_id"],
                "origin_fog": reservations[0]["origin_fog"],
                "pile_ids": [
                    row["pile_id"] for row in reservations
                ]
            }

        if not all(row["status"] == "HOLD" for row in reservations):
            return None

        # Check whether the temporary reservation has expired.
        if any(
            datetime.fromisoformat(row["expires_at"]) <= now
            for row in reservations
        ):
            connection.execute("""
                UPDATE reservations
                SET status = 'EXPIRED'
                WHERE hold_id = ? AND status = 'HOLD'
            """, (hold_id,))
            return None

        connection.execute("""
            UPDATE reservations
            SET status = 'CONFIRMED'
            WHERE hold_id = ? AND status = 'HOLD'
        """, (hold_id,))

        return {
            "hold_id": hold_id,
            "request_id": reservations[0]["request_id"],
            "origin_fog": reservations[0]["origin_fog"],
            "pile_ids": [
                row["pile_id"] for row in reservations
            ]
        }


def cancel_hold(hold_id):
    """
    Cancel an existing HOLD or CONFIRMED reservation.
    """

    with sqlite3.connect(DB_PATH, timeout=10) as connection:
        connection.row_factory = sqlite3.Row
        connection.execute("BEGIN IMMEDIATE")

        reservations = connection.execute("""
            SELECT hold_id, request_id, origin_fog,
                   pile_id, status
            FROM reservations
            WHERE hold_id = ?
            ORDER BY pile_id
        """, (hold_id,)).fetchall()

        if not reservations:
            return None

        if all(row["status"] == "CANCELLED" for row in reservations):
            return {
                "hold_id": hold_id,
                "request_id": reservations[0]["request_id"],
                "origin_fog": reservations[0]["origin_fog"],
                "pile_ids": [
                    row["pile_id"] for row in reservations
                ],
                "status": "CANCELLED"
            }

        if not all(
            row["status"] in ("HOLD", "CONFIRMED")
            for row in reservations
        ):
            return None

        connection.execute("""
            UPDATE reservations
            SET status = 'CANCELLED'
            WHERE hold_id = ?
              AND status IN ('HOLD', 'CONFIRMED')
        """, (hold_id,))

        return {
            "hold_id": hold_id,
            "request_id": reservations[0]["request_id"],
            "origin_fog": reservations[0]["origin_fog"],
            "pile_ids": [
                row["pile_id"] for row in reservations
            ],
            "status": "CANCELLED"
        }


def activate_hold(hold_id: str):
    """
    Step 3 of V7 Protocol: Activate a confirmed reservation.
    Atomically transitions CONFIRMED reservation into an ACTIVE charging session
    and sets pile status to OCCUPIED.
    """
    with sqlite3.connect(DB_PATH, timeout=10) as connection:
        connection.row_factory = sqlite3.Row
        connection.execute("BEGIN IMMEDIATE")

        reservations = connection.execute("""
            SELECT hold_id, request_id, origin_fog,
                   pile_id, status
            FROM reservations
            WHERE hold_id = ?
            ORDER BY pile_id
        """, (hold_id,)).fetchall()

        if not reservations:
            return None

        # Idempotent check
        if all(row["status"] == "ACTIVE" for row in reservations):
            return {
                "hold_id": hold_id,
                "request_id": reservations[0]["request_id"],
                "origin_fog": reservations[0]["origin_fog"],
                "pile_ids": [row["pile_id"] for row in reservations],
                "status": "ACTIVE"
            }

        # Must be CONFIRMED to be activated
        if not all(row["status"] == "CONFIRMED" for row in reservations):
            return None

        pile_ids = [row["pile_id"] for row in reservations]

        connection.execute("""
            UPDATE reservations
            SET status = 'ACTIVE'
            WHERE hold_id = ? AND status = 'CONFIRMED'
        """, (hold_id,))

        for pid in pile_ids:
            connection.execute("""
                UPDATE piles
                SET status = 'OCCUPIED'
                WHERE pile_id = ?
            """, (pid,))

        return {
            "hold_id": hold_id,
            "request_id": reservations[0]["request_id"],
            "origin_fog": reservations[0]["origin_fog"],
            "pile_ids": pile_ids,
            "status": "ACTIVE"
        }


def complete_hold(hold_id: str):
    """
    Step 4 of V7 Protocol: Complete a charging session.
    Frees the pile (restoring AVAILABLE status) and marks reservation COMPLETED.
    """
    with sqlite3.connect(DB_PATH, timeout=10) as connection:
        connection.row_factory = sqlite3.Row
        connection.execute("BEGIN IMMEDIATE")

        reservations = connection.execute("""
            SELECT hold_id, request_id, origin_fog,
                   pile_id, status
            FROM reservations
            WHERE hold_id = ?
            ORDER BY pile_id
        """, (hold_id,)).fetchall()

        if not reservations:
            return None

        # Idempotent check
        if all(row["status"] == "COMPLETED" for row in reservations):
            return {
                "hold_id": hold_id,
                "request_id": reservations[0]["request_id"],
                "origin_fog": reservations[0]["origin_fog"],
                "pile_ids": [row["pile_id"] for row in reservations],
                "status": "COMPLETED"
            }

        # Can complete ACTIVE or CONFIRMED sessions
        if not all(row["status"] in ("ACTIVE", "CONFIRMED") for row in reservations):
            return None

        pile_ids = [row["pile_id"] for row in reservations]

        connection.execute("""
            UPDATE reservations
            SET status = 'COMPLETED'
            WHERE hold_id = ? AND status IN ('ACTIVE', 'CONFIRMED')
        """, (hold_id,))

        for pid in pile_ids:
            connection.execute("""
                UPDATE piles
                SET status = 'AVAILABLE'
                WHERE pile_id = ?
            """, (pid,))

        return {
            "hold_id": hold_id,
            "request_id": reservations[0]["request_id"],
            "origin_fog": reservations[0]["origin_fog"],
            "pile_ids": pile_ids,
            "status": "COMPLETED"
        }


def create_local_session(vehicle_id: str, required_power_kw: float = 22.0, station_id: str | None = None, fog_id: str = "fog-a"):
    """
    Scenario 1: Local communication between vehicle and its connected Fog.
    Verifies local pile availability directly on this Fog.
    If available, accepts request and immediately creates an ACTIVE local session.
    """
    now = datetime.now(timezone.utc)
    now_text = now.isoformat(timespec="seconds")
    session_expiry = (now + timedelta(hours=2)).isoformat(timespec="seconds")

    with sqlite3.connect(DB_PATH, timeout=10) as connection:
        connection.row_factory = sqlite3.Row
        connection.execute("BEGIN IMMEDIATE")

        # Expire old temporary holds first
        connection.execute("""
            UPDATE reservations
            SET status = 'EXPIRED'
            WHERE status = 'HOLD'
              AND julianday(expires_at) <= julianday(?)
        """, (now_text,))

        # Query local available pile
        query = """
            SELECT p.pile_id, p.station_id, p.power_kw
            FROM piles p
            WHERE p.status = 'AVAILABLE'
              AND p.is_reservable = 1
              AND NOT EXISTS (
                  SELECT 1
                  FROM reservations r
                  WHERE r.pile_id = p.pile_id
                    AND (
                        r.status IN ('CONFIRMED', 'ACTIVE')
                        OR (
                            r.status = 'HOLD'
                            AND julianday(r.expires_at) > julianday(?)
                        )
                    )
              )
        """
        params = [now_text]
        if station_id:
            query += " AND p.station_id = ?"
            params.append(station_id)

        query += " ORDER BY p.power_kw DESC LIMIT 1"

        available_pile = connection.execute(query, params).fetchone()

        if not available_pile:
            return None

        session_id = f"local-session-{uuid4()}"

        connection.execute("""
            INSERT INTO reservations (
                hold_id,
                request_id,
                origin_fog,
                pile_id,
                status,
                expires_at
            )
            VALUES (?, ?, ?, ?, 'ACTIVE', ?)
        """, (
            session_id,
            f"req-{vehicle_id}",
            fog_id,
            available_pile["pile_id"],
            session_expiry
        ))

        connection.execute("""
            UPDATE piles
            SET status = 'OCCUPIED'
            WHERE pile_id = ?
        """, (available_pile["pile_id"],))

        return {
            "session_id": session_id,
            "vehicle_id": vehicle_id,
            "fog_id": fog_id,
            "station_id": available_pile["station_id"],
            "pile_id": available_pile["pile_id"],
            "power_kw": available_pile["power_kw"],
            "status": "ACTIVE",
            "created_at": now_text
        }
