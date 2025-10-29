from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import routes_predict, routes_reports, routes_stations
from app.core.config import settings
from app.services.scheduler_service import start_scheduler

app = FastAPI(title=settings.PROJECT_NAME, version=settings.PROJECT_VERSION)

# Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(routes_predict.router, prefix="/predict", tags=["predict"])
app.include_router(routes_reports.router, prefix="/reports", tags=["reports"])
app.include_router(routes_stations.router, prefix="/stations", tags=["stations"])

# Global variable to hold the scheduler instance
scheduler = None

@app.on_event("startup")
def startup_event():
    """
    Called when the application starts up. Initializes and starts the scheduler.
    """
    global scheduler
    scheduler = start_scheduler()

@app.on_event("shutdown")
def shutdown_event():
    """
    Called when the application shuts down. Shuts down the scheduler gracefully.
    """
    global scheduler
    if scheduler:
        scheduler.shutdown()