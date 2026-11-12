
import sqlite3
from types import SimpleNamespace

import pytest

from fog.repositories import reservation_repository


@pytest.fixture
def temporary_db(tmp_path, monkeypatch):
    """
    Create an isolated SQLite database using the current
    stations / piles / reservations architecture.
    """
    db_path = tmp_path / "test_fog.db"

    monkeypatch.setattr(
        reservation_repository,
        "DB_PATH",
        db_path
    )

    with sqlite3.connect(db_path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")

        connection.execute("""
            CREATE TABLE stations (
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

        connection.execute("""
            CREATE TABLE piles (
                pile_id TEXT PRIMARY KEY,
                station_id TEXT NOT NULL,
                power_kw REAL NOT NULL,
                pile_type TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'AVAILABLE',
                is_reservable INTEGER NOT NULL DEFAULT 1,
                FOREIGN KEY (station_id)
                    REFERENCES stations(station_id)
            )
        """)

        connection.execute("""
            CREATE TABLE reservations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                hold_id TEXT NOT NULL,
                request_id TEXT NOT NULL,
                origin_fog TEXT NOT NULL,
                pile_id TEXT NOT NULL,
                status TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (pile_id)
                    REFERENCES piles(pile_id)
            )
        """)

        connection.execute("""
            CREATE UNIQUE INDEX unique_active_pile_reservation
            ON reservations(pile_id)
            WHERE status IN ('HOLD', 'CONFIRMED')
        """)

        connection.execute("""
            INSERT INTO stations (
                station_id, longitude, latitude, fog_id
            )
            VALUES (?, ?, ?, ?)
        """, ("ST-01", 10.75, 34.74, "fog-a"))

        connection.executemany("""
            INSERT INTO piles (
                pile_id, station_id, power_kw,
                pile_type, status, is_reservable
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, [
            ("P-01", "ST-01", 22.0, "AC", "AVAILABLE", 1),
            ("P-02", "ST-01", 22.0, "AC", "AVAILABLE", 1),
            ("P-03", "ST-01", 22.0, "AC", "OCCUPIED", 1),
        ])

    return db_path


def test_create_hold_success(temporary_db):
    request = SimpleNamespace(
        request_id="test-request-001",
        origin_fog="fog-b",
        required_piles=2,
        required_power_kw=40,
        ttl_seconds=120
    )

    result = reservation_repository.create_hold(request)

    assert result is not None
    assert result["request_id"] == "test-request-001"
    assert result["origin_fog"] == "fog-b"
    assert len(result["pile_ids"]) == 2
    assert result["expires_at"] is not None

    with sqlite3.connect(temporary_db) as connection:
        rows = connection.execute("""
            SELECT pile_id, status
            FROM reservations
            WHERE hold_id = ?
            ORDER BY pile_id
        """, (result["hold_id"],)).fetchall()

    assert len(rows) == 2
    assert all(status == "HOLD" for _, status in rows)

def test_create_hold_is_idempotent(temporary_db):
    request = SimpleNamespace(
        request_id="test-request-002",
        origin_fog="fog-b",
        required_piles=2,
        required_power_kw=40,
        ttl_seconds=120
    )

    first_result = reservation_repository.create_hold(request)
    second_result = reservation_repository.create_hold(request)

    # Both calls must return the same reservation.
    assert first_result["hold_id"] == second_result["hold_id"]
    assert first_result["pile_ids"] == second_result["pile_ids"]

    with sqlite3.connect(temporary_db) as connection:
        count = connection.execute("""
            SELECT COUNT(*)
            FROM reservations
            WHERE request_id = ?
        """, (request.request_id,)).fetchone()[0]

    # Only two reservation rows must exist.
    assert count == 2

def test_confirm_hold_success(temporary_db):
    request = SimpleNamespace(
        request_id="test-request-003",
        origin_fog="fog-b",
        required_piles=2,
        required_power_kw=40,
        ttl_seconds=120
    )

    hold_result = reservation_repository.create_hold(request)

    result = reservation_repository.confirm_hold(
        hold_result["hold_id"]
    )

    assert result is not None
    assert result["hold_id"] == hold_result["hold_id"]
    assert result["pile_ids"] == hold_result["pile_ids"]

    with sqlite3.connect(temporary_db) as connection:
        rows = connection.execute("""
            SELECT status
            FROM reservations
            WHERE hold_id = ?
        """, (hold_result["hold_id"],)).fetchall()

    assert len(rows) == 2
    assert all(row[0] == "CONFIRMED" for row in rows)

def test_confirm_hold_is_idempotent(temporary_db):
    request = SimpleNamespace(
        request_id="test-request-004",
        origin_fog="fog-b",
        required_piles=2,
        required_power_kw=40,
        ttl_seconds=120
    )

    hold_result = reservation_repository.create_hold(request)
    hold_id = hold_result["hold_id"]

    first_confirmation = reservation_repository.confirm_hold(hold_id)
    second_confirmation = reservation_repository.confirm_hold(hold_id)

    assert first_confirmation == second_confirmation
    assert first_confirmation["hold_id"] == hold_id

    with sqlite3.connect(temporary_db) as connection:
        rows = connection.execute("""
            SELECT status
            FROM reservations
            WHERE hold_id = ?
        """, (hold_id,)).fetchall()

    assert len(rows) == 2
    assert all(row[0] == "CONFIRMED" for row in rows)

from datetime import datetime, timedelta, timezone


def test_expired_hold_cannot_be_confirmed(temporary_db):
    request = SimpleNamespace(
        request_id="test-request-005",
        origin_fog="fog-b",
        required_piles=2,
        required_power_kw=40,
        ttl_seconds=120
    )

    hold_result = reservation_repository.create_hold(request)
    hold_id = hold_result["hold_id"]

    # Force the expiration date to the past.
    expired_at = (
        datetime.now(timezone.utc) - timedelta(seconds=10)
    ).isoformat(timespec="seconds")

    with sqlite3.connect(temporary_db) as connection:
        connection.execute("""
            UPDATE reservations
            SET expires_at = ?
            WHERE hold_id = ?
        """, (expired_at, hold_id))

    result = reservation_repository.confirm_hold(hold_id)

    assert result is None

    with sqlite3.connect(temporary_db) as connection:
        rows = connection.execute("""
            SELECT status
            FROM reservations
            WHERE hold_id = ?
        """, (hold_id,)).fetchall()

    assert len(rows) == 2
    assert all(row[0] == "EXPIRED" for row in rows)

def test_cancel_hold_success(temporary_db):
    request = SimpleNamespace(
        request_id="test-request-006",
        origin_fog="fog-b",
        required_piles=2,
        required_power_kw=40,
        ttl_seconds=120
    )

    hold_result = reservation_repository.create_hold(request)
    hold_id = hold_result["hold_id"]

    result = reservation_repository.cancel_hold(hold_id)

    assert result is not None
    assert result["hold_id"] == hold_id
    assert result["status"] == "CANCELLED"
    assert result["pile_ids"] == hold_result["pile_ids"]

    with sqlite3.connect(temporary_db) as connection:
        rows = connection.execute("""
            SELECT status
            FROM reservations
            WHERE hold_id = ?
        """, (hold_id,)).fetchall()

    assert len(rows) == 2
    assert all(row[0] == "CANCELLED" for row in rows)

def test_cancel_hold_is_idempotent(temporary_db):
    request = SimpleNamespace(
        request_id="test-request-007",
        origin_fog="fog-b",
        required_piles=2,
        required_power_kw=40,
        ttl_seconds=120
    )

    hold_result = reservation_repository.create_hold(request)
    hold_id = hold_result["hold_id"]

    first_cancellation = reservation_repository.cancel_hold(hold_id)
    second_cancellation = reservation_repository.cancel_hold(hold_id)

    assert first_cancellation == second_cancellation
    assert first_cancellation["status"] == "CANCELLED"

    with sqlite3.connect(temporary_db) as connection:
        rows = connection.execute("""
            SELECT status
            FROM reservations
            WHERE hold_id = ?
        """, (hold_id,)).fetchall()

    assert len(rows) == 2
    assert all(row[0] == "CANCELLED" for row in rows)

def test_cancelled_hold_cannot_be_confirmed(temporary_db):
    request = SimpleNamespace(
        request_id="test-request-008",
        origin_fog="fog-b",
        required_piles=2,
        required_power_kw=40,
        ttl_seconds=120
    )

    hold_result = reservation_repository.create_hold(request)
    hold_id = hold_result["hold_id"]

    cancellation = reservation_repository.cancel_hold(hold_id)

    assert cancellation["status"] == "CANCELLED"

    confirmation = reservation_repository.confirm_hold(hold_id)

    assert confirmation is None

    with sqlite3.connect(temporary_db) as connection:
        rows = connection.execute("""
            SELECT status
            FROM reservations
            WHERE hold_id = ?
        """, (hold_id,)).fetchall()

    assert len(rows) == 2
    assert all(row[0] == "CANCELLED" for row in rows)

def test_cancelled_stations_can_be_reserved_again(temporary_db):
    first_request = SimpleNamespace(
        request_id="test-request-009",
        origin_fog="fog-b",
        required_piles=2,
        required_power_kw=40,
        ttl_seconds=120
    )

    first_hold = reservation_repository.create_hold(first_request)
    assert first_hold is not None

    # Cancel the first reservation.
    cancellation = reservation_repository.cancel_hold(
        first_hold["hold_id"]
    )
    assert cancellation["status"] == "CANCELLED"

    # A new user requests the same resources.
    second_request = SimpleNamespace(
        request_id="test-request-010",
        origin_fog="fog-c",
        required_piles=2,
        required_power_kw=40,
        ttl_seconds=120
    )

    second_hold = reservation_repository.create_hold(second_request)

    assert second_hold is not None
    assert second_hold["hold_id"] != first_hold["hold_id"]
    assert set(second_hold["pile_ids"]) == set(first_hold["pile_ids"])

def test_confirmed_reservation_can_be_cancelled(temporary_db):
    request = SimpleNamespace(
        request_id="test-request-011",
        origin_fog="fog-b",
        required_piles=2,
        required_power_kw=40,
        ttl_seconds=120
    )

    # Create and confirm the reservation.
    hold_result = reservation_repository.create_hold(request)
    hold_id = hold_result["hold_id"]

    confirmation = reservation_repository.confirm_hold(hold_id)
    assert confirmation is not None

    # Cancel the confirmed reservation.
    cancellation = reservation_repository.cancel_hold(hold_id)

    assert cancellation is not None
    assert cancellation["status"] == "CANCELLED"
    assert cancellation["pile_ids"] == hold_result["pile_ids"]

    with sqlite3.connect(temporary_db) as connection:
        rows = connection.execute("""
            SELECT status
            FROM reservations
            WHERE hold_id = ?
        """, (hold_id,)).fetchall()

    assert len(rows) == 2
    assert all(row[0] == "CANCELLED" for row in rows)

def test_create_hold_fails_when_capacity_is_insufficient(temporary_db):
    request = SimpleNamespace(
        request_id="test-request-012",
        origin_fog="fog-b",
        required_piles=3,
        required_power_kw=60,
        ttl_seconds=120
    )

    result = reservation_repository.create_hold(request)

    assert result is None

    with sqlite3.connect(temporary_db) as connection:
        count = connection.execute("""
            SELECT COUNT(*)
            FROM reservations
            WHERE request_id = ?
        """, (request.request_id,)).fetchone()[0]

    assert count == 0

def test_confirm_nonexistent_hold_returns_none(temporary_db):
    result = reservation_repository.confirm_hold(
        "nonexistent-hold-id"
    )

    assert result is None

    with sqlite3.connect(temporary_db) as connection:
        count = connection.execute("""
            SELECT COUNT(*)
            FROM reservations
        """).fetchone()[0]

    assert count == 0

def test_cancel_nonexistent_hold_returns_none(temporary_db):
    result = reservation_repository.cancel_hold(
        "nonexistent-hold-id"
    )

    assert result is None

    with sqlite3.connect(temporary_db) as connection:
        count = connection.execute("""
            SELECT COUNT(*)
            FROM reservations
        """).fetchone()[0]

    assert count == 0
