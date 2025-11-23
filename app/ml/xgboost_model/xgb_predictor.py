import os
import logging
import numpy as np
import xgboost as xgb
from app.ml.base_model import BasePredictor

logger = logging.getLogger(__name__)

class XGBoostPredictor(BasePredictor):
    """
    Predictor basado en modelos XGBoost entrenados para diferentes horizontes de tiempo.
    Implementa la interfaz BasePredictor.
    """

    VALID_HORIZONS = [1, 3, 6, 12]
    FEATURE_ORDER = [
        "pm10", "o3", "precipitacion", "temp", "hr",
        "vviento", "dviento", "no", "no2", "nox", "co",
        "rsolar", "pm25_lag1", "pm25_lag3", "pm25_lag6",
        "pm25_lag12", "pm25_lag24"
    ]

    def __init__(self):
        self._models: dict[int, xgb.Booster] = {}
        self.model_dir = os.path.join(os.path.dirname(__file__), "models")
        self.model_type = "xgboost"

    def _load_model(self, horizon: int) -> xgb.Booster:
        """Load and cache an XGBoost model for a given horizon."""
        if horizon not in self.VALID_HORIZONS:
            raise ValueError(f"Invalid horizon {horizon}. Must be one of {self.VALID_HORIZONS}")

        if horizon not in self._models:
            model_name = f"xgb_pm25_tplus{horizon}.json"
            model_path = os.path.join(self.model_dir, model_name)

            if not os.path.exists(model_path):
                raise FileNotFoundError(f"Model not found for {horizon}h: {model_path}")

            booster = xgb.Booster()
            booster.load_model(model_path)
            self._models[horizon] = booster
            logger.info(f"Loaded XGBoost model for horizon {horizon}h")

        return self._models[horizon]

    def _validate_features(self, features: dict) -> bool:
        """Ensure all required features are present."""
        missing = set(self.FEATURE_ORDER) - set(features)
        if missing:
            logger.error(f"Missing features: {missing}")
            return False
        return True

    def predict(self, features: dict, horizon: int = 1) -> float:
        """Predict PM2.5 concentration for a single record and horizon."""
        if not self._validate_features(features):
            raise ValueError("Invalid or missing features for prediction.")

        model = self._load_model(horizon)
        ordered_values = [features[name] for name in self.FEATURE_ORDER]
        dmat = xgb.DMatrix(np.array([ordered_values]))
        prediction = float(model.predict(dmat)[0])
        return max(0.0, prediction)

    def get_info(self) -> dict:
        """Return metadata about this predictor."""
        return {
            "model_type": self.model_type,
            "valid_horizons": self.VALID_HORIZONS,
            "expected_features": self.FEATURE_ORDER,
            "num_features": len(self.FEATURE_ORDER),
            "loaded_models": list(self._models.keys()),
        }
