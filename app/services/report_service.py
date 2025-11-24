import logging
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import text
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
    Generates and saves a daily average PM2.5 report per station
    based only on readings from the previous day (00:00 → 23:59).
    """
    logger.info("Generating daily PM2.5 reports (for previous day)...")
    db = SessionLocal()

    try:
        today = date.today()
        yesterday = today - timedelta(days=1)
        start_dt = datetime.combine(yesterday, datetime.min.time())
        end_dt = datetime.combine(today, datetime.min.time())

        # Query promedio PM2.5 por estación en el día anterior
        query = text("""
            SELECT 
                st.id AS station_id,
                st.name,
                ROUND(AVG(s.value)::numeric, 2) AS promedio_pm25
            FROM sensors s
            JOIN monitors m ON s.monitor_id = m.id
            JOIN stations st ON m.station_id = st.id
            WHERE m.type = 'PM2.5'
              AND s.timestamp >= :start_dt
              AND s.timestamp < :end_dt
            GROUP BY st.id, st.name
        """)

        results = db.execute(query, {"start_dt": start_dt, "end_dt": end_dt}).fetchall()
        created = 0

        for row in results:
            avg = float(row[2]) if row[2] is not None else 0.0
            status = calculate_pm25_status(avg)

            existing = (
                db.query(Report)
                .filter(Report.station_id == row[0], Report.date == yesterday)
                .first()
            )

            if existing:
                existing.avg = avg
                existing.status = status
            else:
                report = Report(
                    station_id=row[0],
                    date=yesterday,
                    avg=avg,
                    status=status,
                )
                db.add(report)
                created += 1

        db.commit()
        logger.info(f"Daily reports created/updated for {yesterday}: {created}")

    except Exception as e:
        logger.exception("Error generating daily reports: %s", e)
        db.rollback()
    finally:
        db.close()

