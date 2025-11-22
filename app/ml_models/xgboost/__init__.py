"""
ML Models Module

Provides XGBoost models for PM2.5 forecasting at different time horizons.
Supports 1h, 3h, 6h, and 12h ahead predictions.
"""

from .predictor import (
    load_model,
    predict_one,
    predict_batch,  # <-- Usar 'predict_batch'
    predict_all_horizons,
    get_model_info,
    validate_features, # <-- Se recomienda añadir
    get_feature_order, # <-- Se recomienda añadir
    VALID_HORIZONS
)

__all__ = [
    "load_model",
    "predict_one",
    "predict_batch",  # <-- Usar 'predict_batch'
    "predict_all_horizons",
    "get_model_info",
    "validate_features",
    "get_feature_order",
    "VALID_HORIZONS"
]

__version__ = "1.0.0"