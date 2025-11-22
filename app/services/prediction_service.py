#app/services/prediction_service.py
"""
Prediction service for PM2.5 forecasting.

Orchestrates feature preparation and model prediction.
"""

from datetime import datetime, timezone, timedelta
from typing import List, Dict
import logging
from app.db.session import SessionLocal
from app.models.predict import Prediction
from app.services.features_service import (
    prepare_features_for_prediction,
    get_station_name,
    FeaturePreparationError
)

from app.ml_models.xgboost.predictor import predict_one, predict_all_horizons
logger = logging.getLogger(__name__)

# Estaciones permitidas para predicción (las 10 con datos completos)
ALLOWED_STATIONS = [
    "Centro_de_Alto_Rendimiento",
    "Guaymaral",
    "San_Cristobal",
    "Tunal",
    "Puente_Aranda",
    "Kennedy",
    "Fontibon",
    "Las_Ferias",
    "Usaquen",
    "Suba"
]


class PredictionError(Exception):
    """Exception raised when prediction fails."""
    pass


def is_station_allowed(station_id: int) -> bool:
    """
    Check if a station is allowed for predictions.
    
    Args:
        station_id: Station ID
        
    Returns:
        True if station is in the allowed list
    """
    station_name = get_station_name(station_id)
    
    if not station_name:
        return False
    
    # Normalize station name for comparison
    normalized_name = station_name.lower().replace(" ", "_").replace(".", "")
    
    return any(
        allowed.lower() == normalized_name
        for allowed in ALLOWED_STATIONS
    )


def generate_prediction(
    station_id: int,
    horizons: List[int] = None
) -> Dict:
    """
    Generate PM2.5 predictions for a station.
    
    Args:
        station_id: ID of the station
        horizons: List of horizons to predict (default: [1, 3, 6, 12])
        
    Returns:
        Dictionary with prediction results
        
    Raises:
        PredictionError: If prediction fails
        
    Example:
        >>> result = generate_prediction(1, horizons=[1, 6, 12])
        >>> print(result['predictions'])
        [
            {'horizon': 1, 'value': 12.5, 'timestamp': '...'},
            {'horizon': 3, 'value': 12.5, 'timestamp': '...'},
            {'horizon': 6, 'value': 15.8, 'timestamp': '...'},
            {'horizon': 12, 'value': 18.3, 'timestamp': '...'}
        ]
    """
    logger.info(f"Starting prediction for station {station_id}")
    
    # Default horizons
    if horizons is None:
        horizons = [1, 3, 6, 12]
    
    # Validate horizons
    valid_horizons = [1, 3, 6, 12]
    horizons = [h for h in horizons if h in valid_horizons]
    
    if not horizons:
        raise PredictionError(
            f"Invalid horizons. Must be one or more of {valid_horizons}"
        )
    
    # Check if station is allowed
    if not is_station_allowed(station_id):
        station_name = get_station_name(station_id) or "Unknown"
        raise PredictionError(
            f"Station '{station_name}' is not in the allowed list for predictions. "
            f"Only these stations are supported: {', '.join(ALLOWED_STATIONS)}"
        )
    
    try:
        # 1. Prepare features
        logger.info("Preparing features...")
        features = prepare_features_for_prediction(station_id)
        
        # 2. Generate predictions for each horizon
        logger.info(f"Generating predictions for horizons: {horizons}")
        predictions = []
        now = datetime.now(timezone.utc)
        
        for horizon in horizons:
            try:
                # Predict
                predicted_value = predict_one(features, horizon=horizon)
                
                # Calculate timestamp for this horizon
                prediction_time = now + timedelta(hours=horizon)
                
                predictions.append({
                    "horizon": horizon,
                    "predicted_pm25": round(predicted_value, 2),
                    "timestamp": prediction_time.isoformat(),
                    "features_used": len(features)
                })
                
                logger.info(
                    f" Horizon {horizon}h: {predicted_value:.2f} μg/m³"
                )
                
            except Exception as e:
                logger.error(f" Failed prediction for horizon {horizon}h: {e}")
                predictions.append({
                    "horizon": horizon,
                    "predicted_pm25": None,
                    "error": str(e)
                })
        
        # 3. Build response
        station_name = get_station_name(station_id)
        
        result = {
            "success": True,
            "station_id": station_id,
            "station_name": station_name,
            "predictions": predictions,
            "features": features,
            "generated_at": now.isoformat(),
            "method": "xgboost",
            "model_version": "1.0"
        }
        
        logger.info(
            f" Successfully generated {len(predictions)} predictions "
            f"for station {station_id}"
        )
        
        return result
        
    except FeaturePreparationError as e:
        logger.error(f" Feature preparation failed: {e}")
        raise PredictionError(f"Cannot prepare data: {str(e)}")
    
    except Exception as e:
        logger.error(f" Unexpected error in prediction: {e}", exc_info=True)
        raise PredictionError(f"Prediction failed: {str(e)}")


def generate_all_horizons_prediction(
    station_id: int
) -> Dict:
    """
    Generate predictions for ALL available horizons (1, 3, 6, 12).
    
    This is a convenience wrapper around generate_prediction.
    
    Args:
        station_id: ID of the station
        
    Returns:
        Dictionary with prediction results for all horizons
    """
    return generate_prediction(station_id, horizons=[1, 3, 6, 12])


def save_prediction_to_db(
    station_id: int,
    features: Dict,
    result: float,
    horizon: int = 1
) -> Prediction:
    """
    Save a prediction to the database.
    
    Args:
        station_id: Station ID
        features: Feature dictionary used for prediction
        result: Predicted PM2.5 value
        horizon: Prediction horizon in hours
        
    Returns:
        Saved Prediction object
    """
    db = SessionLocal()
    
    try:
        prediction = Prediction(
            station_id=station_id,
            features=features,
            result=result,
            horizon=horizon,
            created_at=datetime.now(timezone.utc)
        )
        
        db.add(prediction)
        db.commit()
        db.refresh(prediction)
        
        logger.info(
            f" Saved prediction {prediction.id} for station {station_id}, "
            f"horizon {horizon}h: {result:.2f} μg/m³"
        )
        
        return prediction
        
    except Exception as e:
        db.rollback()
        logger.error(f" Error saving prediction: {e}")
        raise
    finally:
        db.close()


def get_recent_predictions(
    station_id: int,
    limit: int = 10
) -> List[Dict]:
    """
    Get recent predictions for a station.
    
    Args:
        station_id: Station ID
        limit: Maximum number of predictions to return
        
    Returns:
        List of recent predictions
    """
    db = SessionLocal()
    
    try:
        predictions = db.query(Prediction).filter(
            Prediction.station_id == station_id
        ).order_by(
            Prediction.created_at.desc()
        ).limit(limit).all()
        
        return [
            {
                "id": p.id,
                "result": p.result,
                "horizon": getattr(p, 'horizon', 1),  # Default to 1h if not set
                "created_at": p.created_at.isoformat(),
                "features": p.features
            }
            for p in predictions
        ]
        
    finally:
        db.close()


def get_allowed_stations_info() -> List[Dict]:
    """
    Get information about stations allowed for predictions.
    
    Returns:
        List of allowed stations with their IDs and names
    """
    from sqlalchemy import text
    db = SessionLocal()
    
    try:
        # Normalize allowed names for SQL comparison
        normalized_names = [s.lower().replace("_", " ") for s in ALLOWED_STATIONS]
        
        query = text("""
            SELECT id, name, latitude, longitude
            FROM stations
            WHERE LOWER(REPLACE(name, '_', ' ')) = ANY(:allowed_names)
        """)
        
        result = db.execute(query, {
            "allowed_names": normalized_names
        }).fetchall()
        
        return [
            {
                "id": row[0],
                "name": row[1],
                "lat": float(row[2]) if row[2] else None,
                "lng": float(row[3]) if row[3] else None
            }
            for row in result
        ]
        
    except Exception as e:
        logger.error(f"Error fetching allowed stations: {e}")
        return []
    finally:
        db.close()