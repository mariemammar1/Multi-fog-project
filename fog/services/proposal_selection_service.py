
def select_best_proposal(responses, required_piles, required_power_kw):
    """
    Select the best valid proposal received from other Fog Nodes.
    """

    valid_proposals = []

    for response in responses:

        # Ignore Fog Nodes that declined the request.
        if response["status"] != "PROPOSAL":
            continue

        if response["available_piles"] < required_piles:
            continue

        if response["available_power_kw"] < required_power_kw:
            continue

        valid_proposals.append(response)

    if not valid_proposals:
        return None

    # Prefer the Fog with the greatest available capacity.
    valid_proposals.sort(
        key=lambda proposal: (
            proposal["available_piles"],
            proposal["available_power_kw"]
        ),
        reverse=True
    )

    return valid_proposals[0]
