
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from fog.settings import FOG_ID
from fog.services.pile_service import (
    list_local_piles,
    change_pile_status,
    calculate_local_pile_capacity,
    calculate_station_capacities,
)


router = APIRouter(
    prefix="/api/v1/piles",
    tags=["Charging Piles"]
)


class PileResponse(BaseModel):
    pile_id: str
    station_id: str
    power_kw: float
    pile_type: Literal["AC", "DC"]
    status: Literal["AVAILABLE", "OCCUPIED", "OUT_OF_SERVICE"]
    is_reservable: bool
    longitude: float
    latitude: float
    reservation_status: Literal[
        "HOLD", "CONFIRMED", "CANCELLED", "EXPIRED"
    ] | None = None
    currently_reservable: bool


class PileStatusUpdate(BaseModel):
    status: Literal["AVAILABLE", "OCCUPIED", "OUT_OF_SERVICE"]

class StationCapacityResponse(BaseModel):
    station_id: str
    total_piles: int
    available_piles: int
    occupied_piles: int
    out_of_service_piles: int
    available_power_kw: float
@router.get(
    "/station-capacities",
    response_model=list[StationCapacityResponse]
)
def get_station_capacities():
    """
    Return charging capacity grouped by station for this Fog.
    """
    return calculate_station_capacities()
@router.get("", response_model=list[PileResponse])
def list_piles():
    """
    Return all charging piles managed by this Fog.
    """
    return list_local_piles()


@router.patch("/{pile_id}/status")
def update_pile_status(pile_id: str, request: PileStatusUpdate):
    """
    Update the status of a charging pile.
    """
    result = change_pile_status(pile_id, request.status)

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Pile not found"
        )

    return result


@router.get("/capacity")
def get_pile_capacity():
    """
    Return the current charging capacity of this Fog.
    """
    return {
        "fog_id": FOG_ID,
        **calculate_local_pile_capacity()
    }
