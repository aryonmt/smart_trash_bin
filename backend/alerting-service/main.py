# backend/alerting-service/main.py
# -------------------------------------------------------------------------
# Alerting Service - Generates high-fill alerts in database
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
logger = logging.getLogger("AlertingService")

# Environment configurations
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://wastebin_app:securepassword@localhost:5432/wastebin"
)

# Stream configurations
STREAM_FILL_UPDATED = "bin-fill-updated"
GROUP_ALERTING = "alerting-telemetry-group"
CONSUMER_NAME = "alerting-consumer-1"

# Connect to Redis with retry
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

# Connect to Database with retry
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

# Create consumer group
try:
    redis_client.xgroup_create(
        STREAM_FILL_UPDATED, GROUP_ALERTING, id="0", mkstream=True
    )
    logger.info(f"Created consumer group '{GROUP_ALERTING}' on '{STREAM_FILL_UPDATED}'")
except redis.exceptions.ResponseError as e:
    if "BUSYGROUP" not in str(e):
        logger.error(f"Error creating consumer group: {e}")


def check_and_trigger_alerts(msg_id: str, fields: dict):
    bin_id = fields.get("device_id")
    fill_percent = float(fields.get("fill_percent"))
    ts = datetime.fromtimestamp(int(fields.get("timestamp")))

    with db_conn.cursor() as cursor:
        # Check if there is already an active (unresolved) high_fill alert for this bin
        cursor.execute(
            "SELECT id FROM alerts WHERE bin_id = %s AND alert_type = 'high_fill' AND resolved_at IS NULL;",
            (bin_id,),
        )
        active_alert = cursor.fetchone()

        if fill_percent >= 80.0:
            if not active_alert:
                # Trigger a new alert
                cursor.execute(
                    "INSERT INTO alerts (bin_id, alert_type, triggered_at) VALUES (%s, 'high_fill', %s);",
                    (bin_id, ts),
                )
                logger.warning(
                    f"[ALERT] High fill level triggered for bin {bin_id}: {fill_percent}%"
                )
        else:
            if active_alert:
                # Resolve the active alert since the fill level has dropped below 80%
                cursor.execute(
                    "UPDATE alerts SET resolved_at = %s WHERE id = %s;",
                    (ts, active_alert[0]),
                )
                logger.info(f"[ALERT] High fill level resolved for bin {bin_id}")

    # Acknowledge the message
    redis_client.xack(STREAM_FILL_UPDATED, GROUP_ALERTING, msg_id)


def main():
    logger.info("Starting Alerting Service stream listener...")
    while True:
        try:
            streams_data = redis_client.xreadgroup(
                GROUP_ALERTING,
                CONSUMER_NAME,
                {STREAM_FILL_UPDATED: ">"},
                count=5,
                block=500,
            )
            for _, messages in streams_data:
                for msg_id, fields in messages:
                    check_and_trigger_alerts(msg_id, fields)
        except Exception as e:
            logger.error(f"Alerting service processing error: {e}")
            time.sleep(2)


if __name__ == "__main__":
    main()
