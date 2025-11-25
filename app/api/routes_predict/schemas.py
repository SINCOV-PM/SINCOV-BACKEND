from pydantic import BaseModel, Field, field_validator
from typing import List, Optional


class PredictRequest(BaseModel):
    """Legacy prediction request model (deprecated)."""
    features: List[float]


class PredictionRequest(BaseModel):
    """
    Request model for PM2.5 predictions.

    Behaviors:
      - model_type="xgboost" → horizons must be in {1,3,6,12}
      - model_type="prophet" → horizons are ignored and forced to [24]
    """

    station_id: int = Field(..., description="ID of the station to predict")

    horizons: Optional[List[int]] = Field(
        default=[1, 3, 6, 12],
        description=(
            "Prediction horizons in hours.\n"
            "- XGBoost supports: 1, 3, 6, 12\n"
            "- Prophet ALWAYS uses: 24\n"
        )
    )

    model_type: Optional[str] = Field(
        default="xgboost",
        description="Model to use: 'xgboost' or 'prophet'"
    )

    @field_validator("model_type")
    def validate_model_type(cls, v):
        allowed = {"xgboost", "prophet"}
        if v.lower() not in allowed:
            raise ValueError(f"model_type must be one of: {allowed}")
        return v.lower()

    class Config:
        json_schema_extra = {
            "examples": {
                "XGBoost Example": {
                    "summary": "XGBoost multi-horizon example",
                    "value": {
                        "station_id": 1,
                        "horizons": [1, 3, 6, 12],
                        "model_type": "xgboost"
                    }
                },
                "Prophet Example": {
                    "summary": "Prophet 24-hour forecast example",
                    "value": {
                        "station_id": 1,
                        "model_type": "prophet",
                        "horizons": [24]
                    }
                }
            }
        }


class PredictionResponse(BaseModel):
    """Response model for PM2.5 predictions."""
    success: bool
    station_id: int
    station_name: str
    predictions: List[dict]
    generated_at: str
    method: str
    model_info: Optional[dict] = None
