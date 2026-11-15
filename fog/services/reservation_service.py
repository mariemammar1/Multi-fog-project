from fog.repositories.reservation_repository import (
    create_hold,
    confirm_hold,
    cancel_hold,
    activate_hold,
    complete_hold,
    create_local_session
)
from fog.settings import FOG_ID

def create_temporary_hold(request):
    result = create_hold(request)

    if result is None:
        return None

    return {
        **result,
        "proposer_fog": FOG_ID,
        "status": "HOLD"
    }

def confirm_temporary_hold(hold_id):
    result = confirm_hold(hold_id)

    if result is None:
        return None

    return {
        **result,
        "proposer_fog": FOG_ID,
        "status": "CONFIRMED"
    }

def cancel_temporary_hold(hold_id):
    result = cancel_hold(hold_id)

    if result is None:
        return None

    return {
        **result,
        "proposer_fog": FOG_ID,
        "status": "CANCELLED"
    }

def activate_confirmed_hold(hold_id):
    result = activate_hold(hold_id)

    if result is None:
        return None

    return {
        **result,
        "proposer_fog": FOG_ID,
        "status": "ACTIVE"
    }

def complete_active_hold(hold_id):
    result = complete_hold(hold_id)

    if result is None:
        return None

    return {
        **result,
        "proposer_fog": FOG_ID,
        "status": "COMPLETED"
    }

def process_local_vehicle_request(vehicle_id: str, required_power_kw: float = 22.0, station_id: str | None = None):
    return create_local_session(
        vehicle_id=vehicle_id,
        required_power_kw=required_power_kw,
        station_id=station_id,
        fog_id=FOG_ID
    )