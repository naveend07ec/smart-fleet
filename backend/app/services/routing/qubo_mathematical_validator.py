"""
Phase 5.1 — Independent QUBO Mathematical Validator for Fleet Optimization.

This module provides an entirely independent, standalone mathematical implementation
of the CVRP Hamiltonian, variable mapping, constraint penalties, and exhaustive
oracle to audit the primary `QuboRoutingService` without shared code paths.
"""

import math
from typing import List, Dict, Any, Tuple, Optional


class IndependentQuboValidator:
    """
    Independent validator implemented from first principles to audit
    the QUBO matrix formulation, variable mapping, and energy conservation.
    """

    def __init__(
        self,
        depot: Dict[str, Any],
        waypoints: List[Dict[str, Any]],
        vehicles: List[Dict[str, Any]],
        max_steps: int,
        dist_matrix: Dict[str, Dict[str, float]],
        penalty_visit: float = 150.0,
        penalty_slot: float = 120.0,
        penalty_contig: float = 80.0,
        penalty_cap: float = 100.0
    ):
        self.depot = depot
        self.waypoints = waypoints
        self.vehicles = vehicles
        self.max_steps = max_steps
        self.dist_matrix = dist_matrix
        self.penalty_visit = penalty_visit
        self.penalty_slot = penalty_slot
        self.penalty_contig = penalty_contig
        self.penalty_cap = penalty_cap

        self.V = len(vehicles)
        self.N = len(waypoints)
        self.T = max_steps
        self.M = self.V * self.N * self.T

    # --------------------------------------------------------------------------
    # 1. Independent Variable Index Mapping
    # --------------------------------------------------------------------------
    def map_variable_0indexed(self, v: int, i: int, t: int) -> int:
        """
        Maps 0-indexed indices:
        v in [0..V-1], i in [0..N-1], t in [0..T-1] -> u in [0..M-1]
        """
        if not (0 <= v < self.V):
            raise IndexError(f"Vehicle index {v} out of bounds [0, {self.V-1}]")
        if not (0 <= i < self.N):
            raise IndexError(f"Destination index {i} out of bounds [0, {self.N-1}]")
        if not (0 <= t < self.T):
            raise IndexError(f"Step index {t} out of bounds [0, {self.T-1}]")
        return v * (self.N * self.T) + i * self.T + t

    def map_variable_1indexed(self, v_1: int, i_1: int, t_1: int) -> int:
        """
        Maps 1-indexed documented variables:
        v_1 in [1..V], i_1 in [1..N], t_1 in [1..T] -> u in [0..M-1]
        Formula: (v_1 - 1)*(N*T) + (i_1 - 1)*T + (t_1 - 1)
        """
        if not (1 <= v_1 <= self.V):
            raise IndexError(f"Vehicle index {v_1} out of bounds [1, {self.V}]")
        if not (1 <= i_1 <= self.N):
            raise IndexError(f"Destination index {i_1} out of bounds [1, {self.N}]")
        if not (1 <= t_1 <= self.T):
            raise IndexError(f"Step index {t_1} out of bounds [1, {self.T}]")
        return (v_1 - 1) * (self.N * self.T) + (i_1 - 1) * self.T + (t_1 - 1)

    def unmap_index_0indexed(self, u: int) -> Tuple[int, int, int]:
        """Inverts flattened index u in [0..M-1] back to (v, i, t)."""
        if not (0 <= u < self.M):
            raise IndexError(f"Flattened index {u} out of bounds [0, {self.M-1}]")
        t = u % self.T
        temp = u // self.T
        i = temp % self.N
        v = temp // self.N
        return v, i, t

    # --------------------------------------------------------------------------
    # 2. Independent Direct Hamiltonian Evaluation
    # --------------------------------------------------------------------------
    def evaluate_direct_hamiltonian(self, x: List[int]) -> Dict[str, float]:
        """
        Calculates the complete Hamiltonian energy directly from mathematical equations
        WITHOUT constructing or referencing any QUBO matrix.
        """
        if len(x) != self.M:
            raise ValueError(f"State vector length {len(x)} != M={self.M}")

        depot_id = self.depot["id"]

        # 1. Routing objective terms
        # A. Depot departure
        o_depot = 0.0
        for v in range(self.V):
            for i in range(self.N):
                u = self.map_variable_0indexed(v, i, 0)
                if x[u]:
                    o_depot += self.dist_matrix[depot_id][self.waypoints[i]["id"]]

        # B. Inter-destination transit
        o_transit = 0.0
        for v in range(self.V):
            for t in range(self.T - 1):
                for i in range(self.N):
                    u_curr = self.map_variable_0indexed(v, i, t)
                    if x[u_curr]:
                        for j in range(self.N):
                            u_next = self.map_variable_0indexed(v, j, t + 1)
                            if x[u_next]:
                                o_transit += self.dist_matrix[self.waypoints[i]["id"]][self.waypoints[j]["id"]]

        # C. Depot return
        o_return = 0.0
        for v in range(self.V):
            for i in range(self.N):
                wp_i_id = self.waypoints[i]["id"]
                d_ret = self.dist_matrix[wp_i_id][depot_id]

                # Terminal step t = T - 1
                u_last = self.map_variable_0indexed(v, i, self.T - 1)
                if x[u_last]:
                    o_return += d_ret

                # Intermediate steps t < T - 1
                for t in range(self.T - 1):
                    u_t = self.map_variable_0indexed(v, i, t)
                    if x[u_t]:
                        next_assigned = sum(x[self.map_variable_0indexed(v, j, t + 1)] for j in range(self.N))
                        o_return += d_ret * (1.0 - next_assigned)

        # 2. Constraint Penalties
        # Constraint 1: Destination Visitation
        h_visit = 0.0
        for i in range(self.N):
            total_visits = sum(
                x[self.map_variable_0indexed(v, i, t)]
                for v in range(self.V)
                for t in range(self.T)
            )
            h_visit += self.penalty_visit * ((total_visits - 1.0) ** 2)

        # Constraint 2: Slot Uniqueness
        h_slot = 0.0
        for v in range(self.V):
            for t in range(self.T):
                for i in range(self.N):
                    u_i = self.map_variable_0indexed(v, i, t)
                    if x[u_i]:
                        for j in range(i + 1, self.N):
                            u_j = self.map_variable_0indexed(v, j, t)
                            if x[u_j]:
                                h_slot += self.penalty_slot

        # Constraint 3: Route Contiguity
        h_contig = 0.0
        for v in range(self.V):
            for t in range(self.T - 1):
                for i in range(self.N):
                    u_next = self.map_variable_0indexed(v, i, t + 1)
                    if x[u_next]:
                        curr_sum = sum(x[self.map_variable_0indexed(v, j, t)] for j in range(self.N))
                        h_contig += self.penalty_contig * (1.0 - curr_sum)

        # Constraint 4: Quadratic Load Balance / Capacity Surrogate
        h_cap = 0.0
        for v in range(self.V):
            cap_v = self.vehicles[v]["capacity"]
            for i in range(self.N):
                q_i = self.waypoints[i].get("demand", 10)
                for t in range(self.T):
                    u_i = self.map_variable_0indexed(v, i, t)
                    if x[u_i]:
                        for j in range(i + 1, self.N):
                            q_j = self.waypoints[j].get("demand", 10)
                            for t_prime in range(self.T):
                                u_j = self.map_variable_0indexed(v, j, t_prime)
                                if x[u_j]:
                                    h_cap += self.penalty_cap * (q_i * q_j) / (cap_v ** 2)

        total_energy = o_depot + o_transit + o_return + h_visit + h_slot + h_contig + h_cap

        return {
            "total_energy": total_energy,
            "o_depot": o_depot,
            "o_transit": o_transit,
            "o_return": o_return,
            "total_routing_obj": o_depot + o_transit + o_return,
            "h_visit": h_visit,
            "h_slot": h_slot,
            "h_contig": h_contig,
            "h_cap": h_cap,
            "total_penalties": h_visit + h_slot + h_contig + h_cap
        }

    # --------------------------------------------------------------------------
    # 3. Independent Matrix Energy Evaluation
    # --------------------------------------------------------------------------
    @staticmethod
    def evaluate_matrix_energy(Q: List[List[float]], c: float, x: List[int]) -> float:
        """Evaluates E(x) = x^T Q x + c for upper-triangular Q."""
        M = len(x)
        val = c
        for u in range(M):
            if x[u]:
                val += Q[u][u]
                for w in range(u + 1, M):
                    if x[w]:
                        val += Q[u][w]
        return val

    # --------------------------------------------------------------------------
    # 4. Independent State-Space Exhaustive Validator
    # --------------------------------------------------------------------------
    def audit_entire_state_space(self, Q: List[List[float]], c: float) -> Dict[str, Any]:
        """
        Evaluates every state in {0, 1}^M, comparing direct Hamiltonian with matrix energy.
        Computes maximum discrepancy and finds independent global optimum.
        """
        if self.M > 16:
            raise ValueError(f"State space 2^{self.M} too large for exhaustive scan. Max M=16.")

        total_states = 1 << self.M
        max_discrepancy = 0.0
        discrepancy_count = 0
        min_direct_energy = float("inf")
        best_direct_state = None

        for s in range(total_states):
            x = [(s >> u) & 1 for u in range(self.M)]
            direct_eval = self.evaluate_direct_hamiltonian(x)
            direct_e = direct_eval["total_energy"]
            mat_e = self.evaluate_matrix_energy(Q, c, x)

            diff = abs(direct_e - mat_e)
            if diff > max_discrepancy:
                max_discrepancy = diff
            if diff > 1e-4:
                discrepancy_count += 1

            if direct_e < min_direct_energy:
                min_direct_energy = direct_e
                best_direct_state = list(x)

        return {
            "total_states": total_states,
            "max_discrepancy": max_discrepancy,
            "discrepancy_count": discrepancy_count,
            "min_direct_energy": min_direct_energy,
            "best_direct_bitstring": "".join(str(b) for b in best_direct_state) if best_direct_state else ""
        }

    # --------------------------------------------------------------------------
    # 5. Independent Route Decoder & Feasibility Auditor
    # --------------------------------------------------------------------------
    def audit_route_feasibility(self, x: List[int]) -> Dict[str, Any]:
        """
        Independently audits a decoded candidate solution against hard CVRP rules:
        - Exactly one visit per destination
        - At most one destination per vehicle slot
        - Contiguity (no gaps before a visit)
        - Vehicle capacity limit
        """
        visit_counts = [0] * self.N
        slot_collisions = 0
        contiguity_violations = 0
        capacity_violations = 0
        total_distance = 0.0

        depot_id = self.depot["id"]

        for v in range(self.V):
            v_cap = self.vehicles[v]["capacity"]
            v_demand = 0
            v_stops = []

            seen_empty_slot = False
            for t in range(self.T):
                slot_wps = []
                for i in range(self.N):
                    u = self.map_variable_0indexed(v, i, t)
                    if x[u]:
                        slot_wps.append(i)
                        visit_counts[i] += 1

                if len(slot_wps) > 1:
                    slot_collisions += (len(slot_wps) - 1)

                if len(slot_wps) == 1:
                    i_dest = slot_wps[0]
                    v_stops.append(i_dest)
                    v_demand += self.waypoints[i_dest].get("demand", 10)
                    if seen_empty_slot:
                        contiguity_violations += 1
                else:
                    seen_empty_slot = True

            if v_demand > v_cap:
                capacity_violations += (v_demand - v_cap)

            # Compute route distance if vehicle has stops
            if v_stops:
                first_wp = self.waypoints[v_stops[0]]["id"]
                total_distance += self.dist_matrix[depot_id][first_wp]
                for idx_s in range(len(v_stops) - 1):
                    w1 = self.waypoints[v_stops[idx_s]]["id"]
                    w2 = self.waypoints[v_stops[idx_s + 1]]["id"]
                    total_distance += self.dist_matrix[w1][w2]
                last_wp = self.waypoints[v_stops[-1]]["id"]
                total_distance += self.dist_matrix[last_wp][depot_id]

        missing_visits = sum(1 for c in visit_counts if c == 0)
        duplicate_visits = sum(max(0, c - 1) for c in visit_counts)

        total_violations = (
            missing_visits
            + duplicate_visits
            + slot_collisions
            + contiguity_violations
            + (1 if capacity_violations > 0 else 0)
        )

        return {
            "feasible": (total_violations == 0),
            "total_violations": total_violations,
            "missing_visits": missing_visits,
            "duplicate_visits": duplicate_visits,
            "slot_collisions": slot_collisions,
            "contiguity_violations": contiguity_violations,
            "capacity_violations": capacity_violations,
            "total_distance": round(total_distance, 3)
        }
