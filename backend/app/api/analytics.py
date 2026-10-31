from datetime import datetime, timezone, timedelta
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from app.database import get_db
from app.models.vehicle import Vehicle
from app.models.telemetry import Telemetry
from app.schemas.analytics import (
    AnalyticsOverviewResponse,
    StatusDistributionItem,
    SpeedAnalytics,
    ActivityOverTimePoint,
    TelemetryVolumePoint,
    VehicleHistorySummary
)

router = APIRouter(prefix="/api/analytics", tags=["Fleet Analytics"])

@router.get("/overview", response_model=AnalyticsOverviewResponse, summary="Get comprehensive fleet analytics metrics")
def get_analytics_overview(db: Session = Depends(get_db)):
    total_records = db.query(Telemetry).count()
    total_vehicles = db.query(Vehicle).count()

    # 1. Status distribution
    status_counts = (
        db.query(Vehicle.status, func.count(Vehicle.id))
        .group_by(Vehicle.status)
        .all()
    )
    distribution: List[StatusDistributionItem] = []
    for st, count in status_counts:
        pct = round((count / total_vehicles * 100), 1) if total_vehicles > 0 else 0.0
        distribution.append(StatusDistributionItem(status=st, count=count, percentage=pct))

    # 2. Speed analytics
    avg_speed_row = db.query(func.avg(Telemetry.speed)).scalar()
    overall_avg = round(float(avg_speed_row or 0.0), 1)

    active_avg_row = (
        db.query(func.avg(Telemetry.speed))
        .filter(Telemetry.speed > 0, Telemetry.status == "moving")
        .scalar()
    )
    active_avg = round(float(active_avg_row or 0.0), 1)

    max_spd_row = db.query(func.max(Telemetry.speed)).scalar()
    max_spd = round(float(max_spd_row or 0.0), 1)

    # 3. Activity and volume over time (past 6 hours divided into 6 1-hour buckets)
    now = datetime.now(timezone.utc)
    activity_points: List[ActivityOverTimePoint] = []
    volume_points: List[TelemetryVolumePoint] = []

    for i in range(5, -1, -1):
        bucket_start = now - timedelta(hours=i + 1)
        bucket_end = now - timedelta(hours=i)
        bucket_label = bucket_end.strftime("%H:00")

        # Telemetry volume in bucket
        vol = (
            db.query(func.count(Telemetry.id))
            .filter(Telemetry.timestamp >= bucket_start, Telemetry.timestamp < bucket_end)
            .scalar() or 0
        )
        volume_points.append(TelemetryVolumePoint(timestamp_bucket=bucket_label, record_count=vol))

        # Activity breakdown in bucket
        subq = (
            db.query(Telemetry.status, func.count(Telemetry.id))
            .filter(Telemetry.timestamp >= bucket_start, Telemetry.timestamp < bucket_end)
            .group_by(Telemetry.status)
            .all()
        )
        st_map = {row[0]: row[1] for row in subq}
        activity_points.append(
            ActivityOverTimePoint(
                timestamp_bucket=bucket_label,
                moving_count=st_map.get("moving", 0),
                idle_count=st_map.get("idle", 0),
                offline_count=st_map.get("offline", 0)
            )
        )

    # 4. Top active vehicles with historical trend summary
    top_vehicles = db.query(Vehicle).limit(8).all()
    vehicle_summaries: List[VehicleHistorySummary] = []
    for v in top_vehicles:
        count = db.query(Telemetry).filter(Telemetry.vehicle_id == v.id).count()
        v_avg = db.query(func.avg(Telemetry.speed)).filter(Telemetry.vehicle_id == v.id).scalar() or 0.0
        v_max = db.query(func.max(Telemetry.speed)).filter(Telemetry.vehicle_id == v.id).scalar() or 0.0
        latest_tel = (
            db.query(Telemetry.battery_level)
            .filter(Telemetry.vehicle_id == v.id)
            .order_by(desc(Telemetry.timestamp))
            .first()
        )
        batt = latest_tel[0] if latest_tel else 100.0

        vehicle_summaries.append(
            VehicleHistorySummary(
                vehicle_id=v.id,
                vehicle_identifier=v.vehicle_identifier,
                name=v.name,
                total_telemetry_points=count,
                average_speed=round(float(v_avg), 1),
                max_speed=round(float(v_max), 1),
                latest_battery_level=round(float(batt), 1)
            )
        )

    return AnalyticsOverviewResponse(
        total_records=total_records,
        status_distribution=distribution,
        speed_analytics=SpeedAnalytics(
            overall_average_kmh=overall_avg,
            active_average_kmh=active_avg,
            max_recorded_kmh=max_spd
        ),
        activity_over_time=activity_points,
        telemetry_volume_over_time=volume_points,
        top_active_vehicles=vehicle_summaries,
        is_simulated=True,
        disclaimer="Research demonstration metrics computed strictly from synthetic IoT simulation data."
    )
