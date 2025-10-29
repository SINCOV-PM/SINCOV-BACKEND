from fastapi import APIRouter
from app.schemas.predict_schema import PMRequest
from app.services.predict_service import mock_predict

router = APIRouter(tags=["Predict"])

@router.post("/")
def predict_pm25(data: PMRequest):
    return {"prediction": mock_predict(data.features)}
