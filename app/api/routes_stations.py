from fastapi import APIRouter
from app.services.stations_service import get_stations_sync

router = APIRouter(prefix="/stations", tags=["Stations"])

@router.get("/")
def stations():
    return {"stations": get_stations_sync()}