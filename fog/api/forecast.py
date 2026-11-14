import csv
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

from fastapi import APIRouter, HTTPException

from fog.settings import FOG_ID

router = APIRouter(prefix="/api/v1", tags=["forecast"])

CSV_PATH = Path("/app/data/forecast.csv")
CHRONOS_URL = os.getenv("CHRONOS_URL", "http://chronos-ml:8000")


@router.get("/forecasts")
def get_forecast():
    try:
        with CSV_PATH.open("r", newline="", encoding="utf-8") as file:
            rows = list(csv.DictReader(file))

        if len(rows) < 12:
            raise HTTPException(
                status_code=500,
                detail="Not enough historical data: 12 values required.",
            )

        history = [float(row["busy"]) for row in rows[-12:]]

        payload = json.dumps({
            "history": history,
            "prediction_length": 1,
        }).encode("utf-8")

        request = Request(
            f"{CHRONOS_URL}/api/v1/forecast",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        with urlopen(request, timeout=120) as response:
            result = json.loads(response.read().decode("utf-8"))

        return {
            "fog_id": FOG_ID,
            "metric": "aggregate_occupied_points",
            "history_points": len(history),
            "horizon_min": result["step_minutes"],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "model_version": result["model"],
            "forecasts": result["forecasts"],
        }

    except HTTPException:
        raise
    except (URLError, TimeoutError) as error:
        raise HTTPException(
            status_code=503,
            detail=f"Chronos service unavailable: {error}",
        )
    except (OSError, KeyError, ValueError, json.JSONDecodeError) as error:
        raise HTTPException(status_code=500, detail=str(error))
