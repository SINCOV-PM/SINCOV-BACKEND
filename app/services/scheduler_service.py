# app/services/scheduler_service.py
from apscheduler.schedulers.background import BackgroundScheduler
from app.jobs.hourly_fetch import fetch_reports_job

def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(fetch_reports_job, "interval", minutes=30, id="fetch_reports_job")
    scheduler.start()
    print(" Scheduler iniciado: se ejecutará cada hora.")
