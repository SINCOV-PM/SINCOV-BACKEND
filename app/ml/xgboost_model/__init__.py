"""
XGBoost Model Module

Provides PM2.5 forecasting models for different horizons (1h, 3h, 6h, 12h).
Exports helper functions to load, validate, and use trained XGBoost models.
"""

from app.ml.xgboost_model.xgb_predictor import (
    load_model,
    predict_one,
    predict_batch,
    predict_all_horizons,
    get_model_info,
    validate_features,
    get_feature_order,
    VALID_HORIZONS,
)

__all__ = [
    "load_model",
    "predict_one",
    "predict_batch",
    "predict_all_horizons",
    "get_model_info",
    "validate_features",
    "get_feature_order",
    "VALID_HORIZONS",
]

__version__ = "1.0.0"
