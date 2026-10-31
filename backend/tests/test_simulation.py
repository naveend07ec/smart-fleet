import time

def test_simulation_start_stop_status(client):
    # Initial status
    status_res = client.get("/api/simulation/status")
    assert status_res.status_code == 200
    assert status_res.json()["is_simulated"] is True

    # Start simulation with scenario of 10 vehicles and deterministic seed 123
    start_res = client.post("/api/simulation/start", json={
        "vehicle_count": 10,
        "interval_seconds": 1.0,
        "random_seed": 123
    })
    assert start_res.status_code == 200
    start_data = start_res.json()
    assert start_data["is_running"] is True
    assert start_data["vehicle_count"] == 10
    assert start_data["random_seed"] == 123

    # Wait briefly for at least one tick
    time.sleep(1.5)

    check_res = client.get("/api/simulation/status")
    assert check_res.status_code == 200
    assert check_res.json()["is_running"] is True

    # Stop simulation
    stop_res = client.post("/api/simulation/stop")
    assert stop_res.status_code == 200
    assert stop_res.json()["is_running"] is False

    # Confirm stopped status
    final_res = client.get("/api/simulation/status")
    assert final_res.status_code == 200
    assert final_res.json()["is_running"] is False
