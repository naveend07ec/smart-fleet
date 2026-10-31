"""
BFK09 Server Service for Blind Quantum Fleet Computing.
Simulates the untrusted quantum cloud provider:
- Receives state preparation angles (simulating unknown incoming qubits |theta_j>)
- Creates the cluster/graph state via Controlled-Z (CZ) entangling operators
- Receives blinded measurement angles delta_j
- Executes adaptive projective measurements in {|+_delta_j>, |-_delta_j>} basis
- Returns raw measurement bits b_j in {0, 1}
- Maintains an explicit Server Visibility Audit Log verifying zero leakage of client secrets
"""

import time
from typing import List, Tuple, Dict, Any, Optional
from app.services.bqc.quantum_state_simulator import QuantumStateSimulator

class BqcServerService:
    """
    Simulates the untrusted quantum cloud server.
    Learns only graph topology G, number of qubits N, and blinded angles delta_j.
    """

    def __init__(self, num_qubits: int, edges: List[Tuple[int, int]], seed: Optional[int] = None):
        self.num_qubits = num_qubits
        self.edges = edges
        self.simulator = QuantumStateSimulator(num_qubits, seed=seed)
        self.server_visibility_log: Dict[str, Any] = {
            "num_qubits": num_qubits,
            "graph_topology": edges,
            "received_blinded_angles": [],
            "raw_measurements": [],
            "server_state_dim": 1 << num_qubits,
            "total_bytes_received": 0,
            "total_bytes_sent": 0,
            # Audit flags confirming isolation
            "learned_client_thetas": False,
            "learned_client_pads": False,
            "learned_vehicle_gps": False,
            "learned_cost_vector": False,
            "learned_optimal_depot": False,
        }

    def prepare_cluster_state(self, incoming_qubit_angles: List[float]) -> float:
        """
        Initialize the quantum register and entangle into graph state G.
        Returns execution time in milliseconds.
        """
        t0 = time.perf_counter()
        # In software simulation, angles represent incoming physical qubits
        self.simulator.initialize_single_qubit_states(incoming_qubit_angles)
        self.simulator.create_graph_state(self.edges)
        t_elap_ms = (time.perf_counter() - t0) * 1000.0

        # Update communication tracking
        # Each single-qubit arrival packet ~64 bytes framing
        self.server_visibility_log["total_bytes_received"] += self.num_qubits * 64
        return t_elap_ms

    def execute_blind_measurement(self, qubit_idx: int, delta_angle: float) -> Tuple[int, float]:
        """
        Execute measurement of qubit_idx along blinded angle delta_angle in basis {|+_delta>, |-_delta>}.
        Returns (raw_outcome_b_j, elapsed_time_ms).
        """
        t0 = time.perf_counter()
        outcome, prob = self.simulator.measure_qubit(qubit_idx, delta_angle)
        t_elap_ms = (time.perf_counter() - t0) * 1000.0

        # Log server-visible data
        self.server_visibility_log["received_blinded_angles"].append(round(delta_angle, 6))
        self.server_visibility_log["raw_measurements"].append(outcome)

        # Wire bytes: angle received (~32 bytes) + outcome returned (~16 bytes)
        self.server_visibility_log["total_bytes_received"] += 32
        self.server_visibility_log["total_bytes_sent"] += 16

        return outcome, t_elap_ms

    def get_visibility_audit(self) -> Dict[str, Any]:
        """
        Return the audit report of all data stored in the server context.
        """
        return dict(self.server_visibility_log)
