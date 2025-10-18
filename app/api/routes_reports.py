# app/api/routes_reports.py
from fastapi import APIRouter, HTTPException
from app.services.stations_service import get_stations_summary
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


def calculate_pm25_status(value: float) -> str:
    """Calculate air quality status based on PM2.5 value"""
    if value >= 55.5:
        return "Muy Alto"
    elif value >= 35.5:
        return "Alto"
    elif value >= 12.1:
        return "Moderado"
    else:
        return "Bueno"


@router.get("/")
async def get_all_reports():
    """Get PM2.5 reports for all stations using stations_summary"""
    try:
        # Get the stations summary
        summary_data = get_stations_summary()
        
        reports = []
        
        # Process each station
        for station in summary_data:
            # Find PM2.5 monitor
            pm25_monitor = next((m for m in station['monitors'] if m['type'] == 'PM2.5'), None)
            
            if pm25_monitor:
                reports.append({
                    "station_id": station['id'],
                    "station_name": station['name'],
                    "lat": station['lat'],
                    "lng": station['lng'],
                    "pm25_value": pm25_monitor['promedio'],
                    "status": calculate_pm25_status(pm25_monitor['promedio']),
                    "timestamp": pm25_monitor['ultima_medicion'],
                    "date": pm25_monitor['ultima_medicion']
                })
        
        if not reports:
            raise ValueError("No se encontraron datos de PM2.5")
        
        # Sort by PM2.5 value descending
        reports.sort(key=lambda x: x['pm25_value'], reverse=True)
        
        logger.info(f"Retrieved {len(reports)} reports from stations_summary")
        return {
            "success": True,
            "total": len(reports),
            "reports": reports
        }
        
    except ValueError as e:
        logger.warning(f"No data available: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error in reports endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.get("/summary")
async def get_summary():
    """Get statistical summary of PM2.5 data"""
    try:
        # Get the stations summary
        summary_data = get_stations_summary()
        
        pm25_values = []
        status_count = {}
        
        # Extract PM2.5 values
        for station in summary_data:
            pm25_monitor = next((m for m in station['monitors'] if m['type'] == 'PM2.5'), None)
            if pm25_monitor:
                value = pm25_monitor['promedio']
                pm25_values.append(value)
                
                status = calculate_pm25_status(value)
                status_count[status] = status_count.get(status, 0) + 1
        
        if not pm25_values:
            raise ValueError("No hay datos de PM2.5 disponibles")
        
        summary = {
            "total_stations": len(pm25_values),
            "avg_pm25": round(sum(pm25_values) / len(pm25_values), 2),
            "min_pm25": round(min(pm25_values), 2),
            "max_pm25": round(max(pm25_values), 2),
            "status_distribution": status_count
        }
        
        logger.info(f"Retrieved summary: {summary}")
        return {
            "success": True,
            "data": summary
        }
        
    except ValueError as e:
        logger.warning(f"No data available: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error in summary endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")