# backend/api-gateway/main.py
# -------------------------------------------------------------------------
# API Gateway - Enhanced with Manual Empty override feature
# -------------------------------------------------------------------------

import os
import time
import logging
from typing import List, Optional
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import psycopg2
from psycopg2.extras import RealDictCursor
import redis  # Import Redis

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("APIGateway")

# Environment configurations
DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://wastebin_app:securepassword@localhost:5432/wastebin"
)
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

app = FastAPI(title="Smart Waste Bin IoT API Gateway")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Connect to TimescaleDB
db_conn = None
for attempt in range(1, 11):
    try:
        db_conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
        db_conn.autocommit = True
        logger.info("API Gateway successfully connected to TimescaleDB.")
        break
    except Exception as e:
        logger.warning(f"Database connection attempt {attempt}/10 failed: {e}")
        time.sleep(3)
if not db_conn:
    exit(1)

# Connect to Redis
redis_client = None
for attempt in range(1, 11):
    try:
        redis_client = redis.Redis(
            host=REDIS_HOST, port=REDIS_PORT, decode_responses=True
        )
        redis_client.ping()
        logger.info(f"API Gateway connected to Redis at {REDIS_HOST}:{REDIS_PORT}")
        break
    except Exception as e:
        logger.warning(f"Redis connection attempt {attempt}/10 failed: {e}")
        time.sleep(3)
if not redis_client:
    exit(1)


# --- Pydantic Schemas ---
class BinResponse(BaseModel):
    bin_id: str
    zone_id: str
    bin_depth_cm: float
    current_fill_pct: Optional[float] = None
    last_reading_at: Optional[datetime] = None
    last_emptied_at: Optional[datetime] = None
    status: str
    last_status_at: Optional[datetime] = None


class ReadingHistoryResponse(BaseModel):
    time: datetime
    distance_cm: float
    fill_percent: float
    emptied_this_cycle: bool


class AlertResponse(BaseModel):
    id: int
    bin_id: str
    alert_type: str
    triggered_at: datetime
    resolved_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None


class AcknowledgeRequest(BaseModel):
    operator_name: str


# --- REST Endpoints ---


@app.get("/api/bins", response_model=List[BinResponse])
def get_bins():
    try:
        with db_conn.cursor() as cursor:
            cursor.execute(
                "SELECT bin_id, zone_id, bin_depth_cm, current_fill_pct, "
                "last_reading_at, last_emptied_at, status, last_status_at FROM bins ORDER BY bin_id;"
            )
            return cursor.fetchall()
    except Exception as e:
        logger.error(f"Error fetching bins list: {e}")
        raise HTTPException(status_code=500, detail="Database fetch error")


@app.get("/api/bins/{bin_id}/history", response_model=List[ReadingHistoryResponse])
def get_bin_history(bin_id: str, limit: int = 30):
    try:
        with db_conn.cursor() as cursor:
            cursor.execute(
                "SELECT time, distance_cm, fill_percent, emptied_this_cycle FROM readings "
                "WHERE bin_id = %s ORDER BY time DESC LIMIT %s;",
                (bin_id, limit),
            )
            return cursor.fetchall()
    except Exception as e:
        logger.error(f"Error fetching history for {bin_id}: {e}")
        raise HTTPException(status_code=500, detail="Database fetch error")


@app.get("/api/alerts", response_model=List[AlertResponse])
def get_alerts(status: str = "open"):
    try:
        with db_conn.cursor() as cursor:
            if status == "open":
                cursor.execute(
                    "SELECT * FROM alerts WHERE resolved_at IS NULL ORDER BY triggered_at DESC;"
                )
            else:
                cursor.execute("SELECT * FROM alerts ORDER BY triggered_at DESC;")
            return cursor.fetchall()
    except Exception as e:
        logger.error(f"Error fetching alerts: {e}")
        raise HTTPException(status_code=500, detail="Database fetch error")


@app.post("/api/alerts/{alert_id}/acknowledge")
def acknowledge_alert(alert_id: int, req: AcknowledgeRequest):
    try:
        with db_conn.cursor() as cursor:
            cursor.execute("SELECT id FROM alerts WHERE id = %s;", (alert_id,))
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail="Alert not found")

            cursor.execute(
                "UPDATE alerts SET acknowledged_by = %s WHERE id = %s;",
                (req.operator_name, alert_id),
            )
            return {"status": "success", "message": f"Alert {alert_id} acknowledged."}
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error acknowledging alert {alert_id}: {e}")
        raise HTTPException(status_code=500, detail="Database update error")


# --- NEW: Manual Empty Override Endpoint ---
@app.post("/api/bins/{bin_id}/empty")
def manual_empty_bin(bin_id: str):
    """Manually mark a bin as empty, resetting persistent DB state and Redis cache."""
    try:
        now_ts = datetime.utcnow()

        with db_conn.cursor() as cursor:
            # 1. Fetch current bin configuration depth
            cursor.execute(
                "SELECT bin_depth_cm FROM bins WHERE bin_id = %s;", (bin_id,)
            )
            record = cursor.fetchone()
            if not record:
                raise HTTPException(status_code=404, detail=f"Bin {bin_id} not found")

            bin_depth = record["bin_depth_cm"]

            # 2. Update TimescaleDB state to 0% fill
            cursor.execute(
                "UPDATE bins SET current_fill_pct = 0.0, last_emptied_at = %s, last_reading_at = %s WHERE bin_id = %s;",
                (now_ts, now_ts, bin_id),
            )

            # 3. Auto-resolve any active alerts for this bin
            cursor.execute(
                "UPDATE alerts SET resolved_at = %s WHERE bin_id = %s AND resolved_at IS NULL;",
                (now_ts, bin_id),
            )

            # 4. Insert a clean empty reading into the time-series readings hypertable
            cursor.execute(
                "INSERT INTO readings (time, bin_id, distance_cm, fill_percent, is_confirmed, emptied_this_cycle) "
                "VALUES (%s, %s, %s, 0.0, True, True);",
                (now_ts, bin_id, bin_depth),
            )

        # 5. Clear Redis baselines state key to let the next sensor read start fresh (Crucial!)
        state_key = f"bin_state:{bin_id}"
        redis_client.delete(state_key)

        logger.warning(
            f"[MANUAL OVERRIDE] Bin {bin_id} manually cleared by administrator."
        )
        return {
            "status": "success",
            "message": f"Bin {bin_id} manually cleared and Redis state reset.",
        }

    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error manually emptying bin {bin_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal manual empty error")
