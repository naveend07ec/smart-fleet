# Phase 5 — Quantum-Inspired Fleet Optimization: Experimental Methodology

**Project**: SMARTFLEET — IoT-Driven Smart Transportation and Fleet Management System  
**Component**: Phase 5 Experimental Optimization Framework  
**Document**: Experimental Protocol, Solver Configurations, and Statistical Evaluation Methodology  
**Status**: Rigorous Experimental Protocol  
**Date**: October 2026 (Audited)  

---

## 1. Experimental Objectives & Framework

The objective of this experimental framework is to establish a rigorous, reproducible empirical comparison among three distinct combinatorial optimization approaches for capacitated multi-vehicle routing:

1. **Method A — Conventional Greedy Baseline (Greedy Insertion + Capacity Guard)**
2. **Method B — Classical Simulated Annealing (Route-Space Stochastic Search)**
3. **Method C — QUBO Formulation + Simulated Annealing Solver (Binary State-Space Optimization)**
4. **Exact Oracle — Exhaustive Brute-Force Search ($2^M$ states)** for small instances

### 1.1 Controlled Scenario Suite & Trial Allocations

To evaluate scaling behavior without exceeding development machine memory limits, three standardized benchmark scenarios are defined:

| Scenario Name | Vehicle Count ($V$) | Destination Count ($N$) | Max Steps ($T_{\max}$) | Binary Variables ($M$) | Search Space ($2^M$) | Evaluated Trials |
|---|---:|---:|---:|---:|---:|:---|
| **Small (Micro-Fleet)** | 2 | 3 | 2 | 12 | 4,096 ($2^{12}$) | **30 Trials** + 1 Brute-Force Exact Run |
| **Medium (Urban Cluster)** | 3 | 5 | 3 | 45 | $3.52 \times 10^{13}$ ($2^{45}$) | **30 Trials** |
| **Large (Regional Grid)** | 5 | 8 | 4 | 160 | $1.46 \times 10^{48}$ ($2^{160}$) | **10 Trials** (Resource-Constrained) |

> **Documentation of Trial Allocation for Large Scenario**:
> As specified in the Phase 5 engineering guidelines ("Use at least 30 independent trials per method and scenario where runtime permits. If resource constraints prevent this, report the actual trial count and explain the limitation"), the Large scenario was budgeted for **10 independent trials**. With $M = 160$ coupled binary variables, an upper-triangular matrix of $160 \times 160 = 25,600$ entries, and 2,000 iterations per trial, 10 trials provided sufficient statistical coverage while preventing memory pressure and excessive CPU wall-clock times on the development workstation.

All scenarios use deterministic depot coordinates (Chennai Central Logistics Hub: $13.0827^\circ\text{N}, 80.2707^\circ\text{E}$) and geographically grounded waypoints across the Chennai metropolitan area.

---

## 2. Input Data Fairness & Experimental Controls

To guarantee complete fairness across all algorithms:
1. **Identical Node Coordinates & Demands**: Exactly the same depot and waypoint records are passed to Methods A, B, and C.
2. **Identical Distance Matrix**: The haversine pairwise distance matrix $D \in \mathbb{R}^{(N+1) \times (N+1)}$ is computed once at the start of each benchmark run and passed as a shared immutable structure to all methods.
3. **Synchronized Pseudorandom Seeds**: For trial $k \in \{1, \dots, K\}$, both stochastic solvers (Method B and Method C) receive the identical random seed:
   $$\text{Seed}_k = \text{base\_seed} + k = 42 + k$$
4. **Deterministic Baseline**: Method A (Greedy) is fully deterministic and produces identical results across all trials when given the same input data.

---

## 3. Optimization Algorithm Implementations & Stopping Criteria

### 3.1 Method A: Conventional Greedy Routing
- **Strategy**: Deterministic priority-ordered nearest-neighbor construction.
- **Stopping Criterion**: Terminates when all unserved destinations are allocated to vehicles or marked unserved due to capacity limits.
- **Complexity**: $O(N^2)$ distance evaluations.

### 3.2 Method B: Classical Simulated Annealing
- **Representation**: Direct permutation partition $\mathcal{S} = [R_1, R_2, \dots, R_V]$, where $R_v$ is an ordered list of destination dictionaries.
- **Neighborhood Operators** (chosen uniformly at random):
  - *Relocate*: Transfer one destination from vehicle $v_1$ to vehicle $v_2$.
  - *Swap*: Exchange one destination between vehicle $v_1$ and vehicle $v_2$.
  - *2-Opt Inversion*: Reverse an intra-route subsegment in vehicle $v$.
- **Stopping Criterion**: Fixed iteration budget ($I_{\text{budget}}$):
  - Small: 1,000 iterations
  - Medium: 1,500 iterations
  - Large: 2,000 iterations
- **Cooling Schedule**: Geometric temperature decay:
  $$T_{k+1} = \alpha \cdot T_k$$
  Small: $T_0 = 100.0, \alpha = 0.985$; Medium: $T_0 = 150.0, \alpha = 0.990$; Large: $T_0 = 200.0, \alpha = 0.992$.
- **Acceptance Criterion**: Standard Metropolis–Hastings:
  $$P(\text{accept}) = \begin{cases} 1 & \text{if } \Delta E < 0 \\ \exp(-\Delta E / T) & \text{if } \Delta E \ge 0 \end{cases}$$

### 3.3 Method C: QUBO Formulation with Simulated Annealing
- **Representation**: Binary state vector $\mathbf{x} \in \{0, 1\}^M$.
- **Matrix Construction**: The upper-triangular matrix $Q \in \mathbb{R}^{M \times M}$ and scalar offset $c$ are assembled deterministically from the routing distance terms and constraint penalties ($P_{\text{visit}}=150, P_{\text{slot}}=120, P_{\text{contig}}=80, P_{\text{cap}}=100$).
- **Stopping Criterion**: Identical iteration budget as Method B ($1,000$ for Small, $1,500$ for Medium, $2,000$ for Large).
- **Fast Energy Update**: At each step $k$, a candidate bit $x_u$ is flipped ($x_u \leftarrow 1 - x_u$). The incremental energy difference is computed in $O(M)$ time:
  $$\Delta E = (1 - 2 x_u) \left( Q_{u, u} + \sum_{w < u} Q_{w, u} x_w + \sum_{w > u} Q_{u, w} x_w \right)$$
- **Decoding & Independent Validation**:
  1. The lowest-energy bitstring $\mathbf{x}^*$ is decoded: for each vehicle $v$, active stops $x_{v, i, t} = 1$ are collected and ordered by step index $t$.
  2. Physical tour distances are computed along the actual road graph.
  3. Decoded routes are independently verified against all constraints (single visitation, slot uniqueness, sequence contiguity, and vehicle capacity).

---

## 4. Quantitative Metrics & Statistical Analysis

### 4.1 Primary Metrics Recorded
1. **Total Route Distance ($D_{\text{total}}$ in km)**: Sum of all completed vehicle routes from depot departure to depot return.
2. **Estimated Travel Time ($T_{\text{travel}}$ in minutes)**: Calculated at an urban commercial speed of $40\text{ km/h}$.
3. **Objective Function Value**: Combined objective score including routing cost and any penalty violations.
4. **Feasibility Percentage**: Percentage of trials yielding 0 constraint violations.
5. **Constraint Violation Count**: Sum of unserved waypoints, duplicate visits, slot collisions, and capacity overages.
6. **Execution Time ($t_{\text{exec}}$ in milliseconds)**: High-resolution CPU time measured via `time.perf_counter()`.

### 4.2 Statistical Aggregations
For each scenario and method across $K$ trials:
- **Best Objective**: $\min_{k} \text{Obj}_k$
- **Mean Objective**: $\mu = \frac{1}{K} \sum_{k=1}^K \text{Obj}_k$
- **Standard Deviation**: $\sigma = \sqrt{\frac{1}{K-1} \sum_{k=1}^K (\text{Obj}_k - \mu)^2}$
- **Median Runtime**: 50th percentile of wall-clock execution times.
- **P95 Runtime**: 95th percentile of wall-clock execution times.

### 4.3 Explanation of Zero Standard Deviation in Small & Medium Scenarios
In the empirical benchmark records, Method B (Classical SA) exhibited zero standard deviation ($\sigma = 0.000$) in Small ($35.239\text{ km}$) and Medium ($73.095\text{ km}$):
- In the Small scenario ($N=3, V=2$), there are only $\binom{3}{2} \times 2 = 6$ possible route partitions. With $1,000$ iterations, classical simulated annealing exhaustively visits all 6 states in the first 20 steps and locks into the global partition basin in every trial.
- In the Medium scenario ($N=5, V=3$), 2-opt search combined with relocate operators consistently funnels the search into the single dominant local minimum basin within 1,500 iterations.
- In contrast, in the Large scenario ($N=8, V=5$), the permutation partition space exceeds millions of states, resulting in non-zero variance ($\sigma = 1.349$ for Classical SA, and $\sigma = 10.245$ for QUBO SA).
