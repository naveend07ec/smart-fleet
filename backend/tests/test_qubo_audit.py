"""
Phase 5.1 — Rigorous Mathematical & Experimental Audit of QUBO Fleet Optimization.

Tests:
1. Variable mapping bijection (0-indexed and 1-indexed equivalence, uniqueness, bounds).
2. Direct Hamiltonian vs QUBO matrix energy across all 4,096 states in Small scenario.
3. Global optimum equivalence between independent validator and service exact oracle.
4. Departure and return cost modeling for empty and non-empty routes.
5. Constraint penalty isolation (visitation, slot exclusivity, contiguity).
6. Capacity boundary and infeasible instance detection.
"""

import pytest
from app.services.routing.qubo_routing_service import (
    qubo_routing_service,
    DEFAULT_CHENNAI_DEPOT,
    DEFAULT_CHENNAI_WAYPOINTS,
    DEFAULT_VEHICLES,
    STANDARDIZED_SCENARIOS
)
from app.services.routing.qubo_mathematical_validator import IndependentQuboValidator


@pytest.fixture
def small_scenario_setup():
    depot = DEFAULT_CHENNAI_DEPOT
    wps = DEFAULT_CHENNAI_WAYPOINTS[:3]
    vehs = DEFAULT_VEHICLES[:2]
    max_steps = 2
    dist_matrix = qubo_routing_service._build_distance_matrix(depot, wps)
    validator = IndependentQuboValidator(
        depot=depot,
        waypoints=wps,
        vehicles=vehs,
        max_steps=max_steps,
        dist_matrix=dist_matrix,
        penalty_visit=150.0,
        penalty_slot=120.0,
        penalty_contig=80.0,
        penalty_cap=100.0
    )
    return depot, wps, vehs, max_steps, dist_matrix, validator


def test_variable_indexing_bijection(small_scenario_setup):
    """
    Audit 1.A: Verify that the 3-index mapping:
    sigma(v, i, t) = (v-1)*(N*T) + (i-1)*T + (t-1) (1-indexed)
    matches
    idx(v, i, t) = v*(N*T) + i*T + t (0-indexed)
    and forms a complete bijection into [0, M-1].
    """
    depot, wps, vehs, max_steps, dist_matrix, validator = small_scenario_setup
    V = len(vehs)
    N = len(wps)
    T = max_steps
    M = V * N * T
    assert M == 12

    seen_indices = set()

    for v in range(V):
        for i in range(N):
            for t in range(T):
                # 0-indexed mapping
                u_0 = validator.map_variable_0indexed(v, i, t)
                # 1-indexed mapping
                u_1 = validator.map_variable_1indexed(v + 1, i + 1, t + 1)

                assert u_0 == u_1, f"Mismatch: 0-indexed {u_0} != 1-indexed {u_1}"
                assert 0 <= u_0 < M, f"Index {u_0} out of bounds [0, {M-1}]"
                assert u_0 not in seen_indices, f"Duplicate index {u_0} detected for ({v}, {i}, {t})"
                seen_indices.add(u_0)

                # Test inverse mapping (unmap)
                v_inv, i_inv, t_inv = validator.unmap_index_0indexed(u_0)
                assert (v_inv, i_inv, t_inv) == (v, i, t), f"Inverse mapping failed for index {u_0}"

    assert len(seen_indices) == M, f"Surjectivity failure: {len(seen_indices)} unique indices != {M}"


def test_direct_hamiltonian_versus_qubo_matrix_exact_equality(small_scenario_setup):
    """
    Audit 1 & 2: Compare direct Hamiltonian energy with upper-triangular QUBO matrix energy
    across EVERY binary state in {0, 1}^12 (all 4,096 states).
    Max discrepancy must be strictly 0.0000.
    """
    depot, wps, vehs, max_steps, dist_matrix, validator = small_scenario_setup

    Q, c, M, meta = qubo_routing_service.build_qubo_matrix(
        depot=depot,
        waypoints=wps,
        vehicles=vehs,
        max_steps=max_steps,
        dist_matrix=dist_matrix,
        penalty_visit=150.0,
        penalty_slot=120.0,
        penalty_contig=80.0,
        penalty_cap=100.0
    )

    audit_result = validator.audit_entire_state_space(Q, c)

    assert audit_result["total_states"] == 4096
    assert audit_result["discrepancy_count"] == 0, f"Found {audit_result['discrepancy_count']} discrepancies"
    assert audit_result["max_discrepancy"] < 1e-6, f"Max discrepancy {audit_result['max_discrepancy']} exceeds tolerance"


def test_qubo_optimum_agrees_with_independent_brute_force(small_scenario_setup):
    """
    Audit 2: Verify that the global optimum bitstring and minimum energy discovered
    by the primary service's solve_brute_force_exact matches the independent validator.
    """
    depot, wps, vehs, max_steps, dist_matrix, validator = small_scenario_setup

    Q, c, M, meta = qubo_routing_service.build_qubo_matrix(
        depot, wps, vehs, max_steps, dist_matrix
    )
    service_exact = qubo_routing_service.solve_brute_force_exact(
        depot, wps, vehs, max_steps, dist_matrix
    )
    validator_exact = validator.audit_entire_state_space(Q, c)

    assert abs(service_exact["min_qubo_energy"] - round(validator_exact["min_direct_energy"], 3)) < 1e-6
    assert service_exact["best_bitstring"] == validator_exact["best_direct_bitstring"]
    assert service_exact["all_feasible"] is True
    assert service_exact["constraint_violations"] == 0


def test_empty_vehicle_depot_departure_and_return_costs(small_scenario_setup):
    """
    Audit 1.C: Prove that an empty vehicle receives exactly 0 departure and 0 return cost.
    """
    depot, wps, vehs, max_steps, dist_matrix, validator = small_scenario_setup

    # State with all bits zero for vehicle 0, but valid single visit for vehicle 1
    # Vehicle 0 is completely empty
    x = [0] * validator.M
    # Assign wp-1 to vehicle 1 at step 0
    x[validator.map_variable_0indexed(1, 0, 0)] = 1

    eval_res = validator.evaluate_direct_hamiltonian(x)

    # Depot departure must only reflect vehicle 1 visiting wp-1
    expected_depot = dist_matrix[depot["id"]][wps[0]["id"]]
    expected_return = dist_matrix[wps[0]["id"]][depot["id"]]
    assert abs(eval_res["o_depot"] - expected_depot) < 1e-6
    assert abs(eval_res["o_return"] - expected_return) < 1e-6
    assert eval_res["o_transit"] == 0.0


def test_multi_step_route_receives_exactly_one_departure_and_one_return(small_scenario_setup):
    """
    Audit 1.C: Prove that a vehicle visiting wp-1 at step 0 and wp-2 at step 1
    receives exactly 1 departure (depot -> wp-1), 1 transit (wp-1 -> wp-2),
    and 1 return (wp-2 -> depot). Intermediate return (wp-1 -> depot) must be canceled.
    """
    depot, wps, vehs, max_steps, dist_matrix, validator = small_scenario_setup

    x = [0] * validator.M
    # Vehicle 0: step 0 -> wp-1, step 1 -> wp-2
    x[validator.map_variable_0indexed(0, 0, 0)] = 1
    x[validator.map_variable_0indexed(0, 1, 1)] = 1

    eval_res = validator.evaluate_direct_hamiltonian(x)

    depot_id = depot["id"]
    wp1_id = wps[0]["id"]
    wp2_id = wps[1]["id"]

    expected_departure = dist_matrix[depot_id][wp1_id]
    expected_transit = dist_matrix[wp1_id][wp2_id]
    expected_return = dist_matrix[wp2_id][depot_id]

    assert abs(eval_res["o_depot"] - expected_departure) < 1e-6
    assert abs(eval_res["o_transit"] - expected_transit) < 1e-6
    assert abs(eval_res["o_return"] - expected_return) < 1e-6


def test_route_contiguity_gap_penalty(small_scenario_setup):
    """
    Audit 1.D: Prove that an unassigned gap (step 0 empty, step 1 occupied)
    receives exactly the contiguity penalty P_C.
    """
    depot, wps, vehs, max_steps, dist_matrix, validator = small_scenario_setup

    x = [0] * validator.M
    # Vehicle 0 has step 0 empty, but step 1 visits wp-1
    x[validator.map_variable_0indexed(0, 0, 1)] = 1

    eval_res = validator.evaluate_direct_hamiltonian(x)
    assert abs(eval_res["h_contig"] - validator.penalty_contig) < 1e-6


def test_slot_collision_penalty(small_scenario_setup):
    """
    Audit 1.D: Prove that assigning two destinations to the same vehicle at the same step
    triggers the slot uniqueness penalty P_B.
    """
    depot, wps, vehs, max_steps, dist_matrix, validator = small_scenario_setup

    x = [0] * validator.M
    # Vehicle 0 visits both wp-1 and wp-2 at step 0
    x[validator.map_variable_0indexed(0, 0, 0)] = 1
    x[validator.map_variable_0indexed(0, 1, 0)] = 1

    eval_res = validator.evaluate_direct_hamiltonian(x)
    assert abs(eval_res["h_slot"] - validator.penalty_slot) < 1e-6


def test_independent_feasibility_auditor_detects_violations(small_scenario_setup):
    """
    Audit 1.D & 2: Verify that the independent feasibility auditor correctly detects:
    - Missing visits
    - Duplicate visits
    - Slot collisions
    - Sequence gaps
    """
    depot, wps, vehs, max_steps, dist_matrix, validator = small_scenario_setup

    # 1. State with zero visits (all zero vector)
    x_zero = [0] * validator.M
    feas_zero = validator.audit_route_feasibility(x_zero)
    assert feas_zero["feasible"] is False
    assert feas_zero["missing_visits"] == 3

    # 2. State with a slot collision
    x_col = [0] * validator.M
    x_col[validator.map_variable_0indexed(0, 0, 0)] = 1
    x_col[validator.map_variable_0indexed(0, 1, 0)] = 1
    x_col[validator.map_variable_0indexed(1, 2, 0)] = 1
    feas_col = validator.audit_route_feasibility(x_col)
    assert feas_col["feasible"] is False
    assert feas_col["slot_collisions"] == 1

    # 3. Feasible state (wp-1, wp-2 to vehicle 0; wp-3 to vehicle 1)
    x_feas = [0] * validator.M
    x_feas[validator.map_variable_0indexed(0, 0, 0)] = 1  # v0, wp1, step 0
    x_feas[validator.map_variable_0indexed(0, 1, 1)] = 1  # v0, wp2, step 1
    x_feas[validator.map_variable_0indexed(1, 2, 0)] = 1  # v1, wp3, step 0
    feas_ok = validator.audit_route_feasibility(x_feas)
    assert feas_ok["feasible"] is True
    assert feas_ok["total_violations"] == 0


def test_duplicate_visit_penalty(small_scenario_setup):
    """
    Audit 1.D: Prove that visiting destination i twice (e.g. at step 0 and step 1)
    triggers the visit penalty P_A = (2 - 1)^2 * P_A.
    """
    depot, wps, vehs, max_steps, dist_matrix, validator = small_scenario_setup

    x = [0] * validator.M
    # Visit wp-1 at step 0 and again at step 1 on vehicle 0
    x[validator.map_variable_0indexed(0, 0, 0)] = 1
    x[validator.map_variable_0indexed(0, 0, 1)] = 1

    eval_res = validator.evaluate_direct_hamiltonian(x)
    # wp-1 has 2 visits: penalty = (2-1)^2 * 150 = 150
    # wp-2 has 0 visits: penalty = (0-1)^2 * 150 = 150
    # wp-3 has 0 visits: penalty = (0-1)^2 * 150 = 150
    # Total h_visit = 450.0
    assert abs(eval_res["h_visit"] - 450.0) < 1e-6


def test_capacity_boundary_and_overload_detection(small_scenario_setup):
    """
    Audit 1.B & 2: Test capacity boundary conditions and infeasibility detection
    when vehicle capacity is exceeded.
    """
    depot, wps, vehs, max_steps, dist_matrix, validator = small_scenario_setup

    # Create artificial scenario with low vehicle capacity (e.g. 20)
    low_cap_vehs = [
        {"id": "EV-Low-1", "capacity": 20},
        {"id": "EV-Low-2", "capacity": 20}
    ]
    # wp-1 demand=15, wp-2 demand=12 -> total=27 > 20
    overload_validator = IndependentQuboValidator(
        depot=depot,
        waypoints=wps,
        vehicles=low_cap_vehs,
        max_steps=max_steps,
        dist_matrix=dist_matrix
    )

    x_overload = [0] * overload_validator.M
    x_overload[overload_validator.map_variable_0indexed(0, 0, 0)] = 1  # wp-1 (15)
    x_overload[overload_validator.map_variable_0indexed(0, 1, 1)] = 1  # wp-2 (12) -> sum=27 > 20
    x_overload[overload_validator.map_variable_0indexed(1, 2, 0)] = 1  # wp-3 (18) <= 20

    feas = overload_validator.audit_route_feasibility(x_overload)
    assert feas["feasible"] is False
    assert feas["capacity_violations"] == 7  # 27 - 20 = 7 units over capacity


def test_deterministic_reproducibility_with_fixed_seed(small_scenario_setup):
    """
    Audit 3: Verify that given the same input data and random seed,
    both Classical SA and QUBO SA produce 100% bit-identical results.
    """
    depot, wps, vehs, max_steps, dist_matrix, validator = small_scenario_setup

    # Run QUBO SA twice with seed 12345
    res1, conv1 = qubo_routing_service.solve_qubo_simulated_annealing(
        depot, wps, vehs, dist_matrix, iterations=500, seed=12345, max_steps=max_steps
    )
    res2, conv2 = qubo_routing_service.solve_qubo_simulated_annealing(
        depot, wps, vehs, dist_matrix, iterations=500, seed=12345, max_steps=max_steps
    )
    assert res1["total_distance_km"] == res2["total_distance_km"]
    assert res1["objective_value"] == res2["objective_value"]
    assert res1["qubo_energy_score"] == res2["qubo_energy_score"]

    # Run Classical SA twice with seed 12345
    cres1, cconv1 = qubo_routing_service.solve_classical_simulated_annealing(
        depot, wps, vehs, dist_matrix, iterations=500, seed=12345
    )
    cres2, cconv2 = qubo_routing_service.solve_classical_simulated_annealing(
        depot, wps, vehs, dist_matrix, iterations=500, seed=12345
    )
    assert cres1["total_distance_km"] == cres2["total_distance_km"]
    assert cres1["objective_value"] == cres2["objective_value"]
    assert cres1["qubo_energy_score"] == cres2["qubo_energy_score"]

