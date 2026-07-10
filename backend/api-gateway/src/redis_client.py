# backend/api-gateway/src/redis_client.py
# -------------------------------------------------------------------------
# Redis client connection initializer
# -------------------------------------------------------------------------

import logging
import time

import redis

from .config import settings

logger = logging.getLogger("APIGateway.Redis")

redis_client = None
for attempt in range(1, 11):
    try:
        redis_client = redis.Redis(
            host=settings.REDIS_HOST, port=settings.REDIS_PORT, decode_responses=True
        )
        redis_client.ping()
        logger.info("Connected to Redis successfully.")
        break
    except Exception as e:
        logger.warning(f"Redis connection attempt {attempt}/10 failed: {e}")
        time.sleep(3)

if not redis_client:
    logger.critical("Could not connect to Redis. Exiting.")
    exit(1)
