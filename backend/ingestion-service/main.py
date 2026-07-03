# backend/ingestion-service/main.py
# -------------------------------------------------------------------------
# Ingestion Service - Subscribes to MQTT telemetry and validates payloads
# -------------------------------------------------------------------------

import json
import logging
import os

import paho.mqtt.client as mqtt
from pydantic import BaseModel, Field, ValidationError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("IngestionService")

# Environment configurations (with default local values)
MQTT_BROKER = os.getenv("MQTT_BROKER", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))
TELEMETRY_TOPIC = "wastebin/+/+/telemetry"


class TelemetryPayload(BaseModel):
    """Schema validation class for incoming bin telemetry data."""

    device_id: str = Field(..., min_length=3)
    distance_cm: float = Field(..., ge=0.0, le=1000.0)
    uptime_s: int = Field(..., ge=0)


def on_connect(client, userdata, flags, rc):
    """Callback triggered when the client connects to the broker."""
    if rc == 0:
        logger.info(
            f"Connected successfully to MQTT Broker at {MQTT_BROKER}:{MQTT_PORT}"
        )
        client.subscribe(TELEMETRY_TOPIC)
        logger.info(f"Subscribed to topic: {TELEMETRY_TOPIC}")
    else:
        logger.error(f"Connection failed with code {rc}")


def on_message(client, userdata, msg):
    """Callback triggered when a message is received on a subscribed topic."""
    topic = msg.topic
    payload_str = msg.payload.decode("utf-8")
    logger.info(f"Received message on topic '{topic}': {payload_str}")

    try:
        # Step 1: Parse JSON
        data = json.loads(payload_str)

        # Step 2: Validate using Pydantic model
        validated_data = TelemetryPayload(**data)
        logger.info(
            f"Data validated successfully for device: {validated_data.device_id}"
        )

        # TODO: In the next step, publish this validated data to Kafka/RabbitMQ or DB

    except json.JSONDecodeError:
        logger.error(f"Failed to decode invalid JSON payload from topic: {topic}")
    except ValidationError as e:
        logger.error(f"Payload validation failed for topic {topic}. Errors: {e.json()}")


def main():
    logger.info("Starting Ingestion Service...")
    client = mqtt.Client(client_id="ingestion_service_consumer")
    client.on_connect = on_connect
    client.on_message = on_message

    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        # Keep client running in a blocking loop
        client.loop_forever()
    except Exception as e:
        logger.critical(f"MQTT client connection error: {e}")


if __name__ == "__main__":
    main()
