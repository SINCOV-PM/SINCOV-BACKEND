# app/api/routes_stations.py
from fastapi import APIRouter, HTTPException
from app.services.stations_service import (
    get_stations_pm25, 
    get_station_detail, 
    get_stations_summary,
    get_station_report_24h  # 🆕 Nueva importación
)
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


# 🆕 NUEVA RUTA PARA REPORTES DETALLADOS
@router.get("/{station_id}/report")
async def get_station_report(station_id: int):
    """
    Get a detailed 24-hour report for a specific station.
    
    Includes:
    - PM2.5 statistics (average, min, max, SMA 4h)
    - Other monitors statistics (NO2, O3, CO, etc.)
    - Trends for all monitors
    
    Args:
        station_id: ID of the station
        
    Returns:
        Detailed report with 24h data
        
    Example:
        GET /stations/3/report
        
        Response:
        {
            "success": true,
            "data": {
                "station_id": 3,
                "station_name": "Kennedy",
                "lat": 4.6255,
                "lng": -74.1469,
                "pm25": {
                    "type": "PM2.5",
                    "unit": "µg/m³",
                    "total_lecturas": 24,
                    "promedio_24h": 20.5,
                    "minimo_24h": 15.2,
                    "maximo_24h": 28.7,
                    "sma_4h": 21.3,
                    "ultima_lectura": "2025-01-15 10:30:00",
                    "tendencia": "Estable"
                },
                "other_monitors": [...],
                "report_timestamp": "2025-01-15 10:35:00"
            }
        }
    """
    try:
        logger.info(f"Fetching 24h report for station {station_id}")
        report = get_station_report_24h(station_id)
        logger.info(f"Successfully generated report for station {station_id}")
        return {
            "success": True,
            "data": report
        }
    except ValueError as e:
        logger.warning(f"Station {station_id} not found: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error generating report for station {station_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error al generar el reporte")