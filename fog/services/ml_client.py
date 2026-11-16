"""
Scenario 7 — ML Prediction Client for Chronos-2.

Provides get_chronos_prediction(fog_id) which:
  1. Reads the last 12 hourly 'busy' values from the fog's historical CSV
     (ml-service/data/<fog_id>.csv) — the same file mounted into each container.
  2. POSTs them to the Chronos-2 service (CHRONOS_URL env var, default
     http://chronos-ml:8000, falls back to http://127.0.0.1:8000 for local dev).
  3. Returns the q50 (median) prediction for the next time step as a float.

If the Chronos service is unavailable, returns None so the caller can
fall back to a heuristic (last-value baseline).

This replaces the hardcoded `predicted = 18` constant in realtime_engine.py
and makes S7 consume a *real* ML forecast.
"""

import csv
import json
import logging
import os
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

logger = logging.getLogger("ml_client")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "ml-service" / "data"

CHRONOS_URL = os.getenv("CHRONOS_URL", "http://127.0.0.1:8000")
CONTEXT_SIZE = 12       # Chronos-2 minimum context requirement
TIMEOUT_SEC = 10        # keep it fast enough for real-time ticks

# In-memory cache: fog_id -> list of recent 'busy' values (rolling window)
_history_cache: dict[str, list[float]] = {}


def _load_history(fog_id: str) -> list[float]:
    """
    Load historical occupancy series from the fog's CSV file.
    Returns the full column of 'busy' values (all rows).
    Uses an in-memory cache refreshed on each call so new rows are picked up.
    """
    csv_path = DATA_DIR / f"{fog_id}.csv"
    if not csv_path.exists():
        logger.warning(f"[S7] No CSV found for {fog_id}: {csv_path}")
        return []

    try:
        with csv_path.open("r", newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        values = [float(row["busy"]) for row in rows if row.get("busy")]
        return values
    except (OSError, KeyError, ValueError) as e:
        logger.error(f"[S7] Failed to load history for {fog_id}: {e}")
        return []


def get_chronos_prediction(fog_id: str) -> float | None:
    """
    Query Chronos-2 for a one-step-ahead occupancy prediction for `fog_id`.

    Returns
    -------
    float | None
        Predicted 'busy' value (q50 quantile) for the next time step,
        or None if the service is unreachable or data is insufficient.
    """
    history = _load_history(fog_id)

    if len(history) < CONTEXT_SIZE:
        logger.warning(
            f"[S7] Not enough history for {fog_id} "
            f"({len(history)} < {CONTEXT_SIZE} required). Using None."
        )
        return None

    context = history[-CONTEXT_SIZE:]

    payload = json.dumps({
        "history": context,
        "prediction_length": 1,
    }).encode("utf-8")

    endpoint = f"{CHRONOS_URL}/api/v1/forecast"
    req = Request(endpoint, data=payload, headers={"Content-Type": "application/json"}, method="POST")

    try:
        with urlopen(req, timeout=TIMEOUT_SEC) as response:
            result = json.loads(response.read().decode("utf-8"))

        q50 = float(result["forecasts"]["q50"][0])
        logger.info(f"[S7] Chronos-2 prediction for {fog_id}: {q50:.1f}")
        return q50

    except (URLError, TimeoutError) as e:
        logger.warning(f"[S7] Chronos-2 unreachable ({endpoint}): {e}. Falling back to baseline.")
        return None
    except (KeyError, ValueError, json.JSONDecodeError) as e:
        logger.error(f"[S7] Chronos-2 response parsing error for {fog_id}: {e}")
        return None


def get_baseline_prediction(fog_id: str) -> float | None:
    """
    Naive last-value baseline: returns the most recent 'busy' value as the
    forecast. Used as a fallback when Chronos-2 is unavailable.
    """
    history = _load_history(fog_id)
    return history[-1] if history else None


def scale_busy_to_arrivals(busy_value: float, fog_id: str, scale_factor: float | None = None) -> int:
    """
    Convert a 'busy' occupancy prediction (number of occupied charging points
    in the zone) into an estimated count of *new EV arrivals* for one tick.

    The scale_factor is derived from the ratio between the fog's total piles
    and the typical maximum 'busy' value in the dataset, clamped to [1, 60].

    If scale_factor is not provided, a conservative default of 0.01 is used
    (1% of busy = arrivals per tick), suitable for the UrbanEV dataset where
    'busy' values are in the thousands.
    """
    if busy_value <= 0:
        return 0

    factor = scale_factor if scale_factor is not None else 0.01
    arrivals = max(1, int(round(busy_value * factor)))
    return min(arrivals, 60)  # cap to avoid unrealistic spikes
