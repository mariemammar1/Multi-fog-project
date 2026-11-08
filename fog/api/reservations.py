from fastapi import APIRouter, HTTPException

from fog.services.reservation_service import create_temporary_hold
from shared.schemas import HoldRequest, HoldResponse
from fog.services.reservation_service import confirm_temporary_hold
from fog.services.reservation_service import cancel_temporary_hold
from shared.schemas import ConfirmRequest, ConfirmResponse,CancelRequest, CancelResponse

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
@router.post("/cancel", response_model=CancelResponse)
def cancel_reservation(request: CancelRequest):
    result = cancel_temporary_hold(request.hold_id)

    if result is None:
        raise HTTPException(
            status_code=409,
            detail="Reservation cannot be cancelled. It may be expired or invalid."
        )

    return result