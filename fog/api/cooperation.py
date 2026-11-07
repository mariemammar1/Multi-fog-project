from fastapi import APIRouter, HTTPException

from fog.settings import FOG_ID
from fog.services.cooperation_service import evaluate_help_request
from fog.services.peer_communication_service import (
    send_help_request_to_peers
)
from shared.schemas import HelpRequest, HelpResponse


router = APIRouter(
    prefix="/api/v1/cooperation",
    tags=["Cooperation"]
)


@router.post("/help-requests", response_model=HelpResponse)
def receive_help_request(request: HelpRequest):
    """
    Receive and evaluate a help request from another Fog.
    """
    return evaluate_help_request(request)


@router.post("/request-help")
def request_help(request: HelpRequest):
    """
    Contact all other Fog Nodes and collect their proposals.
    """

    if request.origin_fog != FOG_ID:
        raise HTTPException(
            status_code=400,
            detail=f"origin_fog must be {FOG_ID}"
        )

    return send_help_request_to_peers(request)