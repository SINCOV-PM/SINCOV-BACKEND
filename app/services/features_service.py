"""
Feature preparation service for ML predictions.

CRITICAL: This service must return features in the EXACT order used during training.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging
from sqlalchemy import text
from app.db.session import SessionLocal

logger = logging.getLogger(__name__)



# CRÍTICO: Este orden DEBE coincidir con el entrenamiento del modelo
# NOTA: pm25 actual NO se usa como input, solo los lags
BASE_FEATURES_ORDER = [
    "pm10", 
    "o3", 
    "precipitacion", 
    "temp", 
    "hr",
    "vviento", 
    "dviento", 
    "no", 
    "no2", 
    "nox", 
    "co", 
    "rsolar"
]

# Lags de PM2.5 que el modelo necesita
LAG_HOURS = [1, 3, 6, 12, 24]

# Mapeo de tipos de monitor RMCAB → nombres de features del modelo
MONITOR_TYPE_MAPPING = {
    "PM2.5": "pm25",
    "PM10": "pm10",
    "O3": "o3",
    "Precipitación": "precipitacion",
    "Precipitacion": "precipitacion",
    "Temperatura": "temp",
    "Temp": "temp",
    "Humedad Relativa": "hr",
    "HR": "hr",
    "Velocidad del Viento": "vviento",
    "VViento": "vviento",
    "Dirección del Viento": "dviento",
    "DViento": "dviento",
    "NO": "no",
    "NO2": "no2",
    "NOx": "nox",
    "NOX": "nox",
    "CO": "co",
    "Radiación Solar": "rsolar",
    "RSolar": "rsolar"
}


class FeaturePreparationError(Exception):
    """Exception raised when feature preparation fails."""
    pass


def get_last_30_hours_data(station_id: int) -> List[Dict]:
    """Retrieve the last 30 hours of sensor data for a specific station."""
    db = SessionLocal()
    
    try:
        now = datetime.now()
        from_time = now - timedelta(hours=30)
        
        query = text("""
            SELECT 
                DATE_TRUNC('hour', s.timestamp AT TIME ZONE 'America/Bogota') as hour,
                m.type as monitor_type,
                AVG(s.value) as avg_value
            FROM sensors s
            JOIN monitors m ON s.monitor_id = m.id
            JOIN stations st ON m.station_id = st.id
            WHERE st.id = :station_id
              AND s.timestamp >= :from_time
            GROUP BY DATE_TRUNC('hour', s.timestamp AT TIME ZONE 'America/Bogota'), m.type
            ORDER BY hour DESC
        """)
        
        result = db.execute(query, {
            "station_id": station_id,
            "from_time": from_time
        }).fetchall()
        
        if not result:
            raise FeaturePreparationError(
                f"No data available for station {station_id} in the last 30 hours"
            )
        
        hours_data = {}
        for row in result:
            hour = row[0]
            monitor_type = row[1]
            avg_value = float(row[2])
            
            if hour not in hours_data:
                hours_data[hour] = {}
            
            feature_name = MONITOR_TYPE_MAPPING.get(monitor_type)
            if feature_name:
                hours_data[hour][feature_name] = avg_value
        
        return [
            {"hour": hour, "data": data}
            for hour, data in sorted(hours_data.items(), reverse=True)
        ]
        
    except Exception as e:
        logger.error(f"Error retrieving data for station {station_id}: {e}")
        raise FeaturePreparationError(str(e))
    finally:
        db.close()


def impute_missing_features(data: Dict[str, float]) -> Dict[str, float]:
    """
    Impute missing features with 0 and return in CORRECT ORDER.
    
    IMPORTANTE: Usa imputación a 0 para datos faltantes.
    Si necesitas otra estrategia (media, último valor conocido), modifica aquí.
    """
    imputed = {}
    for feature in BASE_FEATURES_ORDER:
        imputed[feature] = data.get(feature, 0.0)
    return imputed


def calculate_pm25_lags(hours_data: List[Dict]) -> Dict[str, float]:
    """
    Calculate PM2.5 lag features in CORRECT ORDER.
    
    Args:
        hours_data: Lista de datos horarios ordenados de más reciente a más antiguo
    
    Returns:
        Dict con lags en formato {"pm25_lag1": value, "pm25_lag3": value, ...}
    """
    lags = {}
    for lag in LAG_HOURS:
        if lag < len(hours_data):
            pm25_value = hours_data[lag]["data"].get("pm25", 0.0)
        else:
            pm25_value = 0.0
        lags[f"pm25_lag{lag}"] = pm25_value
    return lags


def prepare_features_for_prediction(station_id: int) -> Dict[str, float]:
    """
    Prepare complete feature set for ML prediction.

    Returns features in the EXACT order expected by the model:
    1. Base features (pm25, pm10, o3, ..., rsolar)
    2. Lag features (pm25_lag1, pm25_lag3, ..., pm25_lag24)
    
    Args:
        station_id: ID de la estación
    
    Returns:
        Dict con features ordenadas correctamente
        
    Raises:
        FeaturePreparationError: Si no hay datos o falla la preparación
    """
    logger.info(f"Preparing features for station {station_id}")
    
    try:
        # 1. Obtener datos históricos
        hours_data = get_last_30_hours_data(station_id)
        if not hours_data:
            raise FeaturePreparationError("No historical data available")
        
        # 2. Preparar features base (hora actual)
        current_data = hours_data[0]["data"]
        base_features = impute_missing_features(current_data)
        
        # 3. Calcular lags de PM2.5
        lag_features = calculate_pm25_lags(hours_data)
        
        # 4. Ensamblar features en orden correcto
        ordered_features = {}
        
        # Primero: Base features en orden
        for feature in BASE_FEATURES_ORDER:
            ordered_features[feature] = base_features[feature]
        
        # Segundo: Lag features en orden
        for lag in LAG_HOURS:
            ordered_features[f"pm25_lag{lag}"] = lag_features[f"pm25_lag{lag}"]
        
        logger.info(f"Successfully prepared {len(ordered_features)} features for station {station_id}")
        logger.debug(f"Feature order: {list(ordered_features.keys())}")
        
        return ordered_features
        
    except Exception as e:
        logger.error(f"Feature preparation failed: {e}")
        raise FeaturePreparationError(str(e))


def validate_features(features: dict) -> bool:
    """
    Validate that the feature dictionary contains all expected features.
    
    Args:
        features: Dict de features a validar
    
    Returns:
        True si todas las features están presentes y son válidas
        
    Raises:
        FeaturePreparationError: Si faltan features o tienen valores inválidos
    """
    # Verificar que estén todas las features base
    missing = [f for f in BASE_FEATURES_ORDER if f not in features]
    
    # Verificar que estén todas las features lag
    lag_missing = [f"pm25_lag{lag}" for lag in LAG_HOURS if f"pm25_lag{lag}" not in features]
    
    if missing or lag_missing:
        raise FeaturePreparationError(f"Missing features: {missing + lag_missing}")
    
    # Verificar tipos válidos
    for key, value in features.items():
        if not isinstance(value, (int, float)):
            raise FeaturePreparationError(f"Invalid value for {key}: {value} (type: {type(value)})")
    
    logger.info(f" Feature validation passed: {len(features)} features")
    return True


def get_station_name(station_id: int) -> Optional[str]:
    """Get station name by ID."""
    db = SessionLocal()
    try:
        result = db.execute(
            text("SELECT name FROM stations WHERE id = :id"),
            {"id": station_id}
        ).fetchone()
        return result[0] if result else None
    finally:
        db.close()