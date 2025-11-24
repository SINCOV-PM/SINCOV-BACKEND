from fastapi import APIRouter, HTTPException
from app.services.stations_service import (
    get_stations_pm25,
    get_station_detail,
    get_stations_summary,
    get_station_report_24h,
)
import logging

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Stations"])


@router.get("/")
async def get_all_stations():
    """
    Retrieve all stations with their latest PM2.5 readings.
    """
    try:
        stations = get_stations_pm25()
        if not stations:
            raise HTTPException(status_code=404, detail="No PM2.5 data available")
        logger.info(f"Retrieved {len(stations)} stations with PM2.5 data")
        return {"success": True, "total": len(stations), "stations": stations}

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error retrieving stations")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/summary/all")
async def get_summary():
    """
    Return a summary of all stations with aggregated PM2.5 statistics.
    """
    try:
        summary = get_stations_summary()
        if not summary:
            raise HTTPException(status_code=404, detail="No summary data available")
        logger.info(f"Retrieved summary for {len(summary)} stations")
        return {"success": True, "total": len(summary), "data": summary}

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error retrieving summary")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{station_id}")
async def get_station(station_id: int):
    """
    Retrieve detailed sensor data for a specific station by ID.
    """
    try:
        station_data = get_station_detail(station_id)
        if not station_data:
            raise HTTPException(status_code=404, detail="Station not found")
        logger.info(f"Retrieved details for station ID {station_id}")
        return {"success": True, "data": station_data}

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error retrieving data for station {station_id}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{station_id}/report")
async def get_station_report(station_id: int):
    """
    Generate a detailed 24-hour report for a specific station.

    Includes:
      - PM2.5 statistics (average, min, max, SMA 4h)
      - Other monitor statistics (NO₂, O₃, CO, etc.)
      - Trend indicators and timestamps
    """
    try:
        logger.info(f"Generating 24h report for station {station_id}")
        report = get_station_report_24h(station_id)
        if not report:
            raise HTTPException(status_code=404, detail="No report data available")
        logger.info(f"Report generated successfully for station {station_id}")
        return {"success": True, "data": report}

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error generating report for station {station_id}")
        raise HTTPException(status_code=500, detail="Internal server error")
