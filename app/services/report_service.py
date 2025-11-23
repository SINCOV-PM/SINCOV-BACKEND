import logging
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.report import Report
from app.services.stations_service import get_stations_summary

logger = logging.getLogger(__name__)


def calculate_pm25_status(value: float) -> str:
    """Classifies air quality based on PM2.5"""
    if value >= 55.5:
        return "Very High"
    elif value >= 35.5:
        return "High"
    elif value >= 12.1:
        return "Moderate"
    return "Good"


def generate_daily_reports():
    """
    Generates and saves a daily average PM2.5 report per station.
    Runs every 24 hours via the scheduler.
    """
    logger.info("Generating daily PM2.5 reports...")
    db: Session = SessionLocal()

    try:
        summary_data = get_stations_summary()
        today = date.today()
        created = 0

        for station in summary_data:
            pm25_monitor = next((m for m in station['monitors'] if m['type'] == 'PM2.5'), None)
            if not pm25_monitor:
                continue

            avg = float(pm25_monitor['promedio'])
            status = calculate_pm25_status(avg)

            existing = (
                db.query(Report)
                .filter(Report.station_id == station['id'], Report.date == today)
                .first()
            )

            if existing:
                existing.avg = avg
                existing.status = status
            else:
                report = Report(
                    station_id=station['id'],
                    date=today,
                    avg=avg,
                    status=status,
                )
                db.add(report)
                created += 1

        db.commit()
        logger.info(f"Daily reports created or updated: {created}")

    except Exception as e:
        logger.exception("Error generating daily reports: %s", e)
        db.rollback()
    finally:
        db.close()
