
from fog.repositories.pile_repository import get_all_piles, get_pile_capacity
from fog.settings import FOG_ID


def evaluate_help_request(request):
    """
    Evaluate a help request using this Fog's local pile capacity.
    The Fog only proposes help; it does not reserve piles here.
    """

    capacity = get_pile_capacity()

    available_piles = capacity["available_piles"]
    available_power_kw = capacity["available_power_kw"]

    # A Fog cannot propose help to itself.
    if request.origin_fog == FOG_ID:
        status = "DECLINE"
        reason = "A Fog cannot request help from itself."

    else:
        # Get only piles that can currently be reserved.
        piles = [
            pile for pile in get_all_piles()
            if pile["currently_reservable"]
        ]

        # Select the most powerful piles to check the request.
        best_piles = sorted(
            piles,
            key=lambda pile: pile["power_kw"],
            reverse=True
        )[:request.required_piles]

        selected_power_kw = sum(
            pile["power_kw"] for pile in best_piles
        )

        enough_piles = len(best_piles) >= request.required_piles
        enough_power = selected_power_kw >= request.required_power_kw

        if enough_piles and enough_power:
            status = "PROPOSAL"
            reason = (
                f"Sufficient capacity: {len(best_piles)} piles "
                f"providing {selected_power_kw:.2f} kW."
            )
        else:
            status = "DECLINE"
            reason = "Insufficient available piles or power."

    return {
        "request_id": request.request_id,
        "origin_fog": request.origin_fog,
        "proposer_fog": FOG_ID,
        "zone": FOG_ID,
        "status": status,
        "available_piles": available_piles,
        "available_power_kw": available_power_kw,
        "reason": reason
    }
