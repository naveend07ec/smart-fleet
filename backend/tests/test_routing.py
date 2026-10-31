"""
Automated Pytest Suite for Phase 5 QUBO / Simulated Annealing Fleet Routing & Optimization.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.routing.qubo_routing_service import (
    QuboRoutingService,
    haversine_km,
    DEFAULT_CHENNAI_DEPOT,
    DEFAULT_CHENNAI_WAYPOINTS,
    DEFAULT_VEHICLES
)

client = TestClient(app)


def test_haversine_symmetry_and_accuracy():
    """Verify haversine distance calculation is positive, symmetric, and accurate."""
    d1 = haversine_km(13.0827, 80.2707, 13.0418, 80.2341)
    d2 = haversine_km(13.0418, 80.2341, 13.0827, 80.2707)
    assert d1 > 0.0
    assert d1 == d2
    assert 4.0 <= d1 <= 8.0  # Approx ~6 km in Chennai


def test_distance_matrix_construction():
    """Ensure distance matrix is built with zero diagonal and symmetric entries."""
    service = QuboRoutingService(seed=42)
    matrix = service._build_distance_matrix(DEFAULT_CHENNAI_DEPOT, DEFAULT_CHENNAI_WAYPOINTS[:3])
    depot_id = DEFAULT_CHENNAI_DEPOT["id"]
    assert matrix[depot_id][depot_id] == 0.0
    for wp in DEFAULT_CHENNAI_WAYPOINTS[:3]:
        assert matrix[wp["id"]][wp["id"]] == 0.0
        assert matrix[depot_id][wp["id"]] == matrix[wp["id"]][depot_id]


def test_classical_heuristic_feasibility():
    """Verify classical heuristic produces valid, non-empty routes."""
    service = QuboRoutingService(seed=42)
    matrix = service._build_distance_matrix(DEFAULT_CHENNAI_DEPOT, DEFAULT_CHENNAI_WAYPOINTS)
    result = service.solve_classical_heuristic(
        DEFAULT_CHENNAI_DEPOT,
        DEFAULT_CHENNAI_WAYPOINTS,
        DEFAULT_VEHICLES,
        matrix
    )
    assert result["total_distance_km"] > 0.0
    assert result["total_energy_kwh"] > 0.0
    assert len(result["routes"]) == len(DEFAULT_VEHICLES)
    assert result["execution_time_ms"] >= 0.0

    # Verify all waypoints are visited
    visited_ids = set()
    for r in result["routes"]:
        for stop in r["stop_sequence"]:
            if stop.get("type") == "waypoint":
                visited_ids.add(stop["id"])
    assert visited_ids == {w["id"] for w in DEFAULT_CHENNAI_WAYPOINTS}


def test_qubo_simulated_annealing_convergence():
    """Verify Simulated Annealing converges and produces valid routes."""
    service = QuboRoutingService(seed=42)
    matrix = service._build_distance_matrix(DEFAULT_CHENNAI_DEPOT, DEFAULT_CHENNAI_WAYPOINTS)
    result, history = service.solve_qubo_simulated_annealing(
        DEFAULT_CHENNAI_DEPOT,
        DEFAULT_CHENNAI_WAYPOINTS,
        DEFAULT_VEHICLES,
        matrix,
        iterations=300
    )
    assert result["total_distance_km"] > 0.0
    assert len(history) > 0
    # Energy at start should be >= best energy at end
    assert history[-1]["best_energy"] <= history[0]["current_energy"] + 1e-4

    visited_ids = set()
    for r in result["routes"]:
        for stop in r["stop_sequence"]:
            if stop.get("type") == "waypoint":
                visited_ids.add(stop["id"])
    assert visited_ids == {w["id"] for w in DEFAULT_CHENNAI_WAYPOINTS}


def test_qubo_hamiltonian_penalties():
    """Verify Hamiltonian penalizes over-capacity and battery-range violations."""
    service = QuboRoutingService(seed=42)
    matrix = service._build_distance_matrix(DEFAULT_CHENNAI_DEPOT, DEFAULT_CHENNAI_WAYPOINTS)
    depot_id = DEFAULT_CHENNAI_DEPOT["id"]

    # Low capacity fleet that will cause severe capacity penalties
    low_cap_vehicles = [
        {"id": "V1", "capacity": 5, "battery_range_km": 10.0},
        {"id": "V2", "capacity": 5, "battery_range_km": 10.0},
        {"id": "V3", "capacity": 5, "battery_range_km": 10.0},
    ]
    partition = [DEFAULT_CHENNAI_WAYPOINTS[:3], DEFAULT_CHENNAI_WAYPOINTS[3:6], DEFAULT_CHENNAI_WAYPOINTS[6:]]
    energy_penalized = service._qubo_hamiltonian(partition, depot_id, low_cap_vehicles, matrix)

    # Standard capacity fleet
    energy_standard = service._qubo_hamiltonian(partition, depot_id, DEFAULT_VEHICLES, matrix)
    assert energy_penalized > energy_standard


def test_api_routing_defaults():
    """Verify GET /api/routing/defaults returns expected structure."""
    resp = client.get("/api/routing/defaults")
    assert resp.status_code == 200
    data = resp.json()
    assert "depot" in data
    assert "waypoints" in data
    assert "vehicles" in data
    assert len(data["scenarios"]) >= 3


def test_api_routing_optimize_and_experiment_lifecycle():
    """Verify POST /api/routing/optimize executes and saves experiment."""
    payload = {
        "scenario": "urban_delivery",
        "sa_iterations": 200,
        "save_experiment": True,
        "experiment_name": "Pytest Urban Test Run"
    }
    resp = client.post("/api/routing/optimize", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert "classical_heuristic" in data
    assert "qubo_simulated_annealing" in data
    assert "differential_kpis" in data
    assert "convergence_history" in data
    assert data["num_vehicles"] == 3
    assert data["num_waypoints"] == 8
    exp_id = data.get("experiment_id")

    if exp_id is not None:
        # Check listing
        list_resp = client.get("/api/routing/experiments")
        assert list_resp.status_code == 200
        items = list_resp.json()
        assert any(item["id"] == exp_id for item in items)

        # Check detail
        det_resp = client.get(f"/api/routing/experiments/{exp_id}")
        assert det_resp.status_code == 200
        assert det_resp.json()["id"] == exp_id

        # Delete
        del_resp = client.delete(f"/api/routing/experiments/{exp_id}")
        assert del_resp.status_code == 204


def test_api_routing_validation_errors():
    """Verify validation rejection when waypoints or vehicles are empty."""
    resp = client.post("/api/routing/optimize", json={"waypoints": []})
    assert resp.status_code == 400

    resp2 = client.post("/api/routing/optimize", json={"vehicles": []})
    assert resp2.status_code == 400
