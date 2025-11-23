from fastapi import APIRouter, HTTPException
from app.services.prediction_service import get_allowed_stations_info
import logging

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Stations"])


@router.get("/allowed-stations")
async def get_allowed_stations():
    """
    Get list of stations that support XGBoost predictions.
    """
    try:
        stations = get_allowed_stations_info()
        return {"success": True, "count": len(stations), "stations": stations}
    except Exception as e:
        logger.exception("Error retrieving allowed stations")
        raise HTTPException(status_code=500, detail="Error retrieving station list")
