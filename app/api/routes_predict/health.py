from fastapi import APIRouter
from app.ml.predictor_factory import get_predictor
import logging

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Health"])


@router.get("/health")
async def prediction_health():
    """
    Health check for prediction service.
    Verifies that all available models (XGBoost + Prophet) can be loaded.
    """
    models_status = {}

    # XGBoost health check
    try:
        xgb = get_predictor("xgboost")
        models_status["xgboost"] = {
            "loaded": True,
            "info": xgb.get_info(),
        }
    except Exception as e:
        logger.error(f"XGBoost health check failed: {e}")
        models_status["xgboost"] = {"loaded": False, "error": str(e)}

    # Prophet health check
    try:
        prophet = get_predictor("prophet")
        models_status["prophet"] = {
            "loaded": True,
            "info": prophet.get_info(),
        }
    except Exception as e:
        logger.error(f"Prophet health check failed: {e}")
        models_status["prophet"] = {"loaded": False, "error": str(e)}

    all_loaded = all(m["loaded"] for m in models_status.values())

    return {
        "service": "prediction",
        "status": "healthy" if all_loaded else "degraded",
        "models": models_status,
        "note": "Use POST /predict with 'model_type' = 'xgboost' or 'prophet'"
    }
