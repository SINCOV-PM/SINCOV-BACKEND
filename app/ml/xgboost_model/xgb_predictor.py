import os
import xgboost as xgb
import numpy as np
import logging

logger = logging.getLogger(__name__)

_MODELS = {}  # cache por horizonte

VALID_HORIZONS = [1, 3, 6, 12]  # ← Agregar esta constante

# ORDEN EXACTO de features según entrenamiento (modelo.py)
# Este orden es CRÍTICO - NO cambiar
FEATURE_ORDER = [
    "pm10",
    "o3",
    "precipitacion",
    "temp",
    "hr",
    "vviento",
    "dviento",
    "no",
    "no2",
    "nox",
    "co",
    "rsolar",
    "pm25_lag1",
    "pm25_lag3",
    "pm25_lag6",
    "pm25_lag12",
    "pm25_lag24"
]

def load_model(horizon: int = 1) -> xgb.Booster:
    """
    Load the model for the given horizon (1, 3, 6, or 12 hours ahead).
    """
    global _MODELS
    
    if horizon not in VALID_HORIZONS:
        raise ValueError(f"Invalid horizon {horizon}. Must be one of {VALID_HORIZONS}")
    
    if horizon not in _MODELS:
        model_name = f"xgb_pm25_tplus{horizon}.json"
        path = os.path.join(os.path.dirname(__file__), "models", model_name)
        
        if not os.path.exists(path):
            raise FileNotFoundError(f"Model not found for {horizon}h: {path}")
        
        booster = xgb.Booster()
        booster.load_model(path)
        _MODELS[horizon] = booster
        logger.info(f" Model loaded for horizon {horizon}h")
    
    return _MODELS[horizon]

def predict_one(features: dict, horizon: int = 1) -> float:
    """
    Predict PM2.5 value for the given horizon (hours ahead).
    
    IMPORTANT: Features will be automatically reordered to match training order.
    """
    model = load_model(horizon)
    
    # CRITICAL: Reorder features to match training order
    try:
        ordered_values = [features[name] for name in FEATURE_ORDER]
    except KeyError as e:
        missing = str(e)
        available = list(features.keys())
        raise ValueError(
            f"Missing feature {missing}. "
            f"Expected: {FEATURE_ORDER}. "
            f"Got: {available}"
        )
    
    # Convert to numpy array (1 row, 17 columns)
    values = np.array([ordered_values])
    
    # Create DMatrix WITHOUT feature_names (models don't have them)
    dmat = xgb.DMatrix(values)
    
    # Predict
    prediction = float(model.predict(dmat)[0])
    
    # Clip negative values (PM2.5 cannot be negative)
    if prediction < 0:
        logger.warning(f" Negative prediction {prediction:.2f} for horizon {horizon}h, clipping to 0")
        prediction = 0.0
    
    logger.debug(f" Prediction for horizon {horizon}h: {prediction:.2f} µg/m³")
    
    return prediction

def predict_batch(records: list[dict], horizon: int = 1) -> list[float]:
    """
    Predict PM2.5 values for multiple records.
    
    IMPORTANT: Features will be automatically reordered to match training order.
    """
    model = load_model(horizon)
    if not records:
        return []
    
    # CRITICAL: Reorder all records
    try:
        matrix = []
        for record in records:
            ordered_values = [record[name] for name in FEATURE_ORDER]
            matrix.append(ordered_values)
    except KeyError as e:
        raise ValueError(f"Missing feature in batch: {e}")
    
    # Create DMatrix WITHOUT feature_names
    dmat = xgb.DMatrix(np.array(matrix))
    
    # Predict
    predictions = model.predict(dmat).tolist()
    
    # Clip negative values
    predictions = [max(0.0, p) for p in predictions]
    
    logger.info(f"Batch prediction for {len(records)} records, horizon {horizon}h")
    
    return predictions

def predict_all_horizons(features: dict) -> dict[int, float]:
    """Predict PM2.5 for all available horizons."""
    predictions = {}
    
    for horizon in VALID_HORIZONS:
        try:
            predictions[horizon] = predict_one(features, horizon)
        except Exception as e:
            logger.error(f"Failed to predict for horizon {horizon}h: {e}")
            predictions[horizon] = None
    
    return predictions

def validate_features(features: dict) -> bool:
    """Validate that all required features are present."""
    missing = set(FEATURE_ORDER) - set(features.keys())
    extra = set(features.keys()) - set(FEATURE_ORDER)
    
    if missing:
        logger.error(f" Missing features: {missing}")
        return False
    
    if extra:
        logger.warning(f" Extra features (will be ignored): {extra}")
    
    return True

def get_feature_order() -> list:
    """Get the expected feature order."""
    return FEATURE_ORDER.copy()

def get_model_info(horizon: int) -> dict:
    """Get metadata about a loaded model."""
    try:
        model = load_model(horizon)
        
        return {
            "horizon": horizon,
            "num_features": model.num_features(),
            "num_boosted_rounds": model.num_boosted_rounds(),
            "feature_names": model.feature_names if model.feature_names else [],
            "expected_order": FEATURE_ORDER,
            "loaded": True
        }
    except Exception as e:
        logger.error(f"Error getting model info: {e}")
        return {
            "horizon": horizon,
            "loaded": False,
            "error": str(e)
        }