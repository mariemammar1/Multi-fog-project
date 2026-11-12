
import sqlite3
from datetime import datetime, timezone

DB_PATH = "data/fog_a.db"

with sqlite3.connect(DB_PATH) as connection:
    connection.execute("BEGIN IMMEDIATE")

    try:
        now = datetime.now(timezone.utc)

        # Temporarily clean expired HOLD reservations
        rows = connection.execute("""
            SELECT hold_id, expires_at
            FROM reservations
            WHERE station_id = 'A-01'
              AND status = 'HOLD'
        """).fetchall()

        for hold_id, expires_at in rows:
            expiration = datetime.fromisoformat(expires_at)

            if expiration <= now:
                connection.execute("""
                    UPDATE reservations
                    SET status = 'EXPIRED'
                    WHERE hold_id = ?
                      AND station_id = 'A-01'
                """, (hold_id,))

        # First active reservation: should succeed
        connection.execute("""
            INSERT INTO reservations (
                hold_id, request_id, origin_fog,
                station_id, status, expires_at
            )
            VALUES (
                'TEST-HOLD-1', 'TEST-REQ-1', 'fog-b',
                'A-01', 'HOLD', '2099-01-01T00:00:00'
            )
        """)

        print("SUCCESS: First HOLD inserted.")

        try:
            # Second active reservation: must be rejected
            connection.execute("""
                INSERT INTO reservations (
                    hold_id, request_id, origin_fog,
                    station_id, status, expires_at
                )
                VALUES (
                    'TEST-HOLD-2', 'TEST-REQ-2', 'fog-c',
                    'A-01', 'CONFIRMED', '2099-01-01T00:00:00'
                )
            """)

            print("ERROR: Duplicate reservation was accepted!")

        except sqlite3.IntegrityError as error:
            print("SUCCESS: Duplicate reservation rejected.")
            print("Reason:", error)

    finally:
        connection.rollback()
        print("Test transaction rolled back.")
