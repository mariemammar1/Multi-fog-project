from fog.repositories.reservation_repository import create_hold
from fog.settings import FOG_ID
from fog.repositories.reservation_repository import confirm_hold
from fog.repositories.reservation_repository import cancel_hold

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