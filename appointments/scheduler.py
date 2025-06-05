from apscheduler.schedulers.background import BackgroundScheduler
from django.core.management import call_command
from django_apscheduler.jobstores import DjangoJobStore
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

def process_reminders_job():
    """Job to process appointment reminders"""
    try:
        call_command('process_reminders')
    except Exception as e:
        logger.error(f"Error processing reminders: {e}")

def cleanup_slots_job():
    """Job to cleanup unused slots"""
    try:
        call_command('cleanup_slots')
    except Exception as e:
        logger.error(f"Error cleaning up slots: {e}")

def start():
    scheduler = BackgroundScheduler()
    scheduler.add_jobstore(DjangoJobStore(), "default")
    
    # Process reminders daily at 8:00 AM
    scheduler.add_job(
        process_reminders_job,
        'cron',
        hour=8,
        minute=0,
        name='process_reminders',
        jobstore='default',
        replace_existing=True
    )
    
    # Cleanup slots daily at midnight
    scheduler.add_job(
        cleanup_slots_job,
        'cron',
        hour=0,
        minute=0,
        name='cleanup_slots',
        jobstore='default',
        replace_existing=True
    )
    
    scheduler.start()
    logger.info("Started appointment scheduler")
