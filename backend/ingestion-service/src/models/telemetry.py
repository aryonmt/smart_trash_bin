# backend/ingestion-service/src/models/telemetry.py
# -------------------------------------------------------------------------
# Pydantic schemas for data validation
# -------------------------------------------------------------------------

from typing import Optional

from pydantic import BaseModel, Field


class TelemetryPayload(BaseModel):
    """Resilient validation schema accepting both old and new firmware fields."""

    device_id: str = Field(..., min_length=3)
    zone_id: Optional[str] = Field(default=None, min_length=3)
    distance_cm: float = Field(..., ge=0.0, le=1000.0)
    bin_depth_cm: float = Field(default=150.0, ge=100.0, le=1000.0)
    sample_count: int = Field(default=11, ge=1, le=50)
    uptime_s: int = Field(..., ge=0)
