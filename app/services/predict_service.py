import random
from datetime import datetime, timedelta
from typing import List, Literal
from app.schemas.predict_schema import (
    PredictionRequest,
    PredictionResponse,
    PredictionPoint,
    TimeRange
)
from app.services.stations_service import get_stations_pm25
import logging

logger = logging.getLogger(__name__)

# ===== FUNCIÓN ORIGINAL (mantener compatibilidad) =====
def mock_predict(features: list[float]) -> float:
    """
    Función original de predicción simple.
    .
    """
    return round(random.uniform(0.2, 0.9), 2)


# ===== NUEVAS FUNCIONES PARA SERIES TEMPORALES =====

def time_range_to_hours(time_range: TimeRange) -> int:
    """Convierte el rango temporal a número de horas."""
    mapping = {
        "1h": 1,
        "3h": 3,
        "6h": 6,
        "12h": 12,
        "24h": 24,
        "48h": 48
    }
    return mapping[time_range]


def get_station_info(station_id: int) -> dict:
    """
    Obtiene información de una estación.
    Reutiliza la función existente de stations_service.
    """
    try:
        stations = get_stations_pm25()
        station = next((s for s in stations if s["id"] == station_id), None)
        
        if not station:
            raise ValueError(f"Estación {station_id} no encontrada")
        
        return station
    except Exception as e:
        logger.error(f"Error obteniendo estación {station_id}: {e}")
        raise


def generate_realistic_predictions(
    station_id: int,
    station_name: str,
    current_pm25: float,
    hours: int,
    start_time: str | None
) -> List[PredictionPoint]:
    """
    Genera predicciones mock con algoritmo realista.
    
    Algoritmo:
    1. Random walk con drift (tendencia aleatoria)
    2. Ciclo diurno (más contaminación en horas pico: 7-9, 17-19)
    3. Ruido gaussiano
    4. Error proporcional al horizonte temporal
    
    Args:
        station_id: ID de la estación
        station_name: Nombre de la estación
        current_pm25: Valor actual de PM2.5
        hours: Cantidad de horas a predecir
        start_time: Timestamp de inicio (opcional)
    
    Returns:
        List[PredictionPoint]: Lista de predicciones horarias
    """
    # Determinar timestamp inicial
    if start_time:
        try:
            start = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
        except Exception:
            start = datetime.now()
    else:
        start = datetime.now()
    
    predictions = []
    value = current_pm25
    
    for i in range(1, hours + 1):
        timestamp = start + timedelta(hours=i)
        hour = timestamp.hour
        
        # 1. Random walk con drift
        drift = (random.random() - 0.5) * 2  # ±1 μg/m³ por hora
        
        # 2. Ciclo diurno (más contaminación en horas pico)
        diurnal_effect = 0
        if 7 <= hour <= 9:  # Pico matutino (tráfico)
            diurnal_effect = 3 + random.random() * 5
        elif 17 <= hour <= 19:  # Pico vespertino (tráfico)
            diurnal_effect = 4 + random.random() * 6
        elif 0 <= hour <= 5:  # Valle nocturno (menos actividad)
            diurnal_effect = -(2 + random.random() * 3)
        
        # 3. Ruido gaussiano (aproximación con suma de uniformes)
        noise = (random.random() + random.random() + random.random() - 1.5) * 1.5
        
        # Actualizar valor con límites realistas (5-150 μg/m³)
        value = max(5.0, min(150.0, value + drift + diurnal_effect + noise))
        
        # 4. Error proporcional al horizonte temporal
        base_error = 5.0  # 5% base de error
        time_error = (i / hours) * 15  # hasta +15% adicional al final
        random_noise = random.random() * 5  # variabilidad aleatoria
        error_percentage = base_error + time_error + random_noise
        
        predictions.append(
            PredictionPoint(
                timestamp=timestamp.isoformat(),
                predicted_pm25=round(value, 1),
                error_percentage=round(error_percentage, 1)
            )
        )
    
    return predictions


async def predict_pm25_timeseries(
    request: PredictionRequest,
    method: Literal["backend_pkl", "backend_spark"]
) -> PredictionResponse:
    """
    Genera predicción de serie temporal de PM2.5.
    
    IMPORTANTE PARA EL EQUIPO DE ML:
    Esta función actualmente usa datos MOCK. Para integrar el modelo real:
    
    1. Si method == "backend_pkl":
       - Cargar modelo con joblib: model = joblib.load("path/to/model.pkl")
       - Preparar features desde la BD
       - Predecir: predictions = model.predict(features)
    
    2. Si method == "backend_spark":
       - Inicializar Spark Session
       - Cargar modelo: model = PipelineModel.load("path/to/spark_model")
       - Crear DataFrame con features
       - Predecir: df_pred = model.transform(df_features)
    
    Args:
        request: Solicitud de predicción con station_id y time_range
        method: Método de predicción a usar ("backend_pkl" o "backend_spark")
    
    Returns:
        PredictionResponse: Respuesta con predicciones horarias
    
    Raises:
        ValueError: Si la estación no existe
        Exception: Si hay error en la predicción
    """
    try:
        # Obtener información de la estación
        station = get_station_info(request.station_id)
        
        # Convertir time_range a horas
        hours = time_range_to_hours(request.time_range)
        
        # Simular latencia del modelo
        # PKL: 1-2 segundos, Spark: 2-4 segundos (Spark es más lento al iniciar)
        import time
        if method == "backend_spark":
            time.sleep(1 + random.random() * 2)
        else:
            time.sleep(0.5 + random.random())
        
        # Generar predicciones (actualmente mock)
        predictions = generate_realistic_predictions(
            station_id=request.station_id,
            station_name=station["name"],
            current_pm25=station["value"],
            hours=hours,
            start_time=request.start_time
        )
        
        # Si es método Spark, agregar pequeña variación para simular diferencia
        if method == "backend_spark":
            for pred in predictions:
                pred.predicted_pm25 += random.uniform(-1, 1)
                pred.predicted_pm25 = round(max(5.0, pred.predicted_pm25), 1)
        
        logger.info(f"Generated {len(predictions)} predictions for station {request.station_id} using {method}")
        
        return PredictionResponse(
            success=True,
            station_id=request.station_id,
            station_name=station["name"],
            time_range=request.time_range,
            method=method,
            predictions=predictions,
            generated_at=datetime.now().isoformat()
        )
    
    except ValueError:
        # Re-lanzar errores de validación
        raise
    except Exception as e:
        logger.error(f"Error en predicción {method}: {e}")
        raise Exception(f"Error generando predicción: {str(e)}")


async def check_prediction_methods() -> dict:
    """
    Verifica qué métodos de predicción están disponibles.
    
    Returns:
        dict: Estado de cada método (mock_mode=True por ahora)
    """
    return {
        "backend_pkl": {
            "available": True,
            "mock_mode": True,
            "description": "Modelo .pkl/joblib (actualmente mock)"
        },
        "backend_spark": {
            "available": True,
            "mock_mode": True,
            "description": "Modelo Spark MLlib (actualmente mock)"
        }
    }


# ===== FUNCIONES PARA INTEGRACIÓN FUTURA (comentadas) =====
"""
PARA EL EQUIPO DE ML: Ejemplo de cómo integrar el modelo real

def load_pkl_model():
    '''Carga el modelo .pkl una sola vez al iniciar'''
    import joblib
    model = joblib.load("models/xgboost_pm25.pkl")
    return model

def prepare_features_for_pkl(station_id: int, hours: int):
    '''Prepara features desde la BD para el modelo'''
    from app.services.stations_service import get_station_detail
    
    # Obtener datos históricos
    station_data = get_station_detail(station_id)
    
    # Extraer features (ejemplo)
    # - Valores lag (t-1, t-2, ..., t-24)
    # - Hora del día, día de la semana, mes
    # - Promedios móviles
    
    features = []  # Construir array de features
    
    return features

def predict_with_real_pkl_model(model, features):
    '''Predice con el modelo real'''
    predictions = model.predict(features)
    return predictions
"""