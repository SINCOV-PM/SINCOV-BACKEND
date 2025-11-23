from fastapi import APIRouter
from app.api.routes_reports.report_routes import router as reports_router

router = APIRouter(prefix="/reports", tags=["Reports"])
router.include_router(reports_router)
