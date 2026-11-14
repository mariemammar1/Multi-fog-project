from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from services.forecast_service import forecast


app = FastAPI(
    title="Chronos-2 Forecasting Service",
    description="API de prédiction de séries temporelles pour l'architecture Multi-Fog EV.",
    version="1.0.0",
)


class ForecastRequest(BaseModel):
    history: list[float] = Field(
        ...,
        min_length=12,
        description="Valeurs historiques espacées de 5 minutes.",
    )
    prediction_length: int = Field(
        default=6,
        ge=1,
        le=12,
        description="Nombre de pas à prédire.",
    )


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "chronos-2",
    }


@app.post("/api/v1/forecast")
def predict(request: ForecastRequest):
    try:
        result = forecast(
            history=request.history,
            prediction_length=request.prediction_length,
        )
        return result

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )
