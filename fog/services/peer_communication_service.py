
import os
import httpx

from fog.settings import FOG_ID
from fog.services.proposal_selection_service import select_best_proposal


# URLs configurable via environment variables.
# Default values are used during local development.
FOG_URLS = {
    "fog-a": os.getenv("FOG_A_URL", "http://127.0.0.1:8001"),
    "fog-b": os.getenv("FOG_B_URL", "http://127.0.0.1:8002"),
    "fog-c": os.getenv("FOG_C_URL", "http://127.0.0.1:8003"),
}


def send_help_request_to_peers(request):
    responses = []
    errors = []

    request_data = request.model_dump()

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
                "error": str(error)
            })

    best_proposal = select_best_proposal(
        responses=responses,
        required_stations=request.required_stations,
        required_power_kw=request.required_power_kw
    )

    return {
        "request_id": request.request_id,
        "origin_fog": FOG_ID,
        "responses": responses,
        "selected_proposal": best_proposal,
        "errors": errors
    }
