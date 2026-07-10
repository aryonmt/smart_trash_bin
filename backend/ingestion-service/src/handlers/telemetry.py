# backend/ingestion-service/src/handlers/telemetry.py
# -------------------------------------------------------------------------
# Handler for routing validated device telemetry
# -------------------------------------------------------------------------

import json
import logging

from pydantic import ValidationError

from ..config import settings
from ..models.telemetry import TelemetryPayload
from ..redis_client import redis_client

logger = logging.getLogger("IngestionService.Handlers.Telemetry")


def handle_telemetry(topic: str, payload_str: str) -> None:
    """Parses, validates, and routes telemetry payload to Redis Streams.

    Args:
        topic: The exact MQTT topic on which the telemetry was received.
        payload_str: The raw JSON string payload sent by the device.
    """
    parts = topic.split("/")
    if len(parts) != 4:
        logger.warning(f"Ignored invalid topic structure: {topic}")
        return

    topic_zone = parts[1]
    topic_bin = parts[2]

    try:
        raw_data = json.loads(payload_str)
        validated_data = TelemetryPayload(**raw_data)

        # Fallback: Extract zone_id from MQTT topic metadata if missing in payload
        if not validated_data.zone_id:
            validated_data.zone_id = topic_zone

        # Anti-Spoofing Check: Enforce topic metadata matching with payload content
        if (
            validated_data.device_id != topic_bin
            or validated_data.zone_id != topic_zone
        ):
            logger.error(
                f"Spoofing attempt blocked! Topic metadata ({topic_zone}/{topic_bin}) "
                f"does not match payload content ({validated_data.zone_id}/{validated_data.device_id})"
            )
            return

        # Push to Redis stream
        redis_client.xadd(settings.STREAM_TELEMETRY, validated_data.model_dump())
        logger.info(
            f"Routed telemetry from {topic_bin} to Stream '{settings.STREAM_TELEMETRY}'"
        )

    except json.JSONDecodeError:
        logger.error(f"Non-JSON payload received on telemetry topic: {topic}")
    except ValidationError as e:
        logger.error(f"Payload validation failed for topic {topic}. Error: {e.json()}")
    except Exception as e:
        logger.error(f"Error handling telemetry data ingestion: {e}")
