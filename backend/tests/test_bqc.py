"""
Automated Pytest Suite for Phase 4 Blind Quantum Computing (BQC).
Validates:
1. Quantum-state normalization <psi|psi> = 1.0
2. Entanglement operations (CZ gates)
3. Projective measurement probabilities & Born rule collapse
4. Adaptive measurement corrections (Pauli feedforward)
5. Output decoding (one-time pad unpadding)
6. Classical vs delegated computation correctness (i*_BQC == i*_classical)
7. Blinding & server-transcript analysis (entropy, metadata leakage, TVD)
8. FastAPI BQC endpoints against PostgreSQL
"""

import math
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.bqc.quantum_state_simulator import QuantumStateSimulator
from app.services.bqc.bqc_client_service import BqcClientService, THETA_SET, haversine_km
from app.services.bqc.bqc_server_service import BqcServerService
from app.services.bqc.bqc_orchestrator import (
    BqcOrchestrator,
    compute_angle_entropy,
    compute_total_variation_distance
)

client = TestClient(app)

SAMPLE_DEPOTS = [
    {"id": "depot-0", "name": "Depot Alpha", "latitude": 13.0067, "longitude": 80.2021, "congestion": 0.2},
    {"id": "depot-1", "name": "Depot Beta", "latitude": 13.0418, "longitude": 80.2341, "congestion": 0.8},
    {"id": "depot-2", "name": "Depot Gamma", "latitude": 13.0100, "longitude": 80.2400, "congestion": 0.4},
    {"id": "depot-3", "name": "Depot Delta", "latitude": 12.9800, "longitude": 80.2100, "congestion": 0.1},
]

# ---------------------------------------------------------------------------
# 1. Quantum State Simulator Tests
# ---------------------------------------------------------------------------

def test_quantum_state_normalization():
    """Verify state vector maintains norm <psi|psi> = 1.0 upon init and operations."""
    sim = QuantumStateSimulator(num_qubits=3, seed=42)
    assert abs(sim.norm() - 1.0) < 1e-9

    # Initialize single qubit states
    angles = [0.0, math.pi / 4.0, math.pi / 2.0]
    sim.initialize_single_qubit_states(angles)
    assert abs(sim.norm() - 1.0) < 1e-9

    # Apply CZ gates
    sim.apply_cz(0, 1)
    sim.apply_cz(1, 2)
    assert abs(sim.norm() - 1.0) < 1e-9

    # Perform measurement and check post-measurement norm
    outcome, prob = sim.measure_qubit(0, delta=0.0)
    assert outcome in (0, 1)
    assert 0.0 <= prob <= 1.0
    assert abs(sim.norm() - 1.0) < 1e-9


def test_entanglement_cz_operation():
    """Verify CZ entangling gate flips the sign of |11> component only."""
    sim = QuantumStateSimulator(num_qubits=2, seed=123)
    # Set to uniform superposition |+>|+> = 1/2 (|00> + |01> + |10> + |11>)
    sim.initialize_single_qubit_states([0.0, 0.0])
    for c in sim.state:
        assert abs(c - 0.5) < 1e-9

    # Apply CZ between qubit 0 and qubit 1
    sim.apply_cz(0, 1)
    # State should be 1/2 (|00> + |01> + |10> - |11>)
    assert abs(sim.state[0] - 0.5) < 1e-9  # |00>
    assert abs(sim.state[1] - 0.5) < 1e-9  # |01>
    assert abs(sim.state[2] - 0.5) < 1e-9  # |10>
    assert abs(sim.state[3] - (-0.5)) < 1e-9  # |11> inverted!
    assert sim.is_entangled is True


def test_measurement_born_rule_probabilities():
    """Verify projective measurement probabilities match Born rule for known states."""
    sim = QuantumStateSimulator(num_qubits=1, seed=999)
    # Prepare |theta=0> = |+> = 1/sqrt(2) (|0> + |1>)
    sim.initialize_single_qubit_states([0.0])

    # Measure in delta=0 basis ({|+>, |->}):
    # Since state is |+>, outcome should be 0 with probability 1.0!
    outcome, prob = sim.measure_qubit(0, delta=0.0)
    assert outcome == 0
    assert abs(prob - 1.0) < 1e-7

    # Prepare |theta=pi> = |-> = 1/sqrt(2) (|0> - |1>)
    sim.initialize_single_qubit_states([math.pi])
    # Measure in delta=0 basis: outcome should be 1 with probability 1.0!
    outcome, prob = sim.measure_qubit(0, delta=0.0)
    assert outcome == 1
    assert abs(prob - 1.0) < 1e-7


# ---------------------------------------------------------------------------
# 2. BFK09 Client & Adaptive Feedforward Tests
# ---------------------------------------------------------------------------

def test_client_secret_blinding_generation():
    """Verify client generates valid theta angles in Theta set and binary pads."""
    client_srv = BqcClientService(seed=42)
    thetas = client_srv.prepare_secret_blinding(num_qubits=4)

    assert len(thetas) == 4
    assert len(client_srv.secret_thetas) == 4
    assert len(client_srv.secret_pads) == 4

    for th in thetas:
        assert any(abs(th - valid_th) < 1e-6 for valid_th in THETA_SET)

    for r in client_srv.secret_pads:
        assert r in (0, 1)


def test_adaptive_measurement_feedforward_and_unpadding():
    """Verify client unpads server outcomes and applies feedforward Pauli corrections."""
    client_srv = BqcClientService(seed=101)
    client_srv.prepare_secret_blinding(num_qubits=4)

    # Mock server outcome for qubit 0
    server_b0 = 1
    pad0 = client_srv.secret_pads[0]
    unpadded_s0 = client_srv.process_server_outcome(0, server_b0)
    assert unpadded_s0 == (server_b0 ^ pad0)

    # Compute blind angle for qubit 1 (with feedforward dependent on s0)
    nominal_phi = math.pi / 2.0
    delta_1 = client_srv.compute_blind_angle(1, nominal_phi, cluster_topology="linear")
    assert 0.0 <= delta_1 < 2.0 * math.pi


# ---------------------------------------------------------------------------
# 3. Server Visibility Audit & Privacy Verification Tests
# ---------------------------------------------------------------------------

def test_server_visibility_audit_zero_leakage():
    """Verify that server visibility audit log contains zero client secrets."""
    orchestrator = BqcOrchestrator(seed=555)
    res = orchestrator.execute_mode_b_bqc(
        vehicle_lat=13.0000,
        vehicle_lon=80.2200,
        battery_level=80.0,
        candidate_depots=SAMPLE_DEPOTS[:2],
        cluster_topology="linear"
    )

    audit = res["server_visibility_audit"]
    assert audit["learned_client_thetas"] is False
    assert audit["learned_client_pads"] is False
    assert audit["learned_vehicle_gps"] is False
    assert audit["learned_cost_vector"] is False
    assert audit["learned_optimal_depot"] is False
    assert res["server_learned_gps"] is False
    assert res["server_learned_costs"] is False
    assert res["server_learned_output"] is False


def test_angle_entropy_and_distinguishability():
    """Verify that blinded angles exhibit high entropy and low TVD across different inputs."""
    # Run 10 trials for Depot 0 being optimal
    depots_favor_0 = [
        {"id": "d0", "name": "Very Close", "latitude": 13.001, "longitude": 80.201, "congestion": 0.1},
        {"id": "d1", "name": "Very Far", "latitude": 13.500, "longitude": 80.800, "congestion": 0.9},
    ]
    # Run 10 trials for Depot 1 being optimal
    depots_favor_1 = [
        {"id": "d0", "name": "Very Far", "latitude": 13.500, "longitude": 80.800, "congestion": 0.9},
        {"id": "d1", "name": "Very Close", "latitude": 13.001, "longitude": 80.201, "congestion": 0.1},
    ]

    angles_0: list[float] = []
    angles_1: list[float] = []

    for i in range(10):
        orch_0 = BqcOrchestrator(seed=100 + i)
        r0 = orch_0.execute_mode_b_bqc(13.000, 80.200, 80.0, depots_favor_0)
        angles_0.extend(r0["blinded_angles_rad"])

        orch_1 = BqcOrchestrator(seed=200 + i)
        r1 = orch_1.execute_mode_b_bqc(13.000, 80.200, 80.0, depots_favor_1)
        angles_1.extend(r1["blinded_angles_rad"])

    entropy_0 = compute_angle_entropy(angles_0)
    entropy_1 = compute_angle_entropy(angles_1)

    # Entropy should be high (> 2.0 out of theoretical max 3.0 bits)
    assert entropy_0 > 2.0
    assert entropy_1 > 2.0

    # Total Variation Distance between 8-bin histograms
    hist_0 = [0.0] * 8
    hist_1 = [0.0] * 8
    bin_size = (2.0 * math.pi) / 8.0
    for a in angles_0:
        hist_0[int((a % (2 * math.pi)) / bin_size) % 8] += 1.0 / len(angles_0)
    for a in angles_1:
        hist_1[int((a % (2 * math.pi)) / bin_size) % 8] += 1.0 / len(angles_1)

    tvd = compute_total_variation_distance(hist_0, hist_1)
    # Empirical TVD should be bounded under uniform random blinding
    assert tvd < 0.25


# ---------------------------------------------------------------------------
# 4. Classical vs BQC Correctness Tests (M=2 and M=4)
# ---------------------------------------------------------------------------

def test_correctness_m2_candidates():
    """Verify Mode B (BQC) selects identical optimal depot as Mode A for M=2 candidates."""
    orchestrator = BqcOrchestrator(seed=777)
    res = orchestrator.execute_comparison(
        vehicle_lat=13.0050,
        vehicle_lon=80.2030,
        battery_level=65.0,
        candidate_depots=SAMPLE_DEPOTS[:2]
    )

    assert res["correctness_verified"] is True
    assert res["mode_a"]["selected_depot_index"] == res["mode_b"]["selected_depot_index"]
    assert res["mode_b"]["correctness"] is True


def test_correctness_m4_candidates():
    """Verify Mode B (BQC) selects identical optimal depot as Mode A for M=4 candidates."""
    orchestrator = BqcOrchestrator(seed=888)
    res = orchestrator.execute_comparison(
        vehicle_lat=12.9850,
        vehicle_lon=80.2150,
        battery_level=40.0,
        candidate_depots=SAMPLE_DEPOTS[:4]
    )

    assert res["correctness_verified"] is True
    assert res["mode_a"]["selected_depot_index"] == res["mode_b"]["selected_depot_index"]
    assert res["mode_b"]["correctness"] is True


# ---------------------------------------------------------------------------
# 5. FastAPI Endpoints Integration Tests (PostgreSQL on Port 5435)
# ---------------------------------------------------------------------------

def test_api_bqc_status():
    """Verify GET /api/security/bqc/status returns protocol specifications."""
    r = client.get("/api/security/bqc/status")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "active"
    assert "BFK09" in data["protocol"]
    assert 2 in data["supported_candidates"]
    assert 4 in data["supported_candidates"]


def test_api_bqc_demonstrate():
    """Verify POST /api/security/bqc/demonstrate executes side-by-side comparison."""
    payload = {
        "num_candidates": 2,
        "cluster_topology": "linear"
    }
    r = client.post("/api/security/bqc/demonstrate", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data["num_candidates"] == 2
    assert data["correctness_verified"] is True
    assert "mode_a" in data
    assert "mode_b" in data
    assert data["mode_b"]["angle_entropy_bits"] > 1.0


def test_api_bqc_batch_trials_and_experiments_list():
    """Verify POST /api/security/bqc/batch-trials persists in PostgreSQL and aggregates statistics."""
    payload = {
        "num_candidates": 2,
        "trials_per_mode": 5,
        "cluster_topology": "linear",
        "experiment_name": "Pytest-Verification-Batch"
    }
    r = client.post("/api/security/bqc/batch-trials", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data["experiment_id"] > 0
    assert data["trials_executed_per_mode"] == 5
    assert data["algorithmic_correctness_rate"] == 100.0
    assert data["mode_b"]["median_latency_ms"] > 0.0
    assert data["mode_b"]["mean_wire_bytes"] > data["mode_a"]["mean_wire_bytes"]

    # Verify experiment appears in list
    r_list = client.get("/api/security/bqc/experiments?limit=10")
    assert r_list.status_code == 200
    items = r_list.json()
    assert any(exp["id"] == data["experiment_id"] for exp in items)
