# backend/persistence-service/src/redis_client.py
# -------------------------------------------------------------------------
# Redis client connection and consumer groups initializer
# -------------------------------------------------------------------------

import logging
import time

import redis

from .config import settings

logger = logging.getLogger("PersistenceService.Redis")

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

# Create consumer groups for telemetry and status streams
for stream, group in [
    (settings.STREAM_FILL_UPDATED, settings.GROUP_TELEMETRY),
    (settings.STREAM_STATUS, settings.GROUP_STATUS),
]:
    try:
        redis_client.xgroup_create(stream, group, id="0", mkstream=True)
        logger.info(f"Created consumer group '{group}' on '{stream}'")
    except redis.exceptions.ResponseError as e:
        if "BUSYGROUP" not in str(e):
            logger.error(f"Error creating group {group}: {e}")
