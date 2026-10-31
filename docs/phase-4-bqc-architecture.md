# Phase 4 — Blind Quantum Computing (BQC): System Architecture & Integration Specification

**Project**: IoT-Driven Smart Transportation and Fleet Management System  
**Component**: Phase 4 Delegated Quantum Privacy Architecture  
**Document**: Technical Architecture, Database Schemas, and API Interface Specification  
**Status**: Architecture & Design Phase (Pre-Implementation Review)  
**Date**: October 2026  

---

## 1. System Integration Overview

Phase 4 introduces an isolated, modular **Blind Quantum Computing (BQC)** subsystem that integrates seamlessly with our existing architecture:
* **FastAPI Backend**: Hosts the isolated client blinding logic and the untrusted quantum server simulator.
* **PostgreSQL (Port 5435)**: Stores scientific experimental trial batches, runtime latency, wire communication overhead, and privacy audit logs.
* **React + TypeScript Frontend**: Provides an interactive **BQC Privacy Lab** featuring side-by-side Mode A vs. Mode B execution, circuit/cluster visualization, server privacy visibility inspector, and batch trial benchmarking.
* **Non-Interference Guarantee**: Phase 4 does **not** alter Phase 1/2/3 database schemas, services, or endpoints.

---

## 2. Component Separation & Trust Boundaries

To model real-world delegated quantum computing, the system strictly separates three distinct software contexts:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       TRUSTED CLIENT CONTEXT (Fleet Edge)                   │
│                                                                             │
│   • Vehicle Telemetry & Private Coordinates: (x_v, y_v, Battery, Status)    │
│   • Private Cost Vector Generation: C = [c_0, c_1, ..., c_{M-1}]            │
│   • Secret Random Angles: θ_j ∈ {0, π/4, ..., 7π/4}                          │
│   • Secret Random Measurement One-Time Pads: r_j ∈ {0, 1}                   │
│   • Feedforward Angle Compensation & Adaptive Blinding Engine               │
│   • Final Unpadding & Route Assignment Extraction                           │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                      REST API / Interactive Session
             (Blinded Angles δ_j & Transmitted One-Time Padded Bits)
                                       │
┌──────────────────────────────────────▼──────────────────────────────────────┐
│                  UNTRUSTED QUANTUM SERVER CONTEXT (Cloud Provider)          │
│                                                                             │
│   • Cluster/Graph State Simulator (2D Brickwork / Linear Cluster)           │
│   • Entangling Unitary Gates: Controlled-Z (CZ) Matrix Products             │
│   • Adaptive Projective Measurement Operator in |±_δ_j⟩ Basis               │
│   • Server Visibility Audit Log (What the server can see vs. cannot see)   │
│   • Pure Quantum State Vector Evaluation (|ψ⟩ ∈ C^{2^N})                    │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                              Evaluation Records
                                       │
┌──────────────────────────────────────▼──────────────────────────────────────┐
│                     FLEET MANAGEMENT BACKEND & DATABASE                     │
│                                                                             │
│   • Mode A Classical Evaluation Service                                     │
│   • Mode B BQC Orchestration Service                                        │
│   • PostgreSQL Stored Experiments (`bqc_experiments`, `bqc_trials`)        │
│   • Statistical Aggregation (Median, p95, Wire Expansion, Privacy Proofs)   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.1 The Trusted Client Context (`bqc_client_service.py`)
* Operates under the assumption that the vehicle or fleet dispatcher possesses private memory that the cloud cannot access.
* Implements the **angle calculation**, **Pauli feedforward corrections**, and **secret one-time padding**.
* Client memory is completely wiped after trial completion; private keys are never transmitted to the server.

### 2.2 The Untrusted Quantum Server Context (`bqc_server_service.py`)
* Represents a third-party commercial quantum cloud provider (e.g., IBM Quantum / Amazon Braket).
* Holds an $N$-qubit state vector simulator.
* Receives only blinded measurement angles $\delta_j \in [0, 2\pi)$.
* Returns raw measurement outcomes $b_j \in \{0, 1\}$.
* Maintains an audit recorder logging every variable accessible to the server context, empirically verifying that no plaintext GPS, costs, or target depot IDs enter the server's scope.

---

## 3. Database Schema Design (PostgreSQL on Port 5435)

To maintain scientific integrity and auditability, Phase 4 introduces a dedicated Alembic migration: `005_bqc_experiments.py`.

```sql
-- 1. High-level BQC Experiment Batches
CREATE TABLE bqc_experiments (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    num_candidates INT NOT NULL,           -- e.g. 4, 8, 16 depots
    num_qubits INT NOT NULL,               -- e.g. 3, 5, 9 qubits
    cluster_topology VARCHAR(50) NOT NULL, -- 'linear', 'brickwork', 'star'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. Individual Scientific Trial Runs (Mode A vs Mode B)
CREATE TABLE bqc_trials (
    id SERIAL PRIMARY KEY,
    experiment_id INT REFERENCES bqc_experiments(id) ON DELETE CASCADE,
    trial_number INT NOT NULL,
    mode VARCHAR(10) NOT NULL,             -- 'mode_a' (classical) or 'mode_b' (BQC)
    
    -- Fleet Input Parameters (Simulated)
    vehicle_identifier VARCHAR(50) NOT NULL,
    candidate_depot_ids JSONB NOT NULL,
    private_cost_vector JSONB NOT NULL,    -- Client-side private inputs
    optimal_depot_id VARCHAR(50) NOT NULL,
    
    -- Execution Measurements
    client_prep_time_ms DOUBLE PRECISION NOT NULL,   -- Classical blinding time
    server_compute_time_ms DOUBLE PRECISION NOT NULL,-- Quantum state simulation time
    total_execution_time_ms DOUBLE PRECISION NOT NULL,
    
    -- Communication & Wire Overhead
    client_to_server_bytes INT NOT NULL,   -- Total bytes sent (blinded angles, commands)
    server_to_client_bytes INT NOT NULL,   -- Total bytes returned (measurements)
    total_wire_bytes INT NOT NULL,
    
    -- Privacy Verification Audit
    server_learned_target BOOLEAN NOT NULL DEFAULT FALSE,
    server_learned_cost_vector BOOLEAN NOT NULL DEFAULT FALSE,
    privacy_entropy_score DOUBLE PRECISION NOT NULL, -- Shannon entropy of server angles
    verification_passed BOOLEAN NOT NULL DEFAULT TRUE,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_bqc_trials_exp_id ON bqc_trials(experiment_id);
CREATE INDEX idx_bqc_trials_mode ON bqc_trials(mode);
```

---

## 4. API Interface Specification

Phase 4 defines isolated endpoints under `/api/security/bqc`:

### 4.1 Execute Interactive BQC Demonstration
* **Endpoint**: `POST /api/security/bqc/demonstrate`
* **Request Body**:
  ```json
  {
    "vehicle_id": 1,
    "num_candidates": 4,
    "cluster_topology": "linear",
    "noise_simulation": false
  }
  ```
* **Response Body**:
  ```json
  {
    "scenario": "Private Depot Selection",
    "vehicle_identifier": "TN-01-AB-1001",
    "mode_a_result": {
      "selected_depot": "Depot-East-Guindy",
      "cost": 14.82,
      "latency_ms": 0.45,
      "wire_bytes": 142,
      "server_visibility": "Full Plaintext (Coordinates, Costs, Depot ID Exposed)"
    },
    "mode_b_result": {
      "selected_depot": "Depot-East-Guindy",
      "cost": 14.82,
      "client_prep_ms": 1.25,
      "server_quantum_ms": 14.80,
      "total_latency_ms": 16.05,
      "wire_bytes": 848,
      "server_visibility": "Universal Blindness (0 bits of input/output revealed)",
      "angles_entropy": 2.998,
      "unpadding_verified": true
    },
    "privacy_audit": {
      "server_view": {
        "received_angles_rad": [1.5708, 0.7854, 3.1416, 5.4978],
        "measured_raw_bits": [0, 1, 1, 0]
      },
      "client_secrets_hidden": {
        "random_thetas": [0.7854, 5.4978, 1.5708, 2.3562],
        "one_time_pads": [1, 0, 1, 1]
      }
    }
  }
  ```

### 4.2 Run Repeatable Batch Trials
* **Endpoint**: `POST /api/security/bqc/batch-trials`
* **Request Body**:
  ```json
  {
    "num_candidates": 4,
    "trials_per_mode": 10,
    "cluster_topology": "linear"
  }
  ```
* **Response Body**:
  ```json
  {
    "experiment_id": 1,
    "trials_executed": 20,
    "mode_a_summary": {
      "median_latency_ms": 0.42,
      "mean_latency_ms": 0.48,
      "p95_latency_ms": 0.71,
      "mean_wire_bytes": 142.0
    },
    "mode_b_summary": {
      "median_latency_ms": 15.82,
      "mean_latency_ms": 16.24,
      "p95_latency_ms": 18.90,
      "mean_wire_bytes": 848.0,
      "wire_expansion_percent": 497.18,
      "correctness_rate": 100.0,
      "blindness_verified_rate": 100.0
    }
  }
  ```

### 4.3 Retrieve Stored BQC Experiment Analytics
* **Endpoint**: `GET /api/security/bqc/experiments`
* **Response**: List of past experimental batches stored in PostgreSQL.

---

## 5. Frontend UI Proposal: "BQC Privacy Lab"

The frontend will include a dedicated navigation view: **`BQC Privacy Lab`** (`BqcLabPage.tsx`):
1. **Side-by-Side Dual Engine Comparison Panel**:
   * Left: **Mode A (Conventional)** — Displays plaintext transmission flow with red "Unprotected" security warnings.
   * Right: **Mode B (Blind Quantum Computing)** — Displays client-blinding and quantum measurement pattern with green "Universally Blind" badges.
2. **Interactive Measurement Pattern Visualizer**:
   * Renders the measurement graph/cluster state nodes.
   * Visualizes the transformation: $\text{Algorithm Angle } \phi_j \xrightarrow{+\theta_j + \pi r_j} \text{Blinded Angle } \delta_j \xrightarrow{\text{Server Measurement}} b_j \xrightarrow{\oplus r_j} s_j$.
3. **Server Visibility Inspector Modal**:
   * A dynamic transparency window titled *"What the Quantum Cloud Server Sees vs. What Stays on the Vehicle"*.
   * Directly demonstrates that the server's angle log looks like uniform random noise (entropy $\approx 3.0$ bits for 8 angles).
4. **Batch Experiment Runner & Live Charting**:
   * Allows executing $N = 10, 25, 50$ trials.
   * Renders Chart.js latency distribution (Mode A vs Mode B) and wire byte expansion graphs.
