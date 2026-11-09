
import httpx
import time
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
def test_fog_b_receives_proposals_from_fog_a_and_c(fog_cluster):
    """
    Fog B requests help.
    Fog A and Fog C evaluate the request through real HTTP calls.
    """
    response = httpx.post(
        f"{fog_cluster['fog-b']}/api/v1/cooperation/request-help",
        json={
            "request_id": "integration-help-001",
            "origin_fog": "fog-b",
            "required_stations": 1,
            "required_power_kw": 10
        },
        timeout=15.0
    )

    assert response.status_code == 200

    data = response.json()

    assert data["request_id"] == "integration-help-001"
    assert data["origin_fog"] == "fog-b"

    responses = data["responses"]

    # Both neighboring Fogs must have answered.
    assert len(responses) == 2

    proposals_by_fog = {
        item["proposer_fog"]: item
        for item in responses
    }

    assert set(proposals_by_fog.keys()) == {"fog-a", "fog-c"}

    # Both Fogs have one available station with 22 kW.
    assert proposals_by_fog["fog-a"]["status"] == "PROPOSAL"
    assert proposals_by_fog["fog-c"]["status"] == "PROPOSAL"

    # The proposal selection service must select one proposal.
    assert data["selected_proposal"] is not None

    selected_fog = data["selected_proposal"]["proposer_fog"]
    assert selected_fog in {"fog-a", "fog-c"}

    # No communication errors are expected.
    assert data["errors"] == []

def test_cooperative_reservation_hold_and_confirm(fog_cluster):
    """
    Fog B obtains a proposal, asks the selected Fog to hold a station,
    then confirms the reservation.
    """

    # Step 1: Fog B requests help from its peers.
    help_response = httpx.post(
        f"{fog_cluster['fog-b']}/api/v1/cooperation/request-help",
        json={
            "request_id": "integration-reservation-001",
            "origin_fog": "fog-b",
            "required_stations": 1,
            "required_power_kw": 10
        },
        timeout=15.0
    )

    assert help_response.status_code == 200

    help_data = help_response.json()
    proposal = help_data["selected_proposal"]

    assert proposal is not None

    # Step 2: Identify the Fog selected by Fog B.
    selected_fog = proposal["proposer_fog"]
    selected_url = fog_cluster[selected_fog]

    # Step 3: Ask the selected Fog to reserve a station temporarily.
    hold_response = httpx.post(
        f"{selected_url}/api/v1/reservations/hold",
        json={
            "request_id": "integration-reservation-001",
            "origin_fog": "fog-b",
            "required_stations": 1,
            "required_power_kw": 10,
            "ttl_seconds": 120
        },
        timeout=5.0
    )

    assert hold_response.status_code == 200

    hold_data = hold_response.json()

    assert hold_data["status"] == "HOLD"
    assert hold_data["origin_fog"] == "fog-b"
    assert hold_data["proposer_fog"] == selected_fog
    assert len(hold_data["station_ids"]) == 1

    hold_id = hold_data["hold_id"]

    # Step 4: Fog B confirms the temporary reservation.
    confirm_response = httpx.post(
        f"{selected_url}/api/v1/reservations/confirm",
        json={"hold_id": hold_id},
        timeout=5.0
    )

    assert confirm_response.status_code == 200

    confirm_data = confirm_response.json()

    assert confirm_data["hold_id"] == hold_id
    assert confirm_data["status"] == "CONFIRMED"
    assert confirm_data["station_ids"] == hold_data["station_ids"]

    # Step 5: Repeating confirmation is idempotent.
    second_confirm = httpx.post(
        f"{selected_url}/api/v1/reservations/confirm",
        json={"hold_id": hold_id},
        timeout=5.0
    )

    assert second_confirm.status_code == 200

    second_data = second_confirm.json()

    assert second_data["hold_id"] == hold_id
    assert second_data["status"] == "CONFIRMED"
    assert second_data["station_ids"] == confirm_data["station_ids"]
    # Step 6: Cleanup - cancel the confirmed reservation
    # so that the station is available for subsequent tests.
    cancel_response = httpx.post(
        f"{selected_url}/api/v1/reservations/cancel",
        json={"hold_id": hold_id},
        timeout=5.0
    )

    assert cancel_response.status_code == 200
    assert cancel_response.json()["status"] == "CANCELLED"
def test_cancel_hold(fog_cluster):
    """
    A temporary HOLD can be cancelled.
    A cancelled HOLD cannot be confirmed.
    """

    selected_url = fog_cluster["fog-a"]

    # Step 1: Create a temporary HOLD.
    hold_response = httpx.post(
        f"{selected_url}/api/v1/reservations/hold",
        json={
            "request_id": "integration-cancel-001",
            "origin_fog": "fog-b",
            "required_stations": 1,
            "required_power_kw": 10,
            "ttl_seconds": 120
        },
        timeout=5.0
    )

    assert hold_response.status_code == 200

    hold_data = hold_response.json()
    hold_id = hold_data["hold_id"]

    assert hold_data["status"] == "HOLD"

    # Step 2: Cancel the HOLD.
    cancel_response = httpx.post(
        f"{selected_url}/api/v1/reservations/cancel",
        json={"hold_id": hold_id},
        timeout=5.0
    )

    assert cancel_response.status_code == 200

    cancel_data = cancel_response.json()

    assert cancel_data["hold_id"] == hold_id
    assert cancel_data["status"] == "CANCELLED"

    # Step 3: A cancelled HOLD cannot be confirmed.
    confirm_response = httpx.post(
        f"{selected_url}/api/v1/reservations/confirm",
        json={"hold_id": hold_id},
        timeout=5.0
    )

    assert confirm_response.status_code == 409
def test_expired_hold_cannot_be_confirmed_and_station_is_reusable(fog_cluster):
    """
    An expired HOLD cannot be confirmed.
    Its station can be reserved again.
    """

    selected_url = fog_cluster["fog-c"]

    # Step 1: Create a HOLD with a 1-second TTL.
    hold_response = httpx.post(
        f"{selected_url}/api/v1/reservations/hold",
        json={
            "request_id": "integration-expiration-001",
            "origin_fog": "fog-b",
            "required_stations": 1,
            "required_power_kw": 10,
            "ttl_seconds": 1
        },
        timeout=5.0
    )

    assert hold_response.status_code == 200

    hold_data = hold_response.json()
    hold_id = hold_data["hold_id"]
    original_station_ids = hold_data["station_ids"]

    # Step 2: Wait until the HOLD expires.
    time.sleep(1.5)

    # Step 3: Try to confirm the expired HOLD.
    confirm_response = httpx.post(
        f"{selected_url}/api/v1/reservations/confirm",
        json={"hold_id": hold_id},
        timeout=5.0
    )

    assert confirm_response.status_code == 409

    # Step 4: Create a new HOLD.
    # create_hold() should expire old HOLDs before selecting stations.
    new_hold_response = httpx.post(
        f"{selected_url}/api/v1/reservations/hold",
        json={
            "request_id": "integration-expiration-002",
            "origin_fog": "fog-b",
            "required_stations": 1,
            "required_power_kw": 10,
            "ttl_seconds": 120
        },
        timeout=5.0
    )

    assert new_hold_response.status_code == 200

    new_hold_data = new_hold_response.json()

    # The expired reservation must not block its station.
    assert new_hold_data["station_ids"] == original_station_ids

    # Cleanup
    cancel_response = httpx.post(
        f"{selected_url}/api/v1/reservations/cancel",
        json={"hold_id": new_hold_data["hold_id"]},
        timeout=5.0
    )

    assert cancel_response.status_code == 200
def test_concurrent_holds_cannot_reserve_the_same_station(fog_cluster):
    """
    Two simultaneous requests must not reserve the same station.
    Only one request should succeed when one station is available.
    """

    selected_url = fog_cluster["fog-a"]
    barrier = Barrier(2)

    def send_hold(request_id):
        # Synchronize both requests before sending them.
        barrier.wait(timeout=5)

        return httpx.post(
            f"{selected_url}/api/v1/reservations/hold",
            json={
                "request_id": request_id,
                "origin_fog": "fog-b",
                "required_stations": 1,
                "required_power_kw": 10,
                "ttl_seconds": 120
            },
            timeout=10.0
        )

    # Step 1: Send two requests concurrently.
    with ThreadPoolExecutor(max_workers=2) as executor:
        future_1 = executor.submit(
            send_hold, "concurrent-request-001"
        )
        future_2 = executor.submit(
            send_hold, "concurrent-request-002"
        )

        response_1 = future_1.result()
        response_2 = future_2.result()

    # Step 2: Exactly one request must succeed.
    statuses = sorted([
        response_1.status_code,
        response_2.status_code
    ])

    assert statuses == [200, 409]

    # Step 3: Identify the successful reservation.
    successful_response = (
        response_1 if response_1.status_code == 200 else response_2
    )

    hold_data = successful_response.json()

    assert hold_data["status"] == "HOLD"
    assert len(hold_data["station_ids"]) == 1

    # Step 4: Release the station for subsequent tests.
    cancel_response = httpx.post(
        f"{selected_url}/api/v1/reservations/cancel",
        json={"hold_id": hold_data["hold_id"]},
        timeout=5.0
    )

    assert cancel_response.status_code == 200
    assert cancel_response.json()["status"] == "CANCELLED"
def test_fog_b_continues_when_fog_a_is_unavailable(fog_cluster):
    """
    Fog B must continue working when Fog A is stopped.
    Fog C must still provide a proposal.
    """

    # Step 1: Stop Fog A.
    fog_a_process = fog_cluster["_processes"]["fog-a"]

    fog_a_process.terminate()
    fog_a_process.wait(timeout=5)

    # Step 2: Fog B requests help from its peers.
    response = httpx.post(
        f"{fog_cluster['fog-b']}/api/v1/cooperation/request-help",
        json={
            "request_id": "integration-failure-001",
            "origin_fog": "fog-b",
            "required_stations": 1,
            "required_power_kw": 10
        },
        timeout=15.0
    )

    # Step 3: Fog B must remain operational.
    assert response.status_code == 200

    data = response.json()

    assert data["request_id"] == "integration-failure-001"

    # Step 4: Fog A must appear in communication errors.
    failed_peers = {
        error["peer_fog"] for error in data["errors"]
    }

    assert "fog-a" in failed_peers

    # Step 5: Fog C must still provide a proposal.
    proposals_by_fog = {
        item["proposer_fog"]: item
        for item in data["responses"]
    }

    assert "fog-c" in proposals_by_fog
    assert proposals_by_fog["fog-c"]["status"] == "PROPOSAL"

    # Step 6: Fog C must be selected.
    assert data["selected_proposal"] is not None
    assert data["selected_proposal"]["proposer_fog"] == "fog-c"