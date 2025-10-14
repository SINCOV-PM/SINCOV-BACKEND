from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from app.jobs.hourly_fetch import fetch_reports_job
import pytz

def start_scheduler():
    """
    Initializes and starts the BackgroundScheduler to run jobs periodically.
    """
    scheduler = BackgroundScheduler()
    tz = pytz.timezone("America/Bogota")
    
    # Configure the job to run every hour at minute 9
    # Example: 1:09:00, 2:09:00, 3:09:00, etc. (Bogota time)
    trigger = CronTrigger(minute=9, second=0, timezone=tz)
    
    # Add the hourly data fetching job
    scheduler.add_job(fetch_reports_job, trigger=trigger, id="fetch_reports_job")
    scheduler.start()
    
    # Inform about the scheduler status
    print("Scheduler initialized: job will run every hour at minute 9 (Bogota time).")
    
    return scheduler
