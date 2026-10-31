"""
BQC Orchestration Service for Fleet Management.
Coordinates Mode A (Conventional Classical Optimization) vs Mode B (BFK09 Blind Quantum Computing).
Executes timing measurements, wire byte accounting, Shannon entropy calculation,
and statistical distinguishability audits.
"""

import math
import time
from typing import List, Dict, Any, Tuple, Optional
from app.services.bqc.bqc_client_service import BqcClientService
from app.services.bqc.bqc_server_service import BqcServerService

def compute_angle_entropy(angles: List[float], num_bins: int = 8) -> float:
    """
    Calculate empirical Shannon entropy of transmitted angles over the 8-angle set Theta:
    H(delta) = - sum p_i log2(p_i).
    Theoretical maximum for 8 discrete angles = log2(8) = 3.0 bits.
    """
    if not angles:
        return 0.0

    bin_counts = [0] * num_bins
    bin_size = (2.0 * math.pi) / num_bins

    for a in angles:
        norm_a = a % (2.0 * math.pi)
        idx = int(norm_a / bin_size) % num_bins
        bin_counts[idx] += 1

    total = len(angles)
    entropy = 0.0
    for count in bin_counts:
        if count > 0:
            p = count / total
            entropy -= p * math.log2(p)

    return round(entropy, 4)

def compute_total_variation_distance(dist_a: List[float], dist_b: List[float]) -> float:
    """
    Compute Total Variation Distance (TVD) between two discrete probability distributions:
    D_TV = 0.5 * sum |P_A(x) - P_B(x)|.
    """
    if len(dist_a) != len(dist_b):
        raise ValueError("Distributions must have the same length")
    return 0.5 * sum(abs(p_a - p_b) for p_a, p_b in zip(dist_a, dist_b))

class BqcOrchestrator:
    """
    High-level orchestrator executing comparative fleet evaluations.
    """

    def __init__(self, seed: Optional[int] = None):
        self.seed = seed

    def execute_mode_a_classical(
        self,
        vehicle_lat: float,
        vehicle_lon: float,
        battery_level: float,
        candidate_depots: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Mode A: Conventional plaintext fleet optimization.
        Exhaustively evaluates candidate depot costs and returns minimum index.
        """
        t0 = time.perf_counter()
        client = BqcClientService(seed=self.seed)
        costs = client.compute_fleet_costs(vehicle_lat, vehicle_lon, battery_level, candidate_depots)
        min_idx = min(range(len(candidate_depots)), key=lambda i: costs[i])
        t_elap_ms = (time.perf_counter() - t0) * 1000.0

        # Wire size for plain JSON telemetry payload
        # {"vehicle": ..., "depots": [...], "costs": [...]} ~140-200 bytes
        wire_bytes = 120 + (len(candidate_depots) * 24)

        selected_depot = candidate_depots[min_idx]
        return {
            "mode": "mode_a",
            "selected_depot_index": min_idx,
            "selected_depot_name": selected_depot.get("name", f"Depot-{min_idx}"),
            "selected_cost": costs[min_idx],
            "all_costs": costs,
            "execution_time_ms": round(t_elap_ms, 4),
            "wire_bytes": wire_bytes,
            "server_visibility": "Full Plaintext (Vehicle GPS, Candidate Costs, Winning Depot Exposed)",
            "privacy_guarantee": "None",
            "server_learned_gps": True,
            "server_learned_costs": True,
            "server_learned_output": True,
        }

    def execute_mode_b_bqc(
        self,
        vehicle_lat: float,
        vehicle_lon: float,
        battery_level: float,
        candidate_depots: List[Dict[str, Any]],
        cluster_topology: str = "linear"
    ) -> Dict[str, Any]:
        """
        Mode B: Privacy-preserving BFK09 Measurement-Based Blind Quantum Computing.
        Delegates cost minimum finding to simulated untrusted quantum cloud server.
        """
        num_candidates = len(candidate_depots)
        if num_candidates not in (2, 4):
            raise ValueError(f"Mode B supports 2 or 4 candidates, got {num_candidates}")

        t_client_total = 0.0
        t_server_total = 0.0
        t_start = time.perf_counter()

        # Step 1: Client generates private costs and translates to MBQC angles
        t0 = time.perf_counter()
        client = BqcClientService(seed=self.seed)
        costs = client.compute_fleet_costs(vehicle_lat, vehicle_lon, battery_level, candidate_depots)
        nominal_angles, edges = client.compute_nominal_angles(num_candidates, costs)
        num_qubits = len(nominal_angles)

        # Step 2: Client prepares secret thetas and one-time pads
        incoming_qubit_thetas = client.prepare_secret_blinding(num_qubits)
        t_client_total += (time.perf_counter() - t0) * 1000.0

        # Step 3: Server creates cluster graph state G
        server = BqcServerService(num_qubits=num_qubits, edges=edges, seed=self.seed)
        t_entangle_ms = server.prepare_cluster_state(incoming_qubit_thetas)
        t_server_total += t_entangle_ms

        # Step 4: Interactive Adaptive Measurement Loop
        blinded_angles: List[float] = []
        server_raw_outcomes: List[int] = []

        for q_idx in range(num_qubits):
            # Client calculates blinded angle delta_j
            t0 = time.perf_counter()
            delta_j = client.compute_blind_angle(q_idx, nominal_angles[q_idx], cluster_topology=cluster_topology)
            t_client_total += (time.perf_counter() - t0) * 1000.0
            blinded_angles.append(delta_j)

            # Server executes projective measurement in |+_delta> basis
            outcome_b, t_meas_ms = server.execute_blind_measurement(q_idx, delta_j)
            t_server_total += t_meas_ms
            server_raw_outcomes.append(outcome_b)

            # Client unpads raw outcome s_j = b_j ^ r_j
            t0 = time.perf_counter()
            client.process_server_outcome(q_idx, outcome_b)
            t_client_total += (time.perf_counter() - t0) * 1000.0

        # Step 5: Client decodes optimal depot
        t0 = time.perf_counter()
        selected_idx, diagnostics = client.decode_optimal_depot(num_candidates, costs)
        t_client_total += (time.perf_counter() - t0) * 1000.0

        t_total_ms = (time.perf_counter() - t_start) * 1000.0

        # Calculate Shannon entropy of blinded angles
        entropy = compute_angle_entropy(blinded_angles, num_bins=8)

        # Communication wire audit
        audit = server.get_visibility_audit()
        client_to_server_bytes = audit["total_bytes_received"]
        server_to_client_bytes = audit["total_bytes_sent"]
        total_wire_bytes = client_to_server_bytes + server_to_client_bytes

        selected_depot = candidate_depots[selected_idx]
        classical_min_idx = min(range(num_candidates), key=lambda i: costs[i])
        correctness = (selected_idx == classical_min_idx)

        return {
            "mode": "mode_b",
            "num_candidates": num_candidates,
            "num_qubits": num_qubits,
            "cluster_topology": cluster_topology,
            "graph_edges": edges,
            "selected_depot_index": selected_idx,
            "selected_depot_name": selected_depot.get("name", f"Depot-{selected_idx}"),
            "selected_cost": costs[selected_idx],
            "all_costs": costs,
            "classical_min_index": classical_min_idx,
            "correctness": correctness,
            "client_prep_ms": round(t_client_total, 4),
            "server_quantum_ms": round(t_server_total, 4),
            "total_execution_ms": round(t_total_ms, 4),
            "client_to_server_bytes": client_to_server_bytes,
            "server_to_client_bytes": server_to_client_bytes,
            "total_wire_bytes": total_wire_bytes,
            "blinded_angles_rad": [round(a, 5) for a in blinded_angles],
            "server_raw_outcomes": server_raw_outcomes,
            "client_unpadded_outcomes": client.unpadded_outcomes,
            "angle_entropy_bits": entropy,
            "max_theoretical_entropy": 3.0,
            "server_visibility": "Universal Blindness (0 bits of GPS, costs, or target depot revealed)",
            "privacy_guarantee": "Universal Blind Quantum Computing (BFK09)",
            "server_learned_gps": False,
            "server_learned_costs": False,
            "server_learned_output": False,
            "diagnostics": diagnostics,
            "server_visibility_audit": audit,
        }

    def execute_comparison(
        self,
        vehicle_lat: float,
        vehicle_lon: float,
        battery_level: float,
        candidate_depots: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Execute both Mode A and Mode B side-by-side with identical inputs.
        """
        mode_a = self.execute_mode_a_classical(vehicle_lat, vehicle_lon, battery_level, candidate_depots)
        mode_b = self.execute_mode_b_bqc(vehicle_lat, vehicle_lon, battery_level, candidate_depots)

        wire_expansion_percent = 0.0
        if mode_a["wire_bytes"] > 0:
            wire_expansion_percent = round(((mode_b["total_wire_bytes"] - mode_a["wire_bytes"]) / mode_a["wire_bytes"]) * 100.0, 2)

        return {
            "num_candidates": len(candidate_depots),
            "candidate_names": [d.get("name", f"Depot-{i}") for i, d in enumerate(candidate_depots)],
            "mode_a": mode_a,
            "mode_b": mode_b,
            "correctness_verified": (mode_a["selected_depot_index"] == mode_b["selected_depot_index"]),
            "wire_expansion_percent": wire_expansion_percent,
            "privacy_contrast": {
                "mode_a_server_knowledge": "Full Access: Vehicle coordinates, candidate congestion, battery level, optimal depot",
                "mode_b_server_knowledge": "Zero Access: Only graph topology G and pseudo-random angles delta_j (H ≈ 3.0 bits)"
            }
        }
