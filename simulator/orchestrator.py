"""
Scenario 5 — Multi-Fog Orchestrator.

Implements the PREPARE / SETTLE round protocol:
  PREPARE: Each Fog processes local vehicle arrivals and local charging completions.
  SETTLE:  After a global barrier (all Fogs ready for the same tick),
           inter-Fog cooperation decisions are made for unserved vehicles.

In production, communication would use real HTTP calls to peer Fog nodes.
In tests, the orchestrator operates on in-memory FogNode objects directly.
"""


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
