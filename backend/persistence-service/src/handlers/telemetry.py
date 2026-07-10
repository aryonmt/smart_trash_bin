# backend/persistence-service/src/handlers/telemetry.py
# -------------------------------------------------------------------------
# Handler for persisting processed telemetry and readings to TimescaleDB
# -------------------------------------------------------------------------

import logging
from datetime import datetime

from ...config import settings
from ...database import db_manager
from ...redis_client import redis_client

logger = logging.getLogger("PersistenceService.Handlers.Telemetry")


def handle_telemetry_entry(msg_id: str, fields: dict) -> None:
    """Validates, verifies provisioning, and writes telemetry reading to DB.

    Args:
        msg_id: The processed message ID inside the Redis Stream.
        fields: Parsed payload dictionary containing bin measurements.
    """
    raw_bin_id = fields.get("device_id")
    if not raw_bin_id:
        logger.warning(f"Malformed telemetry stream entry {msg_id} lacked device_id.")
        redis_client.xack(
            settings.STREAM_FILL_UPDATED, settings.GROUP_TELEMETRY, msg_id
        )
        return

    bin_id = raw_bin_id.strip()
    zone_id = fields.get("zone_id", "").strip()
    fill_percent = float(fields.get("fill_percent"))
    confirmed_dist = float(fields.get("confirmed_distance_cm"))
    is_emptied = bool(int(fields.get("is_emptied")))
    ts = datetime.fromtimestamp(int(fields.get("timestamp")))

    conn = db_manager.get_connection()
    try:
        with conn.cursor() as cursor:
            # Security Guard: Verify if this bin is registered and provisioned
            cursor.execute("SELECT provisioned FROM bins WHERE bin_id = %s;", (bin_id,))
            bin_record = cursor.fetchone()

            logger.info(
                f"[SECURITY DEBUG] Querying state for '{bin_id}' -> Database returned: {bin_record}"
            )

            # Verified Indexing: Tuple index [0] to protect system integrity
            if not bin_record or not bin_record[0]:
                logger.warning(
                    f"[SECURITY ALERT] Blocked incoming telemetry from unauthorized/unprovisioned device ID: {bin_id}. "
                    f"Payload ignored to protect system integrity."
                )
                redis_client.xack(
                    settings.STREAM_FILL_UPDATED, settings.GROUP_TELEMETRY, msg_id
                )
                return

            # 1. Upsert current state in the bins metadata table
            bin_upsert_query = """
                INSERT INTO bins (bin_id, zone_id, current_fill_pct, last_reading_at, last_emptied_at)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (bin_id) DO UPDATE SET
                    current_fill_pct = EXCLUDED.current_fill_pct,
                    last_reading_at = EXCLUDED.last_reading_at,
                    last_emptied_at = CASE WHEN EXCLUDED.last_emptied_at IS NOT NULL THEN EXCLUDED.last_emptied_at ELSE bins.last_emptied_at END;
            """
            last_empty_ts = ts if is_emptied else None
            cursor.execute(
                bin_upsert_query, (bin_id, zone_id, fill_percent, ts, last_empty_ts)
            )

            # 2. Insert time-series sensor entry in readings hypertable
            reading_insert_query = """
                INSERT INTO readings (time, bin_id, distance_cm, fill_percent, is_confirmed, emptied_this_cycle)
                VALUES (%s, %s, %s, %s, %s, %s);
            """
            cursor.execute(
                reading_insert_query,
                (ts, bin_id, confirmed_dist, fill_percent, True, is_emptied),
            )

        conn.commit()
        redis_client.xack(
            settings.STREAM_FILL_UPDATED, settings.GROUP_TELEMETRY, msg_id
        )
        logger.info(f"Persisted reading for {bin_id}: {fill_percent}% to TimescaleDB")

    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to persist telemetry entry {msg_id} for {bin_id}: {e}")
    finally:
        db_manager.release_connection(conn)
