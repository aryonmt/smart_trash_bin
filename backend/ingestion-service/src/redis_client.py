# backend/ingestion-service/src/redis_client.py
# -------------------------------------------------------------------------
# Redis client connection bootstrapper
# -------------------------------------------------------------------------

import logging
import time

import redis

from .config import settings

logger = logging.getLogger("IngestionService.Redis")

redis_client = None
for attempt in range(1, 11):
    try:
        redis_client = redis.Redis(
            host=settings.REDIS_HOST, port=settings.REDIS_PORT, decode_responses=True
        )
        redis_client.ping()
        logger.info(
            f"Connected to Redis at {settings.REDIS_HOST}:{settings.REDIS_PORT}"
        )
        break
    except Exception as e:
        logger.warning(f"Redis connection attempt {attempt}/10 failed: {e}")
        if attempt == 10:
            logger.critical("Could not connect to Redis. Exiting.")
            exit(1)
        time.sleep(3)
