from datetime import datetime, timezone
from app.models.vehicle import Vehicle
from app.models.telemetry import Telemetry

def test_analytics_overview_with_empty_and_populated_data(client, db_session):
    # Empty/Initial query check
    res_empty = client.get("/api/analytics/overview")
    assert res_empty.status_code == 200
    empty_data = res_empty.json()
    assert "total_records" in empty_data
    assert "speed_analytics" in empty_data
    assert empty_data["is_simulated"] is True

    # Seed vehicles & telemetry
    now = datetime.now(timezone.utc)
    v1 = Vehicle(vehicle_identifier="ANL-V1", name="Analytics Van", status="moving")
    db_session.add(v1)
    db_session.commit()

    t1 = Telemetry(
        vehicle_id=v1.id,
        timestamp=now,
        latitude=13.05,
        longitude=80.20,
        speed=60.0,
        status="moving",
        battery_level=75.0
    )
    db_session.add(t1)
    db_session.commit()

    res = client.get("/api/analytics/overview")
    assert res.status_code == 200
    data = res.json()
    assert data["total_records"] >= 1
    assert data["speed_analytics"]["max_recorded_kmh"] >= 60.0
    assert len(data["status_distribution"]) > 0
    assert len(data["activity_over_time"]) > 0
    assert len(data["telemetry_volume_over_time"]) > 0
