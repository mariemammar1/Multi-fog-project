import sqlite3
import pytest
from pathlib import Path

DB_PATH = Path("data/fog_a.db")


def test_unique_active_pile_constraint():
    """
    Verifies that the unique index prevents duplicate active reservations
    (HOLD, CONFIRMED, ACTIVE) on the same pile.
    """
    if not DB_PATH.exists():
        pytest.skip("data/fog_a.db does not exist")

    with sqlite3.connect(DB_PATH) as connection:
        connection.execute("BEGIN IMMEDIATE")
        try:
            pile = connection.execute("SELECT pile_id FROM piles LIMIT 1").fetchone()
            if not pile:
                pytest.skip("No piles in database")
            pile_id = pile[0]

            # First active reservation: should succeed
            connection.execute("""
                INSERT INTO reservations (
                    hold_id, request_id, origin_fog,
                    pile_id, status, expires_at
                )
                VALUES (
                    'TEST-HOLD-1', 'TEST-REQ-1', 'fog-b',
                    ?, 'HOLD', '2099-01-01T00:00:00'
                )
            """, (pile_id,))

            # Second active reservation on the same pile: must fail
            with pytest.raises(sqlite3.IntegrityError):
                connection.execute("""
                    INSERT INTO reservations (
                        hold_id, request_id, origin_fog,
                        pile_id, status, expires_at
                    )
                    VALUES (
                        'TEST-HOLD-2', 'TEST-REQ-2', 'fog-c',
                        ?, 'CONFIRMED', '2099-01-01T00:00:00'
                    )
                """, (pile_id,))

        finally:
            connection.rollback()
