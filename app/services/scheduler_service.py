import logging
import pytz
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from app.jobs.hourly_fetch import fetch_reports_job
from app.services.report_service import generate_daily_reports

logger = logging.getLogger(__name__)

class SchedulerService:
    """
    Manages background job scheduling using APScheduler.
    Runs initial 24h fetch at startup, then hourly fetch at minute 15.
    """

    def __init__(self, timezone: str = "America/Bogota"):
        self.timezone = pytz.timezone(timezone)
        self.scheduler = BackgroundScheduler(
            timezone=self.timezone,
            job_defaults={
                "coalesce": True,
                "max_instances": 1,
                "misfire_grace_time": 300,
            },
        )
        logger.info("SchedulerService initialized with timezone: %s", timezone)

    def start(self):
        """Run initial job (24 h) and set recurring tasks."""
        self._run_initial_job()
        self._add_recurring_jobs()
        self.scheduler.start()
        logger.info("Background scheduler started successfully.")
        return self.scheduler

    def _run_initial_job(self):
        """Executes the fetch job once at startup (24h window)."""
        logger.info("Running initial 24h data fetch job...")
        try:
            fetch_reports_job(full_init=True)
            logger.info("Initial 24h job completed successfully.")
        except Exception as e:
            logger.exception("Error during initial job execution: %s", e)

    def _add_recurring_jobs(self):
        """Adds periodic jobs: hourly fetch (:15) and daily reports (00:00)."""

        # Fetch last hour data every hour at minute 15
        self.scheduler.add_job(
            fetch_reports_job,
            trigger=CronTrigger(minute=15, second=0, timezone=self.timezone),
            id="fetch_reports_hourly",
            replace_existing=True,
        )

        # Generate daily reports at midnight
        self.scheduler.add_job(
            generate_daily_reports,
            trigger=CronTrigger(hour=0, minute=15, timezone=self.timezone),
            id="daily_reports",
            replace_existing=True,
        )

        logger.info("Jobs configured: hourly fetch at :15, daily reports at 00:00.")

    def stop(self):
        """Gracefully stop the scheduler."""
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            logger.info("Background scheduler stopped cleanly.")


def start_scheduler():
    """Entry point for external use (e.g., from FastAPI lifespan)."""
    return SchedulerService().start()
