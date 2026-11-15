"""
Unit and API-level tests for Scenarios S1, S4, S6, and S7 in Multi-Fog EV.
Tests call the FastAPI route endpoints directly in-process with isolated SQLite databases.
No background processes or port binding required.
"""

import sqlite3
import uuid
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

import fog.database
from fog.api.cooperation import receive_help_request
from fog.api.reservations import (
    activate_reservation,
    cancel_reservation,
    complete_reservation,
    confirm_reservation,
    create_local_charging_session,
    reserve_stations,
)
from fog.repositories import pile_repository, reservation_repository
import fog.services.cooperation_service as cooperation_service
from fog.services.peer_communication_service import send_help_request_to_peers
import fog.services.reservation_service as reservation_service
import fog.settings
from shared.schemas import (
    ActivateRequest,
    CompleteRequest,
    ConfirmRequest,
    HelpRequest,
    HoldRequest,
    LocalSessionRequest,
)

FOG_ID = "fog-a"


@pytest.fixture
def isolated_db(tmp_path, monkeypatch):
    """
    Create an isolated SQLite database with the full V7 schema.
    Monkeypatches DB_PATH across settings, database, services, and repositories.
    """
    db_path = tmp_path / "test_fog_v7.db"

    # Patch paths
    monkeypatch.setattr(fog.settings, "DB_PATH", db_path)
    monkeypatch.setattr(fog.database, "DB_PATH", db_path)
    monkeypatch.setattr(reservation_repository, "DB_PATH", db_path)
    monkeypatch.setattr(pile_repository, "DB_PATH", db_path)

    # Patch Fog ID
    monkeypatch.setattr(fog.settings, "FOG_ID", FOG_ID)
    monkeypatch.setattr(reservation_service, "FOG_ID", FOG_ID)
    monkeypatch.setattr(cooperation_service, "FOG_ID", FOG_ID)

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")

    conn.execute("""
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

    conn.execute("""
        CREATE TABLE piles (
            pile_id TEXT PRIMARY KEY,
            station_id TEXT NOT NULL,
            power_kw REAL NOT NULL,
            pile_type TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'AVAILABLE',
            is_reservable INTEGER NOT NULL DEFAULT 1,
            FOREIGN KEY (station_id) REFERENCES stations(station_id)
        )
    """)

    conn.execute("""
        CREATE TABLE reservations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hold_id TEXT NOT NULL,
            request_id TEXT NOT NULL,
            origin_fog TEXT NOT NULL,
            pile_id TEXT NOT NULL,
            status TEXT NOT NULL CHECK (
                status IN (
                    'HOLD', 'CONFIRMED', 'ACTIVE',
                    'COMPLETED', 'CANCELLED', 'EXPIRED'
                )
            ),
            expires_at TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (pile_id) REFERENCES piles(pile_id)
        )
    """)

    conn.execute("""
        CREATE UNIQUE INDEX unique_active_pile_reservation
        ON reservations(pile_id)
        WHERE status IN ('HOLD', 'CONFIRMED', 'ACTIVE')
    """)

    # Seed 1 station + 5 DC piles of 50 kW each
    conn.execute(
        "INSERT INTO stations (station_id, longitude, latitude, fog_id) VALUES (?, ?, ?, ?)",
        ("ST-01", 10.75, 34.74, FOG_ID),
    )
    conn.executemany(
        "INSERT INTO piles (pile_id, station_id, power_kw, pile_type, status, is_reservable) VALUES (?, ?, ?, ?, ?, ?)",
        [
            (f"P-0{i}", "ST-01", 50.0, "DC", "AVAILABLE", 1)
            for i in range(1, 6)
        ],
    )
    conn.commit()
    conn.close()

    return db_path


# ===========================================================================
# Scénario 1 — Communication locale entre un véhicule et son Fog
# ===========================================================================

class TestScenario1LocalSession:

    def test_s1_local_session_creates_active_session(self, isolated_db):
        """
        Vehicle directly requests charge on its local Fog.
        Borne disponible -> Fog A accepts and immediately creates an ACTIVE session.
        """
        request = LocalSessionRequest(vehicle_id="EV-101", required_power_kw=22.0)
        response = create_local_charging_session(request)

        assert response["status"] == "ACTIVE"
        assert response["vehicle_id"] == "EV-101"
        assert response["fog_id"] == FOG_ID
        assert response["station_id"] == "ST-01"
        assert response["pile_id"] in ["P-01", "P-02", "P-03", "P-04", "P-05"]

        # Verify pile is OCCUPIED in database
        conn = sqlite3.connect(isolated_db)
        pile_status = conn.execute(
            "SELECT status FROM piles WHERE pile_id = ?", (response["pile_id"],)
        ).fetchone()[0]
        conn.close()
        assert pile_status == "OCCUPIED"

    def test_s1_completes_and_releases_pile(self, isolated_db):
        """
        When a local charging session completes, the pile is restored to AVAILABLE.
        """
        request = LocalSessionRequest(vehicle_id="EV-102", required_power_kw=22.0)
        session = create_local_charging_session(request)
        session_id = session["session_id"]
        pile_id = session["pile_id"]

        comp_req = CompleteRequest(hold_id=session_id)
        comp_resp = complete_reservation(comp_req)
        assert comp_resp["status"] == "COMPLETED"

        # Verify pile is AVAILABLE in database
        conn = sqlite3.connect(isolated_db)
        pile_status = conn.execute(
            "SELECT status FROM piles WHERE pile_id = ?", (pile_id,)
        ).fetchone()[0]
        conn.close()
        assert pile_status == "AVAILABLE"

    def test_s1_no_inter_fog_network_calls(self, isolated_db):
        """
        Rule S1: Fog A must never contact other Fogs for local vehicle requests.
        """
        with patch("httpx.post") as mock_post:
            request = LocalSessionRequest(vehicle_id="EV-103", required_power_kw=22.0)
            response = create_local_charging_session(request)
            assert response["status"] == "ACTIVE"
            mock_post.assert_not_called()

    def test_s1_full_capacity_returns_409(self, isolated_db):
        """
        If all local piles are occupied, local request fails with 409 Conflict.
        """
        conn = sqlite3.connect(isolated_db)
        conn.execute("UPDATE piles SET status = 'OCCUPIED'")
        conn.commit()
        conn.close()

        request = LocalSessionRequest(vehicle_id="EV-104", required_power_kw=22.0)
        with pytest.raises(HTTPException) as exc_info:
            create_local_charging_session(request)
        assert exc_info.value.status_code == 409


# ===========================================================================
# Scénario 4 — Transfert et activation des sessions distantes (V7 Complet)
# Protocol: HOLD -> CONFIRM -> ACTIVATE -> COMPLETED
# ===========================================================================

class TestScenario4LifecycleV7:

    def test_s4_full_lifecycle_success(self, isolated_db):
        """
        Tests complete 4-step protocol:
        1. HOLD: temporary reservation created
        2. CONFIRM: reservation confirmed
        3. ACTIVATE: session starts, piles become OCCUPIED
        4. COMPLETED: charge finishes, piles released to AVAILABLE
        """
        # Step 1: HOLD
        hold_req = HoldRequest(
            request_id="req-s4-001",
            origin_fog="fog-b",
            required_piles=2,
            required_power_kw=80.0,
            ttl_seconds=120,
        )
        hold_resp = reserve_stations(hold_req)
        assert hold_resp["status"] == "HOLD"
        hold_id = hold_resp["hold_id"]
        pile_ids = hold_resp["pile_ids"]
        assert len(pile_ids) == 2

        # Step 2: CONFIRM
        confirm_req = ConfirmRequest(hold_id=hold_id)
        confirm_resp = confirm_reservation(confirm_req)
        assert confirm_resp["status"] == "CONFIRMED"

        # Step 3: ACTIVATE
        activate_req = ActivateRequest(hold_id=hold_id)
        activate_resp = activate_reservation(activate_req)
        assert activate_resp["status"] == "ACTIVE"

        conn = sqlite3.connect(isolated_db)
        for pid in pile_ids:
            st = conn.execute("SELECT status FROM piles WHERE pile_id = ?", (pid,)).fetchone()[0]
            assert st == "OCCUPIED", f"Pile {pid} should be OCCUPIED after ACTIVATE"
        conn.close()

        # Step 4: COMPLETED
        comp_req = CompleteRequest(hold_id=hold_id)
        comp_resp = complete_reservation(comp_req)
        assert comp_resp["status"] == "COMPLETED"

        conn = sqlite3.connect(isolated_db)
        for pid in pile_ids:
            st = conn.execute("SELECT status FROM piles WHERE pile_id = ?", (pid,)).fetchone()[0]
            assert st == "AVAILABLE", f"Pile {pid} should be AVAILABLE after COMPLETED"
        conn.close()

    def test_s4_cannot_activate_unconfirmed_hold(self, isolated_db):
        """
        Cannot ACTIVATE directly from HOLD without prior CONFIRM.
        """
        hold_req = HoldRequest(
            request_id="req-s4-002",
            origin_fog="fog-b",
            required_piles=1,
            required_power_kw=40.0,
        )
        hold_resp = reserve_stations(hold_req)
        hold_id = hold_resp["hold_id"]

        with pytest.raises(HTTPException) as exc_info:
            activate_reservation(ActivateRequest(hold_id=hold_id))
        assert exc_info.value.status_code == 409

    def test_s4_activate_is_idempotent(self, isolated_db):
        """
        Re-activating an already ACTIVE reservation succeeds idempotently.
        """
        hold_req = HoldRequest(
            request_id="req-s4-003",
            origin_fog="fog-b",
            required_piles=1,
            required_power_kw=40.0,
        )
        hold_id = reserve_stations(hold_req)["hold_id"]
        confirm_reservation(ConfirmRequest(hold_id=hold_id))

        first_act = activate_reservation(ActivateRequest(hold_id=hold_id))
        assert first_act["status"] == "ACTIVE"

        second_act = activate_reservation(ActivateRequest(hold_id=hold_id))
        assert second_act["status"] == "ACTIVE"

    def test_s4_complete_is_idempotent(self, isolated_db):
        """
        Re-completing an already COMPLETED reservation succeeds idempotently.
        """
        hold_req = HoldRequest(
            request_id="req-s4-004",
            origin_fog="fog-b",
            required_piles=1,
            required_power_kw=40.0,
        )
        hold_id = reserve_stations(hold_req)["hold_id"]
        confirm_reservation(ConfirmRequest(hold_id=hold_id))
        activate_reservation(ActivateRequest(hold_id=hold_id))

        first_comp = complete_reservation(CompleteRequest(hold_id=hold_id))
        assert first_comp["status"] == "COMPLETED"

        second_comp = complete_reservation(CompleteRequest(hold_id=hold_id))
        assert second_comp["status"] == "COMPLETED"

    def test_s4_cannot_double_hold_same_piles(self, isolated_db):
        """
        When all 5 piles are held, a second HOLD must fail with 409.
        """
        first_hold = reserve_stations(HoldRequest(
            request_id="req-s4-full",
            origin_fog="fog-b",
            required_piles=5,
            required_power_kw=200.0,
        ))
        assert first_hold["status"] == "HOLD"

        with pytest.raises(HTTPException) as exc_info:
            reserve_stations(HoldRequest(
                request_id="req-s4-overflow",
                origin_fog="fog-c",
                required_piles=1,
                required_power_kw=20.0,
            ))
        assert exc_info.value.status_code == 409


# ===========================================================================
# Scénario 6 — Saturation de tous les Fogs
# ===========================================================================

class TestScenario6Saturation:

    def test_s6_local_saturated_fog_declines_peer_request(self, isolated_db):
        """
        When this Fog is 100% occupied, receiving a HELP_REQUEST returns DECLINE.
        """
        conn = sqlite3.connect(isolated_db)
        conn.execute("UPDATE piles SET status = 'OCCUPIED'")
        conn.commit()
        conn.close()

        req = HelpRequest(
            request_id="req-s6-001",
            origin_fog="fog-b",
            required_piles=2,
            required_power_kw=80.0,
        )
        response = receive_help_request(req)
        assert response["status"] == "DECLINE"
        assert "insufficient" in response["reason"].lower()

    def test_s6_all_fogs_saturated_no_cooperation_created(self, isolated_db):
        """
        When all peers decline, no proposal is selected and no HOLD is created.
        Vehicles remain unserved with 0 ghost charge sessions.
        """
        fake_decline = MagicMock()
        fake_decline.status_code = 200
        fake_decline.json.return_value = {
            "request_id": "req-s6-peers",
            "origin_fog": FOG_ID,
            "proposer_fog": "fog-b",
            "zone": "shopping_center",
            "status": "DECLINE",
            "available_piles": 0,
            "available_power_kw": 0.0,
            "reason": "Insufficient available piles or power.",
        }
        fake_decline.raise_for_status = MagicMock()

        with patch("httpx.post", return_value=fake_decline):
            request = HelpRequest(
                request_id="req-s6-local",
                origin_fog=FOG_ID,
                required_piles=2,
                required_power_kw=80.0,
            )
            result = send_help_request_to_peers(request)

        assert result["selected_proposal"] is None
        assert result["hold"] is None


# ===========================================================================
# Scénario 7 — Prédiction ML et Coopération Réactive
# ===========================================================================

class TestScenario7MLPredictionReadOnly:

    def test_s7_prediction_query_does_not_modify_reservations(self, isolated_db):
        """
        Calling ML prediction query does not reserve piles or create holds prematurely.
        The DB must remain strictly unmodified.
        """
        conn = sqlite3.connect(isolated_db)
        piles_before = conn.execute("SELECT pile_id, status FROM piles ORDER BY pile_id").fetchall()
        res_count_before = conn.execute("SELECT COUNT(*) FROM reservations").fetchone()[0]
        conn.close()

        # Check capacity calculation - pure read-only operation
        capacity = pile_repository.get_pile_capacity()
        assert capacity["available_piles"] == 5

        conn = sqlite3.connect(isolated_db)
        piles_after = conn.execute("SELECT pile_id, status FROM piles ORDER BY pile_id").fetchall()
        res_count_after = conn.execute("SELECT COUNT(*) FROM reservations").fetchone()[0]
        conn.close()

        assert piles_before == piles_after
        assert res_count_before == res_count_after
