"""
Tests for Scenario 5 (Orchestrator PREPARE/SETTLE) and
Scenario 7 (ML prediction read-only, reactive cooperation).
"""
import pytest
from simulator.orchestrator import FogNodeState, RoundOrchestrator

# --- Scenario 5 tests ---

def test_s5_prepare_settle_basic():
    """Normal tick: each fog handles local arrivals, no cooperation needed."""
    fogs = {
        "fog-a": FogNodeState("fog-a", total_piles=5),
        "fog-b": FogNodeState("fog-b", total_piles=5),
        "fog-c": FogNodeState("fog-c", total_piles=5),
    }
    orch = RoundOrchestrator(fogs)
    result = orch.run_round(
        arrivals={"fog-a": ["v1","v2"], "fog-b": ["v3"], "fog-c": ["v4","v5","v6"]},
        completions={}
    )
    assert result["tick"] == 1
    assert result["total_unserved"] == 0
    assert result["cooperation_triggered"] is False
    assert fogs["fog-a"].occupied == 2
    assert fogs["fog-b"].occupied == 1
    assert fogs["fog-c"].occupied == 3

def test_s5_global_barrier_ensures_same_tick():
    """After PREPARE, all fogs must be at tick=1."""
    fogs = {
        "fog-a": FogNodeState("fog-a", total_piles=5),
        "fog-b": FogNodeState("fog-b", total_piles=5),
        "fog-c": FogNodeState("fog-c", total_piles=5),
    }
    orch = RoundOrchestrator(fogs)
    orch.run_round(arrivals={}, completions={})
    assert all(f.tick == 1 for f in fogs.values())

def test_s5_settle_triggers_cooperation_when_saturated():
    """Fog B is saturated; SETTLE transfers 2 vehicles to Fog A which has capacity."""
    fogs = {
        "fog-a": FogNodeState("fog-a", total_piles=5, occupied_piles=0),
        "fog-b": FogNodeState("fog-b", total_piles=3, occupied_piles=2),  # only 1 free
        "fog-c": FogNodeState("fog-c", total_piles=2, occupied_piles=2),  # saturated
    }
    orch = RoundOrchestrator(fogs)
    # 3 vehicles arrive at Fog B but only 1 fits; 2 unserved
    result = orch.run_round(
        arrivals={"fog-b": ["vb1","vb2","vb3"]},
        completions={}
    )
    assert result["cooperation_triggered"] is True
    assert len(result["transfers"]) == 1
    assert result["transfers"][0]["from_fog"] == "fog-b"
    assert result["transfers"][0]["to_fog"] == "fog-a"
    assert len(result["transfers"][0]["vehicles"]) == 2
    assert result["total_unserved"] == 0

def test_s5_completions_release_piles_before_settle():
    """Completions in PREPARE should free piles before new arrivals are accepted."""
    fogs = {
        "fog-a": FogNodeState("fog-a", total_piles=3, occupied_piles=3),  # full
        "fog-b": FogNodeState("fog-b", total_piles=3),
        "fog-c": FogNodeState("fog-c", total_piles=3),
    }
    orch = RoundOrchestrator(fogs)
    # 2 completions happen on fog-a, 2 new arrive
    result = orch.run_round(
        arrivals={"fog-a": ["v1","v2"]},
        completions={"fog-a": ["old1","old2"]}
    )
    assert fogs["fog-a"].occupied == 3  # 3 occupied - 2 completed + 2 arrived = 3
    assert result["total_unserved"] == 0
    assert result["cooperation_triggered"] is False

def test_s5_multiple_rounds_history():
    """Running 3 rounds accumulates history correctly."""
    fogs = {
        "fog-a": FogNodeState("fog-a", total_piles=5),
        "fog-b": FogNodeState("fog-b", total_piles=5),
        "fog-c": FogNodeState("fog-c", total_piles=5),
    }
    orch = RoundOrchestrator(fogs)
    for i in range(3):
        orch.run_round(arrivals={"fog-a": [f"v{i}"]}, completions={})
    assert len(orch.history) == 3
    assert orch.history[-1]["tick"] == 3

# --- Scenario 6 tests ---

def test_s6_all_fogs_saturated_no_cooperation():
    """When all fogs are full, no transfers occur and all vehicles remain unserved."""
    fogs = {
        "fog-a": FogNodeState("fog-a", total_piles=3, occupied_piles=3),
        "fog-b": FogNodeState("fog-b", total_piles=3, occupied_piles=3),
        "fog-c": FogNodeState("fog-c", total_piles=3, occupied_piles=3),
    }
    orch = RoundOrchestrator(fogs)
    result = orch.run_round(
        arrivals={"fog-b": ["vb1","vb2"]},
        completions={}
    )
    assert result["cooperation_triggered"] is False
    assert result["total_unserved"] == 2
    assert result["unserved"]["fog-b"] == ["vb1","vb2"]
    assert len(result["transfers"]) == 0

def test_s6_partial_saturation_no_sufficient_peer():
    """Fog B has 2 unserved but Fog A only has 1 free pile — no transfer possible (need exact capacity)."""
    fogs = {
        "fog-a": FogNodeState("fog-a", total_piles=3, occupied_piles=2),  # only 1 free
        "fog-b": FogNodeState("fog-b", total_piles=2, occupied_piles=2),  # saturated
        "fog-c": FogNodeState("fog-c", total_piles=2, occupied_piles=2),  # saturated
    }
    orch = RoundOrchestrator(fogs)
    result = orch.run_round(
        arrivals={"fog-b": ["vb1","vb2"]},  # 2 unserved (all saturated)
        completions={}
    )
    # No peer has >= 2 available piles
    assert result["cooperation_triggered"] is False
    assert result["total_unserved"] == 2

# --- Scenario 7 tests ---

def test_s7_ml_prediction_does_not_reserve_piles():
    """ML prediction is read-only. Piles are only reserved when real arrivals exceed capacity."""
    fogs = {
        "fog-a": FogNodeState("fog-a", total_piles=5, occupied_piles=0),
        "fog-b": FogNodeState("fog-b", total_piles=3, occupied_piles=0),
        "fog-c": FogNodeState("fog-c", total_piles=3, occupied_piles=0),
    }
    orch = RoundOrchestrator(fogs)

    # At t=1: ML predicts 6 arrivals at fog-b, no reservations triggered
    ml_at_t1 = {"fog-b": 6}
    result_t1 = orch.run_round(
        arrivals={},  # no real arrivals yet
        completions={},
        ml_predictions=ml_at_t1
    )
    # ML prediction stored but no piles reserved
    assert result_t1["ml_predictions"] == {"fog-b": 6}
    assert all(f.occupied == 0 for f in fogs.values())  # nothing reserved
    assert result_t1["cooperation_triggered"] is False

def test_s7_reactive_cooperation_on_real_arrivals():
    """At t+1, real arrivals exceed Fog B capacity; cooperation is triggered reactively."""
    fogs = {
        "fog-a": FogNodeState("fog-a", total_piles=5, occupied_piles=0),
        "fog-b": FogNodeState("fog-b", total_piles=3, occupied_piles=2),  # only 1 free
        "fog-c": FogNodeState("fog-c", total_piles=3, occupied_piles=3),  # saturated
    }
    orch = RoundOrchestrator(fogs)

    # At t: ML predicted 3, now 3 really arrive at fog-b
    result = orch.run_round(
        arrivals={"fog-b": ["vb1","vb2","vb3"]},  # 1 fits locally, 2 unserved
        completions={},
        ml_predictions={"fog-b": 3}  # prediction stored but does not change pile state
    )
    # fog-b accepted 1, 2 unserved → transferred to fog-a
    assert result["cooperation_triggered"] is True
    assert any(t["to_fog"] == "fog-a" for t in result["transfers"])
    assert result["total_unserved"] == 0

def test_s7_no_premature_reservation_before_arrival():
    """Scenario 7 guard: ML prediction at t must not change pile occupancy."""
    fogs = {
        "fog-a": FogNodeState("fog-a", total_piles=5),
        "fog-b": FogNodeState("fog-b", total_piles=5),
        "fog-c": FogNodeState("fog-c", total_piles=5),
    }
    before_occupied = {fog_id: f.occupied for fog_id, f in fogs.items()}
    orch = RoundOrchestrator(fogs)
    # pass a huge prediction — must not cause any HOLD/reservation
    orch.run_round(arrivals={}, completions={}, ml_predictions={"fog-b": 100, "fog-a": 50})
    after_occupied = {fog_id: f.occupied for fog_id, f in fogs.items()}
    assert before_occupied == after_occupied
