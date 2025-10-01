# app/services/rmcab_client.py
import requests
import json
import asyncio
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RMCABClient:
    def __init__(self):
        self.base_url = os.getenv("RMCAB_BASE_URL", "http://rmcab.ambientebogota.gov.co")
        self.endpoint = "/Report/GetMultiStationsReportNewAsync"
        self.cache_dir = Path("cache")
        self.cache_dir.mkdir(exist_ok=True)
        self.cache_duration = int(os.getenv("CACHE_DURATION", 3600))
        
        self.pm25_codes = {
            "27": "S_27_13", "3": "S_3_15", "5": "S_5_18", "37": "S_37_2",
            "38": "S_38_2", "30": "S_30_12", "8": "S_8_28", "34": "S_34_2",
            "9": "S_9_2", "6": "S_6_15", "17": "S_17_3", "26": "S_26_19",
            "39": "S_39_2", "13": "S_13_13", "24": "S_24_15", "11": "S_11_12",
            "4": "S_4_14", "1": "S_1_10", "32": "S_32_2"
        }
        
    def _load_station_config(self) -> Dict:
        config_path = Path("config/station_monitors.json")
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error(f"Config file {config_path} not found")
            raise FileNotFoundError("Archivo de configuración no encontrado")
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            raise
    
    def _to_dotnet_ticks(self, date_str) -> int:
        try:
            if isinstance(date_str, str):
                if date_str.endswith('Z'):
                    date_str = date_str[:-1] + '+00:00'
                dt = datetime.fromisoformat(date_str)
            else:
                dt = date_str
            
            epoch = datetime(1, 1, 1)
            delta = dt - epoch
            return int(delta.total_seconds() * 10000000)
        except Exception as e:
            logger.error(f"Error converting date: {e}")
            raise
    
    def _build_params(self, station_id: str, station_info: Dict, 
                     from_ticks: int, to_ticks: int) -> Dict:
        monitors = station_info.get("monitors", [])
        name = station_info.get("name", f"Station {station_id}")
        
        monitor_strings = []
        for m in monitors:
            if isinstance(m, int):
                monitor_strings.append(f"S_{station_id}_{m}")
            else:
                monitor_strings.append(str(m))
        
        params = {
            "ListStationId": f"[{station_id}]",
            "ListMonitorIds": json.dumps(monitor_strings),
            "FDate": str(from_ticks),
            "TDate": str(to_ticks),
            "TB": "[60]",
            "ToTB": "60",
            "ReportType": "Average",
            "first": "true",
            "take": "0",
            "skip": "0", 
            "page": "1",
            "pageSize": "0"
        }
        
        if name:
            params["ListStationsNames"] = json.dumps([name])
            
        return params
    
    async def _fetch_station_data(self, station_id: str) -> Optional[Dict]:
        try:
            config = self._load_station_config()
            if station_id not in config:
                logger.error(f"Station {station_id} not in config")
                return None
            
            station_info = config[station_id]
            
            to_date = datetime.now()
            from_date = to_date - timedelta(days=1)
            
            from_ticks = self._to_dotnet_ticks(from_date)
            to_ticks = self._to_dotnet_ticks(to_date)
            
            params = self._build_params(station_id, station_info, from_ticks, to_ticks)
            
            logger.info(f"Fetching data for station {station_id} ({station_info.get('name')})...")
            
            response = requests.get(
                f"{self.base_url}{self.endpoint}",
                params=params,
                timeout=15,
                headers={
                    'User-Agent': 'SINCOV-PM/1.0',
                    'Accept': 'application/json'
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"Successfully fetched data for station {station_id}")
                
                self._save_raw_response(station_id, data)
                self._save_to_cache(station_id, data)
                return data
            else:
                logger.error(f"RMCAB API error {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching station {station_id}: {e}")
            return None
    
    def _save_raw_response(self, station_id: str, data: Dict):
        try:
            debug_dir = Path("debug_responses")
            debug_dir.mkdir(exist_ok=True)
            
            debug_file = debug_dir / f"station_{station_id}_raw.json"
            with open(debug_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error saving raw response: {e}")
    
    def _save_to_cache(self, station_id: str, data: Dict):
        try:
            cache_file = self.cache_dir / f"station_{station_id}.json"
            cache_data = {
                "timestamp": datetime.now().isoformat(),
                "data": data
            }
            
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error saving cache: {e}")
    
    def _load_from_cache(self, station_id: str) -> Optional[Dict]:
        cache_file = self.cache_dir / f"station_{station_id}.json"
        
        if not cache_file.exists():
            return None
            
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                cached = json.load(f)
            
            timestamp = datetime.fromisoformat(cached["timestamp"])
            age = (datetime.now() - timestamp).total_seconds()
            
            if age < self.cache_duration:
                logger.info(f"Using cached data for station {station_id}")
                return cached["data"]
            else:
                return None
        except Exception as e:
            logger.error(f"Error loading cache: {e}")
            return None
    
    def _extract_pm25_value(self, station_id: str, rmcab_data: Dict) -> Optional[float]:
        try:
            pm25_code = self.pm25_codes.get(station_id)
            if not pm25_code:
                logger.error(f"No PM2.5 code for station {station_id}")
                return None
            
            # Formato 1: Lista "Data"
            if isinstance(rmcab_data, dict) and "Data" in rmcab_data:
                data_list = rmcab_data["Data"]
                if isinstance(data_list, list) and len(data_list) > 0:
                    for record in reversed(data_list):
                        if isinstance(record, dict) and pm25_code in record:
                            value = record[pm25_code]
                            if value is not None and value != "":
                                try:
                                    return float(value)
                                except (ValueError, TypeError):
                                    continue
            
            # Formato 2: Raíz
            if isinstance(rmcab_data, dict) and pm25_code in rmcab_data:
                value = rmcab_data[pm25_code]
                if value is not None and value != "":
                    try:
                        return float(value)
                    except (ValueError, TypeError):
                        pass
            
            # Formato 3: "Results"
            if isinstance(rmcab_data, dict) and "Results" in rmcab_data:
                results = rmcab_data["Results"]
                if isinstance(results, list) and len(results) > 0:
                    for record in reversed(results):
                        if isinstance(record, dict) and pm25_code in record:
                            value = record[pm25_code]
                            if value is not None and value != "":
                                try:
                                    return float(value)
                                except (ValueError, TypeError):
                                    continue
            
            logger.error(f"Could not extract PM2.5 for station {station_id}")
            return None
            
        except Exception as e:
            logger.error(f"Error extracting PM2.5: {e}")
            return None
    
    def _transform_to_standard_format(self, station_id: str, station_info: Dict, data: Dict) -> Optional[Dict]:
        try:
            coords = station_info.get("coordinates", {"lat": 4.6, "lng": -74.1})
            
            pm25_value = self._extract_pm25_value(station_id, data)
            
            if pm25_value is None:
                logger.error(f"No PM2.5 data for station {station_id}")
                return None  # NO generar aleatorio
            
            # Normalizar µg/m³ a 0-1
            normalized_value = min(pm25_value / 50.0, 1.0)
            pm25_value = round(normalized_value, 2)
            
            return {
                "id": int(station_id),
                "lat": coords["lat"],
                "lng": coords["lng"],
                "value": pm25_value,
                "name": station_info.get("name", f"Station {station_id}"),
                "last_update": datetime.now().isoformat(),
                "status": "Real Data from RMCAB",
                "data_source": "rmcab",
                "pm25_code": self.pm25_codes.get(station_id, "N/A")
            }
            
        except Exception as e:
            logger.error(f"Error transforming data: {e}")
            return None
    
    async def get_stations_data(self) -> List[Dict]:
        config = self._load_station_config()
        stations_data = []
        failed_stations = []
        
        logger.info(f"Processing {len(config)} stations...")
        
        for station_id, station_info in config.items():
            logger.info(f"Processing station {station_id}: {station_info.get('name')}")
            
            data = self._load_from_cache(station_id)
            
            if data is None:
                data = await self._fetch_station_data(station_id)
            
            if data is None:
                logger.error(f"No data for station {station_id}")
                failed_stations.append(station_id)
                continue  # Saltar, NO generar aleatorio
            
            station = self._transform_to_standard_format(station_id, station_info, data)
            
            if station:
                stations_data.append(station)
            else:
                failed_stations.append(station_id)
        
        logger.info(f"Successfully processed {len(stations_data)} stations")
        
        if failed_stations:
            logger.warning(f"Failed stations: {failed_stations}")
        
        if len(stations_data) == 0:
            raise ValueError("No se pudieron capturar datos de ninguna estación")
        
        return stations_data

rmcab_client = RMCABClient()