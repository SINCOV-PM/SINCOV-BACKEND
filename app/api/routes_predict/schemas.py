from pydantic import BaseModel, Field
from typing import List, Optional


class PredictRequest(BaseModel):
    """Legacy prediction request model."""
    features: List[float]


class PredictionRequest(BaseModel):
    """Request model for PM2.5 predictions (XGBoost or Prophet)."""
    station_id: int = Field(..., description="ID of the station")
    horizons: Optional[List[int]] = Field(
        default=[1, 3, 6, 12],
        description="List of prediction horizons in hours (1, 3, 6, or 12)"
    )
    model_type: Optional[str] = Field(
        default="xgboost",
        description="Model to use for prediction: 'xgboost' or 'prophet'"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "station_id": 1,
                "horizons": [1, 3, 6, 12],
                "model_type": "xgboost"
            }
        }


class PredictionResponse(BaseModel):
    """Response model for predictions."""
    success: bool
    station_id: int
    station_name: str
    predictions: List[dict]
    generated_at: str
    method: str
    model_info: Optional[dict] = None
