"""
Phase 5: QUBO / Simulated Annealing Fleet Routing & Multi-Vehicle Scheduling Service.

Rigorously compares three optimization approaches:
1. Method A — Conventional Greedy Routing (Deterministic Nearest Neighbor with Capacity Constraints)
2. Method B — Classical Simulated Annealing (Stochastic Local Search on Route Permutations)
3. Method C — QUBO Formulation + Simulated Annealing Solver (Binary State-Space Optimization)
"""

import math
import random
import time
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great-circle distance between two points in kilometers."""
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = (math.sin(dphi / 2.0) ** 2 +
         math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2)
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return round(R * c, 3)


# Baseline Depot in Central Chennai
DEFAULT_CHENNAI_DEPOT = {
    "id": "depot-central",
    "name": "Central Logistics Hub",
    "latitude": 13.0827,
    "longitude": 80.2707
}

# Standard 8 Waypoints across Chennai
DEFAULT_CHENNAI_WAYPOINTS = [
    {"id": "wp-1", "name": "T. Nagar Hub", "latitude": 13.0418, "longitude": 80.2341, "demand": 15, "priority": 2},
    {"id": "wp-2", "name": "Adyar Terminal", "latitude": 13.0067, "longitude": 80.2570, "demand": 12, "priority": 1},
    {"id": "wp-3", "name": "Anna Nagar North", "latitude": 13.0850, "longitude": 80.2100, "demand": 18, "priority": 3},
    {"id": "wp-4", "name": "Guindy Industrial", "latitude": 13.0067, "longitude": 80.2021, "demand": 16, "priority": 2},
    {"id": "wp-5", "name": "Velachery Station", "latitude": 12.9800, "longitude": 80.2200, "demand": 20, "priority": 1},
    {"id": "wp-6", "name": "OMR Tech Corridor", "latitude": 12.9500, "longitude": 80.2400, "demand": 22, "priority": 3},
    {"id": "wp-7", "name": "Porur Logistics", "latitude": 13.0300, "longitude": 80.1500, "demand": 14, "priority": 1},
    {"id": "wp-8", "name": "Mylapore Heritage", "latitude": 13.0333, "longitude": 80.2667, "demand": 10, "priority": 2},
]

# Standard 3 Electric Delivery Vehicles (preserves existing 3-vehicle benchmark contracts)
DEFAULT_VEHICLES = [
    {"id": "EV-01", "name": "Alpha Electric Van", "capacity": 65, "battery_range_km": 95.0, "energy_rate_kwh_per_km": 0.22},
    {"id": "EV-02", "name": "Beta Electric Van", "capacity": 65, "battery_range_km": 95.0, "energy_rate_kwh_per_km": 0.22},
    {"id": "EV-03", "name": "Gamma Electric Van", "capacity": 65, "battery_range_km": 95.0, "energy_rate_kwh_per_km": 0.22},
]

EXPANDED_FLEET = DEFAULT_VEHICLES + [
    {"id": "EV-04", "name": "Delta Electric Van", "capacity": 65, "battery_range_km": 95.0, "energy_rate_kwh_per_km": 0.22},
    {"id": "EV-05", "name": "Epsilon Electric Van", "capacity": 65, "battery_range_km": 95.0, "energy_rate_kwh_per_km": 0.22},
]

# Standard Controlled Benchmark Scenarios
STANDARDIZED_SCENARIOS = {
    "small": {
        "id": "small",
        "name": "Small (Micro-Fleet)",
        "description": "2 vehicles, 3 destinations. Search space: 2^12 = 4,096 states. Verifiable against exhaustive enumeration.",
        "num_vehicles": 2,
        "num_destinations": 3,
        "max_steps": 2,
        "vehicles": DEFAULT_VEHICLES[:2],
        "waypoints": DEFAULT_CHENNAI_WAYPOINTS[:3]
    },
    "medium": {
        "id": "medium",
        "name": "Medium (Urban Cluster)",
        "description": "3 vehicles, 5 destinations. Search space: 2^45 = 3.52e13 states.",
        "num_vehicles": 3,
        "num_destinations": 5,
        "max_steps": 3,
        "vehicles": DEFAULT_VEHICLES[:3],
        "waypoints": DEFAULT_CHENNAI_WAYPOINTS[:5]
    },
    "large": {
        "id": "large",
        "name": "Large (Regional Grid)",
        "description": "5 vehicles, 8 destinations. Search space: 2^160 = 1.46e48 states.",
        "num_vehicles": 5,
        "num_destinations": 8,
        "max_steps": 4,
        "vehicles": EXPANDED_FLEET,
        "waypoints": DEFAULT_CHENNAI_WAYPOINTS[:8]
    }
}


class QuboRoutingService:
    """
    Fleet Route Optimization Service providing Conventional Greedy, Classical SA,
    and QUBO-based Quantum-Inspired Solvers.
    """

    def __init__(self, seed: Optional[int] = 42):
        self.random = random.Random(seed)

    def _build_distance_matrix(self, depot: Dict[str, Any], waypoints: List[Dict[str, Any]]) -> Dict[str, Dict[str, float]]:
        """Precomputes pair-wise haversine distance dictionary."""
        all_nodes = [depot] + waypoints
        matrix = {}
        for n1 in all_nodes:
            matrix[n1["id"]] = {}
            for n2 in all_nodes:
                if n1["id"] == n2["id"]:
                    matrix[n1["id"]][n2["id"]] = 0.0
                else:
                    matrix[n1["id"]][n2["id"]] = haversine_km(
                        n1["latitude"], n1["longitude"],
                        n2["latitude"], n2["longitude"]
                    )
        return matrix

    def _route_distance(self, depot_id: str, stops: List[Dict[str, Any]], dist_matrix: Dict[str, Dict[str, float]]) -> float:
        """Computes total round-trip distance: depot -> stop_1 -> ... -> stop_m -> depot."""
        if not stops:
            return 0.0
        total = dist_matrix[depot_id][stops[0]["id"]]
        for i in range(len(stops) - 1):
            total += dist_matrix[stops[i]["id"]][stops[i+1]["id"]]
        total += dist_matrix[stops[-1]["id"]][depot_id]
        return round(total, 3)

    def _two_opt_local_search(self, stops: List[Dict[str, Any]], depot_id: str, dist_matrix: Dict[str, Dict[str, float]]) -> List[Dict[str, Any]]:
        """Applies 2-opt edge-swap heuristic to uncross route segments."""
        if len(stops) <= 2:
            return stops
        best = list(stops)
        improved = True
        iterations = 0
        while improved and iterations < 50:
            improved = False
            iterations += 1
            best_dist = self._route_distance(depot_id, best, dist_matrix)
            for i in range(1, len(best) - 1):
                for k in range(i + 1, len(best)):
                    new_route = best[:i] + best[i:k+1][::-1] + best[k+1:]
                    new_dist = self._route_distance(depot_id, new_route, dist_matrix)
                    if new_dist < best_dist - 1e-4:
                        best = new_route
                        best_dist = new_dist
                        improved = True
                        break
                if improved:
                    break
        return best

    # --------------------------------------------------------------------------
    # Method A: Conventional Greedy Routing Baseline
    # --------------------------------------------------------------------------
    def solve_greedy_routing(
        self,
        depot: Dict[str, Any],
        waypoints: List[Dict[str, Any]],
        vehicles: List[Dict[str, Any]],
        dist_matrix: Dict[str, Dict[str, float]]
    ) -> Dict[str, Any]:
        """
        Conventional deterministic Greedy Routing with capacity enforcement.
        1. Sorts waypoints by priority descending, distance from depot ascending.
        2. Assigns each waypoint to the nearest feasible vehicle.
        3. Optimizes stop order via 2-opt.
        """
        start_time = time.perf_counter()
        depot_id = depot["id"]
        unvisited = list(waypoints)
        # Deterministic sorting
        unvisited.sort(key=lambda w: (-w.get("priority", 1), dist_matrix[depot_id][w["id"]]))

        vehicle_routes = []
        violations = 0

        for v in vehicles:
            v_id = v["id"]
            v_cap = v["capacity"]
            current_load = 0
            curr_loc_id = depot_id
            route_stops = []

            i = 0
            while i < len(unvisited):
                candidate = unvisited[i]
                cand_demand = candidate.get("demand", 0)
                if current_load + cand_demand <= v_cap:
                    route_stops.append(candidate)
                    current_load += cand_demand
                    curr_loc_id = candidate["id"]
                    unvisited.pop(i)
                else:
                    i += 1

            # 2-opt optimization
            optimized_stops = self._two_opt_local_search(route_stops, depot_id, dist_matrix)
            dist_km = self._route_distance(depot_id, optimized_stops, dist_matrix)
            energy_rate = v.get("energy_rate_kwh_per_km", 0.22)
            energy_kwh = round(dist_km * energy_rate, 3)

            stop_seq = [{"type": "depot", **depot}] + \
                       [{"type": "waypoint", **st} for st in optimized_stops] + \
                       [{"type": "depot", **depot}]

            is_feasible = (current_load <= v_cap) and (dist_km <= v.get("battery_range_km", 100.0))
            if not is_feasible:
                violations += 1

            vehicle_routes.append({
                "vehicle_id": v_id,
                "vehicle_name": v.get("name", v_id),
                "stop_sequence": stop_seq,
                "total_distance_km": dist_km,
                "total_energy_kwh": energy_kwh,
                "total_demand_delivered": current_load,
                "capacity_utilized_percent": round((current_load / v_cap) * 100.0, 1),
                "feasible": is_feasible
            })

        # If any waypoints remain unvisited, allocate to lowest-loaded vehicle (flags infeasible)
        if unvisited:
            violations += len(unvisited)
            min_v = min(vehicle_routes, key=lambda vr: vr["total_distance_km"])
            v_conf = next(v for v in vehicles if v["id"] == min_v["vehicle_id"])
            for rem in unvisited:
                stops_only = [s for s in min_v["stop_sequence"] if s.get("type") == "waypoint"]
                stops_only.append(rem)
                optimized = self._two_opt_local_search(stops_only, depot_id, dist_matrix)
                dist_km = self._route_distance(depot_id, optimized, dist_matrix)
                curr_load = sum(s.get("demand", 0) for s in optimized)
                min_v["total_demand_delivered"] = curr_load
                min_v["total_distance_km"] = dist_km
                min_v["total_energy_kwh"] = round(dist_km * v_conf.get("energy_rate_kwh_per_km", 0.22), 3)
                min_v["capacity_utilized_percent"] = round((curr_load / v_conf["capacity"]) * 100.0, 1)
                min_v["feasible"] = (curr_load <= v_conf["capacity"]) and (dist_km <= v_conf.get("battery_range_km", 100.0))
                min_v["stop_sequence"] = [{"type": "depot", **depot}] + \
                                         [{"type": "waypoint", **st} for st in optimized] + \
                                         [{"type": "depot", **depot}]

        exec_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
        total_dist = round(sum(r["total_distance_km"] for r in vehicle_routes), 3)
        total_energy = round(sum(r["total_energy_kwh"] for r in vehicle_routes), 3)
        travel_time_hours = round(total_dist / 40.0, 2)
        all_feasible = (violations == 0) and all(r["feasible"] for r in vehicle_routes)
        objective_value = round(total_dist + (violations * 100.0), 3)

        max_dist = max((r["total_distance_km"] for r in vehicle_routes), default=0.0)
        return {
            "method": "greedy",
            "method_name": "Method A — Conventional Greedy Routing",
            "routes": vehicle_routes,
            "total_distance_km": total_dist,
            "total_energy_kwh": total_energy,
            "estimated_travel_time_hours": travel_time_hours,
            "objective_value": objective_value,
            "execution_time_ms": exec_ms,
            "max_route_distance_km": max_dist,
            "all_feasible": all_feasible,
            "constraint_violations": violations,
            "route_variance_km": round(sum((r["total_distance_km"] - (total_dist / len(vehicles)))**2 for r in vehicle_routes) / max(1, len(vehicles)), 2)
        }

    # Backward compatibility alias
    def solve_classical_heuristic(self, depot, waypoints, vehicles, dist_matrix):
        return self.solve_greedy_routing(depot, waypoints, vehicles, dist_matrix)

    # --------------------------------------------------------------------------
    # Method B: Classical Simulated Annealing (Route Permutation Space)
    # --------------------------------------------------------------------------
    def _qubo_hamiltonian(
        self,
        partition: List[List[Dict[str, Any]]],
        depot_id: str,
        vehicles: List[Dict[str, Any]],
        dist_matrix: Dict[str, Dict[str, float]],
        penalty_cap: float = 80.0,
        penalty_range: float = 40.0,
        penalty_balance: float = 0.8
    ) -> float:
        """Evaluates cost function for partition-based permutation SA."""
        total_dist = 0.0
        cap_violation = 0.0
        range_violation = 0.0
        route_distances = []

        for k, stops in enumerate(partition):
            v_conf = vehicles[k]
            d = self._route_distance(depot_id, stops, dist_matrix)
            route_distances.append(d)
            total_dist += d

            load = sum(st.get("demand", 0) for st in stops)
            if load > v_conf["capacity"]:
                cap_violation += (load - v_conf["capacity"]) ** 2

            if d > v_conf.get("battery_range_km", 100.0):
                range_violation += (d - v_conf.get("battery_range_km", 100.0)) ** 2

        mean_dist = total_dist / max(1, len(vehicles))
        balance_penalty = sum((rd - mean_dist) ** 2 for rd in route_distances)

        energy = total_dist + (penalty_cap * cap_violation) + (penalty_range * range_violation) + (penalty_balance * balance_penalty)
        return energy

    def solve_classical_simulated_annealing(
        self,
        depot: Dict[str, Any],
        waypoints: List[Dict[str, Any]],
        vehicles: List[Dict[str, Any]],
        dist_matrix: Dict[str, Dict[str, float]],
        iterations: int = 1000,
        initial_temp: float = 100.0,
        cooling_rate: float = 0.985,
        seed: Optional[int] = None
    ) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Method B: Classical Simulated Annealing operating directly in route permutation space.
        """
        rng = random.Random(seed if seed is not None else 42)
        start_time = time.perf_counter()
        depot_id = depot["id"]
        num_v = len(vehicles)

        current_state: List[List[Dict[str, Any]]] = [[] for _ in range(num_v)]
        shuffled = list(waypoints)
        rng.shuffle(shuffled)
        for idx, wp in enumerate(shuffled):
            current_state[idx % num_v].append(wp)

        for k in range(num_v):
            current_state[k] = self._two_opt_local_search(current_state[k], depot_id, dist_matrix)

        current_energy = self._qubo_hamiltonian(current_state, depot_id, vehicles, dist_matrix)
        best_state = [list(r) for r in current_state]
        best_energy = current_energy

        temp = initial_temp
        convergence_history = []
        sample_step = max(1, iterations // 25)

        for step in range(iterations):
            move_type = rng.choice(["relocate", "swap", "two_opt"])
            candidate_state = [list(r) for r in current_state]

            if move_type == "relocate":
                src_v = rng.randrange(num_v)
                dst_v = rng.randrange(num_v)
                if src_v != dst_v and candidate_state[src_v]:
                    idx = rng.randrange(len(candidate_state[src_v]))
                    item = candidate_state[src_v].pop(idx)
                    insert_pos = rng.randint(0, len(candidate_state[dst_v]))
                    candidate_state[dst_v].insert(insert_pos, item)

            elif move_type == "swap":
                v1 = rng.randrange(num_v)
                v2 = rng.randrange(num_v)
                if v1 != v2 and candidate_state[v1] and candidate_state[v2]:
                    idx1 = rng.randrange(len(candidate_state[v1]))
                    idx2 = rng.randrange(len(candidate_state[v2]))
                    candidate_state[v1][idx1], candidate_state[v2][idx2] = candidate_state[v2][idx2], candidate_state[v1][idx1]

            elif move_type == "two_opt":
                v_idx = rng.randrange(num_v)
                if len(candidate_state[v_idx]) >= 3:
                    i = rng.randrange(len(candidate_state[v_idx]) - 1)
                    k = rng.randrange(i + 1, len(candidate_state[v_idx]))
                    candidate_state[v_idx] = candidate_state[v_idx][:i] + candidate_state[v_idx][i:k+1][::-1] + candidate_state[v_idx][k+1:]

            cand_energy = self._qubo_hamiltonian(candidate_state, depot_id, vehicles, dist_matrix)
            delta_e = cand_energy - current_energy

            if delta_e < 0.0 or rng.random() < math.exp(-delta_e / max(1e-6, temp)):
                current_state = candidate_state
                current_energy = cand_energy
                if current_energy < best_energy:
                    best_energy = current_energy
                    best_state = [list(r) for r in current_state]

            temp *= cooling_rate

            if step % sample_step == 0 or step == iterations - 1:
                convergence_history.append({
                    "iteration": step,
                    "temperature": round(temp, 3),
                    "current_energy": round(current_energy, 2),
                    "best_energy": round(best_energy, 2)
                })

        for k in range(num_v):
            best_state[k] = self._two_opt_local_search(best_state[k], depot_id, dist_matrix)

        exec_ms = round((time.perf_counter() - start_time) * 1000.0, 2)

        vehicle_routes = []
        violations = 0
        for k, stops in enumerate(best_state):
            v_conf = vehicles[k]
            dist_km = self._route_distance(depot_id, stops, dist_matrix)
            load = sum(st.get("demand", 0) for st in stops)
            energy_kwh = round(dist_km * v_conf.get("energy_rate_kwh_per_km", 0.22), 3)

            stop_seq = [{"type": "depot", **depot}] + \
                       [{"type": "waypoint", **st} for st in stops] + \
                       [{"type": "depot", **depot}]

            is_feasible = (load <= v_conf["capacity"]) and (dist_km <= v_conf.get("battery_range_km", 100.0))
            if not is_feasible:
                violations += 1

            vehicle_routes.append({
                "vehicle_id": v_conf["id"],
                "vehicle_name": v_conf.get("name", v_conf["id"]),
                "stop_sequence": stop_seq,
                "total_distance_km": dist_km,
                "total_energy_kwh": energy_kwh,
                "total_demand_delivered": load,
                "capacity_utilized_percent": round((load / v_conf["capacity"]) * 100.0, 1),
                "feasible": is_feasible
            })

        total_dist = round(sum(r["total_distance_km"] for r in vehicle_routes), 3)
        total_energy = round(sum(r["total_energy_kwh"] for r in vehicle_routes), 3)
        travel_time_hours = round(total_dist / 40.0, 2)
        all_feasible = (violations == 0) and all(r["feasible"] for r in vehicle_routes)
        objective_value = round(total_dist + (violations * 100.0), 3)

        result = {
            "method": "classical_sa",
            "method_name": "Method B — Classical Simulated Annealing (Route Permutation)",
            "routes": vehicle_routes,
            "total_distance_km": total_dist,
            "total_energy_kwh": total_energy,
            "estimated_travel_time_hours": travel_time_hours,
            "objective_value": objective_value,
            "execution_time_ms": exec_ms,
            "all_feasible": all_feasible,
            "constraint_violations": violations,
            "route_variance_km": round(sum((r["total_distance_km"] - (total_dist / len(vehicles)))**2 for r in vehicle_routes) / max(1, len(vehicles)), 2),
            "qubo_energy_score": round(best_energy, 2)
        }

        return result, convergence_history

    # --------------------------------------------------------------------------
    # Method C: QUBO Formulation Solved with Simulated Annealing Solver
    # --------------------------------------------------------------------------
    def build_qubo_matrix(
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
    ) -> Tuple[List[List[float]], float, int, Dict[str, Any]]:
        """
        Builds the explicit upper-triangular QUBO matrix Q in R^{M x M} and constant c.
        Variables: x_{v, i, t} in {0, 1}
        v in {0, ..., V-1}, i in {0, ..., N-1}, t in {0, ..., T-1}
        Index bijection: u = v * (N * T) + i * T + t
        Total M = V * N * T
        """
        V = len(vehicles)
        N = len(waypoints)
        T = max_steps
        M = V * N * T

        def idx(v: int, i: int, t: int) -> int:
            return v * (N * T) + i * T + t

        Q = [[0.0 for _ in range(M)] for _ in range(M)]
        c = 0.0
        depot_id = depot["id"]

        # Helper to add upper-triangular coupling
        def add_q(u1: int, u2: int, val: float):
            if u1 == u2:
                Q[u1][u1] += val
            elif u1 < u2:
                Q[u1][u2] += val
            else:
                Q[u2][u1] += val

        # 1. Routing Distance Objective Terms
        for v in range(V):
            for i in range(N):
                wp_i_id = waypoints[i]["id"]

                # A. Depot departure at step t = 0
                u_start = idx(v, i, 0)
                add_q(u_start, u_start, dist_matrix[depot_id][wp_i_id])

                # B. Inter-destination transit from step t to step t+1
                for t in range(T - 1):
                    u_t = idx(v, i, t)
                    for j in range(N):
                        wp_j_id = waypoints[j]["id"]
                        u_next = idx(v, j, t + 1)
                        add_q(u_t, u_next, dist_matrix[wp_i_id][wp_j_id])

                # C. Depot return from terminal step
                # For t = T - 1:
                u_last = idx(v, i, T - 1)
                add_q(u_last, u_last, dist_matrix[wp_i_id][depot_id])

                # For t < T - 1: if stop t is visited and step t+1 is empty
                for t in range(T - 1):
                    u_t = idx(v, i, t)
                    d_ret = dist_matrix[wp_i_id][depot_id]
                    add_q(u_t, u_t, d_ret)
                    for j in range(N):
                        u_next = idx(v, j, t + 1)
                        add_q(u_t, u_next, -d_ret)

        # 2. Constraint 1: Destination Visitation (Every destination visited exactly once)
        # P_A * sum_{i} (sum_{v, t} x_{v, i, t} - 1)^2
        # = P_A * sum_i [ 1 - sum_{v, t} x_{v, i, t} + 2 sum_{u < w} x_u x_w ]
        for i in range(N):
            c += penalty_visit
            var_indices = [idx(v, i, t) for v in range(V) for t in range(T)]
            for u in var_indices:
                add_q(u, u, -penalty_visit)
            for a_idx in range(len(var_indices)):
                for b_idx in range(a_idx + 1, len(var_indices)):
                    add_q(var_indices[a_idx], var_indices[b_idx], 2.0 * penalty_visit)

        # 3. Constraint 2: Slot Uniqueness (At most one destination per vehicle per step)
        # P_B * sum_{v, t} sum_{i < j} x_{v, i, t} * x_{v, j, t}
        for v in range(V):
            for t in range(T):
                for i in range(N):
                    for j in range(i + 1, N):
                        u_i = idx(v, i, t)
                        u_j = idx(v, j, t)
                        add_q(u_i, u_j, penalty_slot)

        # 4. Constraint 3: Route Contiguity (No unassigned gaps in tour sequence)
        # P_C * sum_v sum_{t < T-1} [ sum_i x_{v, i, t+1} - sum_{i, j} x_{v, i, t+1} x_{v, j, t} ]
        for v in range(V):
            for t in range(T - 1):
                for i in range(N):
                    u_next = idx(v, i, t + 1)
                    add_q(u_next, u_next, penalty_contig)
                    for j in range(N):
                        u_curr = idx(v, j, t)
                        add_q(u_next, u_curr, -penalty_contig)

        # 5. Constraint 4: Vehicle Capacity Soft Penalty
        # For each vehicle, penalize high load concentrations:
        for v in range(V):
            cap_v = vehicles[v]["capacity"]
            for i in range(N):
                q_i = waypoints[i].get("demand", 10)
                for t in range(T):
                    u_i = idx(v, i, t)
                    for j in range(i + 1, N):
                        q_j = waypoints[j].get("demand", 10)
                        for t_prime in range(T):
                            u_j = idx(v, j, t_prime)
                            # Add quadratic demand coupling
                            add_q(u_i, u_j, penalty_cap * (q_i * q_j) / (cap_v ** 2))

        meta = {"num_variables": M, "num_vehicles": V, "num_destinations": N, "max_steps": T}
        return Q, c, M, meta

    def decode_binary_solution(
        self,
        x: List[int],
        depot: Dict[str, Any],
        waypoints: List[Dict[str, Any]],
        vehicles: List[Dict[str, Any]],
        max_steps: int,
        dist_matrix: Dict[str, Dict[str, float]]
    ) -> Tuple[List[Dict[str, Any]], int, Dict[str, Any]]:
        """
        Decodes binary vector x in {0, 1}^M into vehicle routes.
        Independently audits feasibility against capacity, visitation, and tour sequencing.
        """
        V = len(vehicles)
        N = len(waypoints)
        T = max_steps
        depot_id = depot["id"]

        def idx(v: int, i: int, t: int) -> int:
            return v * (N * T) + i * T + t

        visited_counts = {w["id"]: 0 for w in waypoints}
        vehicle_routes = []
        violations = 0

        for v in range(V):
            v_conf = vehicles[v]
            v_cap = v_conf["capacity"]
            v_range = v_conf.get("battery_range_km", 100.0)

            # Extract stops for this vehicle ordered by step t
            stops_by_t = []
            for t in range(T):
                active_at_t = []
                for i in range(N):
                    u = idx(v, i, t)
                    if x[u] == 1:
                        active_at_t.append(waypoints[i])
                        visited_counts[waypoints[i]["id"]] += 1

                if len(active_at_t) > 1:
                    # Slot collision violation
                    violations += (len(active_at_t) - 1)
                if active_at_t:
                    stops_by_t.extend(active_at_t)

            dist_km = self._route_distance(depot_id, stops_by_t, dist_matrix)
            load = sum(st.get("demand", 0) for st in stops_by_t)
            energy_kwh = round(dist_km * v_conf.get("energy_rate_kwh_per_km", 0.22), 3)

            is_feasible = (load <= v_cap) and (dist_km <= v_range)
            if not is_feasible:
                violations += 1

            stop_seq = [{"type": "depot", **depot}] + \
                       [{"type": "waypoint", **st} for st in stops_by_t] + \
                       [{"type": "depot", **depot}]

            vehicle_routes.append({
                "vehicle_id": v_conf["id"],
                "vehicle_name": v_conf.get("name", v_conf["id"]),
                "stop_sequence": stop_seq,
                "total_distance_km": dist_km,
                "total_energy_kwh": energy_kwh,
                "total_demand_delivered": load,
                "capacity_utilized_percent": round((load / v_cap) * 100.0, 1),
                "feasible": is_feasible
            })

        # Check coverage
        unserved = sum(1 for c in visited_counts.values() if c == 0)
        duplicates = sum(c - 1 for c in visited_counts.values() if c > 1)
        violations += (unserved + duplicates)

        audit = {
            "unserved_destinations": unserved,
            "duplicate_visits": duplicates,
            "visited_counts": visited_counts
        }

        return vehicle_routes, violations, audit

    def solve_qubo_simulated_annealing(
        self,
        depot: Dict[str, Any],
        waypoints: List[Dict[str, Any]],
        vehicles: List[Dict[str, Any]],
        dist_matrix: Dict[str, Dict[str, float]],
        iterations: int = 1000,
        initial_temp: float = 100.0,
        cooling_rate: float = 0.985,
        seed: Optional[int] = None,
        max_steps: Optional[int] = None
    ) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Method C: QUBO Formulation solved with Simulated Annealing on binary decision variables.
        """
        rng = random.Random(seed if seed is not None else 42)
        start_time = time.perf_counter()

        T = max_steps or min(len(waypoints), 4)
        Q, c_const, M, meta = self.build_qubo_matrix(
            depot=depot,
            waypoints=waypoints,
            vehicles=vehicles,
            max_steps=T,
            dist_matrix=dist_matrix
        )

        # Initial solution: construct a valid greedy allocation mapped to binary vector x
        x = [0] * M
        # Distribute waypoints sequentially to vehicles across steps
        for idx_w, wp in enumerate(waypoints):
            v = idx_w % len(vehicles)
            t = (idx_w // len(vehicles)) % T
            u = v * (len(waypoints) * T) + idx_w * T + t
            x[u] = 1

        # Calculate initial energy E = x^T Q x + c
        def compute_energy(state: List[int]) -> float:
            energy = c_const
            for u in range(M):
                if state[u]:
                    energy += Q[u][u]
                    for w in range(u + 1, M):
                        if state[w]:
                            energy += Q[u][w]
            return energy

        current_energy = compute_energy(x)
        best_x = list(x)
        best_energy = current_energy

        temp = initial_temp
        convergence_history = []
        sample_step = max(1, iterations // 25)

        for step in range(iterations):
            # Single bit-flip proposal
            u = rng.randrange(M)

            # Compute delta E efficiently
            # If x_u flips: delta_x = 1 - 2*x_u (+1 if 0->1, -1 if 1->0)
            delta_x = 1 - 2 * x[u]
            row_sum = 0.0
            for w in range(u):
                if x[w]:
                    row_sum += Q[w][u]
            for w in range(u + 1, M):
                if x[w]:
                    row_sum += Q[u][w]

            delta_e = delta_x * (Q[u][u] + row_sum)

            if delta_e < 0.0 or rng.random() < math.exp(-delta_e / max(1e-6, temp)):
                x[u] = 1 - x[u]
                current_energy += delta_e
                if current_energy < best_energy:
                    best_energy = current_energy
                    best_x = list(x)

            temp *= cooling_rate

            if step % sample_step == 0 or step == iterations - 1:
                convergence_history.append({
                    "iteration": step,
                    "temperature": round(temp, 3),
                    "current_energy": round(current_energy, 2),
                    "best_energy": round(best_energy, 2)
                })

        exec_ms = round((time.perf_counter() - start_time) * 1000.0, 2)

        # Decode binary solution
        vehicle_routes, violations, audit = self.decode_binary_solution(
            best_x, depot, waypoints, vehicles, T, dist_matrix
        )

        total_dist = round(sum(r["total_distance_km"] for r in vehicle_routes), 3)
        total_energy = round(sum(r["total_energy_kwh"] for r in vehicle_routes), 3)
        travel_time_hours = round(total_dist / 40.0, 2)
        all_feasible = (violations == 0) and all(r["feasible"] for r in vehicle_routes)
        objective_value = round(total_dist + (violations * 100.0), 3)

        max_dist = max((r["total_distance_km"] for r in vehicle_routes), default=0.0)
        result = {
            "method": "qubo_sa",
            "method_name": "Method C — QUBO Formulation + Simulated Annealing Solver",
            "routes": vehicle_routes,
            "total_distance_km": total_dist,
            "total_energy_kwh": total_energy,
            "estimated_travel_time_hours": travel_time_hours,
            "objective_value": objective_value,
            "execution_time_ms": exec_ms,
            "max_route_distance_km": max_dist,
            "all_feasible": all_feasible,
            "constraint_violations": violations,
            "route_variance_km": round(sum((r["total_distance_km"] - (total_dist / len(vehicles)))**2 for r in vehicle_routes) / max(1, len(vehicles)), 2),
            "qubo_energy_score": round(best_energy, 2),
            "audit": audit
        }

        return result, convergence_history

    # --------------------------------------------------------------------------
    # Brute Force Exact Solver for Ground-Truth Validation (M <= 16)
    # --------------------------------------------------------------------------
    def solve_brute_force_exact(
        self,
        depot: Dict[str, Any],
        waypoints: List[Dict[str, Any]],
        vehicles: List[Dict[str, Any]],
        max_steps: int,
        dist_matrix: Dict[str, Dict[str, float]]
    ) -> Dict[str, Any]:
        """
        Exhaustively evaluates all 2^M binary states to find the true global minimum.
        Used to mathematically validate the QUBO formulation on small scenarios.
        """
        start_time = time.perf_counter()
        Q, c_const, M, meta = self.build_qubo_matrix(
            depot=depot,
            waypoints=waypoints,
            vehicles=vehicles,
            max_steps=max_steps,
            dist_matrix=dist_matrix
        )

        if M > 16:
            raise ValueError(f"Exhaustive search space too large (M={M}, states=2^{M}). Max allowed M=16.")

        total_states = 1 << M
        best_state_int = 0
        min_energy = float("inf")

        for state_int in range(total_states):
            # Compute energy
            energy = c_const
            for u in range(M):
                if (state_int >> u) & 1:
                    energy += Q[u][u]
                    for w in range(u + 1, M):
                        if (state_int >> w) & 1:
                            energy += Q[u][w]

            if energy < min_energy:
                min_energy = energy
                best_state_int = state_int

        best_x = [(best_state_int >> u) & 1 for u in range(M)]
        exec_ms = round((time.perf_counter() - start_time) * 1000.0, 2)

        routes, violations, audit = self.decode_binary_solution(
            best_x, depot, waypoints, vehicles, max_steps, dist_matrix
        )
        total_dist = round(sum(r["total_distance_km"] for r in routes), 3)

        return {
            "method": "brute_force_exact",
            "method_name": "Mathematical Ground-Truth (Exhaustive Brute-Force)",
            "num_evaluated_states": total_states,
            "min_qubo_energy": round(min_energy, 3),
            "best_bitstring": "".join(str(b) for b in best_x),
            "total_distance_km": total_dist,
            "constraint_violations": violations,
            "all_feasible": (violations == 0),
            "routes": routes,
            "execution_time_ms": exec_ms
        }

    # --------------------------------------------------------------------------
    # Multi-Trial Experiment Benchmark Runner
    # --------------------------------------------------------------------------
    def run_multi_trial_experiment(
        self,
        scenario: str = "small",
        num_vehicles: Optional[int] = None,
        num_destinations: Optional[int] = None,
        method: str = "all_comparative",
        trials: int = 1,
        random_seed: int = 42,
        sa_iterations: int = 1000,
        sa_initial_temp: float = 100.0,
        sa_cooling_rate: float = 0.985,
        penalty_visit: float = 150.0,
        penalty_slot: float = 120.0,
        penalty_contig: float = 80.0,
        penalty_cap: float = 100.0,
        include_brute_force: bool = False
    ) -> Dict[str, Any]:
        """
        Executes repeatable multi-trial benchmark across Method A, B, and C.
        Computes median runtime, P95 runtime, mean objective, std deviation, and feasibility %.
        """
        # Resolve scenario data
        if scenario in STANDARDIZED_SCENARIOS:
            sc_info = STANDARDIZED_SCENARIOS[scenario]
            vehicles = sc_info["vehicles"]
            waypoints = sc_info["waypoints"]
            max_steps = sc_info["max_steps"]
        else:
            nv = num_vehicles or 3
            nd = num_destinations or 5
            vehicles = DEFAULT_VEHICLES[:nv]
            waypoints = DEFAULT_CHENNAI_WAYPOINTS[:nd]
            max_steps = min(nd, 4)

        if num_vehicles is not None and num_vehicles <= len(DEFAULT_VEHICLES):
            vehicles = DEFAULT_VEHICLES[:num_vehicles]
        if num_destinations is not None and num_destinations <= len(DEFAULT_CHENNAI_WAYPOINTS):
            waypoints = DEFAULT_CHENNAI_WAYPOINTS[:num_destinations]

        depot = DEFAULT_CHENNAI_DEPOT
        dist_matrix = self._build_distance_matrix(depot, waypoints)

        methods_to_run = []
        if method == "all_comparative":
            methods_to_run = ["greedy", "classical_sa", "qubo_sa"]
        elif method in ["greedy", "classical_sa", "qubo_sa"]:
            methods_to_run = [method]
        else:
            methods_to_run = ["greedy", "classical_sa", "qubo_sa"]

        all_trial_records = []
        methods_summary = {}

        for m_name in methods_to_run:
            m_trials = []
            convergence_sample = None

            for t_num in range(1, trials + 1):
                trial_seed = random_seed + t_num

                if m_name == "greedy":
                    res = self.solve_greedy_routing(depot, waypoints, vehicles, dist_matrix)
                elif m_name == "classical_sa":
                    res, conv = self.solve_classical_simulated_annealing(
                        depot, waypoints, vehicles, dist_matrix,
                        iterations=sa_iterations,
                        initial_temp=sa_initial_temp,
                        cooling_rate=sa_cooling_rate,
                        seed=trial_seed
                    )
                    if convergence_sample is None:
                        convergence_sample = conv
                elif m_name == "qubo_sa":
                    res, conv = self.solve_qubo_simulated_annealing(
                        depot, waypoints, vehicles, dist_matrix,
                        iterations=sa_iterations,
                        initial_temp=sa_initial_temp,
                        cooling_rate=sa_cooling_rate,
                        seed=trial_seed,
                        max_steps=max_steps
                    )
                    if convergence_sample is None:
                        convergence_sample = conv

                trial_record = {
                    "trial_number": t_num,
                    "method": m_name,
                    "objective_value": res["objective_value"],
                    "total_distance": res["total_distance_km"],
                    "estimated_travel_time": res["estimated_travel_time_hours"],
                    "execution_time_ms": res["execution_time_ms"],
                    "feasibility_status": res["all_feasible"],
                    "constraint_violations": res["constraint_violations"],
                    "solution_data": {
                        "routes": res["routes"],
                        "total_energy_kwh": res["total_energy_kwh"],
                        "route_variance_km": res["route_variance_km"]
                    }
                }
                m_trials.append(trial_record)
                all_trial_records.append(trial_record)

            # Compute statistical summaries for method
            obj_vals = [t["objective_value"] for t in m_trials]
            dists = [t["total_distance"] for t in m_trials]
            times = [t["execution_time_ms"] for t in m_trials]
            feasibles = [t["feasibility_status"] for t in m_trials]
            viols = [t["constraint_violations"] for t in m_trials]

            times_sorted = sorted(times)
            p95_idx = max(0, min(len(times_sorted) - 1, int(0.95 * len(times_sorted))))
            median_idx = len(times_sorted) // 2
            median_time = times_sorted[median_idx]
            p95_time = times_sorted[p95_idx]

            mean_obj = sum(obj_vals) / len(obj_vals)
            variance_obj = sum((x - mean_obj)**2 for x in obj_vals) / max(1, len(obj_vals))
            std_obj = math.sqrt(variance_obj)

            best_trial = min(m_trials, key=lambda t: t["objective_value"])

            methods_summary[m_name] = {
                "method": m_name,
                "method_name": {
                    "greedy": "Method A — Conventional Greedy Routing",
                    "classical_sa": "Method B — Classical Simulated Annealing",
                    "qubo_sa": "Method C — QUBO + Simulated Annealing Solver"
                }.get(m_name, m_name),
                "trial_count": len(m_trials),
                "feasibility_percentage": round((sum(1 for f in feasibles if f) / len(feasibles)) * 100.0, 1),
                "best_objective": round(min(obj_vals), 3),
                "mean_objective": round(mean_obj, 3),
                "std_objective": round(std_obj, 3),
                "mean_distance_km": round(sum(dists) / len(dists), 3),
                "mean_travel_time_min": round((sum(dists) / len(dists)) * 1.5, 1),
                "median_runtime_ms": round(median_time, 2),
                "p95_runtime_ms": round(p95_time, 2),
                "mean_violations": round(sum(viols) / len(viols), 2),
                "best_solution_routes": best_trial["solution_data"]["routes"],
                "convergence_history": convergence_sample
            }

        # Optional Brute Force Ground Truth
        brute_force_result = None
        M_calc = len(vehicles) * len(waypoints) * max_steps
        if include_brute_force and M_calc <= 14:
            try:
                brute_force_result = self.solve_brute_force_exact(
                    depot=depot,
                    waypoints=waypoints,
                    vehicles=vehicles,
                    max_steps=max_steps,
                    dist_matrix=dist_matrix
                )
            except Exception:
                pass

        return {
            "scenario_name": scenario,
            "vehicle_count": len(vehicles),
            "destination_count": len(waypoints),
            "method": method,
            "random_seed": random_seed,
            "solver_parameters": {
                "trials": trials,
                "sa_iterations": sa_iterations,
                "sa_initial_temp": sa_initial_temp,
                "sa_cooling_rate": sa_cooling_rate,
                "penalty_visit": penalty_visit,
                "penalty_slot": penalty_slot,
                "penalty_contig": penalty_contig,
                "penalty_cap": penalty_cap,
                "max_steps": max_steps,
                "num_qubo_variables": M_calc
            },
            "depot": depot,
            "destinations": waypoints,
            "vehicles": vehicles,
            "methods_summary": methods_summary,
            "trials": all_trial_records,
            "brute_force_exact": brute_force_result,
            "created_at": datetime.utcnow()
        }

    # Backward compatibility benchmark runner
    def run_optimization_benchmark(
        self,
        depot: Optional[Dict[str, Any]] = None,
        waypoints: Optional[List[Dict[str, Any]]] = None,
        vehicles: Optional[List[Dict[str, Any]]] = None,
        sa_iterations: int = 1000,
        sa_initial_temp: float = 100.0,
        sa_cooling_rate: float = 0.985,
        scenario: str = "urban_delivery"
    ) -> Dict[str, Any]:
        """Runs standard comparative run between Classical Greedy and QUBO / SA."""
        depot = depot or DEFAULT_CHENNAI_DEPOT
        waypoints = waypoints or DEFAULT_CHENNAI_WAYPOINTS
        vehicles = vehicles or DEFAULT_VEHICLES

        dist_matrix = self._build_distance_matrix(depot, waypoints)

        classical = self.solve_greedy_routing(depot, waypoints, vehicles, dist_matrix)
        qubo, convergence = self.solve_qubo_simulated_annealing(
            depot, waypoints, vehicles, dist_matrix,
            iterations=sa_iterations,
            initial_temp=sa_initial_temp,
            cooling_rate=sa_cooling_rate,
            seed=42
        )

        dist_diff = classical["total_distance_km"] - qubo["total_distance_km"]
        dist_reduction_pct = round((dist_diff / max(1e-4, classical["total_distance_km"])) * 100.0, 2)
        energy_diff = classical["total_energy_kwh"] - qubo["total_energy_kwh"]
        energy_savings_pct = round((energy_diff / max(1e-4, classical["total_energy_kwh"])) * 100.0, 2)

        differential_kpis = {
            "distance_saved_km": round(dist_diff, 3),
            "distance_reduction_percent": dist_reduction_pct,
            "energy_saved_kwh": round(energy_diff, 3),
            "energy_savings_percent": energy_savings_pct,
            "load_balance_improvement": "Superior" if qubo["route_variance_km"] <= classical["route_variance_km"] else "Comparable",
            "classical_time_ms": classical["execution_time_ms"],
            "qubo_time_ms": qubo["execution_time_ms"],
            "valid_solution": qubo["all_feasible"]
        }

        return {
            "scenario": scenario,
            "num_vehicles": len(vehicles),
            "num_waypoints": len(waypoints),
            "depot": depot,
            "classical_heuristic": classical,
            "qubo_simulated_annealing": qubo,
            "differential_kpis": differential_kpis,
            "convergence_history": convergence
        }


qubo_routing_service = QuboRoutingService()
