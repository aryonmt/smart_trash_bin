# backend/persistence-service/main.py
# -------------------------------------------------------------------------
# Persistence Service - Writes validated streams to TimescaleDB
# -------------------------------------------------------------------------

import logging
import os
import time
from datetime import datetime

import psycopg2
import redis

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("PersistenceService")

# Environment configurations
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://wastebin_app:securepassword@localhost:5432/wastebin"
)

# Streams configuration
STREAM_FILL_UPDATED = "bin-fill-updated"
STREAM_STATUS = "device-status"
GROUP_TELEMETRY = "persistence-telemetry-group"
GROUP_STATUS = "persistence-status-group"
CONSUMER_NAME = "persistence-consumer-1"

# Redis Setup with Retry
redis_client = None
for attempt in range(1, 11):
    try:
        redis_client = redis.Redis(
            host=REDIS_HOST, port=REDIS_PORT, decode_responses=True
        )
        redis_client.ping()
        logger.info(f"Connected to Redis at {REDIS_HOST}:{REDIS_PORT}")
        break
    except Exception as e:
        logger.warning(f"Redis connection attempt {attempt}/10 failed: {e}")
        time.sleep(3)
if not redis_client:
    exit(1)

# TimescaleDB Setup with Retry
db_conn = None
for attempt in range(1, 11):
    try:
        db_conn = psycopg2.connect(DATABASE_URL)
        db_conn.autocommit = True
        logger.info("Connected to TimescaleDB successfully.")
        break
    except Exception as e:
        logger.warning(f"Database connection attempt {attempt}/10 failed: {e}")
        time.sleep(3)
if not db_conn:
    exit(1)

# Create Consumer Groups
for stream, group in [
    (STREAM_FILL_UPDATED, GROUP_TELEMETRY),
    (STREAM_STATUS, GROUP_STATUS),
]:
    try:
        redis_client.xgroup_create(stream, group, id="0", mkstream=True)
        logger.info(f"Created consumer group '{group}' on '{stream}'")
    except redis.exceptions.ResponseError as e:
        if "BUSYGROUP" not in str(e):
            logger.error(f"Error creating group {group}: {e}")


def handle_telemetry_entry(msg_id: str, fields: dict):
    bin_id = fields.get("device_id")
    zone_id = fields.get("zone_id")
    fill_percent = float(fields.get("fill_percent"))
    confirmed_dist = float(fields.get("confirmed_distance_cm"))
    is_emptied = bool(int(fields.get("is_emptied")))
    ts = datetime.fromtimestamp(int(fields.get("timestamp")))

    with db_conn.cursor() as cursor:
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

    redis_client.xack(STREAM_FILL_UPDATED, GROUP_TELEMETRY, msg_id)
    logger.info(f"Persisted reading for {bin_id}: {fill_percent}% to TimescaleDB")


def handle_status_entry(msg_id: str, fields: dict):
    bin_id = fields.get("device_id")
    zone_id = fields.get("zone_id")
    status = fields.get("status")
    ts = datetime.fromtimestamp(int(fields.get("timestamp")))

    with db_conn.cursor() as cursor:
        status_upsert_query = """
            INSERT INTO bins (bin_id, zone_id, status, last_status_at)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (bin_id) DO UPDATE SET
                status = EXCLUDED.status,
                last_status_at = EXCLUDED.last_status_at;
        """
        cursor.execute(status_upsert_query, (bin_id, zone_id, status, ts))

    redis_client.xack(STREAM_STATUS, GROUP_STATUS, msg_id)
    logger.info(f"Persisted status for {bin_id}: {status} to TimescaleDB")


def main():
    logger.info("Starting Persistence Stream consumer main loop...")
    while True:
        try:
            # 1. Read Telemetry Stream
            telemetry_data = redis_client.xreadgroup(
                GROUP_TELEMETRY,
                CONSUMER_NAME,
                {STREAM_FILL_UPDATED: ">"},
                count=5,
                block=500,
            )
            for _, messages in telemetry_data:
                for msg_id, fields in messages:
                    handle_telemetry_entry(msg_id, fields)

            # 2. Read Device Status Stream
            status_data = redis_client.xreadgroup(
                GROUP_STATUS, CONSUMER_NAME, {STREAM_STATUS: ">"}, count=5, block=500
            )
            for _, messages in status_data:
                for msg_id, fields in messages:
                    handle_status_entry(msg_id, fields)

        except psycopg2.InterfaceError:
            logger.warning("Database connection lost. Reconnecting...")
            try:
                db_conn = psycopg2.connect(DATABASE_URL)
                db_conn.autocommit = True
            except Exception as e:
                logger.error(f"Reconnection failed: {e}")
                time.sleep(5)
        except Exception as e:
            logger.error(f"Persistence consumer cycle error: {e}")
            time.sleep(2)


if __name__ == "__main__":
    main()
