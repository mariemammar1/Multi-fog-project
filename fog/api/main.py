from contextlib import asynccontextmanager

from fastapi import FastAPI
from fog.api.forecast import router as forecast_router
from fog.database import init_db
from fog.settings import FOG_ID, FOG_ZONE
from fog.api.stations import router as stations_router
from fog.api.cooperation import router as cooperation_router
from fog.api.reservations import router as reservations_router
from fog.api.piles import router as piles_router
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Multi-Fog EV",
    description="API du système Multi-Fog pour la gestion des bornes de recharge",
    version="0.3.0",
    lifespan=lifespan
)


app.include_router(stations_router)
app.include_router(cooperation_router)
app.include_router(reservations_router)
app.include_router(piles_router)
app.include_router(forecast_router)

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "fog_id": FOG_ID
    }


@app.get("/api/v1/status")
def get_status():
    return {
        "fog_id": FOG_ID,
        "zone": FOG_ZONE,
        "status": "operational",
        "message": f"{FOG_ID} is running"
    }