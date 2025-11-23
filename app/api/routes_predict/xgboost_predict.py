from fastapi import APIRouter, HTTPException
from .schemas import PredictionRequest, PredictionResponse
from app.services.prediction_service import generate_prediction, PredictionError
import logging

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Prediction"])


@router.post("/", response_model=PredictionResponse)
async def predict_pm25(request: PredictionRequest):
    """
    Generate PM2.5 predictions using XGBoost models.
    """
    logger.info(f"Prediction request for station {request.station_id}, horizons: {request.horizons}")
    try:
        result = generate_prediction(request.station_id, request.horizons)
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
