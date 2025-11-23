from fastapi import APIRouter
from app.ml.xgboost_model.xgb_predictor import get_model_info, VALID_HORIZONS

router = APIRouter(tags=["Health"])


@router.get("/health")
async def prediction_health():
    """
    Health check for prediction service.
    """
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
            models_status[f"{horizon}h"] = {"loaded": False, "error": str(e)}

    all_loaded = all(m["loaded"] for m in models_status.values())

    return {
        "service": "prediction",
        "status": "healthy" if all_loaded else "degraded",
        "models": models_status,
        "note": "Use POST /predict/ for XGBoost predictions"
    }
