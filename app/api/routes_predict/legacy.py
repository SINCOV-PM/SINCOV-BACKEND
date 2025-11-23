from fastapi import APIRouter
from .schemas import PredictRequest
import logging

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Legacy"])


@router.post("/legacy")
async def predict_legacy(request: PredictRequest):
    """
    Legacy prediction endpoint (deprecated).
    """
    logger.warning("Legacy predict endpoint called - consider migrating to /predict")
    return {
        "prediction": sum(request.features) / len(request.features),
        "message": "This is a legacy endpoint. Please use POST /predict for XGBoost predictions."
    }
