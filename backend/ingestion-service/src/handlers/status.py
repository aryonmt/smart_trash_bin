# backend/ingestion-service/src/handlers/status.py
# -------------------------------------------------------------------------
# Handler for routing device online/offline status updates
# -------------------------------------------------------------------------

import logging
import time

from ..config import settings
from ..redis_client import redis_client

logger = logging.getLogger("IngestionService.Handlers.Status")


def handle_status(topic: str, payload_str: str) -> None:
    """Parses and routes device status events to Redis Streams.

    Args:
        topic: The exact MQTT status topic.
        payload_str: The raw payload value ("online" or "offline").
    """
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
            settings.STREAM_STATUS,
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
