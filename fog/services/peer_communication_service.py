import os
import httpx

from fog.settings import FOG_ID
from fog.services.proposal_selection_service import select_best_proposal, rank_proposals


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

    # Step 2: Rank all valid proposals meeting pile and power requirements.
    ranked_proposals = rank_proposals(
        responses=responses,
        required_piles=request.required_piles,
        required_power_kw=request.required_power_kw
    )

    selected_proposal = None
    failover_count = 0
    attempted_fogs = []

    # Step 3: Scenario S3 — Robust HOLD with automatic multi-peer failover.
    # Try the best proposal first; if HOLD fails (e.g. 409 Conflict, network error, timeout),
    # immediately fall back to the next ranked eligible Fog proposal.
    for attempt_idx, candidate in enumerate(ranked_proposals):
        candidate_fog = candidate["proposer_fog"]
        candidate_url = FOG_URLS.get(candidate_fog)
        attempted_fogs.append(candidate_fog)

        if candidate_url is None or candidate_fog == FOG_ID:
            errors.append({
                "peer_fog": candidate_fog,
                "stage": "HOLD",
                "error": "Invalid selected Fog Node URL.",
                "failover_attempt": attempt_idx + 1
            })
            continue

        hold_endpoint = f"{candidate_url}/api/v1/reservations/hold"
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
            selected_proposal = candidate
            failover_count = attempt_idx
            break  # Successfully acquired HOLD on this candidate

        except httpx.HTTPStatusError as error:
            status_code = error.response.status_code if error.response else None
            detail = ""
            try:
                detail = error.response.json().get("detail", "")
            except Exception:
                detail = str(error)

            errors.append({
                "peer_fog": candidate_fog,
                "stage": "HOLD",
                "status_code": status_code,
                "error": f"HTTP {status_code}: {detail}",
                "failover_attempt": attempt_idx + 1
            })

        except httpx.HTTPError as error:
            errors.append({
                "peer_fog": candidate_fog,
                "stage": "HOLD",
                "status_code": None,
                "error": str(error),
                "failover_attempt": attempt_idx + 1
            })

    # Determine overall cooperation status
    if hold_result is not None:
        cooperation_status = "HOLD_GRANTED"
    elif ranked_proposals:
        cooperation_status = "ALL_HOLDS_FAILED"
    else:
        cooperation_status = "NO_PROPOSALS"

    return {
        "request_id": request.request_id,
        "origin_fog": FOG_ID,
        "status": cooperation_status,
        "responses": responses,
        "ranked_proposals": ranked_proposals,
        "selected_proposal": selected_proposal,
        "hold": hold_result,
        "failover_count": failover_count,
        "attempted_fogs": attempted_fogs,
        "errors": errors
    }
