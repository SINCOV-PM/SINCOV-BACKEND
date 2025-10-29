from sqlalchemy import text
from app.db.session import SessionLocal
import logging

logger = logging.getLogger(__name__)


def get_stations_pm25():
    """
    Retrieves all stations along with their latest PM2.5 measurement.
    
    Returns:
        list: List of stations with PM2.5 data.
        
    Raises:
        ValueError: If no data is available.
    """
    db = SessionLocal()
    try:
        # Query to get the latest PM2.5 value for each distinct station.
        # Uses DISTINCT ON (st.id) combined with ORDER BY to ensure only 
        # the latest entry (s.timestamp DESC) is retrieved per station.
        result = db.execute(text("""
            SELECT DISTINCT ON (st.id)
                st.id,
                st.name,
                st.latitude,
                st.longitude,
                s.value,
                s.timestamp AT TIME ZONE 'America/Bogota' as timestamp
            FROM sensors s
            JOIN monitors m ON s.monitor_id = m.id
            JOIN stations st ON m.station_id = st.id
            WHERE m.type = 'PM2.5'
            ORDER BY st.id, s.timestamp DESC
        """)).fetchall()
        
        if not result:
            logger.warning("No PM2.5 data found")
            raise ValueError("Sin datos de PM2.5")
        
        # Format the result rows into a list of dictionaries
        stations = [
            {
                "id": row[0],
                "name": row[1],
                "lat": row[2],
                "lng": row[3],
                "value": row[4],
                "timestamp": str(row[5])
            }
            for row in result
        ]
        
        logger.info(f"Retrieved {len(stations)} stations with PM2.5 data")
        return stations
        
    except Exception as e:
        logger.error(f"Error retrieving PM2.5 stations: {e}")
        # Re-raises the exception to be handled by the API route
        raise
    finally:
        # Ensures the database session is closed
        db.close()


def get_station_detail(station_id: int):
    """
    Retrieves all sensor readings for a specific station, limited to 227 latest records.
    
    Args:
        station_id: ID of the station.
        
    Returns:
        dict: Station data and its sensor readings.
        
    Raises:
        ValueError: If the station is not found.
    """
    db = SessionLocal()
    try:
        result = db.execute(text("""
            SELECT 
                s.id,
                m.id as monitor_id,
                m.code,
                m.type,
                m.unit,
                s.value,
                s.timestamp AT TIME ZONE 'America/Bogota' as timestamp
            FROM sensors s
            JOIN monitors m ON s.monitor_id = m.id
            JOIN stations st ON m.station_id = st.id
            WHERE st.id = :station_id
            ORDER BY s.timestamp DESC
            LIMIT 227
        """), {"station_id": station_id}).fetchall()
        
        if not result:
            raise ValueError(f"Station {station_id} not found")
        
        # Format the result rows into a list of sensor dictionaries
        sensors = [
            {
                "id": row[0],
                "monitor_id": row[1],
                "code": row[2],
                "type": row[3],
                "unit": row[4],
                "value": row[5],
                "timestamp": str(row[6])
            }
            for row in result
        ]
        
        logger.info(f"Retrieved {len(sensors)} sensors for station {station_id}")
        return {
            "station_id": station_id,
            "total_sensors": len(sensors),
            "sensors": sensors
        }
        
    except Exception as e:
        logger.error(f"Error retrieving station {station_id}: {e}")
        raise
    finally:
        db.close()


def get_stations_summary():
    """
    Retrieves a summary of all stations, grouped by monitor type,
    including aggregated statistics per monitor type.
    
    Returns:
        list: Summary with statistics per station and monitor type.
    """
    db = SessionLocal()
    try:
        result = db.execute(text("""
            SELECT 
                st.id,
                st.name,
                st.latitude,
                st.longitude,
                m.type as monitor_type,
                m.unit as monitor_unit,
                COUNT(DISTINCT s.id) as total_mediciones,
                ROUND(AVG(s.value)::numeric, 2) as promedio,
                MIN(s.value) as minimo,
                MAX(s.value) as maximo,
                MAX(s.timestamp AT TIME ZONE 'America/Bogota')::text as ultima_medicion
            FROM sensors s
            JOIN monitors m ON s.monitor_id = m.id
            JOIN stations st ON m.station_id = st.id
            GROUP BY st.id, st.name, st.latitude, st.longitude, m.type, m.unit
            ORDER BY st.id, m.type
        """)).fetchall()
        
        # Group by station
        stations_dict = {}
        
        for row in result:
            station_id = row[0]
            
            if station_id not in stations_dict:
                stations_dict[station_id] = {
                    "id": row[0],
                    "name": row[1],
                    "lat": row[2],
                    "lng": row[3],
                    "monitors": []
                }
            
            # Add monitor data
            stations_dict[station_id]["monitors"].append({
                "type": row[4],
                "unit": row[5],
                "total_mediciones": row[6],
                "promedio": float(row[7]) if row[7] else 0,
                "minimo": float(row[8]) if row[8] else 0,
                "maximo": float(row[9]) if row[9] else 0,
                "ultima_medicion": row[10]
            })
        
        summary = list(stations_dict.values())
        
        logger.info(f"Retrieved summary for {len(summary)} stations")
        return summary
        
    except Exception as e:
        logger.error(f"Error retrieving summary: {e}")
        raise
    finally:
        db.close()
# stations_service.py