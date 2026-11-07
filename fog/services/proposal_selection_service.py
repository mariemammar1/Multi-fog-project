def select_best_proposal(responses, required_stations, required_power_kw):
    """
    Select the best valid proposal received from other Fog Nodes.
    """

    valid_proposals = []

    for response in responses:

        if response["status"] != "PROPOSAL":
            continue

        if response["available_stations"] < required_stations:
            continue

        if response["available_power_kw"] < required_power_kw:
            continue

        valid_proposals.append(response)

    if not valid_proposals:
        return None

    # Rank proposals by available capacity.
    valid_proposals.sort(
        key=lambda proposal: (
            proposal["available_stations"],
            proposal["available_power_kw"]
        ),
        reverse=True
    )

    return valid_proposals[0]