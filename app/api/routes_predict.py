"""
Prediction API endpoints.

Handles PM2.5 prediction requests from the frontend.
Includes both legacy predict endpoint and new XGBoost endpoint.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
import logging

from app.services.prediction_service import (
    generate_prediction,
    get_allowed_stations_info,
    PredictionError
)

logger = logging.getLogger(__name__)
router = APIRouter()


# ==================== LEGACY ENDPOINT (mantener por compatibilidad) ====================

class PredictRequest(BaseModel):
    """Legacy prediction request model."""
    features: List[float]


@router.post("/legacy")
async def predict_legacy(request: PredictRequest):
    """
    Legacy prediction endpoint (mantener por compatibilidad).
    
    This endpoint is deprecated. Use POST /predict instead.
    """
    logger.warning("Legacy predict endpoint called - consider migrating to /predict")
    
    # Aquí puedes mantener tu lógica legacy o simplemente retornar un mensaje
    return {
        "prediction": sum(request.features) / len(request.features),
        "message": "This is a legacy endpoint. Please use POST /predict for XGBoost predictions."
    }


# ==================== NEW XGBOOST ENDPOINTS ====================

class PredictionRequest(BaseModel):
    """Request model for XGBoost predictions."""
    station_id: int = Field(..., description="ID of the station")
    horizons: Optional[List[int]] = Field(
        default=[1, 3, 6, 12],
        description="List of prediction horizons in hours (1, 3, 6, or 12)"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "station_id": 1,
                "horizons": [1, 6, 12]
            }
        }


class PredictionResponse(BaseModel):
    """Response model for predictions."""
    success: bool
    station_id: int
    station_name: str
    predictions: List[dict]
    generated_at: str
    method: str


@router.post("/", response_model=PredictionResponse)
async def predict_pm25(request: PredictionRequest):
    """
    Generate PM2.5 predictions using XGBoost models.
    
    This endpoint:
    - Validates that the station is in the allowed list (10 stations)
    - Prepares features from the last 30 hours of data
    - Imputes missing values with 0
    - Generates predictions for requested horizons (1h, 3h, 6h, 12h)
    
    Args:
        request: Prediction request with station_id and horizons
        
    Returns:
        Prediction results for requested horizons
        
    Raises:
        HTTPException: 400 if station not allowed, 404 if no data, 500 on error
        
    Example:
        ```json
        POST /predict/
        {
            "station_id": 1,
            "horizons": [1, 3, 6, 12]
        }
        
        Response:
        {
            "success": true,
            "station_id": 1,
            "station_name": "Kennedy",
            "predictions": [
                {
                    "horizon": 1,
                    "predicted_pm25": 12.5,
                    "timestamp": "2025-11-08T15:00:00Z",
                    "features_used": 17
                }
            ],
            "generated_at": "2025-11-08T14:00:00Z",
            "method": "xgboost"
        }
        ```
    """
    logger.info(
        f"XGBoost prediction request for station {request.station_id}, "
        f"horizons: {request.horizons}"
    )
    
    try:
        result = generate_prediction(
            station_id=request.station_id,
            horizons=request.horizons
        )
        
        return PredictionResponse(**result)
        
    except PredictionError as e:
        error_msg = str(e)
        
        # Determine appropriate HTTP status code
        if "not in the allowed list" in error_msg:
            logger.warning(f"Station not allowed: {request.station_id}")
            raise HTTPException(status_code=400, detail=error_msg)
        
        elif "No data available" in error_msg or "not found" in error_msg.lower():
            logger.warning(f"No data for station: {request.station_id}")
            raise HTTPException(status_code=404, detail=error_msg)
        
        else:
            logger.error(f"Prediction error: {error_msg}")
            raise HTTPException(status_code=500, detail=error_msg)
    
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/allowed-stations")
async def get_allowed_stations():
    """
    Get list of stations that support XGBoost predictions.
    
    Only these 10 stations are supported:
    - Centro_de_Alto_Rendimiento
    - Guaymaral
    - San_Cristobal
    - Tunal
    - Puente_Aranda
    - Kennedy
    - Fontibon
    - Las_Ferias
    - Usaquen
    - Suba
    
    Returns:
        List of allowed stations with IDs, names, and coordinates
        
    Example:
        ```json
        GET /predict/allowed-stations
        
        Response:
        {
            "success": true,
            "count": 10,
            "stations": [
                {
                    "id": 1,
                    "name": "Kennedy",
                    "lat": 4.123,
                    "lng": -74.456
                }
            ]
        }
        ```
    """
    try:
        stations = get_allowed_stations_info()
        
        return {
            "success": True,
            "count": len(stations),
            "stations": stations
        }
        
    except Exception as e:
        logger.error(f"Error getting allowed stations: {e}")
        raise HTTPException(
            status_code=500,
            detail="Error retrieving station list"
        )


@router.get("/health")
async def prediction_health():
    """
    Health check for prediction service.
    
    Checks:
    - Service availability
    - XGBoost model loading status for all horizons (1h, 3h, 6h, 12h)
    - Number of features and boosting rounds per model
    
    Returns:
        Service status and model information
        
    Example:
        ```json
        GET /predict/health
        
        Response:
        {
            "service": "prediction",
            "status": "healthy",
            "models": {
                "1h": {
                    "loaded": true,
                    "features": 17,
                    "rounds": 100
                },
                "3h": {...},
                "6h": {...},
                "12h": {...}
            }
        }
        ```
    """
    from app.ml_models.xgboost.predictor import get_model_info, VALID_HORIZONS
    
    models_status = {}
    
    for horizon in VALID_HORIZONS:
        try:
            info = get_model_info(horizon)
            models_status[f"{horizon}h"] = {
                "loaded": info.get("loaded", False),
                "features": info.get("num_features"),
                "rounds": info.get("num_boosted_rounds")
            }
        except Exception as e:
            models_status[f"{horizon}h"] = {
                "loaded": False,
                "error": str(e)
            }
    
    all_loaded = all(m["loaded"] for m in models_status.values())
    
    return {
        "service": "prediction",
        "status": "healthy" if all_loaded else "degraded",
        "models": models_status,
        "note": "Use POST /predict/ for XGBoost predictions"
    }