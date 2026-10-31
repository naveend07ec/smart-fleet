# SMARTFLEET — Phase 7: Source Code, Architecture & Evidence Audit

**Document Version:** 1.0.0  
**Audit Date:** October 31, 2026  
**Auditor:** Automated Engineering Research Audit Agent  
**Host Environment:** Windows 11 Home (64-bit), 8.00 GB RAM, Python 3.11.9, Node.js v20.18.0  
**Database Deployment:** PostgreSQL 16 on dedicated port `5435` (`iot_fleet_postgres`)  

---

## 1. Objective of the Source Audit

Before preparing the final academic project submission documents (Final Report, Research Paper, Technical Diagrams, Viva Questions, and Presentation Outline), this audit rigorously inspects the codebase, database state, raw benchmark logs, and historical documentation.

Its primary goals are to:
1. Verify the **actual** software and cryptographic architecture as implemented in source code.
2. Catalog all **empirical evidence sources** (raw JSON logs, test outputs, database counts).
3. Identify and rectify any **discrepancies** between earlier historical phase reports and actual implementation reality.
4. Establish explicit **assumptions and unresolved research questions** to ensure academic defensibility.

---

## 2. Verified Project Architecture

The architecture was verified by directly tracing files in `backend/app/`, `frontend/src/`, `backend/alembic/`, and `backend/tests/`.

### 2.1 Backend Architecture
- **Framework:** FastAPI (`app/main.py`) running asynchronous and synchronous route handlers with Pydantic v2 schemas (`app/schemas/`).
- **Database ORM:** SQLAlchemy 2.0 with PostgreSQL dialect via `psycopg2-binary`.
- **Active Database Port:** Dedicated port **`5435`** mapping to container `iot_fleet_postgres` (PostgreSQL 16-alpine).
- **Alembic Migration State:** Current at head migration `007_optimization_experiments` (`backend/alembic/versions/`).
- **Core Cryptographic Engine:**
  - **IBE Scheme:** Boneh-Franklin (BF01) IBE-KEM implemented over the pairing-friendly Barreto-Naehrig BN128 curve (`alt_bn128` via `py_ecc.bn128`).
  - **Map-to-$G1$:** SHA-256 try-and-increment hashing (`IBE-HASH-G1:{identity}:{counter}`) with quadratic residue verification via Euler's criterion.
  - **Symmetric Cipher:** AES-256-GCM (`cryptography.hazmat.primitives.ciphers.aead.AESGCM`) with 12-byte random IV and 16-byte tag.
  - **Key Derivation:** HKDF-SHA256 with 16-byte random salt and info parameter `b"IBE-TELEMETRY-AES256GCM"`.
  - **Digital Signatures:** Ed25519 (SHA-512 RFC 8032 via `cryptography.hazmat.primitives.asymmetric.ed25519`).
  - **Thread Stack Enlargement:** 8 MB stack background worker thread (`threading.stack_size(8 * 1024 * 1024)`) in [ibe_service.py](file:///d:/students%20projects/iot-trasnport/backend/app/services/ibe_service.py) to prevent Windows recursion limits during BN128 Miller loop evaluations.
- **Replay Protection:** Dual-mechanism sliding window ($-300\,\text{s} \le \Delta t \le +30\,\text{s}$) paired with atomic PostgreSQL nested savepoints (`db.begin_nested()`) on table `processed_message_cache`.

### 2.2 Frontend Architecture
- **Framework:** React 18 with TypeScript and Vite 5.4.
- **Styling:** Modular Vanilla CSS design system (`index.css`) with glassmorphism, dark palette, responsive layouts, and zero TailwindCSS dependencies.
- **State Management & Routing:** React Router v6 with Axios API integration.
- **Pages & Labs:**
  - `/` (Dashboard / Fleet Overview)
  - `/vehicles` (Vehicle CRUD & Enrollment Management)
  - `/security-lab` (IBE Encrypted Telemetry Ingestion & Live Attack Demonstration)
  - `/ibe-lab` (Cryptographic Key Inspector & Direct Encryption/Decryption Testing)
  - `/bqc-lab` (Simulated Blind Quantum Computing Depot Delegation)
  - `/optimization` (QUBO Fleet Routing & Comparative Benchmark Solver [Frozen Extension])

---

## 3. Evidence Sources Catalog

Every claim in the final submission is backed by reproducible evidence recorded in the repository:

| Evidence Type | Artifact Path | Description & Provenance |
|---|---|---|
| **Security Audit Logs** | `scratch/step_6_1_audit_results.json` | Exact results of 1 legitimate transmission + 12 attack vectors + 6-worker concurrency + API key audit. |
| **Benchmark Dataset** | `scratch/step_6_2_benchmark_data.json` | Micro-latencies, Mode A vs B comparisons, payload expansions, and scaling up to 25 vehicles. |
| **Backend Test Suite** | `backend/tests/` | 91 automated tests passing (`pytest backend/tests` in 282.31s). |
| **Frontend Test Suite** | `frontend/src/test/` | 25 automated Vitest tests passing (`npm test -- --run` in 18.61s). |
| **Production Build** | `frontend/dist/` | Production bundle built cleanly (`npm run build` in 7.40s). |
| **PostgreSQL Schema** | `backend/app/models/` | SQLAlchemy models for `Vehicle`, `Telemetry`, `VehicleEnrollment`, `SecureTransmission`, `ProcessedMessageCache`, `BqcExperiment`, `OptimizationExperiment`. |

---

## 4. Discrepancies & Corrections Identified

During the audit, the following inconsistencies between older documentation and the verified implementation were discovered and resolved:

### Discrepancy 1: Database Engine and Port
- *Historical Inconsistency:* Some early Phase 1/Phase 3 documentation drafts referenced SQLite or PostgreSQL on default port `5432`.
- *Verified Reality:* The application connects strictly to a dedicated Docker container `iot_fleet_postgres` running PostgreSQL 16 on host port **`5435`**. Ports 5432, 5433, and 5434 host unrelated projects and were preserved untouched.

### Discrepancy 2: Cryptographic Pairing Latency Claims
- *Historical Inconsistency:* Generic literature suggests pairing-based cryptography executes in "a few milliseconds."
- *Verified Reality:* In our Python implementation (`py_ecc`), BN128 pairings execute in **3,923.50 ms** (mean) and IBE encapsulation takes **4,469.55 ms** (mean). This discrepancy is explicitly explained as the difference between interpreted pure-Python arithmetic and compiled C/Rust libraries (e.g. RELIC/mcl).

### Discrepancy 3: Role of Blind Quantum Computing (BQC)
- *Historical Inconsistency:* Early scoping documents occasionally conflated BQC with transmission channel encryption.
- *Verified Reality:* BQC is a **delegated computation privacy simulation** for depot optimization, **not** an in-flight channel encryption protocol. Vehicle-to-server data in transit is protected exclusively by classical **IBE-KEM + AES-256-GCM + Ed25519**.

### Discrepancy 4: Optimization Module (QUBO) Status
- *Historical Inconsistency:* Optimization was developed in Phase 5 as an experimental routing component.
- *Verified Reality:* Phase 5 is completely **frozen** as an optional research extension. It is preserved for academic completeness but is not part of the core secure transmission pipeline.

---

## 5. Explicit Assumptions & Unresolved Questions

To maintain scientific integrity in academic defense:
1. **Host Hardware Specification:** All experimental latencies were captured on an Intel/AMD x86_64 CPU under Windows 11 Home with 8.00 GB RAM. Running on higher-spec Linux servers with multi-core CPUs would reduce latencies but preserve relative scaling ratios.
2. **Key Storage Assumption:** Keys are assumed protected by host operating system discretionary access controls in `.ibe_keys/`. Hardware-rooted security (TPM 2.0 / HSM) is documented as a necessary production enhancement.
3. **Network Latency Assumption:** Benchmark measurements were conducted over local loopback (`localhost`), isolating computational processing latency from variable cellular (4G/5G/LTE-M) network jitter.
4. **BQC Classical Simulation Boundary:** It is explicitly assumed and stated that the BFK09 simulation is a classical state-vector model in $\mathbb{C}^{2^N}$, providing zero quantum speedup.
