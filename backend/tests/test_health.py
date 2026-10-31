def test_health_check(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["healthy", "degraded"]
    assert "version" in data
    assert data["is_simulated_system"] is True
    assert "simulation" in data

def test_root_info(client):
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "IoT-Driven Smart Transportation" in data["system"]
    assert data["simulated"] is True
