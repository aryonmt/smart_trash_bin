# backend/alerting-service/src/redis_client.py
# -------------------------------------------------------------------------
# Redis client connection bootstrapper
# -------------------------------------------------------------------------

import logging
import time

import redis

from .config import settings

logger = logging.getLogger("AlertingService.Redis")

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
        time.sleep(3)

if not redis_client:
    logger.critical("Could not connect to Redis. Exiting.")
    exit(1)

# Ensure the consumer group is initialized on the stream
try:
    redis_client.xgroup_create(
        settings.STREAM_FILL_UPDATED, settings.GROUP_ALERTING, id="0", mkstream=True
    )
    logger.info(
        f"Created consumer group '{settings.GROUP_ALERTING}' on '{settings.STREAM_FILL_UPDATED}'"
    )
except redis.exceptions.ResponseError as e:
    if "BUSYGROUP" not in str(e):
        logger.error(f"Error creating consumer group: {e}")
