# Phase 4 — Blind Quantum Computing (BQC): Research Design & Protocol Specification

**Project**: IoT-Driven Smart Transportation and Fleet Management System  
**Component**: Phase 4 Privacy-Preserving Delegated Quantum Computation Subsystem  
**Document**: Research Design & Foundational Protocol Specification  
**Status**: Architecture & Design Phase (Pre-Implementation Review)  
**Date**: October 2026  

---

## 1. Review of Research Materials & Protocol Identification

### 1.1 Source Document Analysis
A review of the repository's foundational documentation (`README.md` under *Future Phases Roadmap*) reveals the following baseline entry:
> `- Phase 3 — Blind Quantum Computation (BQC) & Privacy: Exploration of delegated quantum privacy protocols for confidential telemetry processing.`
> `- Phase 4 — QUBO / Simulated Annealing Fleet Routing: Algorithmic comparison of classical heuristic routing versus Simulated Annealing / QUBO quantum-inspired optimization formulations for multi-vehicle route scheduling.`

### 1.2 Identification of Missing Information in Source Materials
While the project roadmap explicitly targets **Blind Quantum Computing (BQC)** for confidential telemetry processing and fleet decision-making, the initial documentation does not specify:
1. The exact mathematical BQC protocol (e.g., measurement-based vs. circuit-based trapdoor BQC).
2. The specific quantum client capabilities required (e.g., completely classical client, client with weak coherent state preparation, or client with single-qubit measurement).
3. The algorithmic translation between vehicular fleet telemetry and quantum circuits/cluster states.

### 1.3 Recommended Protocol: Broadbent–Fitzsimons–Kashefi (BFK09) Measurement-Based BQC
To maintain rigorous scientific standards without substituting an unrelated protocol, we recommend the canonical, peer-reviewed **Broadbent–Fitzsimons–Kashefi (BFK09) Universal Blind Quantum Computing Protocol** (adapted for client-delegated vehicular computing):
* **Foundational Reference**: A. Broadbent, J. Fitzsimons, and E. Kashefi, *"Universal Blind Quantum Computation"*, IEEE 50th Annual Symposium on Foundations of Computer Science (FOCS), 2009.
* **Why BFK09?**:
  1. It is the international benchmark for universal blind quantum computation.
  2. It supports **Universal Blindness**: The server learns *nothing* about the client's private input data, the target computation/algorithm, or the output.
  3. It permits a minimally equipped client: The vehicular client or fleet operator only needs single-qubit state preparation capabilities (or in our simulation, generates random phase-rotated classical simulation vectors), while the computationally heavy quantum processing (graph state entanglement and adaptive measurements) is delegated to an untrusted quantum cloud server.

---

## 2. Fleet Management Use Case: Confidential Multi-Depot Resource Allocation & Route Selection

### 2.1 The Problem Context
Modern fleet management frequently requires solving high-value combinatorial routing and allocation problems:
* **Confidential High-Priority Transport**: A security-sensitive or VIP fleet transport must select the optimal rendezvous depot, emergency refuge station, or EV charging facility from $M$ candidates.
* **Sensitive Fleet Variables**:
  * Vehicle real-time confidential coordinates $(x_v, y_v)$.
  * Remaining battery reserve and physical vehicle payload state.
  * Private operational cost weights and security risk levels along transit corridors.
* **The Cloud Delegation Dilemma**: Solving large-scale combinatorial optimization or minimum-finding problems requires significant computational power. While quantum optimization algorithms (e.g., Grover-style Quantum Minimum Finding / Dürr–Høyer algorithm and QAOA) promise future scaling benefits, the fleet operator **cannot trust a public quantum cloud provider** (e.g., third-party quantum server) with unencrypted telemetry coordinates, vehicle payload states, or destination goals.

### 2.2 Selected Research Use Case: Private Fleet Depot Selection via Blind Quantum Search
We define the **Private Fleet Depot & Routing Selection Problem**:
1. A fleet vehicle or dispatcher has $M \in \{2, 4\}$ candidate transit waypoints/depots.
2. The vehicle evaluates a cost function $C(i)$ based on distance, battery usage, and route congestion:
   $$C(i) = w_1 \cdot \text{dist}(\mathbf{x}_v, \mathbf{x}_i) + w_2 \cdot \text{congestion}_i + w_3 \cdot \text{energy}_i$$
   where $\mathbf{x}_v = (\text{lat}_v, \text{lon}_v)$ is the private vehicle location, $\mathbf{x}_i$ is the candidate depot location, and $w_1, w_2, w_3 \ge 0$ are confidential operational weights.
3. **Classical Reference Algorithm**:
   Exhaustively computes $\{C(0), \dots, C(M-1)\}$ and returns $i^* = \arg\min_i C(i)$.
4. **Quantum Circuit Formulation**:
   * **For $M=2$ (1 logical qubit)**:
     - Candidate encoding: $|0\rangle \to \text{Depot 0}$, $|1\rangle \to \text{Depot 1}$.
     - Cost difference parameter: $\phi = \pi \cdot \frac{C(1) - C(0)}{\Delta C_{\max}} \in [-\pi, \pi]$.
     - The circuit applies: $U = H \cdot R_z(\phi) \cdot H$.
     - Initial state: $|0\rangle$. After first Hadamard: $|+\rangle = \frac{1}{\sqrt{2}}(|0\rangle + |1\rangle)$.
     - Phase rotation: $R_z(\phi)|+\rangle = \frac{1}{\sqrt{2}}(e^{-i\phi/2}|0\rangle + e^{i\phi/2}|1\rangle)$.
     - Final Hadamard maps phase difference into computational basis probability:
       $$|\psi_{\text{final}}\rangle = \cos(\phi/2)|0\rangle - i\sin(\phi/2)|1\rangle$$
     - When $C(0) < C(1)$ ($\phi > 0$), state $|0\rangle$ is selected with dominant probability.
   * **For $M=4$ (2 logical qubits)**:
     - Candidate encoding: $|00\rangle \to \text{Depot 0}$, $|01\rangle \to \text{Depot 1}$, $|10\rangle \to \text{Depot 2}$, $|11\rangle \to \text{Depot 3}$.
     - Algorithm: **2-Qubit Grover Minimum Search**.
     - Initial state: Uniform superposition $|\psi_0\rangle = H^{\otimes 2}|00\rangle = \frac{1}{2}(|00\rangle + |01\rangle + |10\rangle + |11\rangle)$.
     - Phase Oracle $U_{\text{oracle}}$: Flips phase of the minimum-cost candidate $i^* = \arg\min_i C(i)$:
       $$U_{\text{oracle}} = I - 2|i^*\rangle\langle i^*|$$
     - Diffusion Operator $U_D$: Inversion about the mean:
       $$U_D = H^{\otimes 2}(2|00\rangle\langle 00| - I)H^{\otimes 2}$$
     - In a 4-item search space, exactly **1 Grover iteration** ($U_D U_{\text{oracle}}|\psi_0\rangle$) achieves **100% deterministic probability** ($P(i^*) = 1.0$) of measuring the optimal candidate index.

### 2.3 MBQC Graph State & Measurement Pattern Derivation
To execute this circuit within the BFK09 measurement-based protocol:
* In MBQC (Raussendorf–Briegel framework), a sequence of single-qubit projective measurements on an entangled cluster state implements unitary gate operations:
  Measuring node $j$ at angle $\alpha_j$ implements the logical gate:
  $$J(\alpha_j) = H \cdot R_z(\alpha_j) = \frac{1}{\sqrt{2}}\begin{pmatrix} 1 & e^{i\alpha_j} \\ 1 & -e^{i\alpha_j} \end{pmatrix}$$
* **Mathematical Demonstration for $M=2$ on a 4-Qubit Linear Cluster**:
  - A 4-qubit cluster state $1 - 2 - 3 - 4$ has vertices $V = \{1, 2, 3, 4\}$ and edges $E = \{(1,2), (2,3), (3,4)\}$.
  - Setting nominal measurement angles $(\alpha_1, \alpha_2, \alpha_3) = (0, \phi, 0)$ implements:
    $$J(0) J(\phi) J(0) = H (H R_z(\phi)) H = R_z(\phi) H$$
  - Measurement of the final readout node at angle $\alpha_4 = 0$ collapses the logical qubit into the computational basis.
  - Therefore, a **4-qubit linear cluster state is mathematically necessary and sufficient** to execute arbitrary 1-qubit phase-discrimination rotations.
* **Mathematical Demonstration for $M=4$ on a 6-Qubit Ladder/Star Cluster**:
  - For 2 logical qubits with a Controlled-$Z$ entangling interaction between wires, an entangled 6-qubit cluster (comprising two 3-node rails interconnected by vertical $CZ$ edges) provides the minimal topological resource state to implement the 2-qubit Grover iteration.

---

## 3. Protocol Mechanics: The BFK09 Measurement-Based Model

The delegated computation operates on a **Measurement-Based Quantum Computing (MBQC)** framework over a universal graph/cluster state $G$:

```
┌─────────────────────────────────────────────────────────────┐
│                       FLEET CLIENT                          │
│  - Holds private cost vector C = [c_0, c_1, ..., c_{M-1}]    │
│  - Selects secret random phase angles: θ_j ∈ {0, π/4, ..., 7π/4} │
│  - Selects secret random binary one-time pads: r_j ∈ {0, 1} │
└──────────────┬──────────────────────────────▲───────────────┘
               │                              │
  Single-qubit states /        Measurement results:
  Blind angles δ_j             s_j' ∈ {0, 1}
               │                              │
┌──────────────▼──────────────────────────────┴───────────────┐
│              UNTRUSTED QUANTUM CLOUD SERVER                 │
│  - Entangles qubits into a 2D brickwork graph state G       │
│  - Receives blinded measurement angles:                     │
│      δ_j = φ_j' + θ_j + π · r_j                             │
│  - Performs adaptive projective measurements on G           │
│  - Learns ZERO information about target circuit or data     │
└─────────────────────────────────────────────────────────────┘
```

### 3.1 Step-by-Step Execution Protocol

1. **Client State Preparation & Blinding**:
   For each physical site $j$ in the computation graph $G$:
   * Client randomly samples a secret blinding phase $\theta_j \in \Theta = \left\{0, \frac{\pi}{4}, \frac{2\pi}{4}, \dots, \frac{7\pi}{4}\right\}$.
   * Client creates the blinded state $|\theta_j\rangle = \frac{1}{\sqrt{2}}(|0\rangle + e^{i\theta_j}|1\rangle)$.
   * Client transmits the stream of blinded single qubits to the quantum server.

2. **Server Entanglement**:
   * The server receives the single qubits and applies Controlled-$Z$ ($CZ$) entangling gates according to the graph structure $G$:
     $$CZ = |0\rangle\langle 0| \otimes I + |1\rangle\langle 1| \otimes Z$$
   * The server creates an entangled resource graph state without knowing the underlying individual states.

3. **Interactive Blind Measurement Loop**:
   For each measurement step $j = 1, \dots, N$:
   * The client determines the nominal algorithm angle $\phi_j$ required for the quantum search logic.
   * The client updates the angle based on past measurement outcomes to compensate for the byproduct Pauli operators ($X_X$ and $Z$ feedforward corrections):
     $$\phi_j' = (-1)^{s_j^X} \phi_j + s_j^Z \pi$$
   * The client blinds the angle using their secret $\theta_j$ and a secret random bit $r_j \in \{0, 1\}$:
     $$\delta_j = \phi_j' + \theta_j + \pi \cdot r_j$$
   * The client sends $\delta_j$ to the server.
   * The server measures qubit $j$ in the basis:
     $$\{|+_{\delta_j}\rangle, |-_{\delta_j}\rangle\} = \left\{\frac{1}{\sqrt{2}}(|0\rangle + e^{i\delta_j}|1\rangle), \frac{1}{\sqrt{2}}(|0\rangle - e^{i\delta_j}|1\rangle)\right\}$$
   * The server sends the raw measurement outcome $b_j \in \{0, 1\}$ back to the client.

4. **Client Outcome Unpadding**:
   * The client unpads the measurement outcome:
     $$s_j = b_j \oplus r_j$$
   * The server's view is statistically independent of $\phi_j$, the input data, and the output, because $\delta_j$ is one-time padded by $\theta_j$ and $r_j$.

---

## 4. Mode Comparison: Baseline (Mode A) vs. BQC (Mode B)

To scientifically evaluate Phase 4, we define two directly comparable modes:

### Mode A: Conventional Classical Optimization Baseline
* **Workflow**: The fleet vehicle transmits plaintext telemetry and cost parameters to a conventional classical server.
* **Algorithm**: Standard classical branch-and-bound or linear exhaustive search over the $M$ candidate depots.
* **Privacy Property**: **None**. The computing server has full visibility into vehicle coordinates, candidate costs, weights, and the resulting optimal depot.
* **Performance Profile**: High speed (sub-millisecond for small $M$), minimal communication overhead, zero privacy preservation.

### Mode B: BQC Privacy-Preserving Quantum Simulation
* **Workflow**: The client blinds the problem instance into an $N$-qubit cluster-state computation. The untrusted quantum server simulator executes entangling operations and adaptive projective measurements driven by client blinded angles $\delta_j$.
* **Algorithm**: Quantum search / minimum selection over candidate depots mapped to cluster-state measurement patterns.
* **Privacy Property**: **Universal Blindness**. The server's observed transcripts $(\delta_1, \dots, \delta_N)$ and $(b_1, \dots, b_N)$ have maximum entropy and are statistically independent of the fleet inputs and outputs.
* **Performance Profile**: Increased latency (interactive round-trips for adaptive angles), communication overhead from angle transmissions, full privacy preservation.

---

## 5. Privacy Evaluation & Information Leakage Categorization

In accordance with rigorous cryptographic evaluation, our privacy assessment distinguishes five distinct levels of information visibility:

### 5.1 Categorization of Information Visibility

1. **Measurement-Angle Distribution**:
   * The server observes a sequence of measurement angles $\boldsymbol{\delta} = [\delta_1, \dots, \delta_N]$.
   * Because each $\delta_j = \phi_j' + \theta_j + \pi r_j$ is shifted by uniformly random secret $\theta_j \in \Theta$ and one-time padded by $r_j \in \{0, 1\}$, the marginal distribution $P(\delta_j)$ is uniform across $\Theta$.
   * We measure **empirical Shannon entropy**: $H(\boldsymbol{\delta}) \approx 3.0$ bits per angle.
2. **Server-Observable Metadata Leakage**:
   * What the server *can* observe from operational telemetry:
     - Number of qubits $N$ and graph connectivity $G$.
     - Number of interactive measurement steps.
     - Timestamp and network packet sizes.
   * In a naive implementation, knowing $N=4$ reveals that the client is evaluating a 2-candidate decision rather than an 8-candidate decision.
3. **Allowed Protocol Leakage**:
   * In the standard BFK09 model, the **computation graph topology $G$ and circuit depth** are treated as *allowed public leakage* unless the client pads the graph with dummy/decoy vertices.
   * Our documentation explicitly acknowledges this: the server knows the graph topology $G$, but learns zero information about the algorithm angles or inputs executed on that graph.
4. **Private Input & Output Leakage**:
   * The server's transcript consists solely of $(\boldsymbol{\delta}, \mathbf{b})$.
   * Since $\mathbf{b}$ is masked by random pad $\mathbf{r}$ and $\boldsymbol{\delta}$ is masked by $\boldsymbol{\theta}$ and $\mathbf{r}$, the mutual information between the server's transcript and the private fleet inputs $C(i)$ or output $i^*$ is mathematically zero:
     $$I(\text{Input } C; \text{Server Transcript } (\boldsymbol{\delta}, \mathbf{b})) = 0$$
5. **Empirical Transcript Distinguishability Testing**:
   * To experimentally evaluate privacy, we generate ensembles of server transcripts under two diametrically opposite fleet inputs:
     - Input Case 1: Minimum at Depot 0 ($i^* = 0$).
     - Input Case 2: Minimum at Depot 1 ($i^* = 1$).
   * We evaluate the **Total Variation Distance (TVD)** and **Kolmogorov–Smirnov (KS) statistic** between the server's angle distributions:
     $$D_{TV}(P_{\boldsymbol{\delta}|i^*=0}, P_{\boldsymbol{\delta}|i^*=1}) = \frac{1}{2} \sum_{\delta} |P(\delta|i^*=0) - P(\delta|i^*=1)| \to 0$$
   * A TVD near zero confirms that the server cannot distinguish which depot was selected from its observed transcripts.

### 5.2 Critical Limitations & Non-Claims
> [!IMPORTANT]
> **Academic Integrity & Scientific Constraints**:
> 1. **No Physical Quantum Advantage**: A classical simulation of a quantum computer on an $x86\_64$ CPU does **not** provide quantum speedup. It requires exponential classical memory $O(2^n)$ as qubit count grows.
> 2. **Finite Simulation vs. Mathematical Proof**: Passing empirical statistical tests (high angle entropy and low TVD across $N=30$ runs) demonstrates the correctness of the protocol simulation, but does **not** replace or constitute an unconditional mathematical proof of universal blindness.
> 3. **Verification (Verifiability)**: BFK09 provides blindness. To detect an active cheating server (who intentionally deviates from instructions), trap qubits must be embedded. In Phase 4, we focus primarily on **blindness**, with trap-based verification documented as an experimental metric.

---

## 6. Implementation Deliverables Outline

The complete Phase 4 design consists of three formal specification artifacts:
1. [`docs/phase-4-bqc-research-design.md`](file:///d:/students%20projects/iot-trasnport/docs/phase-4-bqc-research-design.md) (this document) — Research foundation, protocol specification, and use case.
2. [`docs/phase-4-bqc-architecture.md`](file:///d:/students%20projects/iot-trasnport/docs/phase-4-bqc-architecture.md) — Architectural component separation, database schema, and API contracts.
3. [`docs/phase-4-bqc-experimental-methodology.md`](file:///d:/students%20projects/iot-trasnport/docs/phase-4-bqc-experimental-methodology.md) — Scientific hypotheses, metrics, trial batches, and UI design.
