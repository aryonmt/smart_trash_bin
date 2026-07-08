# backend/fill-estimation-service/main.py
# -------------------------------------------------------------------------
# Stateful Fill Estimation Service with Deep Debugging Logs
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
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
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
        time.sleep(3)
if not redis_client:
    exit(1)

# Create Consumer Group
try:
    redis_client.xgroup_create(STREAM_TELEMETRY, CONSUMER_GROUP, id="0", mkstream=True)
    logger.info(
        f"Created consumer group '{CONSUMER_GROUP}' on Stream '{STREAM_TELEMETRY}'"
    )
except redis.exceptions.ResponseError as e:
    if "BUSYGROUP" not in str(e):
        logger.error(f"Error creating consumer group: {e}")


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
            logger.info(
                f"[DEBUG] Initializing state tracking database for device {device_id}"
            )

        # --- Deep Debugging Log (State BEFORE evaluation) ---
        logger.info(
            f"[ALGORITHM DEBUG] Device: {device_id} | Raw Read: {raw_distance}cm | "
            f"State Before Update -> Confirmed Distance: {state.confirmed_distance_cm}cm, "
            f"Candidate Distance: {state.candidate_distance_cm}cm, Streak: {state.candidate_streak}, "
            f"Near-Empty Streak: {state.near_empty_streak}"
        )

        old_confirmed_distance = state.confirmed_distance_cm

        # Execute core filtering algorithm
        updated_state, fill_percent, was_emptied = estimate_fill(
            state, config, raw_distance
        )

        # --- Deep Debugging Log (Reasoning analysis) ---
        if was_emptied:
            logger.warning(
                f"[ALGORITHM DEBUG] Bin {device_id} emptying verified! Resetting to base."
            )
        elif updated_state.confirmed_distance_cm < old_confirmed_distance:
            logger.info(
                f"[ALGORITHM DEBUG] Fill level increased. New confirmed distance: {updated_state.confirmed_distance_cm}cm"
            )
        elif (
            raw_distance > old_confirmed_distance
            and updated_state.confirmed_distance_cm == old_confirmed_distance
        ):
            logger.info(
                f"[ALGORITHM DEBUG] Ratchet Guard Active! Ignored larger raw distance ({raw_distance}cm) "
                f"to prevent false emptying. Confirmed distance remains locked at {old_confirmed_distance}cm"
            )

        # Save updated state
        redis_client.set(state_key, updated_state.model_dump_json())

        # Publish output metrics on fill-updated stream
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
            f"RESULT: {device_id} ({zone_id}) | Estimated Fill: {fill_percent}% | Empty Event: {was_emptied}"
        )
        logger.info("-" * 80)

        redis_client.xack(STREAM_TELEMETRY, CONSUMER_GROUP, message_id)

    except Exception as e:
        logger.error(f"Error processing stream message {message_id}: {e}")


def main():
    logger.info("Starting Stateful Fill Estimation stream listener...")
    while True:
        try:
            streams_data = redis_client.xreadgroup(
                groupname=CONSUMER_GROUP,
                consumername=CONSUMER_NAME,
                streams={STREAM_TELEMETRY: ">"},
                count=1,
                block=1000,
            )
            for _, messages in streams_data:
                for message_id, fields in messages:
                    process_stream_entry(message_id, fields)
        except Exception as e:
            logger.error(f"Stream ingestion loop error: {e}")
            time.sleep(2)


if __name__ == "__main__":
    main()
