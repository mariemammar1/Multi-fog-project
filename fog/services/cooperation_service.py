from fog.repositories.station_repository import get_station_capacity
from fog.settings import FOG_ID, FOG_ZONE


def evaluate_help_request(request):
    """
    Evaluate a help request using this Fog's local capacity.
    """

    capacity = get_station_capacity()

    available_stations = capacity["available_stations"] or 0
    available_power_kw = capacity["available_power_kw"] or 0

    # A Fog cannot propose help to itself.
    if request.origin_fog == FOG_ID:
        status = "DECLINE"
        reason = "A Fog cannot request help from itself."

    elif (
        available_stations >= request.required_stations
        and available_power_kw >= request.required_power_kw
    ):
        status = "PROPOSAL"
        reason = "Sufficient local capacity is available."

    else:
        status = "DECLINE"
        reason = "Insufficient local capacity."

    return {
        "request_id": request.request_id,
        "origin_fog": request.origin_fog,
        "proposer_fog": FOG_ID,
        "zone": FOG_ZONE,
        "status": status,
        "available_stations": available_stations,
        "available_power_kw": available_power_kw,
        "reason": reason
    }