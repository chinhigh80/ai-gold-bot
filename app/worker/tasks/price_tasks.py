"""Background task to warm the Redis gold price cache."""
import structlog

from app.worker.celery_app import celery_app

logger = structlog.get_logger(__name__)


@celery_app.task(name="app.worker.tasks.price_tasks.refresh_gold_price", bind=True, max_retries=3)
def refresh_gold_price(self):
    """Fetch latest gold price and store in Redis cache."""
    import asyncio
    from app.services.price_service import get_gold_price

    async def _run():
        return await get_gold_price()

    try:
        loop = asyncio.new_event_loop()
        price_data = loop.run_until_complete(_run())
        loop.close()
        logger.info(
            "price_refreshed",
            price_per_gram=price_data.price_per_gram_usd,
            source=price_data.source,
        )
        return {"price_per_gram_usd": price_data.price_per_gram_usd}
    except Exception as exc:
        logger.error("price_refresh_failed", error=str(exc))
        raise self.retry(exc=exc, countdown=30)
