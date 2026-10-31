"""
Quantum State Vector Simulator for BFK09 Measurement-Based Quantum Computing (MBQC).
Pure-Python numerical simulation over complex state vectors in C^(2^N).

Explicitly designed for educational and scientific privacy evaluation:
- Exact state vector evolution: |psi> in C^(2^N)
- Graph-state creation via Controlled-Z (CZ) entangling operators
- Adaptive projective measurements in arbitrary basis {|+_delta>, |-_delta>}
- Verification of normalization <psi|psi> = 1.0
"""

import math
import cmath
import random
from typing import List, Tuple, Dict, Any, Optional

class QuantumStateSimulator:
    """
    Simulates an N-qubit quantum state vector and projective measurement operators.
    Qubit indexing is 0-based: qubit 0 is the least significant bit (bit 0).
    """

    def __init__(self, num_qubits: int, seed: Optional[int] = None):
        if num_qubits < 1 or num_qubits > 16:
            raise ValueError(f"num_qubits must be between 1 and 16, got {num_qubits}")
        self.num_qubits = num_qubits
        self.dim = 1 << num_qubits
        self.rng = random.Random(seed)
        # Initialize state to |0>^N
        self.state: List[complex] = [0.0 + 0.0j] * self.dim
        self.state[0] = 1.0 + 0.0j
        self.is_entangled = False
        self.measurement_history: List[Dict[str, Any]] = []

    def norm(self) -> float:
        """Calculate state vector Euclidean norm <psi|psi>."""
        return math.sqrt(sum(abs(c) ** 2 for c in self.state))

    def normalize(self) -> None:
        """Normalize state vector so that <psi|psi> == 1.0."""
        n = self.norm()
        if n > 1e-12:
            inv = 1.0 / n
            self.state = [c * inv for c in self.state]

    def initialize_single_qubit_states(self, angles: List[float]) -> None:
        """
        Initialize the N-qubit register to a product of single-qubit states:
        |psi> = (x)_{j=0}^{N-1} |theta_j>, where |theta_j> = 1/sqrt(2) (|0> + e^(i theta_j) |1>).
        """
        if len(angles) != self.num_qubits:
            raise ValueError(f"Expected {self.num_qubits} angles, got {len(angles)}")

        # Build tensor product iteratively
        inv_sqrt2 = 1.0 / math.sqrt(2.0)
        curr: List[complex] = [1.0 + 0.0j]

        for theta in angles:
            q0 = inv_sqrt2
            q1 = inv_sqrt2 * cmath.exp(1j * theta)
            next_state: List[complex] = []
            for amp in curr:
                next_state.append(amp * q0)
                next_state.append(amp * q1)
            curr = next_state

        self.state = curr
        self.normalize()
        self.is_entangled = False

    def apply_cz(self, qubit_a: int, qubit_b: int) -> None:
        """
        Apply Controlled-Z (CZ) entangling gate between qubit_a and qubit_b.
        Flips the phase of basis states where both qubit_a and qubit_b are 1.
        """
        if qubit_a == qubit_b or not (0 <= qubit_a < self.num_qubits) or not (0 <= qubit_b < self.num_qubits):
            raise ValueError(f"Invalid qubits for CZ: {qubit_a}, {qubit_b}")

        mask = (1 << qubit_a) | (1 << qubit_b)
        for idx in range(self.dim):
            if (idx & mask) == mask:
                self.state[idx] = -self.state[idx]

        self.is_entangled = True

    def create_graph_state(self, edges: List[Tuple[int, int]]) -> None:
        """
        Create a cluster/graph state by applying CZ gates for each edge in the graph.
        """
        for u, v in edges:
            self.apply_cz(u, v)

    def measure_qubit(self, qubit: int, delta: float) -> Tuple[int, float]:
        """
        Measure a single qubit in the basis {|+_delta>, |-_delta>}:
        |+_delta> = 1/sqrt(2) (|0> + e^(i delta) |1>) -> outcome 0
        |-_delta> = 1/sqrt(2) (|0> - e^(i delta) |1>) -> outcome 1

        Returns (outcome, probability_of_outcome) and collapses the state vector.
        """
        if not (0 <= qubit < self.num_qubits):
            raise ValueError(f"Invalid qubit index: {qubit}")

        inv_sqrt2 = 1.0 / math.sqrt(2.0)
        exp_neg = cmath.exp(-1j * delta)
        exp_pos = cmath.exp(1j * delta)
        bit_mask = 1 << qubit

        # Calculate projection amplitudes
        prob_plus = 0.0
        # Iterate over all pairs (k0, k1) where k0 has bit=0 and k1 has bit=1
        for idx0 in range(self.dim):
            if (idx0 & bit_mask) == 0:
                idx1 = idx0 | bit_mask
                c0 = self.state[idx0]
                c1 = self.state[idx1]

                # Projection amplitude onto |+_delta>
                a_plus = inv_sqrt2 * (c0 + exp_neg * c1)
                prob_plus += abs(a_plus) ** 2

        prob_plus = max(0.0, min(1.0, prob_plus))
        prob_minus = 1.0 - prob_plus

        # Sample outcome using Born rule
        rand_val = self.rng.random()
        outcome = 0 if rand_val < prob_plus else 1
        chosen_prob = prob_plus if outcome == 0 else prob_minus

        # Collapse the state vector
        norm_factor = math.sqrt(chosen_prob) if chosen_prob > 1e-12 else 1e-6
        for idx0 in range(self.dim):
            if (idx0 & bit_mask) == 0:
                idx1 = idx0 | bit_mask
                c0 = self.state[idx0]
                c1 = self.state[idx1]

                if outcome == 0:
                    a_plus = inv_sqrt2 * (c0 + exp_neg * c1)
                    self.state[idx0] = a_plus / norm_factor
                    self.state[idx1] = (a_plus * exp_pos) / norm_factor
                else:
                    a_minus = inv_sqrt2 * (c0 - exp_neg * c1)
                    self.state[idx0] = a_minus / norm_factor
                    self.state[idx1] = (-a_minus * exp_pos) / norm_factor

        self.normalize()

        record = {
            "qubit": qubit,
            "delta_rad": delta,
            "outcome": outcome,
            "probability": chosen_prob,
        }
        self.measurement_history.append(record)

        return outcome, chosen_prob
