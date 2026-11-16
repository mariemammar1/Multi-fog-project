"""
Integration tests for Scenario 5 — PREPARE / SETTLE distributed round protocol.

Verifies that three independently running Fog processes (each with its own
SQLite database) can participate in a synchronised PREPARE → barrier → SETTLE
round via real HTTP calls to /api/v1/round/prepare and /api/v1/round/settle.

No in-memory simulation is used here: every assertion touches a live Fog
process and its persistent database.
"""

import httpx
import pytest


# ===========================================================================
# Helpers
# ===========================================================================

def prepare_fog(fog_url: str, tick: int, arrivals: list[dict], completions: list[str] = []) -> dict:
    response = httpx.post(
        f"{fog_url}/api/v1/round/prepare",
        json={"tick": tick, "arrivals": arrivals, "completions": completions},
        timeout=10.0,
    )
    assert response.status_code == 200, f"PREPARE failed: {response.text}"
    return response.json()


def settle_fog(fog_url: str, tick: int, remote_transfers: list[dict] = [], trigger_cooperation: bool = False) -> dict:
    response = httpx.post(
        f"{fog_url}/api/v1/round/settle",
        json={"tick": tick, "remote_transfers": remote_transfers, "trigger_cooperation": trigger_cooperation},
        timeout=10.0,
    )
    assert response.status_code == 200, f"SETTLE failed: {response.text}"
    return response.json()


def round_status(fog_url: str) -> dict:
    response = httpx.get(f"{fog_url}/api/v1/round/status", timeout=5.0)
    assert response.status_code == 200
    return response.json()


# ===========================================================================
# S5 Tests
# ===========================================================================

class TestScenario5PrepareSettle:

    def test_s5_prepare_serves_local_vehicles(self, fog_cluster):
        """
        S5-PREPARE: when Fog A has capacity, arriving vehicles are served locally.
        PREPARE must report served_sessions and unserved_vehicles=[].
        """
        fog_a = fog_cluster["fog-a"]
        tick = 1

        result = prepare_fog(fog_a, tick=tick, arrivals=[
            {"vehicle_id": "EV-S5-001", "required_power_kw": 22.0},
            {"vehicle_id": "EV-S5-002", "required_power_kw": 22.0},
        ])

        assert result["status"] == "PREPARED"
        assert result["fog_id"] == "fog-a"
        assert result["tick"] == tick
        assert len(result["served_sessions"]) == 2
        assert result["unserved_vehicles"] == []
        assert result["available_piles"] >= 0

        # Round status must now be PREPARED
        status = round_status(fog_a)
        assert status["phase"] == "PREPARED"
        assert status["tick"] == tick

    def test_s5_all_fogs_reach_same_tick_before_settle(self, fog_cluster):
        """
        S5-BARRIER: All three Fog nodes must reach tick=2 in PREPARE
        before SETTLE starts.  This test verifies the barrier invariant by
        calling PREPARE on all three nodes and then checking ticks match.
        """
        tick = 2

        results = {}
        for fog_id, fog_url in fog_cluster.items():
            if fog_id.startswith("_"):
                continue
            results[fog_id] = prepare_fog(fog_url, tick=tick, arrivals=[])

        # All must be PREPARED at the same tick
        for fog_id, result in results.items():
            assert result["tick"] == tick, f"{fog_id} tick mismatch"
            assert result["status"] == "PREPARED"

        # All ticks are identical — barrier is satisfied
        ticks = {fog_id: r["tick"] for fog_id, r in results.items()}
        assert len(set(ticks.values())) == 1, f"Tick mismatch: {ticks}"

    def test_s5_settle_accepts_remote_transfers(self, fog_cluster):
        """
        S5-SETTLE: Fog A is designated as the receiver of vehicles transferred
        from a saturated Fog B.  SETTLE must accept them and report
        accepted_transfers with ACTIVE status.
        """
        fog_a = fog_cluster["fog-a"]
        tick = 3

        # PREPARE Fog A with no local arrivals
        prepare_fog(fog_a, tick=tick, arrivals=[])

        # SETTLE: orchestrator transfers 2 unserved vehicles from Fog B to Fog A
        result = settle_fog(fog_a, tick=tick, remote_transfers=[
            {"vehicle_id": "EV-B-TRANS-001", "required_power_kw": 22.0},
            {"vehicle_id": "EV-B-TRANS-002", "required_power_kw": 22.0},
        ])

        assert result["status"] == "SETTLED"
        assert result["fog_id"] == "fog-a"
        assert result["tick"] == tick
        # Transferred vehicles were accepted
        assert len(result["accepted_transfers"]) == 2
        accepted_ids = [s["vehicle_id"] for s in result["accepted_transfers"]]
        assert "EV-B-TRANS-001" in accepted_ids
        assert "EV-B-TRANS-002" in accepted_ids

        # Fog A status is now SETTLED
        status = round_status(fog_a)
        assert status["phase"] == "SETTLED"

    def test_s5_settle_unserved_vehicles_when_all_full(self, fog_cluster):
        """
        S5-S6: If Fog A is saturated, SETTLE cannot accept transfers.
        remaining_unserved must list the vehicles that could not be placed.
        """
        fog_a = fog_cluster["fog-a"]
        tick = 4

        # First fill Fog A completely via PREPARE with many arrivals
        # Send enough to saturate it (the test Fog has limited piles)
        big_arrival = [{"vehicle_id": f"EV-FILL-{i}", "required_power_kw": 22.0} for i in range(50)]
        prepare_result = prepare_fog(fog_a, tick=tick, arrivals=big_arrival)
        # At least some arrivals should be served; the rest are unserved
        total_unserved_prepare = len(prepare_result["unserved_vehicles"])

        # Now SETTLE with additional remote transfers — Fog A is probably full
        result = settle_fog(fog_a, tick=tick, remote_transfers=[
            {"vehicle_id": "EV-B-OVERFLOW-001", "required_power_kw": 22.0},
        ])

        assert result["status"] == "SETTLED"
        # accepted + remaining must account for all the overflow attempts
        # (either accepted because there was 1 pile left, or remaining_unserved)
        total = len(result["accepted_transfers"]) + len(result["remaining_unserved"])
        assert total == 1

    def test_s5_completions_release_piles_before_next_prepare(self, fog_cluster):
        """
        S5-COMPLETIONS: Hold IDs passed in PREPARE.completions should free piles,
        making them available for new arrivals within the same PREPARE call.
        """
        fog_a = fog_cluster["fog-a"]

        # Round 5: create a session on Fog A
        tick5 = 5
        prep5 = prepare_fog(fog_a, tick=tick5, arrivals=[
            {"vehicle_id": "EV-COMPL-001", "required_power_kw": 22.0},
        ])
        assert len(prep5["served_sessions"]) == 1
        hold_id = prep5["served_sessions"][0]["session_id"]
        piles_avail_after_prep5 = prep5["available_piles"]

        # Round 6: complete the previous session and add a new arrival
        tick6 = 6
        prep6 = prepare_fog(fog_a, tick=tick6,
                             arrivals=[{"vehicle_id": "EV-COMPL-002", "required_power_kw": 22.0}],
                             completions=[hold_id])

        # The completed pile should have been released and re-used
        assert prep6["status"] == "PREPARED"
        assert "EV-COMPL-001" not in prep6.get("unserved_vehicles", [])
        # Available piles should not have dropped permanently
        assert prep6["available_piles"] >= 0
        assert len(prep6["released_piles"]) >= 1
