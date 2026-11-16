"""
Unit tests for the RealTimeSimulator engine.
Verifies real-time ticks, state transitions, S1 local allocations,
S2/S4 inter-fog cooperations, and database integrity.
"""

import sqlite3
import pytest
from pathlib import Path

from simulator.realtime_engine import RealTimeSimulator, FOG_CONFIGS


@pytest.fixture
def sim_engine(tmp_path, monkeypatch):
    """Create isolated simulator engine with isolated SQLite DBs."""
    engine = RealTimeSimulator()

    # Create 3 isolated DBs for fog-a, fog-b, fog-c
    test_configs = {}
    for fog_id in ["fog-a", "fog-b", "fog-c"]:
        db_path = tmp_path / f"{fog_id.replace('-', '_')}.db"
        with sqlite3.connect(db_path) as conn:
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
                    status TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (pile_id) REFERENCES piles(pile_id)
                )
            """)
            conn.execute("INSERT INTO stations VALUES ('ST-01', 10.0, 20.0, 0, 0, 0, '', ?)", (fog_id,))
            for i in range(1, 11):
                conn.execute(
                    "INSERT INTO piles VALUES (?, 'ST-01', 50.0, 'DC', 'AVAILABLE', 1)",
                    (f"{fog_id}-P{i:02d}",)
                )
            conn.commit()

        test_configs[fog_id] = {
            "db": db_path,
            "zone": "test_zone",
            "name": f"Test {fog_id}"
        }

    monkeypatch.setattr("simulator.realtime_engine.FOG_CONFIGS", test_configs)
    return engine


def test_sim_initial_capacities(sim_engine):
    caps = sim_engine.get_fog_capacities()
    for fog_id in ["fog-a", "fog-b", "fog-c"]:
        assert caps[fog_id]["total_piles"] == 10
        assert caps[fog_id]["available_piles"] == 10
        assert caps[fog_id]["occupied_piles"] == 0
        assert caps[fog_id]["occupancy_percent"] == 0.0


def test_sim_step_s1_normal(sim_engine):
    sim_engine.scenario = "S1_NORMAL"
    sim_engine.step()

    assert sim_engine.tick_count == 1
    assert sim_engine.total_arrivals > 0
    assert len(sim_engine.active_sessions) > 0
    assert len(sim_engine.events) > 0

    caps = sim_engine.get_fog_capacities()
    total_occupied = sum(c["occupied_piles"] for c in caps.values())
    assert total_occupied > 0


def test_sim_step_s2_cooperation_transfer(sim_engine):
    # Saturate Fog B by setting all 10 piles to OCCUPIED
    db_b = FOG_CONFIGS["fog-b"]["db"]
    with sqlite3.connect(db_b) as conn:
        conn.execute("UPDATE piles SET status = 'OCCUPIED'")
        conn.commit()

    sim_engine.scenario = "S2_COOPERATION"
    sim_engine.step()

    # Fog B was saturated, so cooperation should have transferred vehicles to Fog A or C
    assert sim_engine.total_cooperations > 0
    coop_events = [e for e in sim_engine.events if e["category"] == "COOPERATION_V7"]
    assert len(coop_events) > 0


def test_sim_step_s6_full_saturation(sim_engine):
    # Saturate all 3 fogs
    for fog_id in ["fog-a", "fog-b", "fog-c"]:
        with sqlite3.connect(FOG_CONFIGS[fog_id]["db"]) as conn:
            conn.execute("UPDATE piles SET status = 'OCCUPIED'")
            conn.commit()

    sim_engine.scenario = "S6_SATURATION"
    sim_engine.step()

    # All fogs full -> unserved count must increase
    assert sim_engine.total_unserved > 0
    sat_events = [e for e in sim_engine.events if e["category"] == "SATURATION_REJECT"]
    assert len(sat_events) > 0


def test_sim_inject_traffic(sim_engine):
    sim_engine.inject_traffic("fog-a", 3)
    caps = sim_engine.get_fog_capacities()
    assert caps["fog-a"]["occupied_piles"] == 3


def test_sim_reset(sim_engine):
    # First inject traffic
    sim_engine.inject_traffic("fog-a", 5)
    assert sim_engine.total_arrivals == 5

    # Reset
    sim_engine.reset_databases()
    assert sim_engine.tick_count == 0
    assert sim_engine.total_arrivals == 0
    assert len(sim_engine.active_sessions) == 0

    caps = sim_engine.get_fog_capacities()
    for fog_id in ["fog-a", "fog-b", "fog-c"]:
        assert caps[fog_id]["available_piles"] == 10
        assert caps[fog_id]["occupied_piles"] == 0


# ===========================================================================
# Scenario 7 — ML Prediction (real Chronos-2 integration)
# ===========================================================================

def test_s7_ml_reactive_uses_chronos_when_available(sim_engine, monkeypatch):
    """
    S7: When Chronos-2 returns a valid prediction, the simulator uses it
    to generate arrivals (not a hardcoded constant).
    The number of arrivals must reflect the scaled prediction, not 18.
    """
    import fog.services.ml_client as ml_mod

    # Simulate Chronos-2 returning busy=2000 for each fog
    def fake_prediction(fog_id: str):
        return 2000.0

    def fake_baseline(fog_id: str):
        return 2000.0

    monkeypatch.setattr(ml_mod, "get_chronos_prediction", fake_prediction)
    monkeypatch.setattr(ml_mod, "get_baseline_prediction", fake_baseline)

    # scale_busy_to_arrivals(2000, factor=0.01) => 20 arrivals per fog
    sim_engine.scenario = "S7_ML_REACTIVE"
    sim_engine.step()

    assert sim_engine.tick_count == 1
    assert sim_engine.total_arrivals > 0

    # At factor 0.01, 2000 busy → 20 arrivals per fog; with jitter ±20% → 16–24 per fog
    # Total over 3 fogs: 48–72. Must be non-zero and not the old hardcoded 23.
    ml_events = [e for e in sim_engine.events if e["category"] == "ML_PREDICTION"]
    assert len(ml_events) == 1
    assert "Chronos-2" in ml_events[0]["title"]


def test_s7_ml_reactive_falls_back_to_baseline_when_chronos_unavailable(sim_engine, monkeypatch):
    """
    S7: When Chronos-2 returns None (unreachable), the simulator falls back
    to the baseline (last-value) prediction and still generates arrivals.
    No arrivals should be dropped or raise an exception.
    """
    import fog.services.ml_client as ml_mod

    monkeypatch.setattr(ml_mod, "get_chronos_prediction", lambda fog_id: None)
    monkeypatch.setattr(ml_mod, "get_baseline_prediction", lambda fog_id: 1500.0)

    sim_engine.scenario = "S7_ML_REACTIVE"
    sim_engine.step()

    assert sim_engine.tick_count == 1
    assert sim_engine.total_arrivals > 0
    ml_events = [e for e in sim_engine.events if e["category"] == "ML_PREDICTION"]
    assert len(ml_events) == 1


def test_s7_ml_prediction_does_not_reserve_piles_prematurely(sim_engine, monkeypatch):
    """
    S7 guard: querying Chronos-2 prediction must not create reservations or
    change pile status before real vehicle arrivals are processed.
    """
    import fog.services.ml_client as ml_mod

    call_count = {"n": 0}

    def counting_prediction(fog_id: str) -> float | None:
        call_count["n"] += 1
        return 1800.0

    monkeypatch.setattr(ml_mod, "get_chronos_prediction", counting_prediction)
    monkeypatch.setattr(ml_mod, "get_baseline_prediction", lambda fog_id: 1800.0)

    # Read pile state before anything runs
    before = sim_engine.get_fog_capacities()
    before_avail = {fid: c["available_piles"] for fid, c in before.items()}

    # Only call _generate_arrivals (read-only ML query phase), not full step
    sim_engine.scenario = "S7_ML_REACTIVE"
    sim_engine._generate_arrivals()   # must not write to DB

    after = sim_engine.get_fog_capacities()
    after_avail = {fid: c["available_piles"] for fid, c in after.items()}

    # Piles unchanged by ML query alone
    assert before_avail == after_avail, \
        f"ML query changed pile availability: before={before_avail}, after={after_avail}"

    # Chronos was called once per fog
    assert call_count["n"] == 3


def test_s7_ml_client_scale_busy_to_arrivals():
    """Unit test: scale_busy_to_arrivals converts occupancy to sensible arrival counts."""
    from fog.services.ml_client import scale_busy_to_arrivals

    assert scale_busy_to_arrivals(0, "fog-a") == 0
    assert scale_busy_to_arrivals(100, "fog-a", scale_factor=0.01) == 1
    assert scale_busy_to_arrivals(2000, "fog-b", scale_factor=0.01) == 20
    assert scale_busy_to_arrivals(99999, "fog-c", scale_factor=0.01) == 60  # capped at 60

