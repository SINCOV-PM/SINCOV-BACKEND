# app/services/stations_service.py
from sqlalchemy import text
from app.db.session import SessionLocal
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

_summary_cache = {"data": None, "timestamp": None}
_CACHE_TTL = timedelta(minutes=5)


def get_stations_pm25():
    """
    Retrieves all stations with their most recent PM2.5 measurement.
    Uses local DB data only (no external fetch).
    """
    db = SessionLocal()
    try:
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
            raise ValueError("No PM2.5 data found")

        stations = [
            {
                "id": row[0],
                "name": row[1],
                "lat": row[2],
                "lng": row[3],
                "value": row[4],
                "timestamp": str(row[5]),
            }
            for row in result
        ]

        logger.info(f"Retrieved {len(stations)} stations with PM2.5 data")
        return stations

    except Exception as e:
        logger.error(f"Error retrieving PM2.5 stations: {e}")
        raise
    finally:
        db.close()

def get_station_report_24h(station_id: int):
    """
    Generates a detailed 24-hour report for a given station.
    Includes PM2.5 statistics and all other monitors.
    """
    db = SessionLocal()
    try:
        station_info = db.execute(text("""
            SELECT id, name, latitude, longitude
            FROM stations
            WHERE id = :station_id
        """), {"station_id": station_id}).fetchone()

        if not station_info:
            raise ValueError(f"Station {station_id} not found")

        monitors_stats = db.execute(text("""
            SELECT 
                m.type as monitor_type,
                m.unit as monitor_unit,
                COUNT(s.id) as total_lecturas,
                ROUND(AVG(s.value)::numeric, 2) as promedio_24h,
                MIN(s.value) as minimo_24h,
                MAX(s.value) as maximo_24h,
                MAX(s.timestamp AT TIME ZONE 'America/Bogota')::text as ultima_lectura
            FROM sensors s
            JOIN monitors m ON s.monitor_id = m.id
            WHERE m.station_id = :station_id
                AND s.timestamp >= NOW() - INTERVAL '24 hours'
            GROUP BY m.type, m.unit
            ORDER BY m.type
        """), {"station_id": station_id}).fetchall()

        sma_results = db.execute(text("""
            SELECT 
                m.type as monitor_type,
                ROUND(AVG(s.value)::numeric, 2) as sma_4h
            FROM sensors s
            JOIN monitors m ON s.monitor_id = m.id
            WHERE m.station_id = :station_id
                AND s.timestamp >= NOW() - INTERVAL '4 hours'
            GROUP BY m.type
        """), {"station_id": station_id}).fetchall()

        sma_dict = {row[0]: float(row[1]) if row[1] else 0 for row in sma_results}

        monitors_data = []
        pm25_data = None

        for row in monitors_stats:
            monitor_type = row[0]
            monitor_info = {
                "type": monitor_type,
                "unit": row[1],
                "total_lecturas": row[2],
                "promedio_24h": float(row[3]) if row[3] else 0,
                "minimo_24h": float(row[4]) if row[4] else 0,
                "maximo_24h": float(row[5]) if row[5] else 0,
                "sma_4h": sma_dict.get(monitor_type, 0),
                "ultima_lectura": row[6],
                "tendencia": calculate_trend(
                    float(row[3]) if row[3] else 0,
                    sma_dict.get(monitor_type, 0)
                )
            }
            if monitor_type == "PM2.5":
                pm25_data = monitor_info
            else:
                monitors_data.append(monitor_info)

        report = {
            "station_id": station_info[0],
            "station_name": station_info[1],
            "lat": float(station_info[2]) if station_info[2] else 0,
            "lng": float(station_info[3]) if station_info[3] else 0,
            "pm25": pm25_data,
            "other_monitors": monitors_data,
            "report_timestamp": db.execute(
                text("SELECT NOW() AT TIME ZONE 'America/Bogota'")
            ).scalar(),
        }

        logger.info(f"Generated 24h report for station {station_id}")
        return report

    except Exception as e:
        logger.error(f"Error generating report for station {station_id}: {e}")
        raise
    finally:
        db.close()


def calculate_trend(promedio: float, sma: float) -> str:
    """Determines trend direction comparing 24h average vs 4h SMA."""
    if sma == 0 or promedio == 0:
        return "Sin Datos"
    diff = ((sma - promedio) / promedio) * 100
    if diff > 10:
        return "Tendencia al Alza"
    elif diff < -10:
        return "Tendencia a la Baja"
    elif abs(diff) <= 10:
        return "Estable"
    return "Variable"

def get_station_detail(station_id: int):
    """
    Retrieves recent sensor readings for a specific station.
    Returns the last 227 records grouped by monitor type.
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

        sensors = [
            {
                "id": row[0],
                "monitor_id": row[1],
                "code": row[2],
                "type": row[3],
                "unit": row[4],
                "value": row[5],
                "timestamp": str(row[6]),
            }
            for row in result
        ]

        logger.info(f"Retrieved {len(sensors)} sensors for station {station_id}")
        return {
            "station_id": station_id,
            "total_sensors": len(sensors),
            "sensors": sensors,
        }

    except Exception as e:
        logger.error(f"Error retrieving station {station_id}: {e}")
        raise
    finally:
        db.close()

def get_stations_summary():
    """
    Returns a summary of all stations grouped by monitor type.
    Cached for 5 minutes to improve response time.
    """
    now = datetime.now()
    if _summary_cache["data"] and (now - _summary_cache["timestamp"]) < _CACHE_TTL:
        logger.debug("Returning cached station summary")
        return _summary_cache["data"]

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

        stations_dict = {}
        for row in result:
            station_id = row[0]
            if station_id not in stations_dict:
                stations_dict[station_id] = {
                    "id": row[0],
                    "name": row[1],
                    "lat": row[2],
                    "lng": row[3],
                    "monitors": [],
                }

            stations_dict[station_id]["monitors"].append({
                "type": row[4],
                "unit": row[5],
                "total_mediciones": row[6],
                "promedio": float(row[7]) if row[7] else 0,
                "minimo": float(row[8]) if row[8] else 0,
                "maximo": float(row[9]) if row[9] else 0,
                "ultima_medicion": row[10],
            })

        summary = list(stations_dict.values())
        _summary_cache["data"] = summary
        _summary_cache["timestamp"] = now

        logger.info(f"Retrieved summary for {len(summary)} stations")
        return summary

    except Exception as e:
        logger.error(f"Error retrieving summary: {e}")
        raise
    finally:
        db.close()
