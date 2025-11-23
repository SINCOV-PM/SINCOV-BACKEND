from fastapi import FastAPI
from contextlib import asynccontextmanager
import logging

from app.services.scheduler_service import start_scheduler
from app.api.routes_predict import router as predict_router
from app.api.routes_reports import router as reports_router
from app.api.routes_stations import router as stations_router
from app.core.config import settings
from app.core.logging_config import setup_logging
from fastapi.middleware.cors import CORSMiddleware

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger.info("Starting application...")

    scheduler = start_scheduler()
    logger.info("Scheduler started.")

    yield

    if scheduler:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped.")
    logger.info("Application shutdown complete.")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    description="SINCOV Air Quality Monitoring and Prediction API",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(predict_router)
app.include_router(reports_router)
app.include_router(stations_router)

@app.get("/", tags=["Health"])
def health_check():
    return {
        "status": "ok",
        "project": settings.PROJECT_NAME,
        "version": settings.PROJECT_VERSION,
    }
