def test_create_and_get_vehicle(client):
    # Create vehicle
    create_payload = {
        "vehicle_identifier": "TEST-VEH-001",
        "name": "Test Express Shuttle",
        "status": "moving"
    }
    res = client.post("/api/vehicles", json=create_payload)
    assert res.status_code == 201
    created = res.json()
    assert created["vehicle_identifier"] == "TEST-VEH-001"
    assert created["name"] == "Test Express Shuttle"
    assert created["status"] == "moving"
    vehicle_id = created["id"]

    # Retrieve by numeric ID
    res_get = client.get(f"/api/vehicles/{vehicle_id}")
    assert res_get.status_code == 200
    assert res_get.json()["vehicle_identifier"] == "TEST-VEH-001"

    # Retrieve by identifier string
    res_get_str = client.get("/api/vehicles/TEST-VEH-001")
    assert res_get_str.status_code == 200
    assert res_get_str.json()["id"] == vehicle_id

def test_duplicate_vehicle_identifier_fails(client):
    payload = {
        "vehicle_identifier": "TEST-DUP-01",
        "name": "Duplicate Test 1",
        "status": "idle"
    }
    res1 = client.post("/api/vehicles", json=payload)
    assert res1.status_code == 201

    res2 = client.post("/api/vehicles", json=payload)
    assert res2.status_code == 400
    assert "already exists" in res2.json()["detail"]

def test_invalid_vehicle_status_validation(client):
    payload = {
        "vehicle_identifier": "TEST-INVALID-STATUS",
        "name": "Invalid Status Shuttle",
        "status": "flying"
    }
    res = client.post("/api/vehicles", json=payload)
    assert res.status_code == 400
    assert "Status must be one of" in res.json()["detail"]

def test_update_and_delete_vehicle(client):
    # Create
    res = client.post("/api/vehicles", json={
        "vehicle_identifier": "TEST-TO-UPDATE",
        "name": "Original Name",
        "status": "idle"
    })
    v_id = res.json()["id"]

    # Patch
    patch_res = client.patch(f"/api/vehicles/{v_id}", json={
        "name": "Updated Name",
        "status": "moving"
    })
    assert patch_res.status_code == 200
    assert patch_res.json()["name"] == "Updated Name"
    assert patch_res.json()["status"] == "moving"

    # Delete
    del_res = client.delete(f"/api/vehicles/{v_id}")
    assert del_res.status_code == 200

    # Ensure 404 after delete
    get_after = client.get(f"/api/vehicles/{v_id}")
    assert get_after.status_code == 404

def test_nonexistent_vehicle_returns_404(client):
    res = client.get("/api/vehicles/NON_EXISTENT_ID_99999")
    assert res.status_code == 404
    assert "not found" in res.json()["detail"]

def test_list_vehicles_pagination_and_filter(client):
    # Create multiple vehicles
    for i in range(1, 6):
        client.post("/api/vehicles", json={
            "vehicle_identifier": f"TEST-LIST-{i:03d}",
            "name": f"Filter Vehicle {i}",
            "status": "moving" if i % 2 == 0 else "idle"
        })

    # List all
    res = client.get("/api/vehicles?limit=3&page=1")
    assert res.status_code == 200
    data = res.json()
    assert len(data["items"]) <= 3
    assert data["page"] == 1

    # Filter by search
    res_search = client.get("/api/vehicles?search=TEST-LIST-002")
    assert res_search.status_code == 200
    items = res_search.json()["items"]
    assert len(items) == 1
    assert items[0]["vehicle_identifier"] == "TEST-LIST-002"

    # Filter by status
    res_status = client.get("/api/vehicles?status=moving")
    assert res_status.status_code == 200
    for it in res_status.json()["items"]:
        assert it["status"] == "moving"
