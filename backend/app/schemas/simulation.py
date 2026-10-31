from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

class SimulationStartRequest(BaseModel):
    vehicle_count: int = Field(default=25, ge=1, le=100, description="Fleet size scenario (e.g. 10, 25, 50)")
    interval_seconds: float = Field(default=3.0, ge=0.5, le=60.0, description="Simulation tick frequency in seconds")
    random_seed: Optional[int] = Field(default=None, description="Optional seed for deterministic reproducibility")

class SimulationStatusResponse(BaseModel):
    is_running: bool
    vehicle_count: int
    interval_seconds: float
    tick_count: int
    random_seed: Optional[int]
    started_at: Optional[datetime]
    last_tick_at: Optional[datetime]
    message: str
    is_simulated: bool = True
