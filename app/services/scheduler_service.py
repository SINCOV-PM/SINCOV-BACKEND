import logging
import pytz
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from app.jobs.hourly_fetch import fetch_reports_job

logger = logging.getLogger(__name__)

class SchedulerService:
    """
    Manages background job scheduling using APScheduler.
    Handles both immediate and recurring tasks.
    """

    def __init__(self, timezone: str = "America/Bogota"):
        self.timezone = pytz.timezone(timezone)
        self.scheduler = BackgroundScheduler(
            timezone=self.timezone,
            job_defaults={
                "coalesce": True,          
                "max_instances": 1,       
                "misfire_grace_time": 300  
            }
        )
        logger.info("SchedulerService initialized with timezone: %s", timezone)

    def start(self):
        """Run immediate job and set up recurring tasks."""
        self._run_immediate_job()
        self._add_recurring_jobs()
        self.scheduler.start()
        logger.info("Background scheduler started successfully.")
        return self.scheduler

    def _run_immediate_job(self):
        """Executes the fetch job once at startup."""
        logger.info("Running initial data synchronization job...")
        try:
            fetch_reports_job()
            logger.info("Initial job completed successfully.")
        except Exception as e:
            logger.exception("Error during initial job execution: %s", e)

    def _add_recurring_jobs(self):
        """Adds all periodic jobs to the scheduler."""
        # Ejecuta cada hora exacta al minuto 10
        self.scheduler.add_job(
            fetch_reports_job,
            trigger=CronTrigger(minute=10, second=0, timezone=self.timezone),
            id="fetch_reports_job",
            replace_existing=True,
        )
        logger.info("Recurring job 'fetch_reports_job' scheduled every hour at minute 13.")

    def stop(self):
        """Gracefully stop the scheduler."""
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            logger.info("Background scheduler stopped cleanly.")

def start_scheduler():
    """Entry point for external use (e.g., from FastAPI lifespan)."""
    return SchedulerService().start()
