"""
Prediction Service
------------------
Handles orchestration of PM2.5 forecasting:
 - Validates allowed stations
 - Prepares input features
 - Runs ML predictions (XGBoost / Prophet)
 - Persists results in the database
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional
from sqlalchemy import text

from app.db.session import SessionLocal
from app.models.predict import Prediction
from app.services.features_service import (
    prepare_features_for_prediction,
    get_station_name,
    FeaturePreparationError,
)
from app.ml.xgboost_model.xgb_predictor import predict_one

logger = logging.getLogger(__name__)

# -------------------------------------------------------------------------
# Constants and custom exceptions
# -------------------------------------------------------------------------
ALLOWED_STATIONS = [
    "Centro_de_Alto_Rendimiento", "Guaymaral", "San_Cristobal", "Tunal",
    "Puente_Aranda", "Kennedy", "Fontibon", "Las_Ferias", "Usaquen", "Suba"
]
VALID_HORIZONS = [1, 3, 6, 12]


class PredictionError(Exception):
    """Raised when a prediction operation fails."""
    pass


# -------------------------------------------------------------------------
# Station validation
# -------------------------------------------------------------------------
def is_station_allowed(station_id: int) -> bool:
    """Check if a given station is eligible for predictions."""
    station_name = get_station_name(station_id)
    if not station_name:
        return False

    normalized_name = (
        station_name.lower().replace(" ", "_").replace(".", "")
    )
    return any(allowed.lower() == normalized_name for allowed in ALLOWED_STATIONS)


# -------------------------------------------------------------------------
# Core prediction logic
# -------------------------------------------------------------------------
def generate_prediction(station_id: int, horizons: Optional[List[int]] = None) -> Dict:
    """
    Generate PM2.5 predictions for a given station using XGBoost models.

    Args:
        station_id: Station ID.
        horizons: List of forecast horizons (default: [1, 3, 6, 12]).

    Returns:
        Dict with all prediction results.

    Raises:
        PredictionError: if something goes wrong.
    """
    logger.info(f"Starting prediction for station {station_id}")

    horizons = horizons or VALID_HORIZONS
    horizons = [h for h in horizons if h in VALID_HORIZONS]
    if not horizons:
        raise PredictionError(f"Invalid horizons. Must be one or more of {VALID_HORIZONS}")

    if not is_station_allowed(station_id):
        station_name = get_station_name(station_id) or "Unknown"
        raise PredictionError(
            f"Station '{station_name}' is not allowed. "
            f"Allowed stations: {', '.join(ALLOWED_STATIONS)}"
        )

    try:
        # 1️⃣ Prepare features
        logger.info("Preparing input features...")
        features = prepare_features_for_prediction(station_id)

        # 2️⃣ Predict for each horizon
        now = datetime.now(timezone.utc)
        predictions = []

        for horizon in horizons:
            try:
                predicted_value = predict_one(features, horizon=horizon)
                prediction_time = now + timedelta(hours=horizon)

                predictions.append({
                    "horizon": horizon,
                    "predicted_pm25": round(predicted_value, 2),
                    "timestamp": prediction_time.isoformat(),
                    "features_used": len(features),
                })

                logger.info(f"H{horizon}: {predicted_value:.2f} μg/m³")

            except Exception as e:
                logger.error(f"Prediction failed for H{horizon}: {e}")
                predictions.append({
                    "horizon": horizon,
                    "predicted_pm25": None,
                    "error": str(e),
                })

        # 3️⃣ Build response
        station_name = get_station_name(station_id)
        result = {
            "success": True,
            "station_id": station_id,
            "station_name": station_name,
            "predictions": predictions,
            "features": features,
            "generated_at": now.isoformat(),
            "method": "xgboost",
            "model_version": "1.0.0",
        }

        logger.info(f"✅ Generated {len(predictions)} predictions for station {station_id}")
        return result

    except FeaturePreparationError as e:
        logger.error(f"Feature preparation failed: {e}")
        raise PredictionError(f"Cannot prepare data: {e}")

    except Exception as e:
        logger.exception(f"Unexpected prediction error: {e}")
        raise PredictionError(f"Prediction failed: {e}")


def generate_all_horizons_prediction(station_id: int) -> Dict:
    """Convenience wrapper to predict for all horizons."""
    return generate_prediction(station_id, horizons=VALID_HORIZONS)


# -------------------------------------------------------------------------
# Database persistence
# -------------------------------------------------------------------------
def save_prediction_to_db(
    station_id: int,
    features: Dict,
    result: float,
    horizon: int = 1,
) -> Prediction:
    """Save a prediction record into the database."""
    db = SessionLocal()
    try:
        prediction = Prediction(
            station_id=station_id,
            features=features,
            result=result,
            horizon=horizon,
            created_at=datetime.now(timezone.utc),
        )
        db.add(prediction)
        db.commit()
        db.refresh(prediction)

        logger.info(f"Saved prediction {prediction.id} (H{horizon}) for station {station_id}")
        return prediction
    except Exception as e:
        db.rollback()
        logger.error(f"Error saving prediction: {e}")
        raise
    finally:
        db.close()


# -------------------------------------------------------------------------
# Retrieval utilities
# -------------------------------------------------------------------------
def get_recent_predictions(station_id: int, limit: int = 10) -> List[Dict]:
    """Return recent predictions for a given station."""
    db = SessionLocal()
    try:
        records = (
            db.query(Prediction)
            .filter(Prediction.station_id == station_id)
            .order_by(Prediction.created_at.desc())
            .limit(limit)
            .all()
        )

        return [
            {
                "id": p.id,
                "result": p.result,
                "horizon": getattr(p, "horizon", 1),
                "created_at": p.created_at.isoformat(),
                "features": p.features,
            }
            for p in records
        ]
    finally:
        db.close()


def get_allowed_stations_info() -> List[Dict]:
    """Retrieve coordinates and metadata for allowed stations."""
    db = SessionLocal()
    try:
        normalized_names = [s.lower().replace("_", " ") for s in ALLOWED_STATIONS]
        query = text("""
            SELECT id, name, latitude, longitude
            FROM stations
            WHERE LOWER(REPLACE(name, '_', ' ')) = ANY(:allowed_names)
        """)

        result = db.execute(query, {"allowed_names": normalized_names}).fetchall()
        return [
            {
                "id": row[0],
                "name": row[1],
                "lat": float(row[2]) if row[2] else None,
                "lng": float(row[3]) if row[3] else None,
            }
            for row in result
        ]
    except Exception as e:
        logger.error(f"Error fetching allowed stations: {e}")
        return []
    finally:
        db.close()
