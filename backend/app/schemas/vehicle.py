from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict
from app.schemas.telemetry import TelemetryResponse

class VehicleBase(BaseModel):
    vehicle_identifier: str = Field(..., min_length=2, max_length=50, description="Unique simulated vehicle ID")
    name: str = Field(..., min_length=2, max_length=100, description="Display name of the vehicle")
    status: str = Field(default="idle", description="Vehicle operational status: moving, idle, offline")

class VehicleCreate(VehicleBase):
    pass

class VehicleUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    status: Optional[str] = Field(None, description="moving, idle, offline")

class VehicleResponse(VehicleBase):
    id: int
    created_at: datetime
    updated_at: datetime
    latest_telemetry: Optional[TelemetryResponse] = None

    model_config = ConfigDict(from_attributes=True)

class VehicleDetailResponse(VehicleResponse):
    telemetry_history_sample: List[TelemetryResponse] = []
    total_telemetry_records: int = 0

class VehiclePaginationResponse(BaseModel):
    items: List[VehicleResponse]
    total: int
    page: int
    limit: int
    total_pages: int
