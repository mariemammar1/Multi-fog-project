"""
Multi-Fog EV Real-Time Simulation Engine.
Synchronizes with real SQLite databases (fog_a.db, fog_b.db, fog_c.db).
Implements realistic dynamic EV arrivals, local sessions (S1), inter-fog cooperation (S2-S4),
global barrier rounds (S5), total saturation (S6), and ML reactive mode (S7).
"""

import logging
import random
import sqlite3
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Literal

logger = logging.getLogger("simulator")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"

FOG_CONFIGS = {
    "fog-a": {"db": DATA_DIR / "fog_a.db", "zone": "university", "name": "Fog A (Université)"},
    "fog-b": {"db": DATA_DIR / "fog_b.db", "zone": "shopping_center", "name": "Fog B (Centre Commercial)"},
    "fog-c": {"db": DATA_DIR / "fog_c.db", "zone": "public_parking", "name": "Fog C (Parking Public)"},
}


class RealTimeSimulator:
    def __init__(self):
        self.tick_count = 0
        self.is_running = False
        self.interval_sec = 2.0
        self.scenario: Literal["S1_NORMAL", "S2_COOPERATION", "S6_SATURATION", "S7_ML_REACTIVE"] = "S1_NORMAL"
        self.events: List[Dict[str, Any]] = []
        self.active_sessions: List[Dict[str, Any]] = []
        self.total_arrivals = 0
        self.total_completed = 0
        self.total_cooperations = 0
        self.total_unserved = 0
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        # S7: cache the last ML predictions per fog (for dashboard display)
        self._last_ml_predictions: Dict[str, float | None] = {}

    def get_fog_capacities(self) -> Dict[str, Dict[str, Any]]:
        """Read real-time capacities directly from each Fog's SQLite database."""
        result = {}
        for fog_id, cfg in FOG_CONFIGS.items():
            db_path = cfg["db"]
            if not db_path.exists():
                result[fog_id] = {
                    "total_piles": 0, "available_piles": 0, "occupied_piles": 0,
                    "available_power_kw": 0.0, "active_sessions": 0, "occupancy_percent": 0.0
                }
                continue

            with sqlite3.connect(db_path) as conn:
                conn.row_factory = sqlite3.Row
                row = conn.execute("""
                    SELECT
                        COUNT(*) AS total_piles,
                        COALESCE(SUM(CASE WHEN status = 'AVAILABLE' AND is_reservable = 1 THEN 1 ELSE 0 END), 0) AS available_piles,
                        COALESCE(SUM(CASE WHEN status = 'OCCUPIED' THEN 1 ELSE 0 END), 0) AS occupied_piles,
                        COALESCE(SUM(CASE WHEN status = 'AVAILABLE' AND is_reservable = 1 THEN power_kw ELSE 0 END), 0) AS available_power_kw
                    FROM piles
                """).fetchone()

                total = row["total_piles"] or 1
                occupied = row["occupied_piles"] or 0
                pct = round((occupied / total) * 100, 1)

                active_res = conn.execute(
                    "SELECT COUNT(*) FROM reservations WHERE status IN ('HOLD', 'CONFIRMED', 'ACTIVE')"
                ).fetchone()[0]

                result[fog_id] = {
                    "fog_id": fog_id,
                    "name": cfg["name"],
                    "zone": cfg["zone"],
                    "total_piles": total,
                    "available_piles": row["available_piles"],
                    "occupied_piles": occupied,
                    "available_power_kw": round(row["available_power_kw"], 1),
                    "active_sessions": active_res,
                    "occupancy_percent": pct,
                }
        return result

    def log_event(self, category: str, title: str, message: str, level: str = "info"):
        now_str = datetime.now(timezone.utc).strftime("%H:%M:%S")
        event = {
            "id": f"evt-{len(self.events) + 1}",
            "time": now_str,
            "tick": self.tick_count,
            "category": category,
            "title": title,
            "message": message,
            "level": level,
        }
        self.events.insert(0, event)
        if len(self.events) > 100:
            self.events.pop()

    def step(self):
        """Execute one simulation tick."""
        with self._lock:
            self.tick_count += 1
            tick = self.tick_count

            # 1. Complete existing charging sessions that reached their end tick
            self._process_completions(tick)

            # 2. Determine arrivals per Fog based on active scenario
            arrivals = self._generate_arrivals()

            # 3. Process PREPARE: local allocations on each Fog
            unserved = self._process_local_arrivals(arrivals, tick)

            # 4. Process SETTLE: inter-Fog cooperation for unserved vehicles
            if any(len(v) > 0 for v in unserved.values()):
                self._process_cooperation(unserved, tick)

    def _process_completions(self, current_tick: int):
        """Find active sessions that are ready to finish and release their piles."""
        remaining = []
        for sess in self.active_sessions:
            if sess["end_tick"] <= current_tick:
                # Release pile in database
                fog_id = sess["fog_id"]
                pile_id = sess["pile_id"]
                db_path = FOG_CONFIGS[fog_id]["db"]
                try:
                    with sqlite3.connect(db_path) as conn:
                        conn.execute("UPDATE piles SET status = 'AVAILABLE' WHERE pile_id = ?", (pile_id,))
                        conn.execute("UPDATE reservations SET status = 'COMPLETED' WHERE hold_id = ?", (sess["session_id"],))
                        conn.commit()
                    self.total_completed += 1
                    self.log_event(
                        "COMPLETED",
                        f"Recharge terminée ({sess['vehicle_id']})",
                        f"Véhicule {sess['vehicle_id']} a libéré la borne {pile_id} sur {fog_id.upper()}.",
                        "success"
                    )
                except Exception as e:
                    logger.error(f"Error completing session: {e}")
            else:
                remaining.append(sess)
        self.active_sessions = remaining

    def _generate_arrivals(self) -> Dict[str, List[str]]:
        """Generate vehicle arrivals depending on scenario."""
        arrivals: Dict[str, List[str]] = {"fog-a": [], "fog-b": [], "fog-c": []}

        if self.scenario == "S1_NORMAL":
            # Balanced, reasonable arrival rate (2-6 per fog)
            for fog_id in arrivals:
                count = random.randint(2, 5)
                for _ in range(count):
                    self.total_arrivals += 1
                    arrivals[fog_id].append(f"EV-{self.total_arrivals:04d}")

        elif self.scenario == "S2_COOPERATION":
            # Fog B receives a surge (15-25 vehicles), while Fog A & C receive normal traffic
            arrivals["fog-a"] = [f"EV-A{i:03d}" for i in range(1, random.randint(2, 4))]
            arrivals["fog-b"] = [f"EV-B{i:03d}" for i in range(1, random.randint(15, 25))]
            arrivals["fog-c"] = [f"EV-C{i:03d}" for i in range(1, random.randint(2, 4))]
            self.total_arrivals += sum(len(v) for v in arrivals.values())

        elif self.scenario == "S6_SATURATION":
            # Massive surge across all Fogs
            for fog_id in arrivals:
                count = random.randint(30, 50)
                arrivals[fog_id] = [f"EV-SAT-{fog_id}-{i}" for i in range(count)]
                self.total_arrivals += count

        elif self.scenario == "S7_ML_REACTIVE":
            # S7: Query Chronos-2 for a real prediction per Fog.
            # Rule: prediction is READ-ONLY — no pile is reserved until real vehicles arrive.
            # The predicted count is used ONLY to generate a realistic arrival wave
            # that may (or may not) saturate a Fog, triggering reactive cooperation.
            try:
                from fog.services.ml_client import (
                    get_chronos_prediction,
                    get_baseline_prediction,
                    scale_busy_to_arrivals,
                )

                predictions_log: Dict[str, str] = {}

                for fog_id in arrivals:
                    busy_pred = get_chronos_prediction(fog_id)
                    is_chronos = busy_pred is not None

                    if busy_pred is None:
                        # Chronos unreachable — use last-value baseline
                        busy_pred = get_baseline_prediction(fog_id) or 0.0

                    predicted_arrivals = scale_busy_to_arrivals(busy_pred, fog_id)
                    # Store raw prediction for status/dashboard
                    self._last_ml_predictions[fog_id] = busy_pred

                    # Apply mild jitter ±20% around prediction (real-world variability)
                    jitter = max(0, int(predicted_arrivals * random.uniform(0.8, 1.2)))
                    actual_count = jitter

                    for i in range(actual_count):
                        self.total_arrivals += 1
                        arrivals[fog_id].append(f"EV-ML-{fog_id}-{self.tick_count}-{i:03d}")

                    source = "Chronos-2" if is_chronos else "baseline"
                    predictions_log[fog_id] = (
                        f"{fog_id.upper()}: busy≈{busy_pred:.0f} → {actual_count} arrivées ({source})"
                    )

                self.log_event(
                    "ML_PREDICTION",
                    "Chronos-2 : Prédictions consommées",
                    " | ".join(predictions_log.values()) +
                    " | 0 borne réservée à l'avance (mode réactif S7).",
                    "info",
                )

            except ImportError as e:
                # ml_client not importable in test isolation — fall back to static values
                logger.warning(f"[S7] ml_client import failed ({e}), using static fallback.")
                for fog_id, count in {"fog-b": 18, "fog-a": 3, "fog-c": 2}.items():
                    for i in range(count):
                        self.total_arrivals += 1
                        arrivals[fog_id].append(f"EV-ML-{i:03d}")
                self.log_event(
                    "ML_PREDICTION",
                    "Chronos-2 : Mode repli statique",
                    "Service ML non disponible. Prédiction statique utilisée (Fog B = 18).",
                    "warning",
                )


        return arrivals

    def _process_local_arrivals(self, arrivals: Dict[str, List[str]], tick: int) -> Dict[str, List[str]]:
        """Scenario 1: Serve vehicles locally from available piles."""
        unserved: Dict[str, List[str]] = {fog_id: [] for fog_id in arrivals}

        for fog_id, vehicles in arrivals.items():
            if not vehicles:
                continue
            db_path = FOG_CONFIGS[fog_id]["db"]
            served_count = 0

            with sqlite3.connect(db_path) as conn:
                conn.row_factory = sqlite3.Row
                for vehicle_id in vehicles:
                    # Find one available pile
                    pile = conn.execute("""
                        SELECT pile_id, station_id, power_kw
                        FROM piles
                        WHERE status = 'AVAILABLE' AND is_reservable = 1
                        ORDER BY power_kw DESC
                        LIMIT 1
                    """).fetchone()

                    if pile:
                        pile_id = pile["pile_id"]
                        sess_id = f"sess-{tick}-{vehicle_id}"
                        duration = random.randint(3, 8)  # duration in ticks
                        now_iso = datetime.now(timezone.utc).isoformat()

                        conn.execute("UPDATE piles SET status = 'OCCUPIED' WHERE pile_id = ?", (pile_id,))
                        conn.execute("""
                            INSERT INTO reservations (hold_id, request_id, origin_fog, pile_id, status, expires_at)
                            VALUES (?, ?, ?, ?, 'ACTIVE', '2099-01-01T00:00:00')
                        """, (sess_id, f"req-{vehicle_id}", fog_id, pile_id))

                        self.active_sessions.append({
                            "session_id": sess_id,
                            "vehicle_id": vehicle_id,
                            "fog_id": fog_id,
                            "pile_id": pile_id,
                            "power_kw": pile["power_kw"],
                            "start_tick": tick,
                            "end_tick": tick + duration,
                            "created_at": now_iso,
                        })
                        served_count += 1
                    else:
                        unserved[fog_id].append(vehicle_id)

                conn.commit()

            if served_count > 0:
                self.log_event(
                    "LOCAL_SESSION",
                    f"Acceptation Locale ({fog_id.upper()})",
                    f"{served_count} véhicule(s) pris en charge directement par {fog_id.upper()} (Scénario 1).",
                    "info"
                )

        return unserved

    def _process_cooperation(self, unserved: Dict[str, List[str]], tick: int):
        """Scenarios 2, 3, 4: Inter-Fog cooperation for unserved vehicles."""
        capacities = self.get_fog_capacities()

        for requesting_fog, vehicles in unserved.items():
            if not vehicles:
                continue

            needed = len(vehicles)
            self.log_event(
                "HELP_REQUEST",
                f"Demande d'aide inter-fog ({requesting_fog.upper()})",
                f"{requesting_fog.upper()} est saturé avec {needed} véhicule(s) en attente. Consultation des voisins...",
                "warning"
            )

            # Find best peer with available capacity
            candidates = [
                (peer_id, cap["available_piles"])
                for peer_id, cap in capacities.items()
                if peer_id != requesting_fog and cap["available_piles"] > 0
            ]
            candidates.sort(key=lambda x: x[1], reverse=True)

            if not candidates:
                # Scenario 6: All fogs saturated!
                self.total_unserved += needed
                self.log_event(
                    "SATURATION_REJECT",
                    "Réseau Saturé (Scénario 6)",
                    f"Aucun Fog voisin ne dispose de bornes libres pour {requesting_fog.upper()}. 0 recharge fictive créée.",
                    "error"
                )
                continue

            # Scenario S3 & S4: Multi-peer candidate failover and reservation
            transferred_total = 0
            remaining_vehicles = list(vehicles)

            for candidate_idx, (peer_id, avail) in enumerate(candidates):
                if not remaining_vehicles:
                    break

                to_transfer = min(len(remaining_vehicles), avail)
                if to_transfer <= 0:
                    continue

                batch_vehicles = remaining_vehicles[:to_transfer]
                allocated_count = 0
                peer_db = FOG_CONFIGS[peer_id]["db"]

                try:
                    with sqlite3.connect(peer_db) as conn:
                        conn.row_factory = sqlite3.Row
                        piles = conn.execute("""
                            SELECT pile_id, power_kw
                            FROM piles
                            WHERE status = 'AVAILABLE' AND is_reservable = 1
                            ORDER BY power_kw DESC
                            LIMIT ?
                        """, (to_transfer,)).fetchall()

                        if len(piles) < to_transfer:
                            # S3 HOLD failure / conflict: candidate has fewer available piles than expected
                            self.log_event(
                                "HOLD_FAILOVER",
                                f"Échec HOLD partiel / Conflit ({peer_id.upper()})",
                                f"Capacité réduite ({len(piles)}/{to_transfer}) sur {peer_id.upper()}. Basculement vers le Fog candidat suivant.",
                                "warning"
                            )

                        for i, pile in enumerate(piles):
                            v_id = batch_vehicles[i]
                            hold_id = f"v7-trans-{tick}-{v_id}"
                            duration = random.randint(4, 9)

                            # Mark pile OCCUPIED and reservation ACTIVE
                            conn.execute("UPDATE piles SET status = 'OCCUPIED' WHERE pile_id = ?", (pile["pile_id"],))
                            conn.execute("""
                                INSERT INTO reservations (hold_id, request_id, origin_fog, pile_id, status, expires_at)
                                VALUES (?, ?, ?, ?, 'ACTIVE', '2099-01-01T00:00:00')
                            """, (hold_id, f"req-{v_id}", requesting_fog, pile["pile_id"]))

                            self.active_sessions.append({
                                "session_id": hold_id,
                                "vehicle_id": v_id,
                                "fog_id": peer_id,
                                "pile_id": pile["pile_id"],
                                "power_kw": pile["power_kw"],
                                "start_tick": tick,
                                "end_tick": tick + duration,
                                "transferred_from": requesting_fog,
                            })
                            allocated_count += 1

                        conn.commit()

                    if allocated_count > 0:
                        transferred_total += allocated_count
                        remaining_vehicles = remaining_vehicles[allocated_count:]
                        self.total_cooperations += allocated_count
                        failover_tag = f" [Basculement S3 candidat #{candidate_idx + 1}]" if candidate_idx > 0 else ""
                        self.log_event(
                            "COOPERATION_V7",
                            f"Coopération V7 Réussie ({requesting_fog.upper()} -> {peer_id.upper()}){failover_tag}",
                            f"{allocated_count} véhicule(s) transférés et activés sur {peer_id.upper()} [HOLD -> CONFIRM -> ACTIVATE].",
                            "success"
                        )

                except Exception as e:
                    self.log_event(
                        "HOLD_FAILED",
                        f"Échec HOLD distant ({peer_id.upper()})",
                        f"Erreur de réservation sur {peer_id.upper()}: {e}. Basculement automatique (Scénario 3).",
                        "error"
                    )

            if remaining_vehicles:
                unserved_count = len(remaining_vehicles)
                self.total_unserved += unserved_count
                self.log_event(
                    "PARTIAL_UNSERVED",
                    f"Véhicules non servis ({requesting_fog.upper()})",
                    f"{unserved_count} véhicule(s) n'ont pas pu être transférés (échec ou saturation de tous les Fogs candidats).",
                    "error"
                )

    def inject_traffic(self, fog_id: str, count: int):
        """Manually inject traffic into a designated Fog node."""
        with self._lock:
            self.total_arrivals += count
            arrivals = {"fog-a": [], "fog-b": [], "fog-c": []}
            arrivals[fog_id] = [f"EV-INJECT-{i}" for i in range(1, count + 1)]
            self.log_event(
                "INJECTION",
                f"Injection Manuelle (+{count} EV sur {fog_id.upper()})",
                f"Pic de demande artificiel injecté par l'utilisateur.",
                "warning"
            )
            unserved = self._process_local_arrivals(arrivals, self.tick_count)
            if any(len(v) > 0 for v in unserved.values()):
                self._process_cooperation(unserved, self.tick_count)

    def reset_databases(self):
        """Reset all piles in databases back to AVAILABLE and clear reservations."""
        with self._lock:
            for fog_id, cfg in FOG_CONFIGS.items():
                db_path = cfg["db"]
                if db_path.exists():
                    with sqlite3.connect(db_path) as conn:
                        conn.execute("UPDATE piles SET status = 'AVAILABLE'")
                        conn.execute("DELETE FROM reservations")
                        conn.commit()
            self.active_sessions.clear()
            self.events.clear()
            self.tick_count = 0
            self.total_arrivals = 0
            self.total_completed = 0
            self.total_cooperations = 0
            self.total_unserved = 0
            self._last_ml_predictions.clear()
            self.log_event("SYSTEM", "Réinitialisation", "Toutes les bases de données ont été remises à zéro (100% disponibles).", "info")

    def start(self, interval_sec: float = 2.0):
        if self.is_running:
            return
        self.interval_sec = interval_sec
        self.is_running = True

        def _loop():
            while self.is_running:
                self.step()
                time.sleep(self.interval_sec)

        self._thread = threading.Thread(target=_loop, daemon=True)
        self._thread.start()
        self.log_event("SYSTEM", "Simulateur Démarré", f"Simulation temps réel lancée (intervalle = {interval_sec}s).", "info")

    def stop(self):
        self.is_running = False
        self.log_event("SYSTEM", "Simulateur en Pause", "La simulation a été mise en pause.", "info")

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            capacities = self.get_fog_capacities()
            return {
                "is_running": self.is_running,
                "interval_sec": self.interval_sec,
                "tick": self.tick_count,
                "scenario": self.scenario,
                "total_arrivals": self.total_arrivals,
                "active_sessions_count": len(self.active_sessions),
                "total_completed": self.total_completed,
                "total_cooperations": self.total_cooperations,
                "total_unserved": self.total_unserved,
                # S7: expose the last raw Chronos-2 (or baseline) predictions
                "ml_predictions": {
                    fog_id: {
                        "busy_forecast": v,
                        "source": "chronos-2" if v is not None else "unavailable",
                    }
                    for fog_id, v in self._last_ml_predictions.items()
                },
                "capacities": capacities,
                "recent_events": self.events[:25],
                "active_sessions": self.active_sessions[-10:],
            }


# Singleton engine instance
engine = RealTimeSimulator()

