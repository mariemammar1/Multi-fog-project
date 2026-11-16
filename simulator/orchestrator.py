"""
Scenario 5 — Multi-Fog Orchestrator.

Implements the PREPARE / SETTLE round protocol:
  PREPARE: Each Fog processes local vehicle arrivals and local charging completions.
  SETTLE:  After a global barrier (all Fogs ready for the same tick),
           inter-Fog cooperation decisions are made for unserved vehicles.

Two orchestrator implementations are provided:
  1. RoundOrchestrator: In-memory simulation over FogNodeState objects for fast unit tests.
  2. DistributedRoundOrchestrator: Real HTTP-based orchestrator coordinating independent
     Fog processes over the network (/api/v1/round/prepare and /api/v1/round/settle).
"""

import httpx



class FogNodeState:
    """Lightweight in-memory model of a single Fog's state for simulation."""

    def __init__(self, fog_id: str, total_piles: int, occupied_piles: int = 0):
        self.fog_id = fog_id
        self.total_piles = total_piles
        self.occupied = occupied_piles
        self.unserved_vehicles: list[str] = []  # vehicle_ids waiting
        self.tick_ready: bool = False
        self.tick: int = 0

    @property
    def available_piles(self) -> int:
        return max(0, self.total_piles - self.occupied)

    def prepare(self, arriving_vehicles: list[str], completing_vehicles: list[str]) -> list[str]:
        """
        PREPARE phase:
        1. Release piles for completed vehicles.
        2. Accept as many arriving vehicles as capacity allows.
        3. Record unserved vehicles.
        Returns list of unserved vehicle_ids.
        """
        # Release piles for completing sessions
        for _ in completing_vehicles:
            if self.occupied > 0:
                self.occupied -= 1

        # Accept arriving vehicles up to available capacity
        self.unserved_vehicles = []
        for vehicle_id in arriving_vehicles:
            if self.available_piles > 0:
                self.occupied += 1
            else:
                self.unserved_vehicles.append(vehicle_id)

        self.tick_ready = True
        self.tick += 1
        return list(self.unserved_vehicles)

    def accept_remote_vehicles(self, vehicles: list[str]) -> list[str]:
        """Accept vehicles transferred from a peer Fog. Returns accepted vehicle_ids."""
        accepted = []
        for vehicle_id in vehicles:
            if self.available_piles > 0:
                self.occupied += 1
                accepted.append(vehicle_id)
        return accepted


class RoundOrchestrator:
    """
    Coordinates the PREPARE / SETTLE cycle across multiple Fog nodes.

    Rules:
    - PREPARE must complete on ALL fogs before SETTLE begins (global barrier).
    - In SETTLE, the saturated Fog selects the best peer with capacity.
    - If no peer has capacity (S6), vehicles remain unserved.
    - ML prediction (S7) does not trigger HOLD; only real arrivals do.
    """

    def __init__(self, fogs: dict[str, FogNodeState]):
        self.fogs = fogs  # fog_id -> FogNodeState
        self.current_tick = 0
        self.history: list[dict] = []

    def run_round(
        self,
        arrivals: dict[str, list[str]],       # fog_id -> [vehicle_id, ...]
        completions: dict[str, list[str]],    # fog_id -> [vehicle_id, ...]
        ml_predictions: dict[str, int] | None = None,  # fog_id -> predicted_count (S7, read-only)
    ) -> dict:
        """
        Execute one full PREPARE → (barrier) → SETTLE round.
        Returns a summary dict with: tick, unserved, transfers, cooperation_triggered.
        """
        self.current_tick += 1
        tick = self.current_tick

        # --- PREPARE phase ---
        # Each fog handles its local arrivals and completions independently
        all_unserved: dict[str, list[str]] = {}
        for fog_id, fog in self.fogs.items():
            fog_arrivals = arrivals.get(fog_id, [])
            fog_completions = completions.get(fog_id, [])
            unserved = fog.prepare(fog_arrivals, fog_completions)
            all_unserved[fog_id] = unserved

        # --- Global barrier ---
        # All fogs must be at the same tick before SETTLE
        ticks = {fog_id: fog.tick for fog_id, fog in self.fogs.items()}
        assert len(set(ticks.values())) == 1, f"Tick mismatch after PREPARE: {ticks}"

        # --- SETTLE phase ---
        transfers: list[dict] = []
        cooperation_triggered = False

        for fog_id, unserved_vehicles in all_unserved.items():
            if not unserved_vehicles:
                continue

            # Find the peer with most available capacity
            best_peer: FogNodeState | None = None
            best_peer_id: str | None = None

            for peer_id, peer in self.fogs.items():
                if peer_id == fog_id:
                    continue
                if peer.available_piles >= len(unserved_vehicles):
                    if best_peer is None or peer.available_piles > best_peer.available_piles:
                        best_peer = peer
                        best_peer_id = peer_id

            if best_peer is not None:
                accepted = best_peer.accept_remote_vehicles(unserved_vehicles)
                if accepted:
                    cooperation_triggered = True
                    transfers.append({
                        "from_fog": fog_id,
                        "to_fog": best_peer_id,
                        "vehicles": accepted
                    })
                    # Remove accepted from unserved
                    for v in accepted:
                        all_unserved[fog_id].remove(v)

        # Compile round summary
        total_unserved = sum(len(v) for v in all_unserved.values())
        summary = {
            "tick": tick,
            "unserved": all_unserved,
            "total_unserved": total_unserved,
            "transfers": transfers,
            "cooperation_triggered": cooperation_triggered,
            "ml_predictions": ml_predictions or {},
            "fog_states": {
                fog_id: {
                    "total_piles": fog.total_piles,
                    "occupied": fog.occupied,
                    "available": fog.available_piles
                }
                for fog_id, fog in self.fogs.items()
            }
        }

        self.history.append(summary)
        return summary


class DistributedRoundOrchestrator:
    """
    Coordinates the PREPARE / SETTLE cycle across multiple independent Fog processes
    communicating via real HTTP calls to the /api/v1/round/* endpoints.

    Parameters
    ----------
    fog_urls : dict[str, str]
        Mapping of fog_id to its base HTTP URL (e.g. {"fog-a": "http://127.0.0.1:8001", ...}).
    client : httpx.Client, optional
        Custom HTTP client (can be an in-process ASGITransport or test client).
    """

    def __init__(self, fog_urls: dict[str, str], client: httpx.Client | None = None):
        self.fog_urls = fog_urls
        self.current_tick = 0
        self.history: list[dict] = []
        self._client = client or httpx.Client(timeout=10.0)

    def run_round(
        self,
        arrivals: dict[str, list[dict | str]],       # fog_id -> list of vehicle_ids or {vehicle_id, required_power_kw}
        completions: dict[str, list[str]],          # fog_id -> list of hold_ids
        ml_predictions: dict[str, int] | None = None,
    ) -> dict:
        self.current_tick += 1
        tick = self.current_tick

        # --- Phase 1: PREPARE Barrier ---
        prepare_results: dict[str, dict] = {}
        for fog_id, url in self.fog_urls.items():
            fog_arrivals = arrivals.get(fog_id, [])
            fog_completions = completions.get(fog_id, [])

            formatted_arrivals = [
                {"vehicle_id": v, "required_power_kw": 22.0} if isinstance(v, str) else v
                for v in fog_arrivals
            ]

            resp = self._client.post(
                f"{url}/api/v1/round/prepare",
                json={
                    "tick": tick,
                    "arrivals": formatted_arrivals,
                    "completions": fog_completions,
                },
            )
            resp.raise_for_status()
            prepare_results[fog_id] = resp.json()

        # Enforce global barrier: all independent Fog processes must reach the same tick
        ticks = {fid: res["tick"] for fid, res in prepare_results.items()}
        assert len(set(ticks.values())) == 1, f"Barrier tick mismatch across Fogs: {ticks}"
        assert all(res["status"] == "PREPARED" for res in prepare_results.values()), "Not all Fogs PREPARED"

        # --- Phase 2: SETTLE Phase ---
        all_unserved: dict[str, list[str]] = {
            fog_id: list(res.get("unserved_vehicles", []))
            for fog_id, res in prepare_results.items()
        }
        capacities: dict[str, int] = {
            fog_id: res.get("available_piles", 0)
            for fog_id, res in prepare_results.items()
        }

        transfers: list[dict] = []
        cooperation_triggered = False

        for fog_id, unserved_list in all_unserved.items():
            if not unserved_list:
                continue

            # Find peer with most available capacity
            best_peer_id = None
            best_cap = 0
            for peer_id, cap in capacities.items():
                if peer_id == fog_id:
                    continue
                if cap >= len(unserved_list) and cap > best_cap:
                    best_peer_id = peer_id
                    best_cap = cap

            if best_peer_id is not None:
                peer_url = self.fog_urls[best_peer_id]
                transfer_payload = [
                    {"vehicle_id": v_id, "required_power_kw": 22.0, "station_id": fog_id}
                    for v_id in unserved_list
                ]
                settle_resp = self._client.post(
                    f"{peer_url}/api/v1/round/settle",
                    json={
                        "tick": tick,
                        "remote_transfers": transfer_payload,
                        "trigger_cooperation": False,
                    },
                )
                settle_resp.raise_for_status()
                settle_data = settle_resp.json()
                accepted = [s["vehicle_id"] for s in settle_data.get("accepted_transfers", [])]

                if accepted:
                    cooperation_triggered = True
                    transfers.append({
                        "from_fog": fog_id,
                        "to_fog": best_peer_id,
                        "vehicles": accepted,
                    })
                    for v in accepted:
                        all_unserved[fog_id].remove(v)
                    capacities[best_peer_id] = settle_data.get("available_piles", 0)

        # Notify remaining fogs to settle
        fog_states = {}
        for fog_id, url in self.fog_urls.items():
            settle_resp = self._client.post(
                f"{url}/api/v1/round/settle",
                json={
                    "tick": tick,
                    "remote_transfers": [],
                    "trigger_cooperation": False,
                },
            )
            settle_resp.raise_for_status()
            s_data = settle_resp.json()
            fog_states[fog_id] = {
                "available": s_data.get("available_piles", 0),
                "occupied": s_data.get("occupied_piles", 0),
            }

        total_unserved = sum(len(v) for v in all_unserved.values())
        summary = {
            "tick": tick,
            "unserved": all_unserved,
            "total_unserved": total_unserved,
            "transfers": transfers,
            "cooperation_triggered": cooperation_triggered,
            "ml_predictions": ml_predictions or {},
            "fog_states": fog_states,
        }
        self.history.append(summary)
        return summary

