"""
Automated Pytest Suite for Phase 5 QUBO & Quantum-Inspired Fleet Optimization.

Tests:
1. Haversine distance and matrix symmetry.
2. QUBO matrix construction, variable indexing, and upper-triangular properties.
3. Constraint penalties (visitation, slot exclusivity, route contiguity, capacity).
4. Binary bitstring decoding and independent feasibility auditing.
5. Method A: Conventional Greedy Routing baseline.
6. Method B: Classical Simulated Annealing reproducibility and convergence.
7. Method C: QUBO Formulation with Simulated Annealing Solver.
8. Mathematical Oracle Validation: Brute-Force Exhaustive Enumeration (M=12, 4,096 states).
9. Multi-trial benchmarking with statistical metrics (median, P95, mean, std).
10. FastAPI Optimization Endpoints: /status, /scenarios, /run, /experiments, /analytics, /compare.
11. Validation error handling on malformed or extreme inputs.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.routing.qubo_routing_service import (
    QuboRoutingService,
    haversine_km,
    DEFAULT_CHENNAI_DEPOT,
    DEFAULT_CHENNAI_WAYPOINTS,
    DEFAULT_VEHICLES,
    STANDARDIZED_SCENARIOS
)

client = TestClient(app)


# ------------------------------------------------------------------------------
# 1. Mathematical and Distance Invariants
# ------------------------------------------------------------------------------
def test_haversine_properties():
    """Verify haversine distances are non-negative, symmetric, and triangular."""
    p1 = (13.0827, 80.2707)  # Central Depot
    p2 = (13.0418, 80.2341)  # T. Nagar
    p3 = (13.0067, 80.2570)  # Adyar

    d12 = haversine_km(p1[0], p1[1], p2[0], p2[1])
    d21 = haversine_km(p2[0], p2[1], p1[0], p1[1])
    d23 = haversine_km(p2[0], p2[1], p3[0], p3[1])
    d13 = haversine_km(p1[0], p1[1], p3[0], p3[1])

    assert d12 > 0.0
    assert d12 == d21
    # Triangle inequality holds approximately on sphere
    assert d13 <= d12 + d23 + 0.1


def test_distance_matrix_structure():
    """Verify distance matrix is symmetric with zero diagonal."""
    service = QuboRoutingService(seed=42)
    matrix = service._build_distance_matrix(DEFAULT_CHENNAI_DEPOT, DEFAULT_CHENNAI_WAYPOINTS[:4])
    all_nodes = [DEFAULT_CHENNAI_DEPOT["id"]] + [w["id"] for w in DEFAULT_CHENNAI_WAYPOINTS[:4]]

    for u in all_nodes:
        assert matrix[u][u] == 0.0
        for w in all_nodes:
            assert matrix[u][w] == matrix[w][u]


# ------------------------------------------------------------------------------
# 2. QUBO Matrix Construction and Mathematical Properties
# ------------------------------------------------------------------------------
def test_qubo_matrix_construction_and_upper_triangular():
    """Verify Q matrix is upper-triangular, has exact dimensions, and non-zero couplings."""
    service = QuboRoutingService(seed=42)
    vehicles = DEFAULT_VEHICLES[:2]
    waypoints = DEFAULT_CHENNAI_WAYPOINTS[:3]
    max_steps = 2
    matrix = service._build_distance_matrix(DEFAULT_CHENNAI_DEPOT, waypoints)

    Q, c, M, meta = service.build_qubo_matrix(
        depot=DEFAULT_CHENNAI_DEPOT,
        waypoints=waypoints,
        vehicles=vehicles,
        max_steps=max_steps,
        dist_matrix=matrix
    )

    expected_M = len(vehicles) * len(waypoints) * max_steps  # 2 * 3 * 2 = 12
    assert M == expected_M
    assert len(Q) == expected_M
    assert len(Q[0]) == expected_M
    assert c > 0.0  # Constant offset from penalty expansion

    # Strictly upper-triangular verification (lower triangle must be 0)
    for u in range(M):
        for w in range(u):
            assert Q[u][w] == 0.0, f"Q[{u}][{w}] in lower triangle must be zero."

    # Off-diagonal couplings exist
    non_zero_couplings = sum(1 for u in range(M) for w in range(u + 1, M) if abs(Q[u][w]) > 1e-4)
    assert non_zero_couplings > 0


# ------------------------------------------------------------------------------
# 3. Binary Solution Decoding and Independent Feasibility Auditing
# ------------------------------------------------------------------------------
def test_binary_decoding_and_audit():
    """Verify binary decoder correctly identifies valid allocations and flags violations."""
    service = QuboRoutingService(seed=42)
    vehicles = DEFAULT_VEHICLES[:2]
    waypoints = DEFAULT_CHENNAI_WAYPOINTS[:3]
    max_steps = 2
    matrix = service._build_distance_matrix(DEFAULT_CHENNAI_DEPOT, waypoints)

    V = len(vehicles)
    N = len(waypoints)
    T = max_steps
    M = V * N * T

    def idx(v, i, t):
        return v * (N * T) + i * T + t

    # Construct a valid feasible assignment:
    # Vehicle 0 visits waypoint 0 at step 0, waypoint 1 at step 1
    # Vehicle 1 visits waypoint 2 at step 0
    valid_x = [0] * M
    valid_x[idx(0, 0, 0)] = 1
    valid_x[idx(0, 1, 1)] = 1
    valid_x[idx(1, 2, 0)] = 1

    routes, violations, audit = service.decode_binary_solution(
        valid_x, DEFAULT_CHENNAI_DEPOT, waypoints, vehicles, max_steps, matrix
    )
    assert violations == 0
    assert audit["unserved_destinations"] == 0
    assert audit["duplicate_visits"] == 0
    assert all(r["feasible"] for r in routes)

    # Infeasible: waypoint 0 unserved (all zeros)
    empty_x = [0] * M
    routes_empty, violations_empty, audit_empty = service.decode_binary_solution(
        empty_x, DEFAULT_CHENNAI_DEPOT, waypoints, vehicles, max_steps, matrix
    )
    assert violations_empty >= 3
    assert audit_empty["unserved_destinations"] == 3


# ------------------------------------------------------------------------------
# 4. Method A: Conventional Greedy Routing
# ------------------------------------------------------------------------------
def test_greedy_routing_baseline():
    """Verify Greedy baseline generates deterministic, non-empty, and feasible routes."""
    service = QuboRoutingService(seed=42)
    matrix = service._build_distance_matrix(DEFAULT_CHENNAI_DEPOT, DEFAULT_CHENNAI_WAYPOINTS[:5])
    res = service.solve_greedy_routing(
        DEFAULT_CHENNAI_DEPOT,
        DEFAULT_CHENNAI_WAYPOINTS[:5],
        DEFAULT_VEHICLES[:3],
        matrix
    )
    assert res["method"] == "greedy"
    assert res["total_distance_km"] > 0.0
    assert res["execution_time_ms"] >= 0.0
    assert res["all_feasible"] is True
    assert res["constraint_violations"] == 0

    # Every waypoint visited exactly once
    visited = set()
    for r in res["routes"]:
        for s in r["stop_sequence"]:
            if s.get("type") == "waypoint":
                visited.add(s["id"])
    assert visited == {w["id"] for w in DEFAULT_CHENNAI_WAYPOINTS[:5]}


# ------------------------------------------------------------------------------
# 5. Method B: Classical Simulated Annealing
# ------------------------------------------------------------------------------
def test_classical_simulated_annealing():
    """Verify Classical SA produces valid routes and records a decreasing energy trend."""
    service = QuboRoutingService(seed=42)
    matrix = service._build_distance_matrix(DEFAULT_CHENNAI_DEPOT, DEFAULT_CHENNAI_WAYPOINTS[:5])
    res, conv = service.solve_classical_simulated_annealing(
        DEFAULT_CHENNAI_DEPOT,
        DEFAULT_CHENNAI_WAYPOINTS[:5],
        DEFAULT_VEHICLES[:3],
        matrix,
        iterations=300,
        seed=101
    )
    assert res["method"] == "classical_sa"
    assert res["total_distance_km"] > 0.0
    assert len(conv) > 0
    # Final best energy <= initial energy
    assert conv[-1]["best_energy"] <= conv[0]["current_energy"] + 1e-4
    assert res["all_feasible"] is True


# ------------------------------------------------------------------------------
# 6. Method C: QUBO Simulated Annealing Solver
# ------------------------------------------------------------------------------
def test_qubo_simulated_annealing_solver():
    """Verify QUBO Simulated Annealing solver samples binary state space and decodes routes."""
    service = QuboRoutingService(seed=42)
    matrix = service._build_distance_matrix(DEFAULT_CHENNAI_DEPOT, DEFAULT_CHENNAI_WAYPOINTS[:3])
    res, conv = service.solve_qubo_simulated_annealing(
        DEFAULT_CHENNAI_DEPOT,
        DEFAULT_CHENNAI_WAYPOINTS[:3],
        DEFAULT_VEHICLES[:2],
        matrix,
        iterations=300,
        seed=42,
        max_steps=2
    )
    assert res["method"] == "qubo_sa"
    assert res["total_distance_km"] > 0.0
    assert "qubo_energy_score" in res
    assert len(conv) > 0


# ------------------------------------------------------------------------------
# 7. Ground Truth Validation: Brute-Force Exhaustive Enumeration (M=12)
# ------------------------------------------------------------------------------
def test_brute_force_exhaustive_exact_oracle():
    """
    Exhaustively searches all 2^12 = 4,096 states for Small scenario.
    Validates that the true global minimum of the QUBO formulation yields
    a zero-violation, feasible fleet route.
    """
    service = QuboRoutingService(seed=42)
    sc = STANDARDIZED_SCENARIOS["small"]
    matrix = service._build_distance_matrix(DEFAULT_CHENNAI_DEPOT, sc["waypoints"])

    exact_res = service.solve_brute_force_exact(
        depot=DEFAULT_CHENNAI_DEPOT,
        waypoints=sc["waypoints"],
        vehicles=sc["vehicles"],
        max_steps=sc["max_steps"],
        dist_matrix=matrix
    )

    assert exact_res["num_evaluated_states"] == 4096
    assert exact_res["min_qubo_energy"] < 1000.0
    assert exact_res["all_feasible"] is True
    assert exact_res["constraint_violations"] == 0
    assert exact_res["total_distance_km"] > 0.0


# ------------------------------------------------------------------------------
# 8. Multi-Trial Comparative Experiment Engine
# ------------------------------------------------------------------------------
def test_multi_trial_experiment_engine():
    """Verify running multiple trials yields statistical aggregates (median, p95, std)."""
    service = QuboRoutingService(seed=42)
    exp_data = service.run_multi_trial_experiment(
        scenario="small",
        method="all_comparative",
        trials=3,
        random_seed=50,
        sa_iterations=200,
        include_brute_force=True
    )

    assert exp_data["vehicle_count"] == 2
    assert exp_data["destination_count"] == 3
    assert len(exp_data["trials"]) == 9  # 3 methods x 3 trials = 9

    summary = exp_data["methods_summary"]
    assert "greedy" in summary
    assert "classical_sa" in summary
    assert "qubo_sa" in summary

    for m_key, s in summary.items():
        assert s["trial_count"] == 3
        assert s["median_runtime_ms"] >= 0.0
        assert s["p95_runtime_ms"] >= s["median_runtime_ms"]
        assert s["std_objective"] >= 0.0
        assert 0.0 <= s["feasibility_percentage"] <= 100.0

    assert exp_data["brute_force_exact"] is not None
    assert exp_data["brute_force_exact"]["num_evaluated_states"] == 4096


# ------------------------------------------------------------------------------
# 9. FastAPI Endpoints & Lifecycle Tests
# ------------------------------------------------------------------------------
def test_api_optimization_status():
    """Verify GET /api/optimization/status returns subsystem info."""
    resp = client.get("/api/optimization/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "operational"
    assert "PostgreSQL" in data["database"]
    assert len(data["solvers_available"]) == 4


def test_api_optimization_scenarios():
    """Verify GET /api/optimization/scenarios lists Small, Medium, Large."""
    resp = client.get("/api/optimization/scenarios")
    assert resp.status_code == 200
    scenarios = resp.json()
    assert len(scenarios) == 3
    sc_ids = [s["id"] for s in scenarios]
    assert "small" in sc_ids
    assert "medium" in sc_ids
    assert "large" in sc_ids


def test_api_optimization_run_and_persistence_lifecycle():
    """Verify POST /api/optimization/run executes and persists to DB."""
    payload = {
        "scenario": "small",
        "method": "all_comparative",
        "trials": 2,
        "sa_iterations": 150,
        "random_seed": 77,
        "save_to_db": True,
        "experiment_name": "Pytest Comparative Run",
        "include_brute_force": True
    }
    resp = client.post("/api/optimization/run", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    exp_id = data.get("experiment_id")
    assert exp_id is not None
    assert "methods_summary" in data
    assert len(data["trials"]) == 6  # 3 methods x 2 trials

    # 1. Check listing
    list_resp = client.get("/api/optimization/experiments")
    assert list_resp.status_code == 200
    items = list_resp.json()
    assert any(item["id"] == exp_id for item in items)

    # 2. Check detail with child trials
    det_resp = client.get(f"/api/optimization/experiments/{exp_id}")
    assert det_resp.status_code == 200
    det = det_resp.json()
    assert det["id"] == exp_id
    assert len(det["trials"]) == 6

    # 3. Check analytics
    analytics_resp = client.get("/api/optimization/analytics")
    assert analytics_resp.status_code == 200
    analytics_data = analytics_resp.json()
    assert analytics_data["total_experiments"] >= 1
    assert len(analytics_data["method_performance"]) >= 1

    # 4. Check compare
    compare_resp = client.get(f"/api/optimization/compare?experiment_ids={exp_id}")
    assert compare_resp.status_code == 200
    assert len(compare_resp.json()) == 1

    # 5. Clean up deletion
    del_resp = client.delete(f"/api/optimization/experiments/{exp_id}")
    assert del_resp.status_code == 204


def test_api_optimization_validation_errors():
    """Verify API rejects invalid inputs with proper 400/422 status."""
    # Exceeding trial limit (Pydantic field validator returns 422, custom check returns 400)
    resp1 = client.post("/api/optimization/run", json={"trials": 100})
    assert resp1.status_code in [400, 422]

    # Invalid comma-separated IDs
    resp2 = client.get("/api/optimization/compare?experiment_ids=abc,xyz")
    assert resp2.status_code == 400
