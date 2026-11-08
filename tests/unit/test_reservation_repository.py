
import sqlite3
from types import SimpleNamespace

import pytest

from fog.repositories import reservation_repository


@pytest.fixture
def temporary_db(tmp_path, monkeypatch):
    """
    Create an isolated SQLite database for each test.
    The real Fog databases are never modified.
    """
    db_path = tmp_path / "test_fog.db"

    monkeypatch.setattr(
        reservation_repository,
        "DB_PATH",
        db_path
    )

    with sqlite3.connect(db_path) as connection:
        connection.execute("""
            CREATE TABLE stations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                station_id TEXT NOT NULL UNIQUE,
                zone TEXT NOT NULL,
                status TEXT NOT NULL,
                power_kw REAL NOT NULL
            )
        """)

        connection.execute("""
            CREATE TABLE reservations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                hold_id TEXT NOT NULL,
                request_id TEXT NOT NULL,
                origin_fog TEXT NOT NULL,
                station_id TEXT NOT NULL,
                status TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        connection.executemany("""
            INSERT INTO stations (
                station_id, zone, status, power_kw
            )
            VALUES (?, ?, ?, ?)
        """, [
            ("A-01", "university", "AVAILABLE", 22.0),
            ("A-02", "university", "AVAILABLE", 22.0),
            ("A-03", "university", "OCCUPIED", 22.0),
        ])

    return db_path


def test_create_hold_success(temporary_db):
    request = SimpleNamespace(
        request_id="test-request-001",
        origin_fog="fog-b",
        required_stations=2,
        required_power_kw=40,
        ttl_seconds=120
    )

    result = reservation_repository.create_hold(request)

    assert result is not None
    assert result["request_id"] == "test-request-001"
    assert result["origin_fog"] == "fog-b"
    assert len(result["station_ids"]) == 2
    assert result["expires_at"] is not None

    with sqlite3.connect(temporary_db) as connection:
        rows = connection.execute("""
            SELECT station_id, status
            FROM reservations
            WHERE hold_id = ?
            ORDER BY station_id
        """, (result["hold_id"],)).fetchall()

    assert len(rows) == 2
    assert all(status == "HOLD" for _, status in rows)

def test_create_hold_is_idempotent(temporary_db):
    request = SimpleNamespace(
        request_id="test-request-002",
        origin_fog="fog-b",
        required_stations=2,
        required_power_kw=40,
        ttl_seconds=120
    )

    first_result = reservation_repository.create_hold(request)
    second_result = reservation_repository.create_hold(request)

    # Both calls must return the same reservation.
    assert first_result["hold_id"] == second_result["hold_id"]
    assert first_result["station_ids"] == second_result["station_ids"]

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
        required_stations=2,
        required_power_kw=40,
        ttl_seconds=120
    )

    hold_result = reservation_repository.create_hold(request)

    result = reservation_repository.confirm_hold(
        hold_result["hold_id"]
    )

    assert result is not None
    assert result["hold_id"] == hold_result["hold_id"]
    assert result["station_ids"] == hold_result["station_ids"]

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
        required_stations=2,
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
        required_stations=2,
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
        required_stations=2,
        required_power_kw=40,
        ttl_seconds=120
    )

    hold_result = reservation_repository.create_hold(request)
    hold_id = hold_result["hold_id"]

    result = reservation_repository.cancel_hold(hold_id)

    assert result is not None
    assert result["hold_id"] == hold_id
    assert result["status"] == "CANCELLED"
    assert result["station_ids"] == hold_result["station_ids"]

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
        required_stations=2,
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
        required_stations=2,
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
        required_stations=2,
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
        required_stations=2,
        required_power_kw=40,
        ttl_seconds=120
    )

    second_hold = reservation_repository.create_hold(second_request)

    assert second_hold is not None
    assert second_hold["hold_id"] != first_hold["hold_id"]
    assert set(second_hold["station_ids"]) == set(first_hold["station_ids"])

def test_confirmed_reservation_can_be_cancelled(temporary_db):
    request = SimpleNamespace(
        request_id="test-request-011",
        origin_fog="fog-b",
        required_stations=2,
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
    assert cancellation["station_ids"] == hold_result["station_ids"]

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
        required_stations=3,
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
