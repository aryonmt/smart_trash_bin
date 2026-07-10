# backend/ingestion-service/src/main.py
# -------------------------------------------------------------------------
# Ingestion Service - Composition root boots MQTT client loop
# -------------------------------------------------------------------------

import logging
import time

import paho.mqtt.client as mqtt

from .config import settings
from .handlers.status import handle_status
from .handlers.telemetry import handle_telemetry

# Configure root logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("IngestionService")


def on_connect(client, userdata, flags, rc):
    """Callback triggered upon successful broker connection."""
    if rc == 0:
        logger.info("Successfully connected to MQTT Broker.")
        client.subscribe(settings.TELEMETRY_PATTERN)
        client.subscribe(settings.STATUS_PATTERN)
        logger.info(
            f"Subscribed to patterns: {settings.TELEMETRY_PATTERN}, {settings.STATUS_PATTERN}"
        )
    else:
        logger.error(f"MQTT Connection failed with return code {rc}")


def on_message(client, userdata, msg):
    """Core message multiplexer routing incoming topics to specific handlers."""
    topic = msg.topic
    payload_str = msg.payload.decode("utf-8")

    if topic.endswith("/telemetry"):
        handle_telemetry(topic, payload_str)
    elif topic.endswith("/status"):
        handle_status(topic, payload_str)


def main():
    logger.info("Starting Ingestion Service orchestrator...")
    client = mqtt.Client(client_id="ingestion_service_consumer")
    client.on_connect = on_connect
    client.on_message = on_message

    # Inject broker credentials if enabled
    if settings.MQTT_USER and settings.MQTT_PASSWORD:
        client.username_pw_set(settings.MQTT_USER, settings.MQTT_PASSWORD)
        logger.info("Credentials configured for MQTT broker connection.")

    connected = False
    for attempt in range(1, 11):
        try:
            client.connect(settings.MQTT_BROKER, settings.MQTT_PORT, 60)
            connected = True
            break
        except Exception as e:
            logger.warning(f"MQTT Broker connection attempt {attempt}/10 failed: {e}")
            time.sleep(3)

    if not connected:
        logger.critical("Fatal: Could not connect to MQTT Broker. Exiting.")
        exit(1)

    client.loop_forever()


if __name__ == "__main__":
    main()
