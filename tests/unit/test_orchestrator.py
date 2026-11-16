"""
Tests for Scenario 5 (Orchestrator PREPARE/SETTLE) and
Scenario 7 (ML prediction read-only, reactive cooperation).
"""
import json
import httpx
import pytest
from simulator.orchestrator import FogNodeState, RoundOrchestrator, DistributedRoundOrchestrator

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


# ===========================================================================
# Scenario 5 — Distributed HTTP Orchestrator Tests
# ===========================================================================

def test_s5_distributed_orchestrator_round_prepare_settle():
    """
    Scenario 5: DistributedRoundOrchestrator sends real HTTP requests to /prepare and /settle.
    Verifies that it respects the global barrier and aggregates round metrics.
    """
    fog_urls = {
        "fog-a": "http://127.0.0.1:8001",
        "fog-b": "http://127.0.0.1:8002",
        "fog-c": "http://127.0.0.1:8003",
    }

    def handler(request: httpx.Request) -> httpx.Response:
        url_str = str(request.url)
        body = json.loads(request.content.decode("utf-8")) if request.content else {}

        if "/api/v1/round/prepare" in url_str:
            fog_id = "fog-a" if "8001" in url_str else ("fog-b" if "8002" in url_str else "fog-c")
            return httpx.Response(
                200,
                json={
                    "fog_id": fog_id,
                    "tick": body.get("tick", 1),
                    "status": "PREPARED",
                    "served_sessions": [],
                    "unserved_vehicles": [],
                    "released_piles": [],
                    "available_piles": 5,
                    "occupied_piles": 2,
                },
            )

        if "/api/v1/round/settle" in url_str:
            fog_id = "fog-a" if "8001" in url_str else ("fog-b" if "8002" in url_str else "fog-c")
            return httpx.Response(
                200,
                json={
                    "fog_id": fog_id,
                    "tick": body.get("tick", 1),
                    "status": "SETTLED",
                    "cooperation_results": [],
                    "accepted_transfers": [],
                    "remaining_unserved": [],
                    "available_piles": 5,
                    "occupied_piles": 2,
                },
            )

        return httpx.Response(404)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    orchestrator = DistributedRoundOrchestrator(fog_urls=fog_urls, client=client)

    result = orchestrator.run_round(
        arrivals={"fog-a": ["v1", "v2"], "fog-b": ["v3"]},
        completions={"fog-a": ["old-1"]},
    )

    assert result["tick"] == 1
    assert result["total_unserved"] == 0
    assert result["cooperation_triggered"] is False
    assert len(orchestrator.history) == 1


def test_s5_distributed_orchestrator_barrier_mismatch_raises():
    """
    Scenario 5 Guard: If one Fog reports tick=2 while others report tick=1,
    the global barrier assertion must raise an AssertionError.
    """
    fog_urls = {
        "fog-a": "http://127.0.0.1:8001",
        "fog-b": "http://127.0.0.1:8002",
    }

    def handler(request: httpx.Request) -> httpx.Response:
        url_str = str(request.url)
        # Desynchronized tick on fog-b
        tick_resp = 1 if "8001" in url_str else 2
        return httpx.Response(
            200,
            json={
                "fog_id": "fog-a" if "8001" in url_str else "fog-b",
                "tick": tick_resp,
                "status": "PREPARED",
                "served_sessions": [],
                "unserved_vehicles": [],
                "released_piles": [],
                "available_piles": 5,
                "occupied_piles": 2,
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    orchestrator = DistributedRoundOrchestrator(fog_urls=fog_urls, client=client)

    with pytest.raises(AssertionError) as exc_info:
        orchestrator.run_round(arrivals={}, completions={})
    assert "Barrier tick mismatch" in str(exc_info.value)


def test_s5_distributed_orchestrator_transfers_unserved_over_http():
    """
    Scenario 5 SETTLE: Fog B has 2 unserved vehicles. Orchestrator transfers them
    to Fog A over HTTP, which accepts them.
    """
    fog_urls = {
        "fog-a": "http://127.0.0.1:8001",
        "fog-b": "http://127.0.0.1:8002",
    }

    def handler(request: httpx.Request) -> httpx.Response:
        url_str = str(request.url)
        body = json.loads(request.content.decode("utf-8")) if request.content else {}

        if "/api/v1/round/prepare" in url_str:
            if "8002" in url_str:  # Fog B is full, 2 unserved
                return httpx.Response(200, json={
                    "fog_id": "fog-b", "tick": 1, "status": "PREPARED",
                    "served_sessions": [], "unserved_vehicles": ["vb1", "vb2"],
                    "released_piles": [], "available_piles": 0, "occupied_piles": 5
                })
            else:  # Fog A has 4 piles available
                return httpx.Response(200, json={
                    "fog_id": "fog-a", "tick": 1, "status": "PREPARED",
                    "served_sessions": [], "unserved_vehicles": [],
                    "released_piles": [], "available_piles": 4, "occupied_piles": 1
                })

        if "/api/v1/round/settle" in url_str:
            transfers = body.get("remote_transfers", [])
            accepted = [
                {"vehicle_id": t["vehicle_id"], "status": "ACTIVE"}
                for t in transfers
            ]
            return httpx.Response(200, json={
                "fog_id": "fog-a" if "8001" in url_str else "fog-b",
                "tick": 1, "status": "SETTLED",
                "cooperation_results": [],
                "accepted_transfers": accepted,
                "remaining_unserved": [],
                "available_piles": 2 if "8001" in url_str else 0,
                "occupied_piles": 3 if "8001" in url_str else 5
            })

        return httpx.Response(404)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    orchestrator = DistributedRoundOrchestrator(fog_urls=fog_urls, client=client)

    result = orchestrator.run_round(
        arrivals={"fog-b": ["vb1", "vb2"]},
        completions={},
    )

    assert result["cooperation_triggered"] is True
    assert len(result["transfers"]) == 1
    assert result["transfers"][0]["from_fog"] == "fog-b"
    assert result["transfers"][0]["to_fog"] == "fog-a"
    assert result["transfers"][0]["vehicles"] == ["vb1", "vb2"]
    assert result["total_unserved"] == 0

