from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from app.jobs.hourly_fetch import fetch_reports_job
import pytz
import logging

# Basic logging configuration
logger = logging.getLogger(__name__)

def start_scheduler():
    """
    Initializes and starts the BackgroundScheduler to run jobs periodically.
    
    The job is executed immediately upon calling this function for the initial data fetch, 
    and then scheduled to run every hour at the 13th minute (Bogota time).
    """
    
    # 1. IMMEDIATE EXECUTION (Run job once at startup)
    logger.info("Starting immediate job execution for initial data synchronization...")
    try:
        fetch_reports_job()
        logger.info("Immediate job execution completed successfully.")
    except Exception as e:
        # Crucial to handle errors here so the main application can still start
        logger.error(f"Error during immediate job execution: {e}. Scheduler will proceed with recurring schedule.")

    # 2. RECURRING SCHEDULE SETUP
    scheduler = BackgroundScheduler()
    # Define the required timezone for the CronTrigger
    tz = pytz.timezone("America/Bogota")
    
    # Configure the job to run every hour at minute 13
    # This triggers at 1:13:00, 2:13:00, 3:13:00, etc. (Bogota time)
    trigger = CronTrigger(minute=13, second=0, timezone=tz)
    
    # Add the hourly data fetching job to the scheduler
    scheduler.add_job(fetch_reports_job, trigger=trigger, id="fetch_reports_job")
    scheduler.start()
    
    # Inform about the scheduler status
    logger.info("Background Scheduler successfully initialized.")
    logger.info(f"Recurring job 'fetch_reports_job' is set to run every hour at minute 13 (Timezone: {tz}).")
    
    return scheduler
