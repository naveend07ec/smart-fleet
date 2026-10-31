from datetime import datetime, timezone
from app.models.telemetry import Telemetry

def test_telemetry_retrieval_and_empty_state(client, db_session):
    # Create vehicle without telemetry
    res = client.post("/api/vehicles", json={
        "vehicle_identifier": "TEST-TEL-001",
        "name": "Telemetry Test Carrier",
        "status": "idle"
    })
    v_id = res.json()["id"]

    # Check telemetry endpoint when empty
    tel_res = client.get(f"/api/vehicles/{v_id}/telemetry")
    assert tel_res.status_code == 200
    tel_data = tel_res.json()
    assert tel_data["total"] == 0
    assert len(tel_data["items"]) == 0

    # Insert test telemetry directly
    t1 = Telemetry(
        vehicle_id=v_id,
        timestamp=datetime.now(timezone.utc),
        latitude=13.0827,
        longitude=80.2707,
        speed=42.5,
        status="moving",
        battery_level=88.0
    )
    db_session.add(t1)
    db_session.commit()

    # Query telemetry
    tel_res2 = client.get(f"/api/vehicles/{v_id}/telemetry")
    assert tel_res2.status_code == 200
    tel_data2 = tel_res2.json()
    assert tel_data2["total"] == 1
    assert tel_data2["items"][0]["speed"] == 42.5
    assert tel_data2["items"][0]["battery_level"] == 88.0

def test_telemetry_nonexistent_vehicle(client):
    res = client.get("/api/vehicles/9999999/telemetry")
    assert res.status_code == 404
