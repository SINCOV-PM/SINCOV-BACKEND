from fastapi import APIRouter
from app.api.routes_predict.legacy import router as legacy_router
from app.api.routes_predict.predict import router as predict_router
from app.api.routes_predict.stations import router as stations_router
from app.api.routes_predict.health import router as health_router

router = APIRouter(prefix="/predict", tags=["Prediction"])
router.include_router(legacy_router)
router.include_router(predict_router)
router.include_router(stations_router)
router.include_router(health_router)
