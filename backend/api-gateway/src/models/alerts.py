from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class AlertResponse(BaseModel):
    """Schema representing active or historical system warning alerts."""

    id: int
    bin_id: str
    alert_type: str
    triggered_at: datetime
    resolved_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None


class AcknowledgeRequest(BaseModel):
    """Schema representing an operator alert acknowledgment request."""

    operator_name: str
