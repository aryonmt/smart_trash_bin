# backend/api-gateway/main.py
# -------------------------------------------------------------------------
# API Gateway - FastAPI interface for TimescaleDB data access
# -------------------------------------------------------------------------

import logging
import os
import time
from datetime import datetime
from typing import List, Optional

import psycopg2
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from psycopg2.extras import RealDictCursor
from pydantic import BaseModel

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("APIGateway")

# Environment configurations
DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://wastebin_app:securepassword@localhost:5432/wastebin"
)

app = FastAPI(title="Smart Waste Bin IoT API Gateway")

# Enable CORS so the React frontend can fetch data successfully
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Connect to database with retry
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


# --- Pydantic Schemas for Response Validation ---
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
    """Retrieve current operational status of all registered bins."""
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
    """Fetch time-series sensory history of a specific bin for charting."""
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
    """Retrieve historical or active/unresolved alerts."""
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
    """Mark an active alert as acknowledged by a dashboard operator."""
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
