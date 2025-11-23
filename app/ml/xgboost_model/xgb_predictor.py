import os
import logging
import numpy as np
import xgboost as xgb

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Constants and global cache
# -----------------------------------------------------------------------------
VALID_HORIZONS = [1, 3, 6, 12]
FEATURE_ORDER = [
    "pm10", "o3", "precipitacion", "temp", "hr",
    "vviento", "dviento", "no", "no2", "nox", "co",
    "rsolar", "pm25_lag1", "pm25_lag3", "pm25_lag6",
    "pm25_lag12", "pm25_lag24"
]

_MODELS: dict[int, xgb.Booster] = {}  # cache per horizon

# -----------------------------------------------------------------------------
# Model Loading
# -----------------------------------------------------------------------------
def load_model(horizon: int = 1) -> xgb.Booster:
    """
    Load and cache the XGBoost model for a given horizon (1, 3, 6, or 12 hours).
    """
    if horizon not in VALID_HORIZONS:
        raise ValueError(f"Invalid horizon {horizon}. Must be one of {VALID_HORIZONS}")

    if horizon not in _MODELS:
        model_name = f"xgb_pm25_tplus{horizon}.json"
        model_path = os.path.join(os.path.dirname(__file__), "models", model_name)

        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model not found for {horizon}h: {model_path}")

        booster = xgb.Booster()
        booster.load_model(model_path)
        _MODELS[horizon] = booster
        logger.info(f"Loaded XGBoost model for horizon {horizon}h")

    return _MODELS[horizon]

# -----------------------------------------------------------------------------
# Prediction
# -----------------------------------------------------------------------------
def predict_one(features: dict, horizon: int = 1) -> float:
    """
    Predict PM2.5 concentration for a single record at the specified horizon.
    Automatically reorders features to match training order.
    """
    if not validate_features(features):
        raise ValueError("Invalid or missing features for prediction.")

    model = load_model(horizon)
    ordered_values = [features[name] for name in FEATURE_ORDER]
    dmat = xgb.DMatrix(np.array([ordered_values]))

    prediction = float(model.predict(dmat)[0])
    prediction = max(0.0, prediction)  # clip negatives
    logger.debug(f"Prediction ({horizon}h): {prediction:.2f} µg/m³")

    return prediction


def predict_batch(records: list[dict], horizon: int = 1) -> list[float]:
    """
    Predict PM2.5 concentration for multiple records at a given horizon.
    """
    if not records:
        return []

    model = load_model(horizon)

    try:
        matrix = [[record[name] for name in FEATURE_ORDER] for record in records]
    except KeyError as e:
        raise ValueError(f"Missing feature in batch: {e}")

    dmat = xgb.DMatrix(np.array(matrix))
    predictions = model.predict(dmat).tolist()
    predictions = [max(0.0, p) for p in predictions]

    logger.info(f"Batch prediction completed: {len(records)} samples, horizon={horizon}h")
    return predictions


def predict_all_horizons(features: dict) -> dict[int, float | None]:
    """
    Predict PM2.5 concentration for all available horizons (1, 3, 6, 12h).
    Returns a dictionary mapping horizon → predicted value or None if failed.
    """
    results: dict[int, float | None] = {}
    for horizon in VALID_HORIZONS:
        try:
            results[horizon] = predict_one(features, horizon)
        except Exception as e:
            logger.error(f"Prediction failed for horizon {horizon}h: {e}")
            results[horizon] = None
    return results

# -----------------------------------------------------------------------------
# Validation and Metadata
# -----------------------------------------------------------------------------
def validate_features(features: dict) -> bool:
    """
    Check if the provided feature dictionary has all required inputs.
    """
    missing = set(FEATURE_ORDER) - set(features)
    extra = set(features) - set(FEATURE_ORDER)

    if missing:
        logger.error(f"Missing features: {missing}")
        return False
    if extra:
        logger.warning(f"Extra features ignored: {extra}")

    return True


def get_feature_order() -> list[str]:
    """Return the expected order of features for model input."""
    return FEATURE_ORDER.copy()


def get_model_info(horizon: int) -> dict:
    """Return metadata for a given model horizon."""
    try:
        model = load_model(horizon)
        return {
            "horizon": horizon,
            "num_features": model.num_features(),
            "num_boosted_rounds": model.num_boosted_rounds(),
            "feature_names": model.feature_names or [],
            "expected_order": FEATURE_ORDER,
            "loaded": True,
        }
    except Exception as e:
        logger.error(f"Error retrieving model info for {horizon}h: {e}")
        return {"horizon": horizon, "loaded": False, "error": str(e)}
