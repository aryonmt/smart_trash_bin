# backend/ingestion-service/main.py
# -------------------------------------------------------------------------
# Ingestion Service - Validates schema and routes data to Redis Streams
# -------------------------------------------------------------------------

import json
import logging
import os
import time
from typing import Optional

import paho.mqtt.client as mqtt
import redis
from pydantic import BaseModel, Field, ValidationError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("IngestionService")

# Environment configurations
MQTT_BROKER = os.getenv("MQTT_BROKER", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

# MQTT Topics
TELEMETRY_PATTERN = "wastebin/+/+/telemetry"
STATUS_PATTERN = "wastebin/+/+/status"

# Redis Streams Name
STREAM_TELEMETRY = "raw-telemetry"
STREAM_STATUS = "device-status"

# Connect to Redis with robust retry loop
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


class TelemetryPayload(BaseModel):
    """Resilient validation schema accepting both old and new firmware."""

    device_id: str = Field(..., min_length=3)
    zone_id: Optional[str] = Field(default=None, min_length=3)  # Optional fallback
    distance_cm: float = Field(..., ge=0.0, le=1000.0)
    sample_count: int = Field(default=11, ge=1, le=50)  # Defaults to 11 if missing
    uptime_s: int = Field(..., ge=0)


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logger.info("Successfully connected to MQTT Broker.")
        client.subscribe(TELEMETRY_PATTERN)
        client.subscribe(STATUS_PATTERN)
        logger.info(f"Subscribed to patterns: {TELEMETRY_PATTERN}, {STATUS_PATTERN}")
    else:
        logger.error(f"MQTT Connection failed with return code {rc}")


def handle_telemetry(topic: str, payload_str: str):
    parts = topic.split("/")
    if len(parts) != 4:
        logger.warning(f"Ignored invalid topic structure: {topic}")
        return

    topic_zone = parts[1]
    topic_bin = parts[2]

    try:
        raw_data = json.loads(payload_str)
        validated_data = TelemetryPayload(**raw_data)

        # Resilient fallback: If zone_id is missing in payload, extract it from MQTT topic metadata
        if not validated_data.zone_id:
            validated_data.zone_id = topic_zone

        # Anti-Spoofing check
        if (
            validated_data.device_id != topic_bin
            or validated_data.zone_id != topic_zone
        ):
            logger.error(
                f"Spoofing attempt blocked! Topic metadata ({topic_zone}/{topic_bin}) "
                f"does not match payload content ({validated_data.zone_id}/{validated_data.device_id})"
            )
            return

        # Add validated data directly to Redis Stream
        redis_client.xadd(STREAM_TELEMETRY, validated_data.model_dump())
        logger.info(f"Routed telemetry from {topic_bin} to Stream '{STREAM_TELEMETRY}'")

    except json.JSONDecodeError:
        logger.error(f"Non-JSON payload received on telemetry topic: {topic}")
    except ValidationError as e:
        logger.error(f"Payload validation failed for topic {topic}. Error: {e.json()}")
    except Exception as e:
        logger.error(f"Error handling telemetry data ingestion: {e}")


def handle_status(topic: str, payload_str: str):
    parts = topic.split("/")
    if len(parts) != 4:
        return

    zone_id = parts[1]
    bin_id = parts[2]
    status = payload_str.strip().lower()

    if status not in ["online", "offline"]:
        logger.warning(f"Invalid status value ignored: {status}")
        return

    try:
        redis_client.xadd(
            STREAM_STATUS,
            {
                "device_id": bin_id,
                "zone_id": zone_id,
                "status": status,
                "timestamp": str(int(time.time())),
            },
        )
        logger.info(f"Device status update recorded: {bin_id} is {status}")
    except Exception as e:
        logger.error(f"Error handling status event: {e}")


def on_message(client, userdata, msg):
    topic = msg.topic
    payload_str = msg.payload.decode("utf-8")

    if topic.endswith("/telemetry"):
        handle_telemetry(topic, payload_str)
    elif topic.endswith("/status"):
        handle_status(topic, payload_str)


# Insert this modification inside the main() function of backend/ingestion-service/main.py


def main():
    logger.info("Starting Ingestion Service...")
    client = mqtt.Client(client_id="ingestion_service_consumer")
    client.on_connect = on_connect
    client.on_message = on_message

    # Read credentials from container environment
    mqtt_user = os.getenv("MQTT_USER")
    mqtt_password = os.getenv("MQTT_PASSWORD")
    if mqtt_user and mqtt_password:
        client.username_pw_set(mqtt_user, mqtt_password)
        logger.info("Credentials configured for MQTT connection.")

    connected = False
    for attempt in range(1, 11):
        try:
            client.connect(MQTT_BROKER, MQTT_PORT, 60)
            connected = True
            break
        except Exception as e:
            logger.warning(f"MQTT Broker attempt {attempt}/10 failed: {e}")
            time.sleep(3)

    if not connected:
        logger.critical("Could not connect to MQTT Broker. Exiting.")
        exit(1)

    client.loop_forever()


if __name__ == "__main__":
    main()
