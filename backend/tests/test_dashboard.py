from datetime import datetime, timezone
from app.models.vehicle import Vehicle
from app.models.telemetry import Telemetry

def test_dashboard_summary_with_data(client, db_session):
    # Add vehicles
    v1 = Vehicle(vehicle_identifier="DASH-V1", name="Dash 1", status="moving")
    v2 = Vehicle(vehicle_identifier="DASH-V2", name="Dash 2", status="idle")
    v3 = Vehicle(vehicle_identifier="DASH-V3", name="Dash 3", status="offline")
    db_session.add_all([v1, v2, v3])
    db_session.commit()

    # Add telemetry
    now = datetime.now(timezone.utc)
    t1 = Telemetry(vehicle_id=v1.id, timestamp=now, latitude=13.0, longitude=80.1, speed=50.0, status="moving", battery_level=90.0)
    t2 = Telemetry(vehicle_id=v2.id, timestamp=now, latitude=13.01, longitude=80.11, speed=0.0, status="idle", battery_level=95.0)
    db_session.add_all([t1, t2])
    db_session.commit()

    res = client.get("/api/dashboard/summary")
    assert res.status_code == 200
    data = res.json()

    assert data["total_vehicles"] >= 3
    assert data["status_breakdown"]["moving"] >= 1
    assert data["status_breakdown"]["idle"] >= 1
    assert data["status_breakdown"]["offline"] >= 1
    assert data["speed_stats"]["average_speed_active_kmh"] > 0
    assert data["is_simulated"] is True
    assert "simulated" in data["disclaimer"].lower()
