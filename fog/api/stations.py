from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from fog.settings import FOG_ID, FOG_ZONE
from fog.repositories.station_repository import get_all_stations
from fog.services.station_service import (
    change_station_status,
    calculate_local_capacity,
)


router = APIRouter(
    prefix="/api/v1/stations",
    tags=["Stations"]
)


class StationResponse(BaseModel):
    station_id: str
    zone: str
    status: Literal["AVAILABLE", "OCCUPIED", "OUT_OF_SERVICE"]
    power_kw: float
    created_at: str | None
    reservation_status: Literal[
        "HOLD", "CONFIRMED", "CANCELLED", "EXPIRED"
    ] | None = None
    is_reservable: bool


class StationStatusUpdate(BaseModel):
    status: Literal["AVAILABLE", "OCCUPIED", "OUT_OF_SERVICE"]


@router.get("", response_model=list[StationResponse])
def list_stations():
    """
    Return all stations managed by this Fog Node.
    """
    return get_all_stations()


@router.patch("/{station_id}/status")
def update_status(station_id: str, request: StationStatusUpdate):
    """
    Update the status of a station.
    """
    try:
        result = change_station_status(station_id, request.status)

        if result is None:
            raise HTTPException(
                status_code=404,
                detail="Station not found"
            )

        return result

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error)
        )


@router.get("/capacity")
def get_capacity():
    """
    Return the current local capacity of this Fog Node.
    """
    return {
        "fog_id": FOG_ID,
        "zone": FOG_ZONE,
        **calculate_local_capacity()
    }