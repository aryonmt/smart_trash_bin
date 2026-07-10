# backend/api-gateway/src/routers/bins.py
# -------------------------------------------------------------------------
# APIRouter - Managing all bin registry and telemetry history database actions
# -------------------------------------------------------------------------

import logging
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException

from ..auth.dependencies import RoleChecker, get_current_user
from ..database import db_manager
from ..models.bins import BinCreateRequest, BinResponse, ReadingHistoryResponse
from ..redis_client import redis_client

logger = logging.getLogger("APIGateway.Routers.Bins")
router = APIRouter(prefix="/api/bins", tags=["Bins Management"])


@router.get("", response_model=List[BinResponse])
def get_bins(user: dict = Depends(get_current_user)):
    """Retrieve current operational status of scoped/visible bins."""
    conn = db_manager.get_connection()
    try:
        with conn.cursor() as cursor:
            if user["role"] in ["operator", "driver"] and user["zone_scope"]:
                cursor.execute(
                    "SELECT bin_id, zone_id, bin_depth_cm, current_fill_pct, "
                    "last_reading_at, last_emptied_at, status, last_status_at FROM bins "
                    "WHERE zone_id = %s ORDER BY bin_id;",
                    (user["zone_scope"],),
                )
            else:
                cursor.execute(
                    "SELECT bin_id, zone_id, bin_depth_cm, current_fill_pct, "
                    "last_reading_at, last_emptied_at, status, last_status_at FROM bins ORDER BY bin_id;"
                )
            return cursor.fetchall()
    except Exception as e:
        logger.error(f"Error fetching bins list: {e}")
        raise HTTPException(status_code=500, detail="Database fetch error")
    finally:
        db_manager.release_connection(conn)


@router.get("/{bin_id}/history", response_model=List[ReadingHistoryResponse])
def get_bin_history(
    bin_id: str, limit: int = 30, user: dict = Depends(get_current_user)
):
    """Fetch time-series sensory history of a specific bin."""
    conn = db_manager.get_connection()
    try:
        with conn.cursor() as cursor:
            if user["role"] == "driver" and user["zone_scope"]:
                cursor.execute("SELECT zone_id FROM bins WHERE bin_id = %s;", (bin_id,))
                bin_record = cursor.fetchone()
                if not bin_record or bin_record["zone_id"] != user["zone_scope"]:
                    raise HTTPException(
                        status_code=403, detail="Access denied to this bin's history"
                    )

            cursor.execute(
                "SELECT time, distance_cm, fill_percent, emptied_this_cycle FROM readings "
                "WHERE bin_id = %s ORDER BY time DESC LIMIT %s;",
                (bin_id, limit),
            )
            return cursor.fetchall()
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error fetching history for {bin_id}: {e}")
        raise HTTPException(status_code=500, detail="Database fetch error")
    finally:
        db_manager.release_connection(conn)


@router.post("/{bin_id}/empty")
def manual_empty_bin(
    bin_id: str, user: dict = Depends(RoleChecker(["admin", "operator"]))
):
    """Manually clear a bin, resetting the baseline state in TimescaleDB and Redis cache."""
    conn = db_manager.get_connection()
    try:
        now_ts = datetime.utcnow()
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT bin_depth_cm FROM bins WHERE bin_id = %s;", (bin_id,)
            )
            record = cursor.fetchone()
            if not record:
                raise HTTPException(status_code=404, detail=f"Bin {bin_id} not found")

            bin_depth = record["bin_depth_cm"]

            cursor.execute(
                "UPDATE bins SET current_fill_pct = 0.0, last_emptied_at = %s, last_reading_at = %s WHERE bin_id = %s;",
                (now_ts, now_ts, bin_id),
            )

            cursor.execute(
                "UPDATE alerts SET resolved_at = %s WHERE bin_id = %s AND resolved_at IS NULL;",
                (now_ts, bin_id),
            )

            cursor.execute(
                "INSERT INTO readings (time, bin_id, distance_cm, fill_percent, is_confirmed, emptied_this_cycle) "
                "VALUES (%s, %s, %s, 0.0, True, True);",
                (now_ts, bin_id, bin_depth),
            )

        state_key = f"bin_state:{bin_id}"
        redis_client.delete(state_key)

        logger.warning(
            f"[MANUAL OVERRIDE] Bin {bin_id} manually cleared by administrator: {user['username']}."
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
    finally:
        db_manager.release_connection(conn)


@router.post("", status_code=201)
def create_bin(req: BinCreateRequest, user: dict = Depends(RoleChecker(["admin"]))):
    """Explicitly registers/provisions a new smart waste bin in the database."""
    conn = db_manager.get_connection()
    try:
        now_ts = datetime.utcnow()
        with conn.cursor() as cursor:  # FIXED: Uses pool connection context cleanly
            cursor.execute("SELECT bin_id FROM bins WHERE bin_id = %s;", (req.bin_id,))
            if cursor.fetchone():
                raise HTTPException(
                    status_code=400, detail="Bin with this ID already registered"
                )

            cursor.execute(
                "INSERT INTO bins (bin_id, zone_id, bin_depth_cm, label, latitude, longitude, status, provisioned, last_status_at) "
                "VALUES (%s, %s, %s, %s, %s, %s, 'unknown', TRUE, %s);",
                (
                    req.bin_id,
                    req.zone_id,
                    req.bin_depth_cm,
                    req.label,
                    req.latitude,
                    req.longitude,
                    now_ts,
                ),
            )
            logger.info(
                f"[PROVISIONING] Bin {req.bin_id} explicitly registered by admin user: {user['username']}."
            )
            return {
                "status": "success",
                "message": f"Bin {req.bin_id} successfully provisioned.",
            }
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error provisioning bin: {e}")
        raise HTTPException(status_code=500, detail="Failed to register bin")
    finally:
        db_manager.release_connection(conn)
