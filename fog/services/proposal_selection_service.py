
def rank_proposals(responses, required_piles, required_power_kw):
    """
    Rank all valid proposals received from other Fog Nodes.
    Proposals must meet pile count and total power requirements.
    Ranked by available_piles descending, then available_power_kw descending.
    """
    valid_proposals = []

    for response in responses:
        # Ignore Fog Nodes that declined the request.
        if response.get("status") != "PROPOSAL":
            continue

        if response.get("available_piles", 0) < required_piles:
            continue

        if response.get("available_power_kw", 0.0) < required_power_kw:
            continue

        valid_proposals.append(response)

    # Prefer the Fog with the greatest available capacity (piles, then power)
    valid_proposals.sort(
        key=lambda proposal: (
            proposal.get("available_piles", 0),
            proposal.get("available_power_kw", 0.0)
        ),
        reverse=True
    )

    return valid_proposals


def select_best_proposal(responses, required_piles, required_power_kw):
    """
    Select the best valid proposal received from other Fog Nodes.
    Returns None if no peer can satisfy the requirements.
    """
    ranked = rank_proposals(
        responses=responses,
        required_piles=required_piles,
        required_power_kw=required_power_kw
    )
    return ranked[0] if ranked else None

