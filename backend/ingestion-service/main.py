# backend/ingestion-service/main.py
# -------------------------------------------------------------------------
# Ingestion Service - Subscribes to MQTT telemetry and validates payloads
# -------------------------------------------------------------------------

import json
import logging
import os

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
TELEMETRY_TOPIC = "wastebin/+/+/telemetry"

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_CHANNEL = "raw-telemetry-channel"

# Initialize Redis client
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)


class TelemetryPayload(BaseModel):
    """Schema validation class for incoming bin telemetry data."""

    device_id: str = Field(..., min_length=3)
    distance_cm: float = Field(..., ge=0.0, le=1000.0)
    uptime_s: int = Field(..., ge=0)


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logger.info(
            f"Connected successfully to MQTT Broker at {MQTT_BROKER}:{MQTT_PORT}"
        )
        client.subscribe(TELEMETRY_TOPIC)
        logger.info(f"Subscribed to topic: {TELEMETRY_TOPIC}")
    else:
        logger.error(f"Connection failed with code {rc}")


def on_message(client, userdata, msg):
    topic = msg.topic
    payload_str = msg.payload.decode("utf-8")
    logger.info(f"Received MQTT message on '{topic}': {payload_str}")

    try:
        # Step 1: Parse JSON
        data = json.loads(payload_str)

        # Step 2: Validate using Pydantic model
        validated_data = TelemetryPayload(**data)

        # Step 3: Forward validated data to Redis Pub/Sub channel
        serialized_msg = validated_data.model_dump_json()
        redis_client.publish(REDIS_CHANNEL, serialized_msg)
        logger.info(f"Published validated telemetry to Redis channel '{REDIS_CHANNEL}'")

    except json.JSONDecodeError:
        logger.error(f"Failed to decode invalid JSON payload from topic: {topic}")
    except ValidationError as e:
        logger.error(f"Payload validation failed for topic {topic}. Errors: {e.json()}")
    except Exception as e:
        logger.error(f"Error publishing to Redis: {e}")


def main():
    logger.info("Starting Ingestion Service...")
    client = mqtt.Client(client_id="ingestion_service_consumer")
    client.on_connect = on_connect
    client.on_message = on_message

    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_forever()
    except Exception as e:
        logger.critical(f"MQTT client connection error: {e}")


if __name__ == "__main__":
    main()
