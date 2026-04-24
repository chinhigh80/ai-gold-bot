"""Celery application with RedBeat scheduler."""
from celery import Celery
from celery.schedules import crontab

from app.config import settings

celery_app = Celery(
    "goldvault",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.worker.tasks.price_tasks",
        "app.worker.tasks.payment_tasks",
        "app.worker.tasks.notification_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    beat_schedule={
        # Refresh gold price every minute
        "refresh-gold-price": {
            "task": "app.worker.tasks.price_tasks.refresh_gold_price",
            "schedule": 60.0,
        },
        # Check pending payments every 2 minutes
        "poll-pending-payments": {
            "task": "app.worker.tasks.payment_tasks.poll_pending_payments",
            "schedule": 120.0,
        },
        # Broadcast daily price update at 9:00 AM UTC
        "daily-price-broadcast": {
            "task": "app.worker.tasks.notification_tasks.daily_price_broadcast",
            "schedule": crontab(hour=9, minute=0),
        },
        # Expire stale price-locked orders every 10 minutes
        "expire-stale-orders": {
            "task": "app.worker.tasks.payment_tasks.expire_stale_orders",
            "schedule": 600.0,
        },
    },
)
