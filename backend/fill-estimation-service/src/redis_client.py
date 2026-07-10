# backend/fill-estimation-service/src/redis_client.py
# -------------------------------------------------------------------------
# Redis client connection and consumer group initializer
# -------------------------------------------------------------------------

import logging
import time

import redis

from .config import settings

logger = logging.getLogger("FillEstimationService.Redis")

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

# Create Redis Stream Consumer Group if it does not exist
try:
    redis_client.xgroup_create(
        settings.STREAM_TELEMETRY, settings.CONSUMER_GROUP, id="0", mkstream=True
    )
    logger.info(
        f"Created consumer group '{settings.CONSUMER_GROUP}' on Stream '{settings.STREAM_TELEMETRY}'"
    )
except redis.exceptions.ResponseError as e:
    if "BUSYGROUP" in str(e):
        logger.info(f"Consumer group '{settings.CONSUMER_GROUP}' already exists.")
    else:
        logger.error(f"Error creating consumer group: {e}")
        exit(1)
