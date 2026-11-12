
import asyncio
import httpx


BASE_URL = "http://127.0.0.1:8001"


async def main():
    async with httpx.AsyncClient(timeout=10.0) as client:

        # 1. Check that A-01 is available before the test
        response = await client.get(f"{BASE_URL}/api/v1/stations")
        response.raise_for_status()

        stations = response.json()
        station_a01 = next(
            station for station in stations
            if station["station_id"] == "A-01"
        )

        print("Initial station state:")
        print(station_a01)

        if not station_a01["is_reservable"]:
            print("\nERROR: A-01 is not available. Stop the test.")
            return

        # 2. Synchronize both requests
        barrier = asyncio.Barrier(2)

        async def send_hold(request_id):
            payload = {
                "request_id": request_id,
                "origin_fog": "fog-b",
                "required_stations": 1,
                "required_power_kw": 22,
                "ttl_seconds": 120
            }

            await barrier.wait()

            response = await client.post(
                f"{BASE_URL}/api/v1/reservations/hold",
                json=payload
            )

            return {
                "request_id": request_id,
                "http_status": response.status_code,
                "response": response.json()
            }

        # 3. Send two requests almost simultaneously
        results = await asyncio.gather(
            send_hold("concurrent-user-001"),
            send_hold("concurrent-user-002")
        )

        print("\n========== CONCURRENT RESULTS ==========")

        for result in results:
            print(f"\nRequest: {result['request_id']}")
            print(f"HTTP status: {result['http_status']}")
            print(f"Response: {result['response']}")

        # 4. Check the final station state
        print("\n========== FINAL STATION STATE ==========")

        response = await client.get(f"{BASE_URL}/api/v1/stations")
        response.raise_for_status()

        stations = response.json()

        for station in stations:
            if station["station_id"] == "A-01":
                print(station)


if __name__ == "__main__":
    asyncio.run(main())
