from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict

class TelemetryBase(BaseModel):
    latitude: float = Field(..., ge=-90.0, le=90.0, description="Simulated latitude coordinate")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="Simulated longitude coordinate")
    speed: float = Field(..., ge=0.0, le=250.0, description="Simulated speed in km/h")
    status: str = Field(..., description="Operational status: moving, idle, offline")
    battery_level: float = Field(..., ge=0.0, le=100.0, description="Simulated power/battery indicator (percentage)")

class TelemetryCreate(TelemetryBase):
    vehicle_id: int
    timestamp: Optional[datetime] = None

class TelemetryResponse(TelemetryBase):
    id: int
    vehicle_id: int
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)

class TelemetryPaginationResponse(BaseModel):
    items: List[TelemetryResponse]
    total: int
    page: int
    limit: int
    total_pages: int
