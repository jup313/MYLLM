import os
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv

load_dotenv()

SCHEDULE_HOUR = int(os.getenv("SCHEDULE_HOUR", 6))
SCHEDULE_MINUTE = int(os.getenv("SCHEDULE_MINUTE", 0))

scheduler = BackgroundScheduler()

def run_daily_batch():
    """Called by scheduler at 6 AM — generates all daily posts."""
    print(f"\n⏰ Scheduled generation started...")
    try:
        from app.generator import generate_daily_batch
        results, errors = generate_daily_batch()
        print(f"✅ Daily batch complete: {len(results)} posts in queue")
    except Exception as e:
        print(f"❌ Daily batch failed: {str(e)}")

def start_scheduler():
    if not scheduler.running:
        scheduler.add_job(
            run_daily_batch,
            trigger="cron",
            hour=SCHEDULE_HOUR,
            minute=SCHEDULE_MINUTE,
            id="daily_batch",
            replace_existing=True
        )
        scheduler.start()
        print(f"⏰ Scheduler running — daily generation at {SCHEDULE_HOUR:02d}:{SCHEDULE_MINUTE:02d} AM")

def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown()

def get_next_run():
    try:
        job = scheduler.get_job("daily_batch")
        if job:
            return str(job.next_run_time)
    except Exception:
        pass
    return "Not scheduled"
