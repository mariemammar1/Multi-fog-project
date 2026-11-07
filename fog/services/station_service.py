from fog.repositories.station_repository import (
    update_station_status,
    get_station_capacity,
)


VALID_STATUSES = {
    "AVAILABLE",
    "OCCUPIED",
    "OUT_OF_SERVICE",
}


def change_station_status(station_id: str, new_status: str):
    """
    Validate and apply a station status change.
    """
    if new_status not in VALID_STATUSES:
        raise ValueError("Invalid station status")

    updated = update_station_status(station_id, new_status)

    if not updated:
        return None

    return {
        "station_id": station_id,
        "status": new_status,
        "message": "Station status updated successfully"
    }


def calculate_local_capacity():
    """
    Return the current local capacity of this Fog.
    """
    return get_station_capacity()