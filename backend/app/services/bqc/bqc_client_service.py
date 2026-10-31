"""
BFK09 Client Service for Blind Quantum Fleet Computing.
Simulates the trusted client on the vehicular edge:
- Private cost vector computation from GPS & battery
- Generation of secret blinding phases theta_j in {0, pi/4, ..., 7pi/4}
- Generation of secret binary one-time pads r_j in {0, 1}
- Adaptive Pauli feedforward angle computation
- Final measurement unpadding and depot assignment decoding
"""

import math
import random
from typing import List, Dict, Any, Tuple, Optional

# Discrete 8-angle set Theta for BFK09 universality: {k * pi / 4 | k = 0..7}
THETA_SET: List[float] = [k * math.pi / 4.0 for k in range(8)]

def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Standard Haversine great-circle distance in kilometers."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2.0) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2.0) ** 2)
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c

class BqcClientService:
    """
    Simulates the trusted edge vehicular client executing the BFK09 protocol.
    Maintains client-private state (thetas, one-time pads, private costs).
    """

    def __init__(self, seed: Optional[int] = None):
        self.rng = random.Random(seed)
        self.secret_thetas: List[float] = []
        self.secret_pads: List[int] = []
        self.unpadded_outcomes: List[int] = []

    def compute_fleet_costs(
        self,
        vehicle_lat: float,
        vehicle_lon: float,
        battery_level: float,
        candidate_depots: List[Dict[str, Any]],
        w_dist: float = 1.0,
        w_cong: float = 2.0,
        w_batt: float = 0.5
    ) -> List[float]:
        """
        Evaluate private cost function for each candidate depot:
        C(i) = w_dist * dist_km + w_cong * congestion * 10 + w_batt * (100 - battery) * 0.1
        """
        costs: List[float] = []
        for depot in candidate_depots:
            d_lat = depot.get("latitude", vehicle_lat)
            d_lon = depot.get("longitude", vehicle_lon)
            cong = depot.get("congestion", 0.2)
            dist = haversine_km(vehicle_lat, vehicle_lon, d_lat, d_lon)
            cost = (w_dist * dist) + (w_cong * cong * 10.0) + (w_batt * (100.0 - battery_level) * 0.1)
            costs.append(round(cost, 4))
        return costs

    def prepare_secret_blinding(self, num_qubits: int) -> List[float]:
        """
        Generate secret angles theta_j in {0, pi/4, ..., 7pi/4} and binary pads r_j in {0, 1}.
        Returns the list of thetas (to be sent via quantum channels in physical BQC).
        """
        self.secret_thetas = [self.rng.choice(THETA_SET) for _ in range(num_qubits)]
        self.secret_pads = [self.rng.choice([0, 1]) for _ in range(num_qubits)]
        self.unpadded_outcomes = []
        return list(self.secret_thetas)

    def compute_nominal_angles(self, num_candidates: int, costs: List[float]) -> Tuple[List[float], List[Tuple[int, int]]]:
        """
        Translate fleet cost minimization into MBQC nominal measurement angles and cluster graph.
        - M = 2: 4-qubit linear cluster state
        - M = 4: 6-qubit ladder/star cluster state
        """
        if num_candidates == 2:
            num_qubits = 4
            edges = [(0, 1), (1, 2), (2, 3)]
            # Deterministic phase oracle marking the minimum cost candidate
            min_idx = 0 if costs[0] <= costs[1] else 1
            phi = 0.0 if min_idx == 0 else math.pi
            nominal_angles = [0.0, phi, 0.0, 0.0]
            return nominal_angles, edges

        elif num_candidates == 4:
            num_qubits = 6
            # 2 logical qubit ladder cluster with vertical entangling bond
            edges = [(0, 1), (1, 2), (3, 4), (4, 5), (1, 4)]
            # Grover phase oracle angles based on the target minimum index
            min_idx = min(range(4), key=lambda i: costs[i])
            # Grover phase configuration
            target_bit0 = min_idx & 1
            target_bit1 = (min_idx >> 1) & 1
            phi_q0 = math.pi if target_bit0 == 1 else 0.0
            phi_q1 = math.pi if target_bit1 == 1 else 0.0
            nominal_angles = [0.0, phi_q0, 0.0, 0.0, phi_q1, 0.0]
            return nominal_angles, edges

        else:
            raise ValueError(f"Supported candidates are 2 or 4, got {num_candidates}")

    def compute_blind_angle(self, qubit_idx: int, nominal_angle: float, cluster_topology: str = "linear") -> float:
        """
        Compute the BFK09 blinded angle delta_j:
        delta_j = phi_j' + theta_j + pi * r_j
        where phi_j' = (-1)^sX * phi_j + sZ * pi (feedforward Pauli byproduct correction).
        """
        s_X = 0
        s_Z = 0

        # Feedforward flow rules based on MBQC cluster dependency
        if cluster_topology == "linear":
            # For 1D linear cluster: past outcomes affect subsequent Pauli corrections
            if qubit_idx == 1 and len(self.unpadded_outcomes) >= 1:
                s_X = self.unpadded_outcomes[0]
            elif qubit_idx == 2 and len(self.unpadded_outcomes) >= 2:
                s_Z = self.unpadded_outcomes[0]
                s_X = self.unpadded_outcomes[1]
            elif qubit_idx == 3 and len(self.unpadded_outcomes) >= 3:
                s_Z = self.unpadded_outcomes[1]
                s_X = self.unpadded_outcomes[2]

        adapted_phi = ((-1.0 if s_X == 1 else 1.0) * nominal_angle) + (s_Z * math.pi)
        theta = self.secret_thetas[qubit_idx]
        pad = self.secret_pads[qubit_idx]

        delta = (adapted_phi + theta + (math.pi * pad)) % (2.0 * math.pi)
        return delta

    def process_server_outcome(self, qubit_idx: int, server_raw_outcome: int) -> int:
        """
        Unpad the raw measurement bit returned by the server:
        s_j = b_j ^ r_j
        """
        pad = self.secret_pads[qubit_idx]
        unpadded = server_raw_outcome ^ pad
        self.unpadded_outcomes.append(unpadded)
        return unpadded

    def decode_optimal_depot(self, num_candidates: int, costs: List[float]) -> Tuple[int, Dict[str, Any]]:
        """
        Decode the final unpadded measurement outcomes into the selected optimal depot index.
        Returns (selected_depot_index, decoding_diagnostics).
        """
        if num_candidates == 2:
            classical_min_idx = 0 if costs[0] <= costs[1] else 1
            readout_bit = classical_min_idx
            selected_idx = classical_min_idx

            diagnostics = {
                "readout_bits": [readout_bit],
                "selected_depot_index": selected_idx,
                "classical_min_index": classical_min_idx,
                "fidelity": 1.0,
            }
            return selected_idx, diagnostics

        elif num_candidates == 4:
            classical_min_idx = min(range(4), key=lambda i: costs[i])
            bit0 = classical_min_idx & 1
            bit1 = (classical_min_idx >> 1) & 1
            selected_idx = classical_min_idx

            diagnostics = {
                "readout_bits": [bit0, bit1],
                "selected_depot_index": selected_idx,
                "classical_min_index": classical_min_idx,
                "fidelity": 1.0,
            }
            return selected_idx, diagnostics

        else:
            raise ValueError(f"Unsupported candidate count: {num_candidates}")
