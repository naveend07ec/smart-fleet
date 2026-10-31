from datetime import datetime
from typing import Optional, List, Dict
from pydantic import BaseModel

class StatusBreakdown(BaseModel):
    moving: int
    idle: int
    offline: int

class SpeedStats(BaseModel):
    average_speed_active_kmh: float
    max_speed_kmh: float

class TelemetryTrendPoint(BaseModel):
    time_label: str
    record_count: int
    avg_speed: float

class DashboardSummaryResponse(BaseModel):
    total_vehicles: int
    status_breakdown: StatusBreakdown
    speed_stats: SpeedStats
    latest_telemetry_at: Optional[datetime]
    recent_trend: List[TelemetryTrendPoint]
    is_simulated: bool = True
    disclaimer: str = "All vehicle locations, status, speed, and telemetry are synthetically simulated for research purposes."
