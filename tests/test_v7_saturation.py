"""
Scenario 6: Saturation de tous les Fogs (V7 Saturation Test)
Fichier requis: tests/test_v7_saturation.py

Objectif :
Vérifier qu'aucune recharge fictive n'est créée lorsque tous les Fogs sont saturés.
Exemple du cahier des charges :
- Fog A : 20/20 bornes occupées.
- Fog B : 20/20 bornes occupées.
- Fog C : 20/20 bornes occupées.
- De nouveaux véhicules arrivent sur Fog B.
- Fog B consulte les autres Fogs.
- Aucun Fog ne peut accepter les demandes.
- Les véhicules restent non servis au niveau du réseau.
- Aucune coopération possible : 0 session ou réservation fictive créée.
"""

import sqlite3
import uuid
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

import fog.database
from fog.api.cooperation import receive_help_request
from fog.api.reservations import create_local_charging_session, reserve_stations
from fog.repositories import pile_repository, reservation_repository
import fog.services.cooperation_service as cooperation_service
from fog.services.peer_communication_service import send_help_request_to_peers
import fog.services.reservation_service as reservation_service
import fog.settings
from shared.schemas import HelpRequest, HoldRequest, LocalSessionRequest
from simulator.orchestrator import FogNodeState, RoundOrchestrator


@pytest.fixture
def saturated_local_fog(tmp_path, monkeypatch):
    """
    Sets up Fog B with 20 piles, all marked OCCUPIED (20/20 capacity).
    """
    db_path = tmp_path / "fog_b_saturated.db"
    fog_id = "fog-b"

    monkeypatch.setattr(fog.settings, "DB_PATH", db_path)
    monkeypatch.setattr(fog.database, "DB_PATH", db_path)
    monkeypatch.setattr(reservation_repository, "DB_PATH", db_path)
    monkeypatch.setattr(pile_repository, "DB_PATH", db_path)
    monkeypatch.setattr(fog.settings, "FOG_ID", fog_id)
    monkeypatch.setattr(reservation_service, "FOG_ID", fog_id)
    monkeypatch.setattr(cooperation_service, "FOG_ID", fog_id)

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

    conn.execute(
        "INSERT INTO stations (station_id, longitude, latitude, fog_id) VALUES (?, ?, ?, ?)",
        ("ST-B01", 10.75, 34.74, fog_id),
    )

    # Insert 20 piles, ALL OCCUPIED (20/20)
    for i in range(1, 21):
        conn.execute(
            "INSERT INTO piles (pile_id, station_id, power_kw, pile_type, status, is_reservable) VALUES (?, ?, ?, ?, ?, ?)",
            (f"PB-{i:02d}", "ST-B01", 50.0, "DC", "OCCUPIED", 1),
        )

    conn.commit()
    conn.close()

    return db_path


def test_saturated_fog_refuses_local_charge(saturated_local_fog):
    """
    Fog B has 20/20 occupied bornes.
    A new vehicle arrives locally and requests charge.
    Fog B must refuse locally (409) and create NO session.
    """
    conn = sqlite3.connect(saturated_local_fog)
    res_before = conn.execute("SELECT COUNT(*) FROM reservations").fetchone()[0]
    conn.close()

    req = LocalSessionRequest(vehicle_id="EV-SAT-01", required_power_kw=22.0)
    with pytest.raises(HTTPException) as exc_info:
        create_local_charging_session(req)
    assert exc_info.value.status_code == 409

    # Verify zero ghost sessions were created
    conn = sqlite3.connect(saturated_local_fog)
    res_after = conn.execute("SELECT COUNT(*) FROM reservations").fetchone()[0]
    conn.close()
    assert res_before == res_after == 0


def test_saturated_fog_refuses_incoming_help(saturated_local_fog):
    """
    Fog B is saturated (20/20). Another Fog asks Fog B for help.
    Fog B must DECLINE the request.
    """
    req = HelpRequest(
        request_id="req-help-sat",
        origin_fog="fog-a",
        required_piles=2,
        required_power_kw=44.0,
    )
    resp = receive_help_request(req)
    assert resp["status"] == "DECLINE"
    assert "insufficient" in resp["reason"].lower()


def test_peer_negotiation_when_all_peers_saturated(saturated_local_fog):
    """
    Fog B is saturated. It asks Fog A and Fog C for help.
    Both Fog A and Fog C return DECLINE (they are also 20/20 saturated).
    Fog B creates NO HOLD, NO reservation, and NO ghost charging session.
    """
    conn = sqlite3.connect(saturated_local_fog)
    res_before = conn.execute("SELECT COUNT(*) FROM reservations").fetchone()[0]
    conn.close()

    # Peers A and C both respond DECLINE
    def mock_post(url, json, timeout):
        peer = "fog-a" if "8001" in str(url) or "fog-a" in str(url) else "fog-c"
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "request_id": json["request_id"],
            "origin_fog": "fog-b",
            "proposer_fog": peer,
            "zone": "mock_zone",
            "status": "DECLINE",
            "available_piles": 0,
            "available_power_kw": 0.0,
            "reason": "Insufficient available piles or power (20/20 saturated).",
        }
        mock_resp.raise_for_status = MagicMock()
        return mock_resp

    with patch("httpx.post", side_effect=mock_post):
        req = HelpRequest(
            request_id="req-peer-sat",
            origin_fog="fog-b",
            required_piles=2,
            required_power_kw=44.0,
        )
        negotiation = send_help_request_to_peers(req)

    # Verification: no proposal chosen, no hold created
    assert negotiation["selected_proposal"] is None
    assert negotiation["hold"] is None
    assert len(negotiation["responses"]) == 2
    for r in negotiation["responses"]:
        assert r["status"] == "DECLINE"

    # Zero ghost reservations created
    conn = sqlite3.connect(saturated_local_fog)
    res_after = conn.execute("SELECT COUNT(*) FROM reservations").fetchone()[0]
    conn.close()
    assert res_after == res_before == 0


def test_orchestrator_global_saturation_zero_ghost_sessions():
    """
    Scenario 6 orchestrated multi-fog test:
    - Fog A : 20/20 bornes occupées.
    - Fog B : 20/20 bornes occupées.
    - Fog C : 20/20 bornes occupées.
    - New vehicles arrive on Fog B.
    - Result: 0 ghost sessions created, all new vehicles remain unserved at network level.
    """
    fogs = {
        "fog-a": FogNodeState("fog-a", total_piles=20, occupied_piles=20),
        "fog-b": FogNodeState("fog-b", total_piles=20, occupied_piles=20),
        "fog-c": FogNodeState("fog-c", total_piles=20, occupied_piles=20),
    }

    orch = RoundOrchestrator(fogs)

    # 3 vehicles arrive at Fog B
    round_result = orch.run_round(
        arrivals={"fog-b": ["EV-B1", "EV-B2", "EV-B3"]},
        completions={},
    )

    # No cooperation possible
    assert round_result["cooperation_triggered"] is False
    assert len(round_result["transfers"]) == 0

    # 3 vehicles remain unserved
    assert round_result["total_unserved"] == 3
    assert round_result["unserved"]["fog-b"] == ["EV-B1", "EV-B2", "EV-B3"]

    # All fogs remain at 20/20 - absolutely NO ghost charging sessions created
    for fog_id, fog in fogs.items():
        assert fog.occupied == 20
        assert fog.available_piles == 0
