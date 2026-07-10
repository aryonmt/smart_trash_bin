# backend/alerting-service/src/domain/rules.py
# -------------------------------------------------------------------------
# Pure business logic rules for managing bin alert thresholds
# -------------------------------------------------------------------------

import logging
from datetime import datetime

logger = logging.getLogger("AlertingService.Domain")


def evaluate_telemetry_alerts(
    cursor, bin_id: str, fill_percent: float, timestamp: datetime
) -> None:
    """Evaluates the calculated fill level and triggers/resolves high_fill alerts.

    Args:
        cursor: Active Postgres transaction cursor.
        bin_id: Unique string identifier of the waste bin.
        fill_percent: The confirmed fill percentage calculated by upstream.
        timestamp: Datetime object representing the telemetry timestamp.
    """
    # 1. Search for an unresolved active high_fill alert for this bin
    cursor.execute(
        "SELECT id FROM alerts WHERE bin_id = %s AND alert_type = 'high_fill' AND resolved_at IS NULL;",
        (bin_id,),
    )
    active_alert = cursor.fetchone()

    # 2. Evaluate rules against 80.0% critical threshold
    if fill_percent >= 80.0:
        if not active_alert:
            # Trigger and persist a new alert
            cursor.execute(
                "INSERT INTO alerts (bin_id, alert_type, triggered_at) VALUES (%s, 'high_fill', %s);",
                (bin_id, timestamp),
            )
            logger.warning(
                f"[ALERT TRIGGERED] High fill level breached for {bin_id}: {fill_percent}%"
            )
    else:
        if active_alert:
            # Resolve the active alert as the level has dropped below the threshold
            cursor.execute(
                "UPDATE alerts SET resolved_at = %s WHERE id = %s;",
                (timestamp, active_alert[0]),
            )
            logger.info(
                f"[ALERT RESOLVED] High fill level resolved for {bin_id} ({fill_percent}%)"
            )
