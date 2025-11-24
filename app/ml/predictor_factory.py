from app.ml.xgboost_model.xgb_predictor import XGBoostPredictor
from app.ml.prophet_model.prophet_predictor import ProphetPredictor

_predictors_cache = {}

def get_predictor(model_type: str = "xgboost"):
    """Return a predictor instance (cached)."""
    model_type = model_type.lower()

    if model_type in _predictors_cache:
        return _predictors_cache[model_type]

    if model_type == "xgboost":
        predictor = XGBoostPredictor()
    elif model_type == "prophet":
        predictor = ProphetPredictor()
    else:
        raise ValueError(f"Unknown model type: {model_type}")

    _predictors_cache[model_type] = predictor
    return predictor
