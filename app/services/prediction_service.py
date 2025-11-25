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
from app.ml.predictor_factory import get_predictor

# -------------------------------------------------------------------------
# Configuration and logging
# -------------------------------------------------------------------------
logger = logging.getLogger(__name__)

ALLOWED_STATIONS = [
    "Centro_de_Alto_Rendimiento", "Guaymaral", "San_Cristobal", "Tunal",
    "Puente_Aranda", "Kennedy", "Fontibon", "Las_Ferias", "Usaquen", "Suba"
]
VALID_HORIZONS = [1, 3, 6, 12]


# -------------------------------------------------------------------------
# Custom exceptions
# -------------------------------------------------------------------------
class PredictionError(Exception):
    """Raised when a prediction operation fails."""
    pass


# -------------------------------------------------------------------------
# Station validation utilities
# -------------------------------------------------------------------------
def is_station_allowed(station_id: int) -> bool:
    """Check if a given station is eligible for predictions."""
    station_name = get_station_name(station_id)
    if not station_name:
        return False

    normalized_name = station_name.lower().replace(" ", "_").replace(".", "")
    return any(allowed.lower() == normalized_name for allowed in ALLOWED_STATIONS)


def get_allowed_stations_info() -> list[dict]:
    """Retrieve coordinates and metadata for allowed stations."""
    db = SessionLocal()
    try:
        normalized_names = [s.lower().replace("_", " ") for s in ALLOWED_STATIONS]
        result = db.execute(text("""
            SELECT id, name, latitude, longitude
            FROM stations
            WHERE LOWER(REPLACE(name, '_', ' ')) = ANY(:allowed_names)
        """), {"allowed_names": normalized_names}).fetchall()

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


# -------------------------------------------------------------------------
# Data retrieval utilities
# -------------------------------------------------------------------------
def get_pm25_history_24h(station_id: int) -> List[Dict[str, float]]:
    """
    Fetch last 24h of PM2.5 readings for Prophet.
    Converts DB timestamps from Bogotá TZ → UTC → naïve (required by Prophet).
    """
    db = SessionLocal()
    try:
        result = db.execute(text("""
            SELECT s.timestamp AT TIME ZONE 'America/Bogota' as timestamp, s.value
            FROM sensors s
            JOIN monitors m ON s.monitor_id = m.id
            WHERE m.station_id = :station_id
              AND m.type = 'PM2.5'
              AND s.timestamp >= NOW() - INTERVAL '24 hours'
            ORDER BY s.timestamp ASC
        """), {"station_id": station_id}).fetchall()

        if not result:
            raise ValueError(f"No PM2.5 data found for last 24h at station {station_id}")

        history = []
        for row in result:
            ts = row[0]

            # ts viene con timezone: 2025-11-24 23:00:00-05:00
            # convertimos a UTC
            ts_utc = ts.astimezone(timezone.utc)

            # removemos zona horaria → Prophet lo exige naive
            ts_naive = ts_utc.replace(tzinfo=None)

            history.append({
                "ds": ts_naive,
                "y": float(row[1])
            })

        return history

    finally:
        db.close()



# -------------------------------------------------------------------------
# Core prediction logic
# -------------------------------------------------------------------------
def generate_prediction(
    station_id: int,
    horizons: Optional[List[int]] = None,
    model_type: str = "xgboost",
) -> Dict:
    """
    Generate PM2.5 predictions for a given station using Prophet or XGBoost.
    """

    logger.info(f"Starting {model_type.upper()} prediction for station {station_id}")

    # Validate station
    if not is_station_allowed(station_id):
        station_name = get_station_name(station_id) or "Unknown"
        raise PredictionError(
            f"Station '{station_name}' is not allowed. "
            f"Allowed stations: {', '.join(ALLOWED_STATIONS)}"
        )

    # Horizons default
    horizons = horizons or VALID_HORIZONS

    # XGBoost valid horizons = 1,3,6,12
    # Prophet valid horizons = 24 ONLY
    if model_type == "prophet":
        horizons = [24]     # override everything
    else:
        horizons = [h for h in horizons if h in VALID_HORIZONS]

    if not horizons:
        raise PredictionError(f"Invalid horizons. Must be one or more of {VALID_HORIZONS}.")

    try:
        predictor = get_predictor(model_type)
        now = datetime.now(timezone.utc)
        predictions = []

        if model_type == "prophet":
            # Prophet ONLY supports 24h
            logger.info("Fetching 24h PM2.5 history for Prophet...")
            history = get_pm25_history_24h(station_id)

            predicted_value = predictor.predict(history, horizon=24)

            predictions.append({
                "horizon": 24,
                "predicted_pm25": round(predicted_value, 2),
                "timestamp": (now + timedelta(hours=24)).isoformat(),
            })

        else:
            # XGBoost branch
            logger.info("Preparing features for XGBoost...")
            features = prepare_features_for_prediction(station_id)

            for horizon in horizons:
                try:
                    value = predictor.predict(features, horizon=horizon)
                    predictions.append({
                        "horizon": horizon,
                        "predicted_pm25": round(value, 2),
                        "timestamp": (now + timedelta(hours=horizon)).isoformat(),
                    })
                except Exception as e:
                    logger.error(f"Prediction failed for H{horizon}: {e}")
                    predictions.append({
                        "horizon": horizon,
                        "predicted_pm25": None,
                        "error": str(e),
                    })

        station_name = get_station_name(station_id)
        return {
            "success": True,
            "station_id": station_id,
            "station_name": station_name,
            "predictions": predictions,
            "generated_at": now.isoformat(),
            "method": model_type,
            "model_info": predictor.get_info(),
        }

    except FeaturePreparationError as e:
        logger.error(f"Feature preparation failed: {e}")
        raise PredictionError(f"Cannot prepare data: {e}")
    except Exception as e:
        logger.exception(f"Unexpected prediction error: {e}")
        raise PredictionError(f"Prediction failed: {e}")

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
