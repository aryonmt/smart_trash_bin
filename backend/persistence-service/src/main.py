# backend/persistence-service/src/main.py
# -------------------------------------------------------------------------
# Persistence Service - Orchestrator consumer main loop
# -------------------------------------------------------------------------

import logging
import time

from .config import settings
from .database import db_manager
from .handlers.status import handle_status_entry
from .handlers.telemetry import handle_telemetry_entry
from .redis_client import redis_client

# Configure root logger
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("PersistenceService")


def main():
    # Initialize thread-safe database connection pool
    db_manager.initialize()

    logger.info("Starting Persistence Stream consumer main loop...")
    while True:
        try:
            # 1. Consume Telemetry Stream
            telemetry_data = redis_client.xreadgroup(
                settings.GROUP_TELEMETRY,
                settings.CONSUMER_NAME,
                {settings.STREAM_FILL_UPDATED: ">"},
                count=5,
                block=500,
            )
            for _, messages in telemetry_data:
                for msg_id, fields in messages:
                    handle_telemetry_entry(msg_id, fields)

            # 2. Consume Device Status Stream
            status_data = redis_client.xreadgroup(
                settings.GROUP_STATUS,
                settings.CONSUMER_NAME,
                {settings.STREAM_STATUS: ">"},
                count=5,
                block=500,
            )
            for _, messages in status_data:
                for msg_id, fields in messages:
                    handle_status_entry(msg_id, fields)

        except Exception as e:
            logger.error(f"Persistence consumer cycle error: {e}")
            time.sleep(2)


if __name__ == "__main__":
    main()
