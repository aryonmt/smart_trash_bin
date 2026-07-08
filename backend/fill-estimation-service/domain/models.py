# backend/fill-estimation-service/domain/models.py
# -------------------------------------------------------------------------
# Domain Models for persistent state of waste bins
# -------------------------------------------------------------------------

from typing import Optional

from pydantic import BaseModel


class BinFillState(BaseModel):
    """Persistent state of a bin tracked across measurement cycles."""

    confirmed_distance_cm: float
    candidate_distance_cm: Optional[float] = None
    candidate_streak: int = 0
    near_empty_streak: int = 0


class BinConfig(BaseModel):
    """Static site-specific parameters for a physical bin installation."""

    bin_depth_cm: float = 150.0
    sensor_blind_zone_cm: float = 20.0
    confirm_cycles: int = 3
    tolerance_cm: float = 5.0
    empty_ratio_threshold: float = 0.90
    empty_confirm_cycles: int = 2

    @property
    def full_line_cm(self) -> float:
        """Distance from the sensor representing 100% full (blind zone limit)."""
        return self.bin_depth_cm - self.sensor_blind_zone_cm

    @property
    def usable_depth_cm(self) -> float:
        """Effective physical range available for garbage accumulation."""
        return self.bin_depth_cm - self.sensor_blind_zone_cm
