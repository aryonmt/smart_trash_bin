# backend/persistence-service/src/handlers/status.py
# -------------------------------------------------------------------------
# Handler for persisting device online/offline status updates to TimescaleDB
# -------------------------------------------------------------------------

import logging
from datetime import datetime

from src.config import settings
from src.database import db_manager
from src.redis_client import redis_client

logger = logging.getLogger("PersistenceService.Handlers.Status")


def handle_status_entry(msg_id: str, fields: dict) -> None:
    """Parses and updates the device status in TimescaleDB.

    Status updates are strictly executed via UPDATE queries. Unregistered or
    unprovisioned devices are completely ignored and cannot register themselves
    implicitly through status updates.

    Args:
        msg_id: The processed status message ID inside the Redis Stream.
        fields: Parsed payload dictionary containing device status metrics.
    """
    raw_bin_id = fields.get("device_id")
    status = fields.get("status")
    ts = datetime.fromtimestamp(int(fields.get("timestamp")))

    if not raw_bin_id:
        redis_client.xack(settings.STREAM_STATUS, settings.GROUP_STATUS, msg_id)
        return

    bin_id = raw_bin_id.strip()

    conn = db_manager.get_connection()
    try:
        with conn.cursor() as cursor:
            status_update_query = """
                UPDATE bins SET
                    status = %s,
                    last_status_at = %s
                WHERE bin_id = %s AND provisioned = TRUE;
            """
            cursor.execute(status_update_query, (status, ts, bin_id))

        conn.commit()
        redis_client.xack(settings.STREAM_STATUS, settings.GROUP_STATUS, msg_id)
        logger.info(f"Persisted status update for registered bin {bin_id}: {status}")

    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to persist status entry {msg_id} for {bin_id}: {e}")
    finally:
        db_manager.release_connection(conn)
