# backend/fill-estimation-service/main.py
# -------------------------------------------------------------------------
# Listen to validated telemetry and calculate stateful fill estimations
# -------------------------------------------------------------------------

import json
import logging
import os

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
REDIS_CHANNEL = "raw-telemetry-channel"

# Initialize Redis client
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)


def process_message(raw_msg_str: str):
    try:
        data = json.loads(raw_msg_str)
        device_id = data["device_id"]
        raw_distance = data["distance_cm"]

        # Load configuration for the specific bin (using default values for MVP)
        config = BinConfig()

        # Retrieve previous state from Redis or create a default starting point
        state_key = f"bin_state:{device_id}"
        stored_state = redis_client.get(state_key)

        if stored_state:
            state = BinFillState(**json.loads(stored_state))
        else:
            # Baseline assumes bin is completely empty initially (sensor reads full depth)
            state = BinFillState(confirmed_distance_cm=config.bin_depth_cm)
            logger.info(f"Initialized new state database for device {device_id}")

        # Execute core filtering algorithm
        updated_state, fill_percent, was_emptied = estimate_fill(
            state, config, raw_distance
        )

        # Save updated state back to Redis
        redis_client.set(state_key, updated_state.model_dump_json())

        logger.info(
            f"Device ID: {device_id} | Raw Read: {raw_distance}cm | "
            f"Estimated Fill: {fill_percent}% | Empty Event: {was_emptied}"
        )

    except Exception as e:
        logger.error(f"Error processing telemetry chunk: {e}")


def main():
    logger.info("Starting Fill Estimation Service...")
    pubsub = redis_client.pubsub()
    pubsub.subscribe(REDIS_CHANNEL)
    logger.info(f"Subscribed to validation channel: {REDIS_CHANNEL}")

    for message in pubsub.listen():
        if message["type"] == "message":
            process_message(message["data"])


if __name__ == "__main__":
    main()
