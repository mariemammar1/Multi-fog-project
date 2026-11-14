import os
import httpx

from fog.settings import FOG_ID
from fog.services.proposal_selection_service import select_best_proposal


FOG_URLS = {
    "fog-a": os.getenv("FOG_A_URL", "http://127.0.0.1:8001"),
    "fog-b": os.getenv("FOG_B_URL", "http://127.0.0.1:8002"),
    "fog-c": os.getenv("FOG_C_URL", "http://127.0.0.1:8003"),
}


def send_help_request_to_peers(request):
    """
    Contact peer Fog Nodes, collect proposals,
    select the best one and create a remote temporary hold.
    """

    responses = []
    errors = []
    hold_result = None

    request_data = request.model_dump()

    # Step 1: Ask all peer Fog Nodes for available capacity.
    for peer_fog, peer_url in FOG_URLS.items():

        if peer_fog == FOG_ID:
            continue

        endpoint = f"{peer_url}/api/v1/cooperation/help-requests"

        try:
            response = httpx.post(
                endpoint,
                json=request_data,
                timeout=5.0
            )
            response.raise_for_status()
            responses.append(response.json())

        except httpx.HTTPError as error:
            errors.append({
                "peer_fog": peer_fog,
                "stage": "HELP_REQUEST",
                "error": str(error)
            })

    # Step 2: Select the best proposal.
    best_proposal = select_best_proposal(
        responses=responses,
        required_piles=request.required_piles,
        required_power_kw=request.required_power_kw
    )

    # Step 3: Ask the selected Fog to create a temporary hold.
    if best_proposal is not None:

        selected_fog = best_proposal["proposer_fog"]
        selected_url = FOG_URLS.get(selected_fog)

        if selected_url is None or selected_fog == FOG_ID:
            errors.append({
                "peer_fog": selected_fog,
                "stage": "HOLD",
                "error": "Invalid selected Fog Node."
            })

        else:
            hold_endpoint = (
                f"{selected_url}/api/v1/reservations/hold"
            )

            hold_data = {
                **request_data,
                "ttl_seconds": 120
            }

            try:
                response = httpx.post(
                    hold_endpoint,
                    json=hold_data,
                    timeout=5.0
                )
                response.raise_for_status()
                hold_result = response.json()

            except httpx.HTTPError as error:
                errors.append({
                    "peer_fog": selected_fog,
                    "stage": "HOLD",
                    "error": str(error)
                })

    return {
        "request_id": request.request_id,
        "origin_fog": FOG_ID,
        "responses": responses,
        "selected_proposal": best_proposal,
        "hold": hold_result,
        "errors": errors
    }
