import requests
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import pytz
from app.db.session import SessionLocal
from app.models.station import Station
from app.models.monitor import Monitor
from app.models.sensor import Sensor
from app.utils.rmcab_utils import to_dotnet_ticks, build_rmcab_params, parse_rmcab_timestamp


class FetchJobLogger:
    """Centralized logger for fetch operations with structured formatting"""
    
    def __init__(self, name: str = __name__):
        self.logger = logging.getLogger(name)
        self._setup_logger()
    
    def _setup_logger(self):
        """Configure logger with custom formatting"""
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "%(asctime)s [%(levelname)s] %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S"
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
    
    def section_header(self, title: str):
        """Log a section header"""
        self.logger.info(f"\n{'='*80}")
        self.logger.info(title)
        self.logger.info(f"{'='*80}")
    
    def station_processing(self, station_name: str, rmcab_id: str):
        """Log station processing start"""
        self.section_header(f"Processing: {station_name} (RMCAB ID: {rmcab_id})")
    
    def monitors_found(self, count: int):
        """Log monitors found"""
        self.logger.info(f"✓ {count} monitors configured")
    
    def time_range(self, config_name: str, from_time: datetime, to_time: datetime):
        """Log time range being tested"""
        self.logger.info(f"→ Testing range: {config_name}")
        self.logger.debug(f"  From: {from_time.strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.debug(f"  To: {to_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    def api_response(self, status_code: int, records_count: int):
        """Log API response"""
        status_icon = "✓" if status_code == 200 else "✗"
        self.logger.info(f"{status_icon} Status: {status_code} | Records: {records_count}")
    
    def data_saved(self, count: int):
        """Log successful data save"""
        self.logger.info(f"✓ {count} sensors saved successfully")
    
    def warning(self, message: str):
        """Log warning"""
        self.logger.warning(f"⚠ {message}")
    
    def error(self, message: str, exception: Optional[Exception] = None):
        """Log error"""
        self.logger.error(f"✗ {message}")
        if exception:
            self.logger.exception("Full stack trace:")
    
    def task_complete(self):
        """Log task completion"""
        self.logger.info("\n" + "="*80)
        self.logger.info("Task completed")
        self.logger.info("="*80 + "\n")


class RMCABDataFetcher:
    """Handles data fetching from RMCAB API"""
    
    def __init__(self, logger: FetchJobLogger):
        self.logger = logger
        self.host = "http://rmcab.ambientebogota.gov.co"
        self.base_url = "/Report/GetMultiStationsReportNewAsync"
        self.tz = pytz.timezone("America/Bogota")
        self.time_configs = [
            {"name": "Last 24 hours", "hours": 24, "granularity": 60}
        ]
    
    def fetch_station_data(self, station: Station, monitors: List[Monitor]) -> bool:
        """
        Fetch data for a specific station
        Returns True if data was found and saved
        """
        self.logger.station_processing(station.name, station.station_rmcab_id)
        
        monitors_with_code = [m for m in monitors if m.code]
        
        if not monitors_with_code:
            self.logger.warning(f"No monitors with RMCAB code for {station.name}")
            return False
        
        self.logger.monitors_found(len(monitors_with_code))
        
        monitor_ids = [m.code for m in monitors_with_code]
        monitor_dict = {m.code: m for m in monitors_with_code}
        
        # Try different time ranges
        for config in self.time_configs:
            data_found = self._try_time_range(
                station, monitor_ids, monitor_dict, config
            )
            if data_found:
                return True
        
        self.logger.warning(f"No data found for {station.name} in any time range")
        return False
    
    def _try_time_range(
        self, 
        station: Station, 
        monitor_ids: List[str], 
        monitor_dict: Dict[str, Monitor], 
        config: Dict
    ) -> bool:
        """Try to fetch data for a specific time range"""
        now = datetime.now(self.tz)
        from_time = now - timedelta(hours=config["hours"])
        to_time = now
        
        self.logger.time_range(config["name"], from_time, to_time)
        
        # Build API parameters
        params = self._build_api_params(
            station, monitor_ids, from_time, to_time, config
        )
        
        try:
            # Make API request
            response = requests.get(
                f"{self.host}{self.base_url}", 
                params=params, 
                timeout=30
            )
            
            if response.status_code != 200:
                self.logger.warning(f"API error {response.status_code}")
                return False
            
            # Parse and process data
            data_list = self._parse_response(response)
            self.logger.api_response(response.status_code, len(data_list))
            
            if len(data_list) == 0:
                return False
            
            # Save data to database
            saved_count = self._process_and_save_data(
                data_list, monitor_dict, now
            )
            
            if saved_count > 0:
                self.logger.data_saved(saved_count)
                return True
            
        except requests.exceptions.Timeout:
            self.logger.error("Request timeout")
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Network error: {str(e)}")
        except Exception as e:
            self.logger.error(f"Error processing data", e)
        
        return False
    
    def _build_api_params(
        self, 
        station: Station, 
        monitor_ids: List[str], 
        from_time: datetime, 
        to_time: datetime, 
        config: Dict
    ) -> Dict:
        """Build API request parameters"""
        from_ticks = to_dotnet_ticks(from_time.isoformat(), str(self.tz))
        to_ticks = to_dotnet_ticks(to_time.isoformat(), str(self.tz))
        
        return build_rmcab_params(
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
    
    def _parse_response(self, response) -> List[Dict]:
        """Parse API response and extract data list"""
        try:
            data = response.json()
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON decode error: {str(e)}")
            return []
        
        # Handle different response structures
        if isinstance(data, dict):
            for key in ["Data", "data", "results"]:
                if key in data and isinstance(data[key], list):
                    return data[key]
        elif isinstance(data, list):
            return data
        
        return []
    
    def _process_and_save_data(
        self, 
        data_list: List[Dict], 
        monitor_dict: Dict[str, Monitor], 
        now: datetime
    ) -> int:
        """Process API data and save to database"""
        db = SessionLocal()
        saved_count = 0
        
        try:
            for record in data_list:
                # Parse timestamp
                timestamp = self._parse_record_timestamp(record, now)
                if timestamp is None:
                    continue
                
                # Process each field in the record
                for key, value in record.items():
                    if self._should_skip_field(key):
                        continue
                    
                    monitor = self._find_monitor(key, monitor_dict)
                    if monitor is None:
                        continue
                    
                    float_value = self._validate_value(value)
                    if float_value is None:
                        continue
                    
                    # Check for duplicates and save
                    if not self._sensor_exists(db, monitor.id, timestamp):
                        new_sensor = Sensor(
                            monitor_id=monitor.id,
                            timestamp=timestamp,
                            value=float_value
                        )
                        db.add(new_sensor)
                        saved_count += 1
            
            if saved_count > 0:
                db.commit()
        
        except Exception as e:
            db.rollback()
            self.logger.error(f"Error saving data", e)
        finally:
            db.close()
        
        return saved_count
    
    def _parse_record_timestamp(self, record: Dict, default: datetime) -> Optional[datetime]:
        """Parse timestamp from record"""
        datetime_str = record.get("datetime", "").strip()
        
        # Skip metadata records
        metadata_values = [
            "Minimum", "Maximum", "Average", "Avg", "Summary:",
            "MinDate", "MaxDate", "MinTime", "MaxTime", "Num",
            "DataPrecent", "STD", ""
        ]
        
        if datetime_str in metadata_values:
            return None
        
        try:
            return parse_rmcab_timestamp(datetime_str, "America/Bogota")
        except Exception:
            return default
    
    def _should_skip_field(self, key: str) -> bool:
        """Check if field should be skipped"""
        skip_fields = ["timestamp", "date", "datetime", "time", "count", "id", "stationid"]
        return key.lower() in skip_fields
    
    def _find_monitor(self, key: str, monitor_dict: Dict[str, Monitor]) -> Optional[Monitor]:
        """Find monitor by code"""
        # Exact match
        if key in monitor_dict:
            return monitor_dict[key]
        
        # Partial match
        for code, monitor in monitor_dict.items():
            if key.endswith(code.split('_')[-1]):
                return monitor
        
        return None
    
    def _validate_value(self, value) -> Optional[float]:
        """Validate and convert value to float"""
        if value is None or value == "":
            return None
        
        value_str = str(value).strip()
        
        # Skip invalid values
        invalid_values = ["----", "-", "N/A", "NA", "null", "None"]
        if value_str in invalid_values:
            return None
        
        # Skip date/time values
        if ":" in value_str or ("-" in value_str and value_str.count("-") >= 2):
            return None
        
        try:
            float_value = float(value_str)
            
            # Validate range
            if float_value < -999999 or float_value > 999999:
                return None
            
            return float_value
        
        except (ValueError, TypeError):
            return None
    
    def _sensor_exists(self, db, monitor_id: int, timestamp: datetime) -> bool:
        """Check if sensor already exists"""
        return db.query(Sensor).filter(
            Sensor.monitor_id == monitor_id,
            Sensor.timestamp == timestamp
        ).first() is not None


def fetch_reports_job():
    """Main job to download reports for all stations"""
    logger = FetchJobLogger(__name__)
    fetcher = RMCABDataFetcher(logger)
    
    logger.section_header("Starting RMCAB Data Fetch Job")
    
    db = SessionLocal()
    
    try:
        stations = db.query(Station).all()
        logger.logger.info(f"Found {len(stations)} stations in database")
        
        for station in stations:
            monitors = db.query(Monitor).filter(
                Monitor.station_id == station.id
            ).all()
            
            if not monitors:
                logger.warning(f"No monitors configured for {station.name}")
                continue
            
            fetcher.fetch_station_data(station, monitors)
    
    except Exception as e:
        logger.error("General error in fetch_reports_job", e)
        db.rollback()
    finally:
        db.close()
    
    logger.task_complete()


def log_execution_summary():
    """Log execution summary with database statistics"""
    logger = FetchJobLogger(__name__)
    db = SessionLocal()
    
    try:
        total_sensors = db.query(Sensor).count()
        total_monitors = db.query(Monitor).count()
        total_stations = db.query(Station).count()
        
        last_sensor = db.query(Sensor).order_by(Sensor.id.desc()).first()
        last_timestamp = last_sensor.timestamp if last_sensor else None
        
        logger.section_header("Database Summary")
        logger.logger.info(f"Total Sensors: {total_sensors}")
        logger.logger.info(f"Total Monitors: {total_monitors}")
        logger.logger.info(f"Total Stations: {total_stations}")
        logger.logger.info(f"Last timestamp: {last_timestamp}")
        
    finally:
        db.close()


if __name__ == "__main__":
    print("Running fetch_reports_job manually...\n")
    fetch_reports_job()
    log_execution_summary()