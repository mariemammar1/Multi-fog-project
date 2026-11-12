
def test_all_fogs_are_healthy(fog_cluster):
    """
    Verify that the three independent Fog nodes are running.
    """
    import httpx

    expected_fogs = {
        "fog-a",
        "fog-b",
        "fog-c",
    }

    discovered_fogs = set()

    for fog_id in expected_fogs:
        url = fog_cluster[fog_id]
        response = httpx.get(f"{url}/health", timeout=5.0)

        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"

        discovered_fogs.add(data["fog_id"])

    assert discovered_fogs == expected_fogs


def test_fogs_have_independent_configurations(fog_cluster):
    """
    Verify that each Fog has its own identity and zone.
    """
    import httpx

    expected_zones = {
        "fog-a": "university",
        "fog-b": "shopping_center",
        "fog-c": "public_parking",
    }

    for fog_id, expected_zone in expected_zones.items():
        url = fog_cluster[fog_id]
        response = httpx.get(f"{url}/api/v1/status", timeout=5.0)

        assert response.status_code == 200

        data = response.json()

        assert data["fog_id"] == fog_id
        assert data["zone"] == expected_zones[fog_id]
        assert data["status"] == "operational"
