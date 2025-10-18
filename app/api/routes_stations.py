# app/api/routes_stations.py
from fastapi import APIRouter, HTTPException
from app.services.stations_service import get_stations_pm25, get_station_detail, get_stations_summary
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/")
async def get_all_stations():
    """Get all stations with latest PM2.5 data"""
    try:
        stations = get_stations_pm25()
        return {"stations": stations}
    except ValueError as e:
        logger.warning(f"No PM2.5 data found: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error retrieving stations: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.get("/{station_id}")
async def get_station(station_id: int):
    """Get detailed sensor data for a specific station"""
    try:
        station_data = get_station_detail(station_id)
        return station_data
    except ValueError as e:
        logger.warning(f"Station {station_id} not found: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error retrieving station {station_id}: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.get("/summary/all")
async def get_summary():
    """Get summary of all stations with aggregated statistics"""
    try:
        summary = get_stations_summary()
        return {
            "total": len(summary),
            "data": summary
        }
    except Exception as e:
        logger.error(f"Error retrieving summary: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")