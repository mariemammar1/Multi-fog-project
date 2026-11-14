
import os

import numpy as np
from chronos import Chronos2Pipeline


MODEL_NAME = "amazon/chronos-2"
DEVICE = os.getenv("CHRONOS_DEVICE", "cpu")
STEP_MINUTES = 60

_model = None


def get_model():
    global _model

    if _model is None:
        print(f"Loading Chronos-2 on {DEVICE}...")
        _model = Chronos2Pipeline.from_pretrained(
            MODEL_NAME,
            device_map=DEVICE,
        )
        print("Chronos-2 loaded successfully.")

    return _model


def forecast(
    history: list[float],
    prediction_length: int = 1,
) -> dict:
    """Predict future hourly occupancy."""

    if len(history) < 12:
        raise ValueError("At least 12 historical values are required.")

    if prediction_length < 1 or prediction_length > 12:
        raise ValueError("prediction_length must be between 1 and 12.")

    if not all(np.isfinite(value) for value in history):
        raise ValueError("History contains invalid values.")

    context = np.asarray(history, dtype=np.float32).reshape(1, 1, -1)

    model = get_model()
    result = model.predict(
        context,
        prediction_length=prediction_length,
    )

    predictions = result[0][0]
    quantile_levels = model.quantiles

    def extract_quantile(level: float) -> list[float]:
        index = quantile_levels.index(level)
        return predictions[index].tolist()

    return {
        "model": MODEL_NAME,
        "horizon_steps": prediction_length,
        "step_minutes": STEP_MINUTES,
        "forecasts": {
            "q10": extract_quantile(0.1),
            "q50": extract_quantile(0.5),
            "q90": extract_quantile(0.9),
        },
    }
