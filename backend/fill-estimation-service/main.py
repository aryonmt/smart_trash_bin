# backend/fill-estimation-service/main.py
# -------------------------------------------------------------------------
# Stateful Fill Estimation Service consuming from Redis Streams Group
# -------------------------------------------------------------------------

import json
import logging
import os
import time

import redis
from domain.estimator import estimate_fill
from domain.models import BinConfig, BinFillState

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("FillEstimationService")

# Environment configurations
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

# Redis Stream Configurations
STREAM_TELEMETRY = "raw-telemetry"
STREAM_FILL_UPDATED = "bin-fill-updated"
CONSUMER_GROUP = "estimation-group"
CONSUMER_NAME = "estimator-consumer-1"

# Connect to Redis
redis_client = None
for attempt in range(1, 11):
    try:
        redis_client = redis.Redis(
            host=REDIS_HOST, port=REDIS_PORT, decode_responses=True
        )
        redis_client.ping()
        logger.info(f"Connected to Redis at {REDIS_HOST}:{REDIS_PORT}")
        break
    except Exception as e:
        logger.warning(f"Redis connection attempt {attempt}/10 failed: {e}")
        if attempt == 10:
            logger.critical("Could not connect to Redis. Exiting.")
            exit(1)
        time.sleep(3)

# Create Redis Stream Consumer Group if it does not exist
try:
    redis_client.xgroup_create(STREAM_TELEMETRY, CONSUMER_GROUP, id="0", mkstream=True)
    logger.info(
        f"Created consumer group '{CONSUMER_GROUP}' on Stream '{STREAM_TELEMETRY}'"
    )
except redis.exceptions.ResponseError as e:
    if "BUSYGROUP" in str(e):
        logger.info(f"Consumer group '{CONSUMER_GROUP}' already exists.")
    else:
        logger.error(f"Error creating consumer group: {e}")
        exit(1)


def process_stream_entry(message_id: str, fields: dict):
    try:
        device_id = fields.get("device_id")
        zone_id = fields.get("zone_id")
        raw_distance = float(fields.get("distance_cm"))

        if not device_id or not zone_id:
            logger.warning(f"Malformed stream entry {message_id} ignored.")
            return

        config = BinConfig()
        state_key = f"bin_state:{device_id}"
        stored_state = redis_client.get(state_key)

        if stored_state:
            state = BinFillState(**json.loads(stored_state))
        else:
            state = BinFillState(confirmed_distance_cm=config.bin_depth_cm)
            logger.info(f"Initialized state tracking database for device {device_id}")

        # Run stateful core estimation algorithm
        updated_state, fill_percent, was_emptied = estimate_fill(
            state, config, raw_distance
        )

        # Save updated baseline state in Redis key
        redis_client.set(state_key, updated_state.model_dump_json())

        # Publish output metrics on fill-updated stream for downstream services
        result_payload = {
            "device_id": device_id,
            "zone_id": zone_id,
            "fill_percent": str(fill_percent),
            "confirmed_distance_cm": str(updated_state.confirmed_distance_cm),
            "is_emptied": str(int(was_emptied)),
            "timestamp": str(int(time.time())),
        }
        redis_client.xadd(STREAM_FILL_UPDATED, result_payload)

        logger.info(
            f"Device ID: {device_id} | Zone: {zone_id} | Raw: {raw_distance}cm | "
            f"Estimated Fill: {fill_percent}% | Empty Event: {was_emptied}"
        )

        # Acknowledge processed message in consumer group
        redis_client.xack(STREAM_TELEMETRY, CONSUMER_GROUP, message_id)

    except Exception as e:
        logger.error(f"Error processing stream message {message_id}: {e}")


def main():
    logger.info("Starting Stateful Fill Estimation stream listener...")
    while True:
        try:
            # Read new messages from group
            # ID '>' means read only new messages that have not been delivered to other consumers
            streams_data = redis_client.xreadgroup(
                groupname=CONSUMER_GROUP,
                consumername=CONSUMER_NAME,
                streams={STREAM_TELEMETRY: ">"},
                count=1,
                block=1000,
            )

            for stream_name, messages in streams_data:
                for message_id, fields in messages:
                    process_stream_entry(message_id, fields)

        except Exception as e:
            logger.error(f"Stream ingestion loop error: {e}")
            time.sleep(2)


if __name__ == "__main__":
    main()
