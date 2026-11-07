from contextlib import asynccontextmanager

from fastapi import FastAPI

from fog.database import init_db
from fog.api.stations import router as stations_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Multi-Fog EV",
    description="API du système Multi-Fog pour la gestion des bornes de recharge",
    version="0.2.0",
    lifespan=lifespan
)


app.include_router(stations_router)


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "fog_id": "fog-a"
    }


@app.get("/api/v1/status")
def get_status():
    return {
        "fog_id": "fog-a",
        "zone": "university",
        "status": "operational",
        "message": "Fog A is running"
    }
