from fastapi import APIRouter
from app.api.routes_stations.station_routes import router as station_routes

router = APIRouter(prefix="/stations", tags=["Stations"])
router.include_router(station_routes)
