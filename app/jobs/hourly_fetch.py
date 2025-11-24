"""
Hourly Fetch Job
----------------
Fetches air quality data from RMCAB and stores it in the database.
Now supports two modes:
 - full_init=True  → Fetch last 24 hours (startup)
 - full_init=False → Fetch last hour (hourly job)
"""

import json
import requests
import logging
import pytz
from datetime import datetime, timedelta
from typing import List, Dict, Optional

from app.db.session import SessionLocal
from app.models.station import Station
from app.models.monitor import Monitor
from app.models.sensor import Sensor
from app.utils.rmcab_utils import (
    to_dotnet_ticks,
    build_rmcab_params,
    parse_rmcab_timestamp,
)
from app.core.config import settings


# -------------------------------------------------------------------------
# Logging Wrapper
# -------------------------------------------------------------------------
class FetchJobLogger:
    """Thin wrapper around global logging for structured messages."""
    _instance = None

    def __new__(cls, name: str = "app.jobs.hourly_fetch"):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.logger = logging.getLogger(name)
        return cls._instance

    def section_header(self, title: str):
        sep = "=" * 80
        self.logger.info(f"\n{sep}\n{title}\n{sep}")

    def info(self, msg: str):
        self.logger.info(msg)

    def warning(self, msg: str):
        self.logger.warning(msg)

    def error(self, msg: str, exc: Optional[Exception] = None):
        self.logger.error(msg)
        if exc:
            self.logger.exception(exc)

    def task_complete(self):
        sep = "=" * 80
        self.logger.info(f"\n{sep}\nTask completed successfully\n{sep}\n")


# -------------------------------------------------------------------------
# Data Fetcher
# -------------------------------------------------------------------------
class RMCABDataFetcher:
    """Handles all RMCAB API interactions and database persistence."""

    def __init__(self, logger: FetchJobLogger, full_init: bool = False):
        self.logger = logger
        self.host = getattr(settings, "RMCAB_API_URL", "http://rmcab.ambientebogota.gov.co")
        self.base_url = "/Report/GetMultiStationsReportNewAsync"
        self.tz = pytz.timezone("America/Bogota")

        # Choose time window: 24h on init, 1h otherwise
        if full_init:
            self.time_configs = [{"name": "Initial 24h Load", "hours": 24, "granularity": 60}]
        else:
            self.time_configs = [{"name": "Last hour", "hours": 1, "granularity": 60}]

    # ---------------------------------------------------------------------
    def fetch_station_data(self, station: Station, monitors: List[Monitor]) -> bool:
        """Fetch data for a single station."""
        self.logger.section_header(f"Processing: {station.name} (RMCAB ID: {station.station_rmcab_id})")

        valid_monitors = [m for m in monitors if m.code]
        if not valid_monitors:
            self.logger.warning(f"No monitors with RMCAB code for {station.name}")
            return False

        self.logger.info(f"Found {len(valid_monitors)} monitors")
        monitor_ids = [m.code for m in valid_monitors]
        monitor_dict = {m.code: m for m in valid_monitors}

        for config in self.time_configs:
            if self._try_time_range(station, monitor_ids, monitor_dict, config):
                return True

        self.logger.warning(f"No data found for {station.name} in any time range")
        return False

    # ---------------------------------------------------------------------
    def _try_time_range(self, station, monitor_ids, monitor_dict, config) -> bool:
        """Try to fetch data for a specific time window."""
        now = datetime.now(self.tz)
        from_time = now - timedelta(hours=config["hours"])
        to_time = now

        self.logger.info(f"Testing time range: {config['name']} ({from_time} → {to_time})")
        params = self._build_api_params(station, monitor_ids, from_time, to_time, config)

        try:
            response = requests.get(f"{self.host}{self.base_url}", params=params, timeout=30)
            if response.status_code != 200:
                self.logger.warning(f"API error {response.status_code}")
                return False

            data_list = self._parse_response(response)
            self.logger.info(f"API Response: {len(data_list)} records")

            if not data_list:
                return False

            saved = self._process_and_save_data(data_list, monitor_dict, now)
            if saved > 0:
                self.logger.info(f"Saved {saved} records successfully")
                return True

        except requests.Timeout:
            self.logger.error("Request timed out.")
        except requests.RequestException as e:
            self.logger.error("Network error during API call", e)
        except Exception as e:
            self.logger.error("Unexpected error while processing response", e)

        return False

    def _build_api_params(self, station, monitor_ids, from_time, to_time, config) -> Dict:
        """Construct API parameters."""
        return build_rmcab_params(
            station_id=station.station_rmcab_id,
            station_name=station.name,
            monitor_ids=monitor_ids,
            from_ticks=to_dotnet_ticks(from_time.isoformat(), str(self.tz)),
            to_ticks=to_dotnet_ticks(to_time.isoformat(), str(self.tz)),
            granularity_minutes=config["granularity"],
            report_type="Average",
            take=0,
            page_size=0,
        )

    def _parse_response(self, response) -> List[Dict]:
        """Decode JSON and normalize response."""
        try:
            data = response.json()
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in API response: {e}")
            return []

        if isinstance(data, dict):
            for key in ["Data", "data", "results"]:
                if isinstance(data.get(key), list):
                    return data[key]
        elif isinstance(data, list):
            return data
        return []

    def _process_and_save_data(self, data_list, monitor_dict, now) -> int:
        """Process and persist fetched data."""
        db = SessionLocal()
        saved = 0

        try:
            for record in data_list:
                timestamp = self._parse_timestamp(record, now)
                if not timestamp:
                    continue

                for key, value in record.items():
                    if self._skip_field(key):
                        continue

                    monitor = self._find_monitor(key, monitor_dict)
                    if not monitor:
                        continue

                    val = self._parse_value(value)
                    if val is None:
                        continue

                    if not self._sensor_exists(db, monitor.id, timestamp):
                        db.add(Sensor(monitor_id=monitor.id, timestamp=timestamp, value=val))
                        saved += 1

            if saved:
                db.commit()
        except Exception as e:
            db.rollback()
            self.logger.error("Error while saving data", e)
        finally:
            db.close()

        return saved

    # ---------------------------------------------------------------------
    @staticmethod
    def _parse_timestamp(record: Dict, default: datetime) -> Optional[datetime]:
        """Parse timestamp safely."""
        dt_str = record.get("datetime", "").strip()
        if dt_str in ["Minimum", "Maximum", "Average", "Summary:", "MinDate", "MaxDate", ""]:
            return None
        try:
            return parse_rmcab_timestamp(dt_str, "America/Bogota")
        except Exception:
            return default

    @staticmethod
    def _skip_field(key: str) -> bool:
        return key.lower() in {"timestamp", "date", "datetime", "time", "count", "id", "stationid"}

    @staticmethod
    def _find_monitor(key: str, monitor_dict: Dict[str, Monitor]) -> Optional[Monitor]:
        if key in monitor_dict:
            return monitor_dict[key]
        for code, m in monitor_dict.items():
            if key.endswith(code.split("_")[-1]):
                return m
        return None

    @staticmethod
    def _parse_value(value) -> Optional[float]:
        if value is None or str(value).strip() in {"", "----", "N/A", "NA", "null", "None"}:
            return None
        try:
            val = float(value)
            if -999999 < val < 999999:
                return val
        except (ValueError, TypeError):
            pass
        return None

    @staticmethod
    def _sensor_exists(db, monitor_id: int, timestamp: datetime) -> bool:
        return db.query(Sensor).filter(
            Sensor.monitor_id == monitor_id, Sensor.timestamp == timestamp
        ).first() is not None


# -------------------------------------------------------------------------
# Job Entrypoint
# -------------------------------------------------------------------------
def fetch_reports_job(full_init: bool = False):
    """Main job executed by the scheduler."""
    logger = FetchJobLogger()
    fetcher = RMCABDataFetcher(logger, full_init=full_init)

    title = "Initial 24h Fetch" if full_init else "Hourly 1h Fetch"
    logger.section_header(f"Starting RMCAB Data Fetch Job: {title}")

    db = SessionLocal()
    try:
        stations = db.query(Station).all()
        logger.info(f"Found {len(stations)} stations in database")

        for station in stations:
            monitors = db.query(Monitor).filter(Monitor.station_id == station.id).all()
            if not monitors:
                logger.warning(f"No monitors for {station.name}")
                continue

            fetcher.fetch_station_data(station, monitors)

    except Exception as e:
        db.rollback()
        logger.error("General error in fetch_reports_job", e)
    finally:
        db.close()

    logger.task_complete()


def log_execution_summary():
    """Log a database summary after a job run."""
    logger = FetchJobLogger()
    db = SessionLocal()

    try:
        total_sensors = db.query(Sensor).count()
        total_monitors = db.query(Monitor).count()
        total_stations = db.query(Station).count()
        last_sensor = db.query(Sensor).order_by(Sensor.id.desc()).first()

        logger.section_header("Database Summary")
        logger.info(f"Total Sensors: {total_sensors}")
        logger.info(f"Total Monitors: {total_monitors}")
        logger.info(f"Total Stations: {total_stations}")
        logger.info(f"Last timestamp: {getattr(last_sensor, 'timestamp', None)}")

    finally:
        db.close()


if __name__ == "__main__":
    from app.core.logging_config import setup_logging

    setup_logging()
    print("Running fetch_reports_job manually...\n")
    fetch_reports_job(full_init=True)
    log_execution_summary()
