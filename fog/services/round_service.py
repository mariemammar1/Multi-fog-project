"""
Scenario 5 — PREPARE / SETTLE distributed round service.

Each Fog node exposes two endpoints to participate in the synchronised round:

  POST /api/v1/round/prepare  — PREPARE phase:
      Processes local vehicle arrivals and charging completions.
      Returns the list of unserved vehicles that overflowed local capacity.

  POST /api/v1/round/settle   — SETTLE phase (called after the global barrier):
      Accepts remote vehicles transferred by the orchestrator and
      (optionally) triggers peer-cooperation for remaining unserved vehicles.

  GET  /api/v1/round/status   — returns current round phase and capacities.

This replaces the previous in-memory FogNodeState simulation:
the three Fog processes now communicate through real HTTP calls, so
PREPARE and SETTLE run on each node's real SQLite database.
"""

import threading
from datetime import datetime, timezone
from typing import Literal

from fog.repositories.pile_repository import get_pile_capacity
from fog.repositories.reservation_repository import create_local_session, complete_hold
from fog.settings import FOG_ID


# ---------------------------------------------------------------------------
# In-process round state (per Fog node, cleared every new round)
# ---------------------------------------------------------------------------

_lock = threading.Lock()

_round_state: dict = {
    "tick": 0,
    "phase": "IDLE",           # IDLE | PREPARED | SETTLED
    "unserved_vehicles": [],   # vehicles that did not fit locally (from PREPARE)
    "served_sessions": [],     # sessions created this round
    "released_piles": [],      # piles freed during this round's PREPARE
}


def _get_state() -> dict:
    with _lock:
        return dict(_round_state)


def _update_state(**kwargs):
    with _lock:
        _round_state.update(kwargs)


# ---------------------------------------------------------------------------
# PREPARE
# ---------------------------------------------------------------------------

def prepare_round(
    tick: int,
    arrivals: list[dict],       # list of {vehicle_id, required_power_kw}
    completions: list[str],     # list of hold_ids to complete
) -> dict:
    """
    PREPARE phase: executed independently on each Fog node.

    1. Complete sessions in `completions` (release piles).
    2. Serve arriving vehicles locally up to available capacity.
    3. Record unserved vehicles for the SETTLE phase.

    Thread-safe; uses SQLite IMMEDIATE transaction for atomicity.
    """
    with _lock:
        _round_state["tick"] = tick
        _round_state["phase"] = "PREPARED"
        _round_state["unserved_vehicles"] = []
        _round_state["served_sessions"] = []
        _round_state["released_piles"] = []

    released = []
    # Step 1: complete sessions (release piles)
    for hold_id in completions:
        result = complete_hold(hold_id)
        if result:
            released.extend(result.get("pile_ids", []))

    # Step 2: serve arriving vehicles locally
    served_sessions = []
    unserved = []

    for vehicle in arrivals:
        vehicle_id = vehicle.get("vehicle_id", "unknown")
        required_power_kw = vehicle.get("required_power_kw", 22.0)

        session = create_local_session(
            vehicle_id=vehicle_id,
            required_power_kw=required_power_kw,
            fog_id=FOG_ID,
        )
        if session:
            served_sessions.append(session)
        else:
            unserved.append(vehicle_id)

    # Snapshot capacity after PREPARE
    cap = get_pile_capacity()

    _update_state(
        unserved_vehicles=unserved,
        served_sessions=served_sessions,
        released_piles=released,
    )

    return {
        "fog_id": FOG_ID,
        "tick": tick,
        "status": "PREPARED",
        "served_sessions": served_sessions,
        "unserved_vehicles": unserved,
        "released_piles": released,
        "available_piles": cap["available_piles"],
        "occupied_piles": cap["occupied_piles"],
    }


# ---------------------------------------------------------------------------
# SETTLE
# ---------------------------------------------------------------------------

def settle_round(
    tick: int,
    remote_transfers: list[dict],       # vehicles sent here by the orchestrator
    trigger_cooperation: bool = True,
) -> dict:
    """
    SETTLE phase: executed after the global barrier across all Fog nodes.

    1. Accept remote vehicles transferred from a saturated peer.
    2. Optionally trigger peer cooperation for still-unserved local vehicles.

    Returns the full SETTLE result including accepted_transfers and
    remaining_unserved.
    """
    accepted_transfers = []

    # Accept remote vehicles transferred from a peer Fog
    for vehicle in remote_transfers:
        vehicle_id = vehicle.get("vehicle_id", "unknown")
        required_power_kw = vehicle.get("required_power_kw", 22.0)

        session = create_local_session(
            vehicle_id=vehicle_id,
            required_power_kw=required_power_kw,
            fog_id=vehicle.get("origin_fog", FOG_ID),
        )
        if session:
            accepted_transfers.append(session)

    # Determine remaining unserved (local + not transferred + no room here)
    state = _get_state()
    remaining_unserved = list(state.get("unserved_vehicles", []))

    cooperation_results: list[dict] = []

    # Optionally trigger S3 HTTP cooperation for remaining unserved local vehicles
    if trigger_cooperation and remaining_unserved:
        from shared.schemas import HelpRequest
        from fog.services.peer_communication_service import send_help_request_to_peers

        help_req = HelpRequest(
            request_id=f"round-{tick}-settle-{FOG_ID}",
            origin_fog=FOG_ID,
            required_piles=len(remaining_unserved),
            required_power_kw=len(remaining_unserved) * 22.0,  # default 22 kW each
        )
        coop_result = send_help_request_to_peers(help_req)
        cooperation_results.append(coop_result)

        # If HOLD was granted, those vehicles are considered served
        if coop_result.get("hold") is not None:
            remaining_unserved = []

    cap = get_pile_capacity()

    _update_state(phase="SETTLED")

    return {
        "fog_id": FOG_ID,
        "tick": tick,
        "status": "SETTLED",
        "cooperation_results": cooperation_results,
        "accepted_transfers": accepted_transfers,
        "remaining_unserved": remaining_unserved,
        "available_piles": cap["available_piles"],
        "occupied_piles": cap["occupied_piles"],
    }


# ---------------------------------------------------------------------------
# STATUS
# ---------------------------------------------------------------------------

def get_round_status() -> dict:
    """Return the current round phase and live capacity for this Fog node."""
    cap = get_pile_capacity()
    state = _get_state()
    return {
        "fog_id": FOG_ID,
        "tick": state["tick"],
        "phase": state["phase"],
        "available_piles": cap["available_piles"],
        "occupied_piles": cap["occupied_piles"],
        "unserved_vehicles": state["unserved_vehicles"],
    }
