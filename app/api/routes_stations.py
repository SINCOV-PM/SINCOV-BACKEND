# app/api/routes_stations.py
from fastapi import APIRouter, HTTPException
from app.services.stations_service import (
    get_stations_pm25,
    get_station_detail,
    get_stations_summary
)
import logging

logger = logging.getLogger(__name__)

# Create router with prefix /stations and tag for API documentation
router = APIRouter(prefix="/stations", tags=["Stations"])


@router.get("/")
async def stations():
    """Returns all stations with REAL PM2.5 data from the database"""
    try:
        stations = get_stations_pm25()
        return {"stations": stations}
    except ValueError as e:
        logger.warning(str(e))
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{station_id}")
async def station_detail(station_id: int):
    """Returns detailed information for a specific station"""
    try:
        data = get_station_detail(station_id)
        return data
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary/all")
async def stations_summary():
    """Returns summary data for all stations"""
    try:
        summary = get_stations_summary()
        return {"total": len(summary), "data": summary}
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))