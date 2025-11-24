from fastapi import APIRouter, HTTPException
from app.db.session import SessionLocal
from app.models.report import Report
from app.models.station import Station
from sqlalchemy import func
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Reports"])

_cache = {"data": None, "timestamp": None}
_CACHE_TTL = timedelta(minutes=10)


@router.get("/")
async def get_latest_reports():
    """Return the latest daily report per active station (cached)."""
    global _cache
    now = datetime.now()

    if _cache["data"] and (now - _cache["timestamp"]) < _CACHE_TTL:
        logger.info("Returning cached report data")
        return _cache["data"]

    db = SessionLocal()
    try:

        reports = (
            db.query(
                Report.station_id,
                Report.date,
                Report.avg,
                Report.status,
                Station.name.label("station_name"),
            )
            .join(Station, Station.id == Report.station_id)
            .distinct(Report.station_id)
            .order_by(Report.station_id, Report.date.desc())
            .all()
        )

        if not reports:
            raise HTTPException(status_code=404, detail="No reports available")

        response = {
            "success": True,
            "total": len(reports),
            "reports": [
                {
                    "station_id": r.station_id,
                    "station_name": r.station_name,
                    "date": r.date,
                    "pm25_value": round(r.avg, 2),
                    "status": r.status,
                }
                for r in reports
            ],
        }

        _cache = {"data": response, "timestamp": now}
        logger.info(f"Cached {len(reports)} reports at {now}")

        return response

    except Exception as e:
        logger.exception("Error fetching latest reports: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        db.close()


@router.get("/summary")
async def get_reports_summary():
    """Return PM2.5 summary statistics for all reports."""
    db = SessionLocal()
    try:
        total, avg_pm25, min_pm25, max_pm25 = (
            db.query(
                func.count(Report.id),
                func.avg(Report.avg),
                func.min(Report.avg),
                func.max(Report.avg),
            ).one()
        )

        return {
            "success": True,
            "data": {
                "total_reports": total,
                "avg_pm25": round(avg_pm25 or 0, 2),
                "min_pm25": round(min_pm25 or 0, 2),
                "max_pm25": round(max_pm25 or 0, 2),
            },
        }

    except Exception as e:
        logger.error(f"Error getting summary: {e}")
        raise HTTPException(status_code=500, detail="Internal error")
    finally:
        db.close()