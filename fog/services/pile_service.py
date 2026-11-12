
from fog.repositories.pile_repository import (
    get_all_piles,
    update_pile_status,
    get_pile_capacity,
)


VALID_STATUSES = {
    "AVAILABLE",
    "OCCUPIED",
    "OUT_OF_SERVICE",
}


def list_local_piles():
    """
    Return all charging piles managed by this Fog.
    """
    return get_all_piles()


def change_pile_status(pile_id: str, new_status: str):
    """
    Validate and update the status of a charging pile.
    """
    if new_status not in VALID_STATUSES:
        raise ValueError("Invalid pile status")

    updated = update_pile_status(pile_id, new_status)

    if not updated:
        return None

    return {
        "pile_id": pile_id,
        "status": new_status,
        "message": "Pile status updated successfully"
    }


def calculate_local_pile_capacity():
    """
    Return the current charging capacity of this Fog.
    """
    return get_pile_capacity()
