
from fog.services.proposal_selection_service import rank_proposals, select_best_proposal


def test_select_best_proposal():
    responses = [
        {
            "status": "PROPOSAL",
            "proposer_fog": "fog-a",
            "available_piles": 3,
            "available_power_kw": 66
        },
        {
            "status": "PROPOSAL",
            "proposer_fog": "fog-c",
            "available_piles": 2,
            "available_power_kw": 44
        },
        {
            "status": "DECLINE",
            "proposer_fog": "fog-d",
            "available_piles": 4,
            "available_power_kw": 88
        }
    ]

    result = select_best_proposal(
        responses=responses,
        required_piles=2,
        required_power_kw=40
    )

    assert result is not None
    assert result["proposer_fog"] == "fog-a"
    assert result["available_piles"] == 3

def test_returns_none_when_no_proposal():
    responses = [
        {
            "status": "DECLINE",
            "proposer_fog": "fog-a",
            "available_piles": 5,
            "available_power_kw": 100
        }
    ]

    result = select_best_proposal(responses, 2, 40)

    assert result is None


def test_ignores_insufficient_stations():
    responses = [
        {
            "status": "PROPOSAL",
            "proposer_fog": "fog-a",
            "available_piles": 1,
            "available_power_kw": 100
        }
    ]

    result = select_best_proposal(responses, 2, 40)

    assert result is None


def test_ignores_insufficient_power():
    responses = [
        {
            "status": "PROPOSAL",
            "proposer_fog": "fog-a",
            "available_piles": 3,
            "available_power_kw": 20
        }
    ]

    result = select_best_proposal(responses, 2, 40)

    assert result is None


def test_returns_none_for_empty_responses():
    result = select_best_proposal([], 2, 40)

    assert result is None


def test_selects_proposal_with_highest_station_count():
    responses = [
        {
            "status": "PROPOSAL",
            "proposer_fog": "fog-a",
            "available_piles": 2,
            "available_power_kw": 100
        },
        {
            "status": "PROPOSAL",
            "proposer_fog": "fog-c",
            "available_piles": 3,
            "available_power_kw": 60
        }
    ]

    result = select_best_proposal(responses, 2, 40)

    assert result["proposer_fog"] == "fog-c"


def test_rank_proposals_returns_ordered_candidates():
    """Verify rank_proposals returns all qualifying candidates in descending order."""
    responses = [
        {"status": "PROPOSAL", "proposer_fog": "fog-a", "available_piles": 2, "available_power_kw": 50},
        {"status": "PROPOSAL", "proposer_fog": "fog-c", "available_piles": 5, "available_power_kw": 120},
        {"status": "PROPOSAL", "proposer_fog": "fog-d", "available_piles": 3, "available_power_kw": 80},
        {"status": "DECLINE", "proposer_fog": "fog-e", "available_piles": 10, "available_power_kw": 200},
    ]

    ranked = rank_proposals(responses, required_piles=2, required_power_kw=40)
    assert len(ranked) == 3
    assert [p["proposer_fog"] for p in ranked] == ["fog-c", "fog-d", "fog-a"]


def test_rank_proposals_filters_out_insufficient():
    """Verify rank_proposals ignores candidates not meeting minimum requirements."""
    responses = [
        {"status": "PROPOSAL", "proposer_fog": "fog-a", "available_piles": 1, "available_power_kw": 50},
        {"status": "PROPOSAL", "proposer_fog": "fog-c", "available_piles": 4, "available_power_kw": 20},  # power too low
        {"status": "PROPOSAL", "proposer_fog": "fog-d", "available_piles": 4, "available_power_kw": 90},
    ]

    ranked = rank_proposals(responses, required_piles=2, required_power_kw=40)
    assert len(ranked) == 1
    assert ranked[0]["proposer_fog"] == "fog-d"



def test_uses_power_as_secondary_ranking():
    responses = [
        {
            "status": "PROPOSAL",
            "proposer_fog": "fog-a",
            "available_piles": 3,
            "available_power_kw": 66
        },
        {
            "status": "PROPOSAL",
            "proposer_fog": "fog-c",
            "available_piles": 3,
            "available_power_kw": 88
        }
    ]

    result = select_best_proposal(responses, 2, 40)

    assert result["proposer_fog"] == "fog-c"


def test_rank_proposals_returns_ordered_candidates():
    """Verify rank_proposals returns all qualifying candidates in descending order."""
    responses = [
        {"status": "PROPOSAL", "proposer_fog": "fog-a", "available_piles": 2, "available_power_kw": 50},
        {"status": "PROPOSAL", "proposer_fog": "fog-c", "available_piles": 5, "available_power_kw": 120},
        {"status": "PROPOSAL", "proposer_fog": "fog-d", "available_piles": 3, "available_power_kw": 80},
        {"status": "DECLINE", "proposer_fog": "fog-e", "available_piles": 10, "available_power_kw": 200},
    ]

    ranked = rank_proposals(responses, required_piles=2, required_power_kw=40)
    assert len(ranked) == 3
    assert [p["proposer_fog"] for p in ranked] == ["fog-c", "fog-d", "fog-a"]


def test_rank_proposals_filters_out_insufficient():
    """Verify rank_proposals ignores candidates not meeting minimum requirements."""
    responses = [
        {"status": "PROPOSAL", "proposer_fog": "fog-a", "available_piles": 1, "available_power_kw": 50},
        {"status": "PROPOSAL", "proposer_fog": "fog-c", "available_piles": 4, "available_power_kw": 20},  # power too low
        {"status": "PROPOSAL", "proposer_fog": "fog-d", "available_piles": 4, "available_power_kw": 90},
    ]

    ranked = rank_proposals(responses, required_piles=2, required_power_kw=40)
    assert len(ranked) == 1
    assert ranked[0]["proposer_fog"] == "fog-d"

