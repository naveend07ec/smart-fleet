from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from app.database import get_db
from app.models.vehicle import Vehicle
from app.models.telemetry import Telemetry
from app.schemas.dashboard import (
    DashboardSummaryResponse,
    StatusBreakdown,
    SpeedStats,
    TelemetryTrendPoint
)

router = APIRouter(prefix="/api/dashboard", tags=["Fleet Dashboard"])

@router.get("/summary", response_model=DashboardSummaryResponse, summary="Get aggregated dashboard metrics")
def get_dashboard_summary(db: Session = Depends(get_db)):
    total_vehicles = db.query(Vehicle).count()

    # Calculate status breakdown
    status_counts = (
        db.query(Vehicle.status, func.count(Vehicle.id))
        .group_by(Vehicle.status)
        .all()
    )
    breakdown_map = {st.lower(): count for st, count in status_counts}
    breakdown = StatusBreakdown(
        moving=breakdown_map.get("moving", 0),
        idle=breakdown_map.get("idle", 0),
        offline=breakdown_map.get("offline", 0)
    )

    # Active vehicles average speed & max speed from recent telemetry
    # Check latest telemetry per vehicle or latest 100 points
    latest_points = (
        db.query(Telemetry.speed, Telemetry.status)
        .order_by(desc(Telemetry.timestamp))
        .limit(200)
        .all()
    )

    active_speeds = [p.speed for p in latest_points if p.status == "moving" and p.speed > 0]
    avg_speed = round(sum(active_speeds) / len(active_speeds), 1) if active_speeds else 0.0

    max_speed_row = db.query(func.max(Telemetry.speed)).scalar()
    max_speed = round(float(max_speed_row or 0.0), 1)

    # Latest telemetry timestamp
    latest_rec = db.query(Telemetry.timestamp).order_by(desc(Telemetry.timestamp)).first()
    latest_telemetry_at = latest_rec[0] if latest_rec else None

    # Trend calculation: sample telemetry points grouped in 5 recent intervals
    now = datetime.now(timezone.utc)
    recent_trend = []
    
    # 6 intervals of 10 minutes each up to 60 minutes
    for i in range(5, -1, -1):
        window_start = now - timedelta(minutes=(i + 1) * 10)
        window_end = now - timedelta(minutes=i * 10)
        time_label = window_end.strftime("%H:%M")

        res = (
            db.query(func.count(Telemetry.id), func.avg(Telemetry.speed))
            .filter(Telemetry.timestamp >= window_start, Telemetry.timestamp < window_end)
            .first()
        )
        count = res[0] or 0
        avg_spd = round(float(res[1] or 0.0), 1)

        recent_trend.append(
            TelemetryTrendPoint(
                time_label=time_label,
                record_count=count,
                avg_speed=avg_spd
            )
        )

    return DashboardSummaryResponse(
        total_vehicles=total_vehicles,
        status_breakdown=breakdown,
        speed_stats=SpeedStats(
            average_speed_active_kmh=avg_speed,
            max_speed_kmh=max_speed
        ),
        latest_telemetry_at=latest_telemetry_at,
        recent_trend=recent_trend,
        is_simulated=True,
        disclaimer="All vehicle locations, status, speed, and telemetry are synthetically simulated for research purposes."
    )
