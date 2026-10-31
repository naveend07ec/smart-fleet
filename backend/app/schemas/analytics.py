from typing import List, Dict, Optional
from pydantic import BaseModel

class StatusDistributionItem(BaseModel):
    status: str
    count: int
    percentage: float

class SpeedAnalytics(BaseModel):
    overall_average_kmh: float
    active_average_kmh: float
    max_recorded_kmh: float

class ActivityOverTimePoint(BaseModel):
    timestamp_bucket: str
    moving_count: int
    idle_count: int
    offline_count: int

class TelemetryVolumePoint(BaseModel):
    timestamp_bucket: str
    record_count: int

class VehicleHistorySummary(BaseModel):
    vehicle_id: int
    vehicle_identifier: str
    name: str
    total_telemetry_points: int
    average_speed: float
    max_speed: float
    latest_battery_level: float

class AnalyticsOverviewResponse(BaseModel):
    total_records: int
    status_distribution: List[StatusDistributionItem]
    speed_analytics: SpeedAnalytics
    activity_over_time: List[ActivityOverTimePoint]
    telemetry_volume_over_time: List[TelemetryVolumePoint]
    top_active_vehicles: List[VehicleHistorySummary]
    is_simulated: bool = True
    disclaimer: str = "Research demonstration metrics computed strictly from synthetic IoT simulation data."
