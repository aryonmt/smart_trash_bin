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

    Args:
        msg_id: The processed status message ID inside the Redis Stream.
        fields: Parsed payload dictionary containing device status metrics.
    """
    bin_id = fields.get("device_id")
    zone_id = fields.get("zone_id")
    status = fields.get("status")
    ts = datetime.fromtimestamp(int(fields.get("timestamp")))

    conn = db_manager.get_connection()
    try:
        with conn.cursor() as cursor:
            status_upsert_query = """
                INSERT INTO bins (bin_id, zone_id, status, last_status_at)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (bin_id) DO UPDATE SET
                    status = EXCLUDED.status,
                    last_status_at = EXCLUDED.last_status_at;
            """
            cursor.execute(status_upsert_query, (bin_id, zone_id, status, ts))

        conn.commit()
        redis_client.xack(settings.STREAM_STATUS, settings.GROUP_STATUS, msg_id)
        logger.info(f"Persisted status for {bin_id}: {status} to TimescaleDB")

    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to persist status entry {msg_id} for {bin_id}: {e}")
    finally:
        db_manager.release_connection(conn)
