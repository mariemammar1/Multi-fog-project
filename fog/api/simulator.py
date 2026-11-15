"""
FastAPI endpoints for the Multi-Fog EV Real-Time Simulator and System Overview.
"""

from typing import Literal
from fastapi import APIRouter
from pydantic import BaseModel, Field

from simulator.realtime_engine import engine

router = APIRouter(prefix="/api/v1/simulator", tags=["Simulator"])


class StartRequest(BaseModel):
    interval_sec: float = Field(default=2.0, ge=0.5, le=30.0)


class ScenarioRequest(BaseModel):
    scenario: Literal["S1_NORMAL", "S2_COOPERATION", "S6_SATURATION", "S7_ML_REACTIVE"]


class InjectRequest(BaseModel):
    fog_id: Literal["fog-a", "fog-b", "fog-c"]
    count: int = Field(default=10, ge=1, le=200)


@router.get("/status")
def get_simulator_status():
    """Return live status of the real-time simulation engine and current Fog capacities."""
    return engine.get_status()


@router.post("/start")
def start_simulator(request: StartRequest):
    """Start continuous real-time simulation."""
    engine.start(interval_sec=request.interval_sec)
    return {"status": "started", "interval_sec": request.interval_sec}


@router.post("/stop")
def stop_simulator():
    """Pause continuous real-time simulation."""
    engine.stop()
    return {"status": "paused"}


@router.post("/step")
def step_simulator():
    """Execute exactly one simulation tick."""
    engine.step()
    return engine.get_status()


@router.post("/scenario")
def set_scenario(request: ScenarioRequest):
    """Switch active scenario (S1_NORMAL, S2_COOPERATION, S6_SATURATION, S7_ML_REACTIVE)."""
    engine.scenario = request.scenario
    engine.log_event("SCENARIO", f"Changement de Scénario : {request.scenario}", f"Le moteur simule désormais le mode {request.scenario}.", "info")
    return {"status": "scenario_set", "scenario": request.scenario}


@router.post("/inject")
def inject_traffic(request: InjectRequest):
    """Inject a burst of vehicles into a specific Fog node."""
    engine.inject_traffic(fog_id=request.fog_id, count=request.count)
    return engine.get_status()


@router.post("/reset")
def reset_simulator():
    """Reset all Fog databases to 100% available and clear active sessions."""
    engine.reset_databases()
    return engine.get_status()
