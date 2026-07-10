# backend/alerting-service/src/main.py
# -------------------------------------------------------------------------
# Composition root of Alerting Service starting stream listener
# -------------------------------------------------------------------------

import logging
import time
from datetime import datetime

from .config import settings
from .database import db_manager
from .domain.rules import evaluate_telemetry_alerts
from .redis_client import redis_client

# Configure root logger
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("AlertingService")


def process_stream_message(msg_id: str, fields: dict) -> None:
    """Parses stream packet, acquires database connection, and executes rule checking."""
    bin_id = fields.get("device_id")
    fill_percent = float(fields.get("fill_percent"))
    ts = datetime.fromtimestamp(int(fields.get("timestamp")))

    conn = db_manager.get_connection()
    try:
        with conn.cursor() as cursor:
            # Execute business logic rules inside a safe transaction block
            evaluate_telemetry_alerts(cursor, bin_id, fill_percent, ts)
        conn.commit()
        # Acknowledge the message only on successful transaction commits
        redis_client.xack(settings.STREAM_FILL_UPDATED, settings.GROUP_ALERTING, msg_id)
    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to process telemetry alert check for {bin_id}: {e}")
    finally:
        db_manager.release_connection(conn)


def main():
    logger.info("Starting Alerting Service stream listener loop...")
    while True:
        try:
            streams_data = redis_client.xreadgroup(
                settings.GROUP_ALERTING,
                settings.CONSUMER_NAME,
                {settings.STREAM_FILL_UPDATED: ">"},
                count=5,
                block=500,
            )
            for _, messages in streams_data:
                for msg_id, fields in messages:
                    process_stream_message(msg_id, fields)
        except Exception as e:
            logger.error(f"Alerting service processing cycle error: {e}")
            time.sleep(2)


if __name__ == "__main__":
    main()
