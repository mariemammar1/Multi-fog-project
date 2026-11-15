from fastapi import APIRouter, HTTPException

from fog.services.reservation_service import (
    create_temporary_hold,
    confirm_temporary_hold,
    cancel_temporary_hold,
    activate_confirmed_hold,
    complete_active_hold,
    process_local_vehicle_request
)
from shared.schemas import (
    HoldRequest, HoldResponse,
    ConfirmRequest, ConfirmResponse,
    CancelRequest, CancelResponse,
    ActivateRequest, ActivateResponse,
    CompleteRequest, CompleteResponse,
    LocalSessionRequest, LocalSessionResponse
)

router = APIRouter(
    prefix="/api/v1/reservations",
    tags=["Reservations"]
)


@router.post("/hold", response_model=HoldResponse)
def reserve_stations(request: HoldRequest):
    result = create_temporary_hold(request)

    if result is None:
        raise HTTPException(
            status_code=409,
            detail="Insufficient available capacity for this reservation."
        )

    return result


@router.post("/confirm", response_model=ConfirmResponse)
def confirm_reservation(request: ConfirmRequest):
    result = confirm_temporary_hold(request.hold_id)

    if result is None:
        raise HTTPException(
            status_code=409,
            detail="Reservation cannot be confirmed. It may be expired, cancelled or invalid."
        )

    return result


@router.post("/activate", response_model=ActivateResponse)
def activate_reservation(request: ActivateRequest):
    """
    Step 3 of V7 Protocol: Activate confirmed reservation into an active charging session.
    Sets pile status to OCCUPIED.
    """
    result = activate_confirmed_hold(request.hold_id)

    if result is None:
        raise HTTPException(
            status_code=409,
            detail="Reservation cannot be activated. It must be in CONFIRMED status."
        )

    return result


@router.post("/complete", response_model=CompleteResponse)
def complete_reservation(request: CompleteRequest):
    """
    Step 4 of V7 Protocol: Complete charging session and release the pile.
    Restores pile status to AVAILABLE.
    """
    result = complete_active_hold(request.hold_id)

    if result is None:
        raise HTTPException(
            status_code=409,
            detail="Reservation cannot be completed. It must be in ACTIVE or CONFIRMED status."
        )

    return result


@router.post("/cancel", response_model=CancelResponse)
def cancel_reservation(request: CancelRequest):
    result = cancel_temporary_hold(request.hold_id)

    if result is None:
        raise HTTPException(
            status_code=409,
            detail="Reservation cannot be cancelled. It may be expired or invalid."
        )

    return result


@router.post("/local", response_model=LocalSessionResponse)
def create_local_charging_session(request: LocalSessionRequest):
    """
    Scenario 1: Direct local vehicle charging request.
    Vehicle directly connects to Fog node without inter-fog cooperation.
    """
    result = process_local_vehicle_request(
        vehicle_id=request.vehicle_id,
        required_power_kw=request.required_power_kw,
        station_id=request.station_id
    )

    if result is None:
        raise HTTPException(
            status_code=409,
            detail="No available charging pile in this Fog node for local request."
        )

    return result