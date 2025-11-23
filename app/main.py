# app/main.py
from fastapi import FastAPI
from contextlib import asynccontextmanager
import logging
from app.services.scheduler_service import start_scheduler
from app.api.routes_predict import router as predict_router
from app.api import routes_reports, routes_stations
from app.core.config import settings
from app.core.logging_config import setup_logging
from fastapi.middleware.cors import CORSMiddleware

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown events."""
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
app.include_router(routes_reports.router, prefix="/reports", tags=["Reports"])
app.include_router(routes_stations.router, prefix="/stations", tags=["Stations"])

@app.get("/", tags=["Health"])
def health_check():
    """Basic health endpoint for uptime monitoring."""
    return {
        "status": "ok",
        "project": settings.PROJECT_NAME,
        "version": settings.PROJECT_VERSION,
    }
