import requests
import json
import logging
from datetime import datetime, timedelta
import pytz
from app.db.session import SessionLocal
from app.models.station import Station
from app.models.monitor import Monitor
from app.models.sensor import Sensor
from app.utils.rmcab_utils import to_dotnet_ticks, build_rmcab_params, parse_rmcab_timestamp

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)


def fetch_reports_job():
    """
    Downloads reports for all stations using the correct RMCAB API format.
    """
    logger.info("Running scheduled task: RMCAB report download")

    # API Configuration
    host = "http://rmcab.ambientebogota.gov.co"
    base_url = "/Report/GetMultiStationsReportNewAsync"
    full_url = f"{host}{base_url}"
    
    # Time Configuration
    tz = pytz.timezone("America/Bogota")
    now = datetime.now(tz)
    
    # Try different time ranges
    time_configs = [
        {"name": "Last hour", "hours": 1, "granularity": 60},
        {"name": "Last 3 hours", "hours": 3, "granularity": 60},
        {"name": "Last 24 hours", "hours": 24, "granularity": 60},
    ]

    db = SessionLocal()

    try:
        # Get all stations
        stations = db.query(Station).all()
        logger.info(f"Found {len(stations)} stations in DB")

        for station in stations:
            logger.info(f"\n{'='*80}")
            logger.info(f"Processing station: {station.name} (RMCAB ID: {station.station_rmcab_id})")
            logger.info(f"{'='*80}")
            
            # Get all monitors for this station
            monitors = db.query(Monitor).filter(Monitor.station_id == station.id).all()
            
            if not monitors:
                logger.warning(f"No monitors configured for {station.name}")
                continue
            
            logger.info(f"{len(monitors)} monitors configured")
            
            # Filter monitors that have a defined code
            monitors_with_code = [m for m in monitors if m.code]
            
            if not monitors_with_code:
                logger.warning(f"No monitors with RMCAB code available for {station.name}")
                continue
            
            # Create list of monitor codes and dictionary for mapping
            monitor_ids = [m.code for m in monitors_with_code]
            monitor_dict = {m.code: m for m in monitors_with_code}
            
            logger.debug(f"Monitor codes for API: {monitor_ids}")
            
            data_found = False
            
            # Try different time ranges
            for config in time_configs:
                if data_found:
                    break
                
                from_time = now - timedelta(hours=config["hours"])
                to_time = now
                
                # Convert to .NET ticks
                from_ticks = to_dotnet_ticks(from_time.isoformat(), str(tz))
                to_ticks = to_dotnet_ticks(to_time.isoformat(), str(tz))
                
                # Build parameters
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
                    logger.info(f"Testing range: {config['name']}")
                    logger.debug(f" From: {from_time.strftime('%Y-%m-%d %H:%M:%S')}")
                    logger.debug(f" To: {to_time.strftime('%Y-%m-%d %H:%M:%S')}")
                    logger.debug(f" From ticks: {from_ticks}")
                    logger.debug(f" To ticks: {to_ticks}")
                    
                    # Make the request
                    response = requests.get(full_url, params=params, timeout=30)
                    
                    logger.info(f" Status: {response.status_code}")
                    logger.debug(f" URL: {response.url}")

                    if response.status_code != 200:
                        logger.warning(f" Error {response.status_code}: {response.text[:200]}")
                        continue

                    # Parse JSON response
                    data = response.json()
                    
                    # The API can return different structures
                    data_list = []
                    
                    if isinstance(data, dict):
                        # Structure 1: {"Data": [...], "summary": [...]}
                        if "Data" in data and isinstance(data["Data"], list):
                            data_list = data["Data"]
                        # Structure 2: {"data": [...]}
                        elif "data" in data and isinstance(data["data"], list):
                            data_list = data["data"]
                        # Structure 3: {"results": [...]}
                        elif "results" in data and isinstance(data["results"], list):
                            data_list = data["results"]
                    elif isinstance(data, list):
                        # Structure 4: directly a list
                        data_list = data
                    
                    logger.info(f" Records found: {len(data_list)}")
                    
                    if len(data_list) == 0:
                        logger.debug(f" Full response: {json.dumps(data, indent=4)[:1000]}")
                        continue
                    
                    # ============================================
                    # PROCESS DATA
                    # ============================================
                    logger.info(f" Data found!")
                    logger.debug(f" Structure of the first record:")
                    logger.debug(f" {json.dumps(data_list[0], indent=6)[:1500]}")
                    
                    logger.debug(f" Available keys in the record: {list(data_list[0].keys())}")
                    
                    saved_count = 0
                    
                    for record in data_list:
                        # Extract timestamp from the 'datetime' field of each record
                        datetime_str = record.get("datetime", "").strip()
                        
                        # Skip records that are metadata
                        if datetime_str in ["Minimum", "Maximum", "Average", "Avg", "Summary:", 
                                             "MinDate", "MaxDate", "MinTime", "MaxTime", "Num", 
                                             "DataPrecent", "STD", ""]:
                            logger.debug(f" Skipping metadata record: {datetime_str}")
                            continue
                        
                        # Use parse_rmcab_timestamp to parse correctly
                        try:
                            timestamp = parse_rmcab_timestamp(datetime_str, "America/Bogota")
                            logger.debug(f" Parsed: {datetime_str} -> {timestamp}")
                        except Exception as e:
                            logger.warning(f" Error parsing datetime '{datetime_str}': {e}")
                            timestamp = now
                        
                        # Process each field in the record that matches a monitor
                        for key, value in record.items():
                            # Skip metadata fields
                            if key.lower() in ["timestamp", "date", "datetime", "time", "count", "id", "stationid"]:
                                continue
                            
                            # Find the corresponding monitor
                            monitor = None
                            
                            # Search 1: By exact code
                            if key in monitor_dict:
                                monitor = monitor_dict[key]
                            
                            # Search 2: By code without prefix
                            if monitor is None:
                                for code, mon in monitor_dict.items():
                                    if key.endswith(code.split('_')[-1]):
                                        monitor = mon
                                        break
                            
                            if monitor is None:
                                logger.debug(f" Monitor not found for code: {key}")
                                continue
                            
                            # Validate and convert value
                            if value is None or value == "":
                                continue
                            
                            value_str = str(value).strip()
                            
                            # Skip common invalid values
                            if value_str in ["----", "-", "N/A", "NA", "null", "None"]:
                                continue
                            
                            # Skip if it looks like a date
                            if "-" in value_str and any(c.isdigit() for c in value_str):
                                if value_str.count("-") >= 2 or ":" in value_str:
                                    logger.debug(f" Skipping date/time value for {key}: {value_str}")
                                    continue
                            
                            # Skip if it contains ":"
                            if ":" in value_str:
                                logger.debug(f" Skipping time value for {key}: {value_str}")
                                continue
                            
                            try:
                                float_value = float(value_str)
                                
                                # Validate that the value is reasonable
                                if float_value < -999999 or float_value > 999999:
                                    logger.warning(f" Value out of range for {key}: {float_value}")
                                    continue
                                
                                logger.debug(f" -> {monitor.type}: {float_value} {monitor.unit}")
                                
                                # Check if the sensor already exists (avoid duplicates)
                                existing_sensor = db.query(Sensor).filter(
                                    Sensor.monitor_id == monitor.id,
                                    Sensor.timestamp == timestamp
                                ).first()
                                
                                if existing_sensor:
                                    logger.debug(f" Sensor already exists (ID: {existing_sensor.id}), skipping...")
                                    continue
                                
                                # Create sensor record only if it doesn't exist
                                new_sensor = Sensor(
                                    monitor_id=monitor.id,
                                    timestamp=timestamp,
                                    value=float_value
                                )
                                db.add(new_sensor)
                                saved_count += 1
                                
                            except (ValueError, TypeError) as e:
                                logger.warning(f" Error converting value {key}={value}: {e}")
                            
                    # Save to database
                    if saved_count > 0:
                        db.commit()
                        logger.info(f" {saved_count} sensors saved successfully")
                        data_found = True
                    else:
                        logger.warning(f" No sensors were saved (no code matches)")

                except requests.exceptions.Timeout:
                    logger.error(f" Timeout on request for {config['name']}")
                except requests.exceptions.RequestException as e:
                    logger.error(f" Network error: {str(e)}")
                except json.JSONDecodeError as e:
                    logger.error(f" Error parsing JSON: {str(e)}")
                    logger.debug(f" Response: {response.text[:500]}")
                except Exception as e:
                    logger.exception(f" Error processing {config['name']}: {str(e)}")
                    db.rollback()
            
            if not data_found:
                logger.warning(f"No data found for {station.name} in any time range")

    except Exception as e:
        logger.error(f"General error in fetch_reports_job: {str(e)}")
        logger.exception("Full stack trace:")
        db.rollback()
    finally:
        db.close()

    logger.info("\nTask completed\n")

def log_execution_summary():
    """
    Logs an execution summary to a log file for auditing.
    """
    import os
    
    db = SessionLocal()
    try:
        total_sensors = db.query(Sensor).count()
        total_monitors = db.query(Monitor).count()
        total_stations = db.query(Station).count()
        
        # Get timestamp of the last inserted sensor
        last_sensor = db.query(Sensor).order_by(Sensor.id.desc()).first()
        last_timestamp = last_sensor.timestamp if last_sensor else None
        
        log_file = "logs/fetch_summary.log"
        os.makedirs("logs", exist_ok=True)
        
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"\n{'='*80}\n")
            f.write(f"Execution: {datetime.now(pytz.timezone('America/Bogota')).strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total Sensors in DB: {total_sensors}\n")
            f.write(f"Total Monitors: {total_monitors}\n")
            f.write(f"Total Stations: {total_stations}\n")
            f.write(f"Last inserted sensor: {last_timestamp}\n")
            f.write(f"{'='*80}\n")
        
        logger.info(f"DB Summary:")
        logger.info(f" - Total Sensors: {total_sensors}")
        logger.info(f" - Total Monitors: {total_monitors}")
        logger.info(f" - Total Stations: {total_stations}")
        logger.info(f" - Last timestamp: {last_timestamp}")
        
    finally:
        db.close()

    
if __name__ == "__main__":
    print("Running fetch_reports_job manually...")
    fetch_reports_job()
    log_execution_summary()
    print("\nCheck logs/fetch_summary.log for execution history")
