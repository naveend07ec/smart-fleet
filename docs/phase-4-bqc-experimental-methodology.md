# Phase 4 — Blind Quantum Computing (BQC): Experimental Methodology & Evaluation Protocol

**Project**: IoT-Driven Smart Transportation and Fleet Management System  
**Component**: Phase 4 Privacy-Preserving Delegated Quantum Computation Subsystem  
**Document**: Experimental Methodology, Statistical Hypotheses, and Evaluation Protocol  
**Status**: Architecture & Design Phase (Pre-Implementation Review)  
**Date**: October 2026  

---

## 1. Experimental Objectives & Research Hypotheses

Phase 4 evaluates the trade-offs between **conventional plaintext computation** (Mode A) and **Blind Quantum Computing simulation** (Mode B) in a delegated fleet management optimization context.

### Formal Scientific Hypotheses

* **Hypothesis $H_1$ (Correctness Preservation)**:
  The simulated BFK09 Measurement-Based Blind Quantum Computing protocol produces identical optimal depot assignments ($i^*_{BQC} = i^*_{classical}$) to conventional classical search with $100.0\%$ algorithmic fidelity under noiseless state evolution.

* **Hypothesis $H_2$ (Universal Blindness & Information Isolation)**:
  The information accessible to the untrusted quantum cloud server (the sequence of measurement angles $\boldsymbol{\delta} = [\delta_1, \dots, \delta_N]$ and raw bit results $\mathbf{b} = [b_1, \dots, b_N]$) exhibits maximal Shannon entropy ($H(\boldsymbol{\delta}) \approx \log_2(|\Theta|) = 3.0$ bits per angle) and is statistically independent of the vehicle's private coordinates and depot cost parameters.

* **Hypothesis $H_3$ (Protocol Overhead Characterization)**:
  Delegating computation blindly via BQC introduces quantifiable latency and communication wire overhead compared to classical processing:
  * Wire expansion overhead of approximately $+400\%$ to $+600\%$ due to step-by-step interactive angle transmission and one-time padding.
  * Protocol execution latency bounded within realistic interactive bounds ($< 50 \text{ ms}$ for 3–5 qubit simulations).

---

## 2. Experimental Scenarios & Test Grid

To avoid single-point bias, experiments will be evaluated across a structured test matrix:

| Scenario ID | Name | Candidate Depots ($M$) | Simulated Qubits ($N$) | Graph Topology | Objective |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **SC-01** | **Micro Fleet (2 Depots)** | $M = 2$ | 2 Qubits | Linear Cluster | Minimal 1-qubit search baseline |
| **SC-02** | **Standard Fleet (4 Depots)** | $M = 4$ | 4 Qubits | 1D Brickwork Cluster | Primary experimental benchmark |
| **SC-03** | **Extended Fleet (8 Depots)** | $M = 8$ | 6 Qubits | 2D Cluster State | Scalability & communication expansion |
| **SC-04** | **Adversarial Server Audit** | $M = 4$ | 4 Qubits | 1D Brickwork Cluster | Empirical privacy leakage test |

---

## 3. Measurable Metrics & Mathematical Definitions

All measurements will be recorded in PostgreSQL (`bqc_trials` table) using microsecond-precision hardware timers (`time.perf_counter()`).

### 3.1 Computational Latency Metrics
1. **Client Preparation Latency ($T_{\text{client}}$)**:
   Time required for the client to generate secret angles $\theta_j$, sample one-time pads $r_j$, and construct initial blinded angles:
   $$T_{\text{client}} = t_{\text{prep\_end}} - t_{\text{prep\_start}} \quad (\text{ms})$$

2. **Server Quantum State Latency ($T_{\text{server}}$)**:
   Time required for the simulated quantum server to construct the graph state $|G\rangle = \left(\prod CZ\right) |+\rangle^{\otimes N}$ and evaluate projective measurement operators:
   $$T_{\text{server}} = \sum_{j=1}^N (t_{\text{meas\_end}, j} - t_{\text{meas\_start}, j}) \quad (\text{ms})$$

3. **Total Round-Trip Latency ($T_{\text{total}}$)**:
   $$T_{\text{total}} = T_{\text{client}} + T_{\text{server}} + T_{\text{feedforward\_unpad}} \quad (\text{ms})$$

### 3.2 Communication Wire Overhead
1. **Client-to-Server Payload ($B_{C \to S}$)**:
   Sum of raw JSON wire bytes for transmitting blinded measurement angles $\delta_j$ and execution directives.
2. **Server-to-Client Payload ($B_{S \to C}$)**:
   Sum of raw JSON wire bytes for returning raw measurement bits $b_j$.
3. **Total Wire Overhead ($\Delta B$) & Expansion Ratio ($E_{\text{wire}}$)**:
   $$\Delta B = (B_{C \to S} + B_{S \to C}) - B_{\text{classical}} \quad (\text{Bytes})$$
   $$E_{\text{wire}} = \left(\frac{B_{C \to S} + B_{S \to C}}{B_{\text{classical}}} - 1\right) \times 100\%$$

### 3.3 Privacy & Information-Theoretic Metrics
1. **Shannon Entropy of Transmitted Angles**:
   For an ensemble of transmitted angles $\delta \in \Theta$, the empirical Shannon entropy is measured across trials:
   $$H(\delta) = -\sum_{k=1}^K p(\delta_k) \log_2 p(\delta_k)$$
   For a perfectly blind protocol with $\Theta = \{0, \frac{\pi}{4}, \dots, \frac{7\pi}{4}\}$ ($K=8$), the theoretical maximum is $H_{\max} = \log_2(8) = 3.0$ bits.
2. **Mutual Information Leakage Audit**:
   Empirical statistical verification that $I(\text{Input Cost } C; \text{Server View } (\boldsymbol{\delta}, \mathbf{b})) = 0$.

---

## 4. Execution Sample Sizes & Statistical Methodology

To meet scientific publishing standards:
1. **Trial Sample Size**: $N = 30$ independent trials per experimental scenario for both Mode A and Mode B (minimum 60 executions per scenario; 240 executions across the 4 scenarios).
2. **Deterministic Seed Control**:
   * Mode A and Mode B trials within the same pair will share an identical pseudo-random seed to guarantee that both modes evaluate the exact same vehicle coordinates and depot distances.
3. **Statistical Reporting Format**:
   * Non-parametric: **Median** and **95th percentile ($p_{95}$)**.
   * Parametric: **Arithmetic Mean ($\mu$)** and **Standard Deviation ($\sigma$)**.
   * Outlier and distribution shape inspection via Interquartile Range (IQR).

---

## 5. Non-Claims & Scientific Boundaries

To preserve strict scientific integrity, the Phase 4 documentation and UI will prominently feature the following explicit disclaimers:
1. **Simulation Disclaimer**: The quantum state simulator executes on a classical CPU using linear algebra over complex state vectors ($\mathbb{C}^{2^N}$). It simulates quantum mechanics; it does not utilize physical quantum hardware.
2. **No Quantum Advantage Claim**: The project demonstrates the **privacy and delegation mechanics** of Blind Quantum Computing. It explicitly does **not** claim a computational quantum speedup over classical algorithms on a classical simulation.
3. **Hardware Boundaries**: Real physical BQC requires optical fiber quantum networks transmitting single-qubit photons. Our implementation demonstrates the exact cryptographic, information-theoretic, and software architectural interfaces required to integrate BQC with an IoT fleet management platform.

---

## 6. Implementation Milestones (Post-Review Roadmap)

Execution will proceed only after this research design is approved:

| Milestone | Deliverable | Scope |
| :--- | :--- | :--- |
| **M1: Core Services** | `bqc_client_service.py` & `bqc_server_service.py` | Implement state vector simulation, BFK09 graph state entangling, angle blinding, and unpadding. |
| **M2: Database & API** | Migration `005_bqc_experiments.py` & `/api/security/bqc/*` | Create PostgreSQL tables on port 5435 and expose demonstration and batch trial endpoints. |
| **M3: Automated Tests** | `backend/tests/test_bqc.py` | Pytest suite verifying 100% assignment correctness, Shannon entropy $\approx 3.0$, and blindness invariants. |
| **M4: Interactive UI** | `BqcLabPage.tsx` | Build the side-by-side Mode A vs Mode B comparison UI, cluster visualizer, and privacy audit inspector. |
| **M5: Scientific Report** | `docs/phase-4-bqc-results.md` | Execute 240 trials against PostgreSQL and document empirical latency, wire expansion, and privacy results. |
