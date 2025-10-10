# app/jobs/hourly_fetch.py
import requests
import json
import logging
from datetime import datetime, timedelta
import pytz
from app.db.session import SessionLocal
from app.models.station import Station
from app.models.monitor import Monitor
from app.models.sensor import Sensor
from app.utils.rmcab_utils import to_dotnet_ticks, build_rmcab_params

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)


def fetch_reports_job():
    """
    Descarga reportes para todas las estaciones usando el formato correcto de RMCAB API.
    """
    logger.info("Ejecutando tarea programada: descarga de reportes RMCAB")

    # Configuración de la API
    host = "http://rmcab.ambientebogota.gov.co"
    base_url = "/Report/GetMultiStationsReportNewAsync"
    full_url = f"{host}{base_url}"
    
    # Configuración de tiempo
    tz = pytz.timezone("America/Bogota")
    now = datetime.now(tz)
    
    # Probar diferentes rangos de tiempo
    time_configs = [
        {"name": "Ultima hora", "hours": 1, "granularity": 60},
        {"name": "Ultimas 3 horas", "hours": 3, "granularity": 60},
        {"name": "Ultimas 24 horas", "hours": 24, "granularity": 60},
    ]

    db = SessionLocal()

    try:
        # Obtener todas las estaciones
        stations = db.query(Station).all()
        logger.info(f"Conteo de estaciones en BD: {len(stations)}")

        for station in stations:
            logger.info(f"\n{'='*80}")
            logger.info(f"Procesando estación: {station.name} (ID RMCAB: {station.station_rmcab_id})")
            logger.info(f"{'='*80}")
            
            # Obtener todos los monitores de esta estación
            monitors = db.query(Monitor).filter(Monitor.station_id == station.id).all()
            
            if not monitors:
                logger.warning(f"No hay monitores configurados para {station.name}")
                continue
            
            logger.info(f"Monitores configurados: {len(monitors)}")
            
            # Filtrar monitores que tengan código definido
            monitors_with_code = [m for m in monitors if m.code]
            
            if not monitors_with_code:
                logger.warning(f"No hay monitores con código RMCAB para {station.name}")
                continue
            
            # Crear lista de códigos de monitores y diccionario para mapeo
            monitor_ids = [m.code for m in monitors_with_code]
            monitor_dict = {m.code: m for m in monitors_with_code}
            
            logger.debug(f"Códigos de monitor para API: {monitor_ids}")
            
            data_found = False
            
            # Probar diferentes rangos de tiempo
            for config in time_configs:
                if data_found:
                    break
                
                from_time = now - timedelta(hours=config["hours"])
                to_time = now
                
                # Convertir a .NET ticks
                from_ticks = to_dotnet_ticks(from_time.isoformat(), str(tz))
                to_ticks = to_dotnet_ticks(to_time.isoformat(), str(tz))
                
                # Construir parámetros
                params = build_rmcab_params(
                    station_id=station.station_rmcab_id,
                    station_name=station.name,
                    monitor_ids=monitor_ids,
                    from_ticks=from_ticks,
                    to_ticks=to_ticks,
                    granularity_minutes=config["granularity"],
                    report_type="Average",
                    take=0,
                    page_size=0
                )
                
                try:
                    logger.info(f"Probando rango: {config['name']}")
                    logger.debug(f"  Desde: {from_time.strftime('%Y-%m-%d %H:%M:%S')}")
                    logger.debug(f"  Hasta: {to_time.strftime('%Y-%m-%d %H:%M:%S')}")
                    logger.debug(f"  From ticks: {from_ticks}")
                    logger.debug(f"  To ticks: {to_ticks}")
                    
                    # Hacer la petición
                    response = requests.get(full_url, params=params, timeout=30)
                    
                    logger.info(f"  Status: {response.status_code}")
                    logger.debug(f"  URL: {response.url}")

                    if response.status_code != 200:
                        logger.warning(f"  Error {response.status_code} en la solicitud: {response.text[:200]}")
                        continue

                    # Parsear respuesta JSON
                    data = response.json()
                    
                    # La API puede retornar diferentes estructuras
                    data_list = []
                    
                    if isinstance(data, dict):
                        # Estructura 1: {"Data": [...], "summary": [...]}
                        if "Data" in data and isinstance(data["Data"], list):
                            data_list = data["Data"]
                        # Estructura 2: {"data": [...]}
                        elif "data" in data and isinstance(data["data"], list):
                            data_list = data["data"]
                        # Estructura 3: {"results": [...]}
                        elif "results" in data and isinstance(data["results"], list):
                            data_list = data["results"]
                    elif isinstance(data, list):
                        # Estructura 4: directamente una lista
                        data_list = data
                    
                    logger.info(f"  Registros encontrados: {len(data_list)}")
                    
                    if len(data_list) == 0:
                        logger.debug(f"  Respuesta completa: {json.dumps(data, indent=4)[:1000]}")
                        continue
                    
                    # ============================================
                    # PROCESAR DATOS
                    # ============================================
                    logger.info(f"  Datos encontrados. Procesando...")
                    logger.debug(f"  Estructura del primer registro: {json.dumps(data_list[0], indent=6)[:500]}")
                    
                    saved_count = 0
                    
                    for record in data_list:
                        # Extraer timestamp del registro
                        timestamp = None
                        for key in ["timestamp", "date", "Timestamp", "Date", "dateTime", "DateTime", "time"]:
                            if key in record:
                                timestamp = record[key]
                                break
                        
                        if timestamp is None:
                            timestamp = now
                        elif isinstance(timestamp, str):
                            try:
                                # Intentar parsear como ISO
                                timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                                # Asegurar que tiene zona horaria
                                if timestamp.tzinfo is None:
                                    timestamp = tz.localize(timestamp)
                            except:
                                try:
                                    # Intentar otros formatos comunes
                                    timestamp = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
                                    timestamp = tz.localize(timestamp)
                                except:
                                    timestamp = now
                        elif isinstance(timestamp, (int, float)):
                            # Si es un timestamp Unix o .NET ticks
                            if timestamp > 10_000_000_000:  # Probablemente .NET ticks
                                from app.utils.rmcab_utils import ticks_to_iso
                                timestamp_str = ticks_to_iso(timestamp, str(tz))
                                timestamp = datetime.fromisoformat(timestamp_str)
                                # Asegurar que tiene zona horaria
                                if timestamp.tzinfo is None:
                                    timestamp = tz.localize(timestamp)
                            else:  # Unix timestamp
                                timestamp = datetime.fromtimestamp(timestamp, tz=tz)
                        
                        # Asegurar que siempre tenga zona horaria
                        if timestamp.tzinfo is None:
                            timestamp = tz.localize(timestamp)
                        
                        logger.debug(f"  Timestamp: {timestamp}")
                        
                        # Procesar cada campo del registro que coincida con un monitor
                        for key, value in record.items():
                            # Skip campos de metadatos
                            if key.lower() in ["timestamp", "date", "datetime", "time", "count", "id", "stationid", "total", "skip", "take"]:
                                continue
                            
                            # Buscar el monitor correspondiente
                            monitor = None
                            
                            # Búsqueda 1: Por código exacto
                            if key in monitor_dict:
                                monitor = monitor_dict[key]
                            
                            # Búsqueda 2: Por código sin prefijo (ej: "S_27_1" -> "1")
                            if monitor is None:
                                for code, mon in monitor_dict.items():
                                    if key.endswith(code.split('_')[-1]):
                                        monitor = mon
                                        break
                            
                            if monitor is None:
                                logger.debug(f"  Monitor no encontrado para código: {key}")
                                continue
                            
                            # Validar y convertir valor
                            if value is None or value == "":
                                continue
                            
                            # Convertir a string para validación
                            value_str = str(value).strip()
                            
                            # Skip valores inválidos comunes
                            if value_str in ["----", "-", "N/A", "NA", "null", "None"]:
                                continue
                            
                            # Skip si parece una fecha/hora
                            if (("-" in value_str and any(c.isdigit() for c in value_str) and value_str.count("-") >= 2) or ":" in value_str):
                                logger.debug(f"  Saltando valor tipo fecha/hora para {key}: {value_str}")
                                continue
                            
                            try:
                                float_value = float(value_str)
                                
                                # Validar que el valor sea razonable (opcional)
                                if float_value < -999999 or float_value > 999999:
                                    logger.warning(f"  Valor fuera de rango para {key}: {float_value}")
                                    continue
                                
                                logger.debug(f"  Valor {monitor.type}: {float_value} {monitor.unit}")
                                
                                # Crear registro de sensor
                                new_sensor = Sensor(
                                    monitor_id=monitor.id,
                                    timestamp=timestamp,
                                    value=float_value
                                )
                                db.add(new_sensor)
                                saved_count += 1
                                
                            except (ValueError, TypeError) as e:
                                logger.warning(f"  Error convirtiendo valor {key}={value}: {e}")
                            
                    # Guardar en la base de datos
                    if saved_count > 0:
                        db.commit()
                        logger.info(f"  {saved_count} sensores guardados exitosamente")
                        data_found = True
                    else:
                        logger.warning(f"  No se guardaron sensores (sin coincidencias de código)")
                        # Solo mostrar los códigos si data_list no está vacío
                        if data_list:
                            logger.debug(f"  Códigos en respuesta: {[k for k in data_list[0].keys() if k not in ['timestamp', 'date', 'count']]}")
                            logger.debug(f"  Códigos esperados: {list(monitor_dict.keys())}")

                except requests.exceptions.Timeout:
                    logger.error(f"  Timeout en petición para {config['name']}")
                except requests.exceptions.RequestException as e:
                    logger.error(f"  Error de red o solicitud: {str(e)}")
                except json.JSONDecodeError as e:
                    logger.error(f"  Error parseando JSON: {str(e)}")
                    if 'response' in locals() and response.text:
                        logger.debug(f"  Respuesta: {response.text[:500]}")
                except Exception as e:
                    logger.exception(f"  Error procesando {config['name']}: {str(e)}")
                    db.rollback()
            
            if not data_found:
                logger.warning(f"No se encontraron datos para {station.name} en ningún rango de tiempo.")

    except Exception as e:
        logger.error(f"Error general en fetch_reports_job: {str(e)}")
        logger.exception("Stack trace completo:")
        db.rollback()
    finally:
        db.close()

    logger.info("\nTarea completada\n")

    
if __name__ == "__main__":
    print("Ejecutando fetch_reports_job manualmente...")
    fetch_reports_job()