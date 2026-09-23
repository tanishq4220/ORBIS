from typing import Optional

from pydantic import BaseModel, Field


class ScreenRequest(BaseModel):
    object_id: str
    time_step_min: int = Field(10, ge=1, le=60)
    window_min: int = Field(60, ge=10, le=720)
    threshold_km: float = Field(50.0, gt=0, le=5000)
    top_n: int = Field(10, ge=1, le=50)
    start_utc: Optional[str] = None