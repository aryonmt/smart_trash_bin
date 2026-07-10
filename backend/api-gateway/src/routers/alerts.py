import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException

from ..auth.dependencies import RoleChecker
from ..database import db_manager
from ..models.alerts import AcknowledgeRequest, AlertResponse

logger = logging.getLogger("APIGateway.Routers.Alerts")
router = APIRouter(prefix="/api/alerts", tags=["Alerts Management"])


@router.get("", response_model=List[AlertResponse])
def get_alerts(
    status: str = "open", user: dict = Depends(RoleChecker(["admin", "operator"]))
):
    """Retrieve historical or active unresolved warnings."""
    conn = db_manager.get_connection()
    try:
        with conn.cursor() as cursor:
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
    finally:
        db_manager.release_connection(conn)


@router.post("/{alert_id}/acknowledge")
def acknowledge_alert(
    alert_id: int,
    req: AcknowledgeRequest,
    user: dict = Depends(RoleChecker(["admin", "operator"])),
):
    """Mark an active alert as acknowledged by a dashboard operator."""
    conn = db_manager.get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id FROM alerts WHERE id = %s;", (alert_id,))
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail="Alert not found")

            cursor.execute(
                "UPDATE alerts SET acknowledged_by = %s WHERE id = %s;",
                (req.operator_name, alert_id),
            )
            return {
                "status": "success",
                "message": f"Alert {alert_id} acknowledged by {req.operator_name}.",
            }
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error acknowledging alert {alert_id}: {e}")
        raise HTTPException(status_code=500, detail="Database update error")
    finally:
        db_manager.release_connection(conn)
