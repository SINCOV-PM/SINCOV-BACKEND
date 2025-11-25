from fastapi import APIRouter, HTTPException
from .schemas import PredictionRequest, PredictionResponse
from app.services.prediction_service import generate_prediction, PredictionError
import logging

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Prediction"])


@router.post("/", response_model=PredictionResponse)
async def predict_pm25(request: PredictionRequest):
    """
    Generate PM2.5 predictions using the selected model (XGBoost or Prophet).
    Default model: XGBoost.
    """
    model_type = request.model_type.lower() if hasattr(request, "model_type") and request.model_type else "xgboost"
    logger.info(f"Prediction request | station={request.station_id} | model={model_type} | horizons={request.horizons}")

    try:
        result = generate_prediction(
            station_id=request.station_id,
            horizons=request.horizons,
            model_type=model_type
        )
        return PredictionResponse(**result)

    except PredictionError as e:
        msg = str(e).lower()
        if "not allowed" in msg:
            raise HTTPException(status_code=400, detail=str(e))
        elif "no data" in msg or "not found" in msg:
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=500, detail=str(e))

    except Exception as e:
        logger.exception("Unexpected error during prediction")
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")
