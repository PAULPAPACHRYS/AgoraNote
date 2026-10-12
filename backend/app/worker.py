"""Celery app and background tasks. Start with: celery -A app.worker worker --loglevel=info"""
from celery import Celery

from app import config

celery = Celery("agoranote", broker=config.REDIS_URL, backend=config.REDIS_URL)
celery.conf.broker_connection_retry_on_startup = True


@celery.task
def ping():
    """Trivial task used to check that the worker is wired up."""
    return "pong"
