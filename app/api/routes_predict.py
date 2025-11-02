from fastapi import APIRouter, HTTPException
from app.schemas.predict_schema import (
    PMRequest,
    PredictionRequest,
    PredictionResponse
)
from app.services.predict_service import (
    mock_predict,
    predict_pm25_timeseries,
    check_prediction_methods
)
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/")
def predict_pm25(data: PMRequest):
    """
    Endpoint original de predicción simple.
    Mantiene compatibilidad con implementación anterior.
    """
    return {"prediction": mock_predict(data.features)}


# ===== NUEVOS ENDPOINTS PARA SERIES TEMPORALES 
@router.post("/pkl", response_model=PredictionResponse)
async def predict_with_pkl(request: PredictionRequest):
    """
    Genera predicciones de PM2.5 usando modelo .pkl/joblib.
    
    Este endpoint simula el uso de un modelo scikit-learn/XGBoost
    guardado con joblib. Cuando el equipo de ML tenga el modelo real,
    solo deben reemplazar la función en predict_service.py
    
    Args:
        request: Solicitud con station_id y time_range
    
    Returns:
        PredictionResponse: Predicciones horarias con timestamps
    """
    try:
        result = await predict_pm25_timeseries(request, method="backend_pkl")
        return result
    except ValueError as e:
        logger.warning(f"Validation error: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error in PKL prediction: {e}")
        raise HTTPException(status_code=500, detail="Error interno en predicción")


@router.post("/spark", response_model=PredictionResponse)
async def predict_with_spark(request: PredictionRequest):
    """
    Genera predicciones de PM2.5 usando modelo Spark MLlib.
    
    Este endpoint simula el uso de un modelo PySpark.
    Cuando el equipo de ML integre el modelo Spark real,
    solo deben modificar la función en predict_service.py
    
    Args:
        request: Solicitud con station_id y time_range
    
    Returns:
        PredictionResponse: Predicciones horarias con timestamps
    """
    try:
        result = await predict_pm25_timeseries(request, method="backend_spark")
        return result
    except ValueError as e:
        logger.warning(f"Validation error: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error in Spark prediction: {e}")
        raise HTTPException(status_code=500, detail="Error interno en predicción")


# ===== HEALTH CHECKS =====
@router.get("/health/predict-pkl")
async def health_check_pkl():
    """
    Verifica disponibilidad del método de predicción .pkl
    """
    return {
        "status": "healthy",
        "model_type": "joblib",
        "loaded": True,
        "mock_mode": True
    }


@router.get("/health/predict-spark")
async def health_check_spark():
    """
    Verifica disponibilidad del método de predicción Spark
    """
    return {
        "status": "healthy",
        "model_type": "spark_mllib",
        "loaded": True,
        "mock_mode": True
    }


@router.get("/methods")
async def get_available_methods():
    """
    Devuelve qué métodos de predicción están disponibles.
    Útil para debugging y verificación.
    """
    try:
        methods = await check_prediction_methods()
        return methods
    except Exception as e:
        logger.error(f"Error checking methods: {e}")
        raise HTTPException(status_code=500, detail="Error verificando métodos")