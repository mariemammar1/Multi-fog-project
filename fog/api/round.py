"""
Scenario 5 — PREPARE / SETTLE API endpoints.

Exposes two synchronisation endpoints that the multi-fog orchestrator
(or the integration test conftest.py) calls on each independent Fog process
to implement the global PREPARE → barrier → SETTLE round protocol.

Endpoints
---------
POST /api/v1/round/prepare
POST /api/v1/round/settle
GET  /api/v1/round/status
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from fog.services.round_service import prepare_round, settle_round, get_round_status
from shared.schemas import (
    RoundPrepareRequest,
    RoundPrepareResponse,
    RoundSettleRequest,
    RoundSettleResponse,
    RoundStatusResponse,
)

router = APIRouter(prefix="/api/v1/round", tags=["Round S5"])


@router.post("/prepare", response_model=RoundPrepareResponse)
def api_prepare_round(request: RoundPrepareRequest):
    """
    Scenario 5 — PREPARE phase.

    Processes local vehicle arrivals and charging completions.
    Returns unserved vehicles that could not be accommodated locally.
    Must be called on all Fog nodes before SETTLE begins (global barrier).
    """
    arrivals_dicts = [
        {
            "vehicle_id": a.vehicle_id,
            "required_power_kw": a.required_power_kw,
        }
        for a in request.arrivals
    ]
    result = prepare_round(
        tick=request.tick,
        arrivals=arrivals_dicts,
        completions=request.completions,
    )
    return result


@router.post("/settle", response_model=RoundSettleResponse)
def api_settle_round(request: RoundSettleRequest):
    """
    Scenario 5 — SETTLE phase.

    Called after the global PREPARE barrier has been reached across all Fog nodes.
    Accepts remote vehicle transfers from saturated peers and optionally
    triggers Scenario 3 HTTP cooperation for locally unserved vehicles.
    """
    transfers_dicts = [
        {
            "vehicle_id": t.vehicle_id,
            "required_power_kw": t.required_power_kw,
            "origin_fog": getattr(t, "station_id", None),  # station_id reused as origin hint
        }
        for t in request.remote_transfers
    ]
    result = settle_round(
        tick=request.tick,
        remote_transfers=transfers_dicts,
        trigger_cooperation=request.trigger_cooperation,
    )
    return result


@router.get("/status", response_model=RoundStatusResponse)
def api_round_status():
    """
    Scenario 5 — round phase status.

    Returns the current tick number, phase (IDLE / PREPARED / SETTLED),
    live capacity metrics, and unserved vehicles from the last PREPARE.
    """
    return get_round_status()
