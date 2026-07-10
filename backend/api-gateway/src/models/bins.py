from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, constr


class BinCreateRequest(BaseModel):
    """Schema representing explicit administrative device provisioning request."""

    bin_id: constr(min_length=3)
    zone_id: constr(min_length=3)
    bin_depth_cm: float = Field(default=150.0, ge=100.0)
    label: Optional[str] = None
    latitude: Optional[float] = Field(default=None, ge=-90.0, le=90.0)
    longitude: Optional[float] = Field(default=None, ge=-180.0, le=180.0)


class BinResponse(BaseModel):
    """Schema representing a bin's operational metadata and live stats."""

    bin_id: str
    zone_id: str
    bin_depth_cm: float
    current_fill_pct: Optional[float] = None
    last_reading_at: Optional[datetime] = None
    last_emptied_at: Optional[datetime] = None
    status: str
    last_status_at: Optional[datetime] = None


class ReadingHistoryResponse(BaseModel):
    """Schema representing historical time-series telemetry data point."""

    time: datetime
    distance_cm: float
    fill_percent: float
    emptied_this_cycle: bool
