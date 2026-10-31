# IoT-Driven Smart Transportation and Fleet Management System
## Phase 3 & 3.1 — Secure Vehicle-to-Server Data Transmission and Security Validation Audit

**Final-Year Engineering Project • Research Prototype**

This repository contains the working prototype of the **IoT-Driven Smart Transportation and Fleet Management System**. The system simulates IoT-connected vehicles across transit corridors (demo bounding box: Chennai metropolitan area), generates synthetic telemetry (GPS coordinates, speed, operational status, and simulated battery indicators), persists records in PostgreSQL, provides fleet management APIs, and incorporates an independently audited **Identity-Based Encryption (IBE-KEM + AES-256-GCM AEAD) and Ed25519 Digital Signature transmission pipeline** with strict sender authentication, AAD ciphertext binding, vehicle enrollment, and atomic replay protection.

---

## 1. System Architecture & Tech Stack

- **Frontend**: React 18, TypeScript, Vite, Vanilla CSS design system, Lucide icons, Chart.js, React-Leaflet.
- **Backend**: Python 3.11+, FastAPI, Pydantic v2 schemas, Pydantic Settings.
- **Database**: PostgreSQL 15 (Docker container on port 5435 with SQLAlchemy 2.0 ORM and Alembic migrations). SQLite is also supported for isolated zero-config local testing.
- **Cryptographic Security Layer**:
  - **Confidentiality**: Type-3 Asymmetric Pairing IBE-KEM over BN128 (`alt_bn128`).
  - **Ciphertext Integrity**: Authenticated Data Encapsulation Mechanism (DEM) with AES-256-GCM and canonical AAD parameter binding.
  - **Sender Authentication**: Ed25519 digital signatures (Edwards-curve 25519) bound to each vehicle in `vehicle_enrollments` over canonical transmission metadata and ciphertext envelope.
  - **Replay & Concurrency Protection**: 300-second sliding-window replay detection backed by database-level atomic unique constraints on `processed_message_cache`.
- **Testing**:
  - Backend: `pytest` with `pytest-asyncio` and `httpx` (47 automated tests against PostgreSQL).
  - Frontend: `vitest`, `jsdom`, `@testing-library/react` (14 automated unit tests).
- **Telemetry Simulation Engine**: Thread-safe background simulation service supporting dynamic parameter updates, auto-start in FastAPI lifespan, and live frontend updates.

---

## 2. Directory Structure

```text
iot-trasnport/
├── backend/
│   ├── alembic/
│   │   ├── versions/
│   │   │   ├── 001_initial_schema.py        # Initial vehicle and telemetry schema
│   │   │   ├── 002_ibe_experiments.py       # Standalone IBE lab experiment records
│   │   │   ├── 003_secure_transmissions.py  # Phase 3 transmissions, enrollments & replay cache
│   │   │   └── 004_ed25519_sender_auth.py   # Phase 3.1 Ed25519 public keys & signatures
│   │   ├── env.py                           # Dynamic migration environment
│   │   └── script.py.mako
│   ├── alembic.ini                          # Alembic configuration
│   ├── app/
│   │   ├── api/
│   │   │   ├── health.py                    # GET /api/health
│   │   │   ├── vehicles.py                  # CRUD & /api/vehicles/{id}/telemetry
│   │   │   ├── dashboard.py                 # GET /api/dashboard/summary
│   │   │   ├── analytics.py                 # GET /api/analytics/overview
│   │   │   ├── simulation.py                # POST /api/simulation/start & stop
│   │   │   ├── ibe.py                       # Standalone IBE research lab endpoints
│   │   │   └── secure_transmission.py       # Phase 3: Mode A & Mode B vehicle transmission APIs
│   │   ├── models/
│   │   │   ├── vehicle.py                   # Vehicle SQLAlchemy model
│   │   │   ├── telemetry.py                 # Telemetry SQLAlchemy model
│   │   │   ├── ibe_experiment.py            # Standalone IBE experiment model
│   │   │   └── secure_transmission.py       # VehicleEnrollment, SecureTransmission, ProcessedMessageCache
│   │   ├── schemas/
│   │   │   ├── vehicle.py                   # Vehicle Pydantic schemas
│   │   │   ├── telemetry.py                 # Telemetry Pydantic schemas
│   │   │   ├── dashboard.py                 # Dashboard schemas
│   │   │   ├── analytics.py                 # Analytics schemas
│   │   │   ├── simulation.py                # Simulation control schemas
│   │   │   ├── ibe.py                       # IBE Lab schemas
│   │   │   └── secure_transmission.py       # Mode A, Mode B, Batch trials & Analytics schemas
│   │   ├── services/
│   │   │   ├── simulation_service.py        # Background telemetry generator
│   │   │   ├── seed_service.py              # Idempotent demo data generator
│   │   │   ├── ibe_service.py               # Cryptographic pairing & key derivation engine
│   │   │   └── secure_transmission_service.py # Phase 3 transmission pipeline & experiment runner
│   │   ├── config.py                        # App settings & env configuration
│   │   ├── database.py                      # SQLAlchemy engine and session dependency
│   │   └── main.py                          # FastAPI application entry point
│   ├── tests/                               # 47 automated pytest test suites against PostgreSQL
│   ├── requirements.txt                     # Python backend dependencies
│   ├── pytest.ini                           # Pytest configuration
│   └── seed.py                              # Standalone idempotent seeding CLI
├── docs/
│   ├── phase-3.1-security-validation-report.md # Phase 3.1 Security validation audit report
│   ├── phase-3-implementation-plan.md       # Complete Phase 3 architecture plan
│   ├── phase-3-experimental-methodology.md  # Scientific methodology and hypotheses
│   ├── phase-3-results.md                   # Real empirical measurements and analytics
│   ├── IBE_AUDIT_REPORT.md                  # Comprehensive cryptographic audit
│   └── POSTGRESQL_VALIDATION_REPORT.md      # PostgreSQL migration and integrity validation
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Sidebar.tsx                  # Navigation sidebar
│   │   │   ├── StatusBadge.tsx              # Moving/Idle/Offline badge
│   │   │   ├── MetricCard.tsx               # Metric cards
│   │   │   ├── SimulatedMap.tsx             # Leaflet interactive simulated map
│   │   │   ├── SimulationControls.tsx       # Simulator controls
│   │   │   └── VehicleModal.tsx             # Vehicle management modal
│   │   ├── pages/
│   │   │   ├── DashboardPage.tsx            # Fleet overview & charts
│   │   │   ├── VehiclesPage.tsx             # Vehicle list, search, filter & CRUD
│   │   │   ├── VehicleDetailPage.tsx        # Single vehicle telemetry history
│   │   │   ├── AnalyticsPage.tsx            # Fleet-wide aggregate telemetry trends
│   │   │   ├── IbeLabPage.tsx               # Standalone IBE Lab
│   │   │   └── SecureTransmissionLabPage.tsx# Phase 3: Secure Transmission Lab
│   │   ├── services/api.ts                  # Typed frontend API client
│   │   ├── test/                            # 14 Vitest / RTL unit tests
│   │   └── types/index.ts                   # TypeScript interfaces
├── scripts/
│   ├── migrate_sqlite_to_postgres.py        # Database migration script
│   └── run_phase3_trials.py                 # Automated Phase 3 benchmark trial runner
├── docker-compose.yml                       # Local PostgreSQL 15 container (port 5435)
└── README.md                                # Setup, instructions and architecture documentation
```

├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Sidebar.tsx             # Responsive sidebar navigation
│   │   │   ├── StatusBadge.tsx         # Moving/Idle/Offline badge
│   │   │   ├── MetricCard.tsx          # Dashboard metric card
│   │   │   ├── SimulatedMap.tsx        # Leaflet interactive simulated map
│   │   │   ├── SimulationControls.tsx  # Scenario & frequency controls
│   │   │   └── VehicleModal.tsx        # Register & edit vehicle modal
│   │   ├── pages/
│   │   │   ├── DashboardPage.tsx       # Fleet overview & charts
│   │   │   ├── VehiclesPage.tsx        # Vehicle list, search, filter & CRUD
│   │   │   ├── VehicleDetailPage.tsx   # Single vehicle details & telemetry log
│   │   │   └── AnalyticsPage.tsx       # Fleet-wide aggregate telemetry trends
│   │   ├── services/
│   │   │   └── api.ts                  # Typed frontend API client
│   │   ├── test/                       # 9 Vitest / RTL unit tests
│   │   ├── types/
│   │   │   └── index.ts                # TypeScript interfaces
│   │   ├── App.tsx                     # Top layout & navigation router
│   │   ├── index.css                   # Custom CSS styling tokens
│   │   └── main.tsx                    # React DOM entry point
│   ├── package.json                    # NPM dependencies & scripts
│   ├── tsconfig.json                   # TypeScript configuration
│   └── vite.config.ts                  # Vite bundler & proxy configuration
├── docker-compose.yml                  # Local PostgreSQL service container
├── .env.example                        # Environment variables template
├── .gitignore                          # Git ignore definitions
└── README.md                           # Documentation and setup instructions
```

---

## 3. Windows PowerShell Quick Start Guide

### ⚡ One-Click Launch (Recommended)
You can launch the entire system (migrations, database checks, backend, and frontend) with a single command:
```powershell
.\start_system.ps1
```

---

### Manual Step-by-Step Setup

### Step 1: Environment Setup & Python Virtual Environment


```powershell
# Open PowerShell in the project directory
cd "d:\students projects\iot-trasnport"

# Create Python virtual environment
python -m venv .venv

# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Install backend dependencies
pip install -r backend\requirements.txt
```

### Step 2: Database Configuration & Migrations

You can run against a local PostgreSQL database, Docker PostgreSQL, or zero-config local SQLite:

**Option A — PostgreSQL (Recommended for production/presentation)**:
```powershell
# Start PostgreSQL via Docker (if Docker is installed):
docker compose up -d

# Set PostgreSQL DATABASE_URL:
$env:DATABASE_URL="postgresql://postgres:postgrespassword@localhost:5432/fleet_management"

# Run Alembic migrations:
.\.venv\Scripts\alembic -c backend\alembic.ini upgrade head

# Seed the demo fleet and initial synthetic telemetry:
.\.venv\Scripts\python backend\seed.py
```

**Option B — SQLite (Zero-config local development & testing)**:
```powershell
# Set SQLite database URL:
$env:DATABASE_URL="sqlite:///./backend/fleet_management.db"

# Run Alembic migrations:
.\.venv\Scripts\alembic -c backend\alembic.ini upgrade head

# Seed demo fleet:
.\.venv\Scripts\python backend\seed.py
```

*Note: `backend\seed.py` is fully idempotent. Running it multiple times will never duplicate vehicles or corrupt historical telemetry.*

### Step 3: Run the FastAPI Backend Server

```powershell
cd "d:\students projects\iot-trasnport\backend"
..\.venv\Scripts\uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
The interactive OpenAPI documentation is immediately accessible at:
- **Swagger UI**: [http://127.0.0.1:8000/api/docs](http://127.0.0.1:8000/api/docs)
- **ReDoc**: [http://127.0.0.1:8000/api/redoc](http://127.0.0.1:8000/api/redoc)
- **Health Check**: [http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health)

### Step 4: Frontend Installation & Launch

Open a second PowerShell window:
```powershell
cd "d:\students projects\iot-trasnport\frontend"

# Install NPM packages
npm install

# Start Vite development server
npm run dev
```
Open your browser at **[http://localhost:5173](http://localhost:5173)** to view the live dashboard and navigate to **"IBE Security Lab"** via the sidebar.

---

## 4. Phase 2 — Identity-Based Encryption (IBE) Cryptographic Module

### 4.1 Cryptographic Architecture
Phase 2 integrates a genuine Identity-Based Encryption research module based on the **Boneh-Franklin IBE (BF01) KEM** over the 128-bit security **BN128 (`alt_bn128`)** pairing curve, coupled with **AES-256-GCM** authenticated hybrid encryption:
- **Zero Certificate Handshake**: Vehicles use arbitrary recipient identities (e.g., `"traffic-control-hub-01"`) directly as public encryption keys without certificate lookups.
- **Private Key Generator (PKG)**: The PKG derives recipient-specific private keys $d_{ID} = s \cdot Q_{ID} \in G_1$ using the master secret scalar $s \in \mathbb{Z}_q^*$.
- **Hybrid AEAD Protection**: The Bilinear Diffie-Hellman shared secret $g = e(P_{pub}, Q_{ID})^r$ is derived via HKDF-SHA256 into a 256-bit symmetric key for AES-256-GCM payload encryption.
- **Cross-Identity Isolation & Tamper Detection**: Cryptographically verified: an unauthorized recipient's key or a corrupted ciphertext is deterministically rejected by AES-GCM tag verification.

> [!WARNING]
> **PKG Key-Escrow Disclosure**: A standard centralized PKG holding master secret $s$ can theoretically derive keys for any identity. In production environments, a distributed threshold PKG or Certificateless Cryptography (CLC) is recommended to mitigate escrow.

### 4.2 IBE API Endpoints
- `GET /api/security/ibe/status` — Returns scheme status, curve parameters, and PKG trust model disclosure.
- `POST /api/security/ibe/setup` — Idempotent master parameter initialization (protected against accidental public reinitialization).
- `POST /api/security/ibe/encrypt` — Encrypts a telemetry payload for a validated recipient identity.
- `POST /api/security/ibe/decrypt` — Decrypts a ciphertext bundle using the extracted recipient key.
- `POST /api/security/ibe/experiments` — Executes a verified 3-stage research trial (authorized decrypt, unauthorized rejection, tamper check) and persists the trial metrics.
- `GET /api/security/ibe/experiments` — Paginated list of scientific evaluation trials.
- `GET /api/security/ibe/experiments/{id}` — Detailed metrics and validation flags for a specific trial.

### 4.3 Detailed Documentation
See [`docs/IBE_RESEARCH_NOTES.md`](docs/IBE_RESEARCH_NOTES.md) for full mathematical specifications, threat models, empirical benchmark tables, and security proofs.

---

## 5. Running Automated Tests

### Backend Tests (pytest)
```powershell
cd "d:\students projects\iot-trasnport"
$env:PYTHONPATH="backend"
.\.venv\Scripts\pytest backend -v
```
*Executes **67 automated test suites** on PostgreSQL covering parameter setup, authorized decryption, unauthorized key rejection, ciphertext tamper resistance, tag tampering, replay attack prevention, cross-vehicle identity substitution, batch trials, BQC state normalization/entanglement/blindness, QUBO Hamiltonian evaluation, Simulated Annealing convergence, API validation, and database trial persistence.*

### Frontend Tests (Vitest & React Testing Library)
```powershell
cd "d:\students projects\iot-trasnport\frontend"
npm test -- --run
```
*Executes **25 automated unit tests** across 8 test suites (`StatusBadge`, `SimulationControls`, `Vehicles`, `TopNavbar`, `IbeLab`, `SecureTransmissionLab`, `BqcLab`, and `QuboRouting`).*

### Production Build Validation
```powershell
cd "d:\students projects\iot-trasnport\frontend"
npm run build
```

---

## 6. API References

### Phase 3: Secure Transmission API
- `POST /api/secure-transmission/enroll` — Enrolls and authorizes a vehicle identity in the PKG access control registry.
- `GET /api/secure-transmission/enrollments` — Lists active vehicle identity enrollments.
- `POST /api/secure-transmission/plaintext` — Mode A: Conventional baseline unencrypted JSON telemetry ingestion.
- `POST /api/secure-transmission/encrypted` — Mode B: IBE-protected envelope ingestion with AAD verification, decryption, and PostgreSQL persistence.
- `POST /api/secure-transmission/demonstration` — Executes controlled attack scenarios (tampered ciphertext, tampered tag, replay resubmission, rogue identity, cross-vehicle substitution).
- `POST /api/secure-transmission/experiments/run` — Executes automated batch trials across vehicle counts, message counts, and payload categories.
- `GET /api/secure-transmission/experiments` — Paginated list of transmission records with mode/status filters.
- `GET /api/secure-transmission/analytics` — Real-time aggregate statistical analytics (median latencies, payload expansion %).
- `GET /api/secure-transmission/security-events` — Audit log of rejected attacks.

### Phase 4: Blind Quantum Computing (BQC) API
- `GET /api/security/bqc/status` — Retrieves BQC subsystem status and default candidate depots.
- `POST /api/security/bqc/demonstrate` — Runs single-shot comparison between Classical Mode A and Blind Delegated Quantum Mode B.
- `POST /api/security/bqc/batch-trials` — Executes statistical trials evaluating execution latencies, TVD distinguishability, and angle entropy.
- `GET /api/security/bqc/experiments` — Lists historical BQC benchmark trials stored in database.

### Phase 5: QUBO / Simulated Annealing Fleet Routing API
- `GET /api/routing/defaults` — Returns central Chennai depot, 8 commercial waypoints, and default EV fleet configurations.
- `POST /api/routing/optimize` — Runs comparative route optimization: Classical Greedy + 2-Opt vs QUBO Simulated Annealing.
- `GET /api/routing/experiments` — Lists historical routing optimization benchmarks with distance and energy reduction metrics.
- `GET /api/routing/experiments/{id}` — Retrieves full route geometry, stop sequences, and annealing convergence history.
- `DELETE /api/routing/experiments/{id}` — Deletes an experiment benchmark record.

---

## 7. Project Roadmap & Completed Phases

### ✅ Phase 1: Core Working Prototype (Completed)
- Fleet Dashboard, Interactive Simulated Chennai Map, Vehicle CRUD, Background Simulation Engine, Analytics Overview, Alembic Migrations, and Automated Tests.

### ✅ Phase 2: Identity-Based Encryption (IBE) for Telemetry (Completed)
- Genuine Boneh-Franklin BN128 + AES-256-GCM Cryptographic Service.
- Private Key Generator (PKG) key extraction and derivation.
- Interactive IBE Security Lab frontend page with live trials and timing comparison charts.
- Database persistence for scientific trials via Alembic migration `002_ibe_experiments.py`.
- Benchmark evaluation across 128B, 512B, and 2KB payloads.

### ✅ Phase 3: Secure Vehicle-to-Server Data Transmission (Completed)
- Integrated vehicle-to-server communication pipeline with Mode A (baseline) and Mode B (IBE-protected).
- Authenticated Associated Data (AAD) binding sender identity, server recipient, message UUID, and UTC timestamp.
- Sliding-window replay detection via `processed_message_cache`.
- Vehicle enrollment access control registry (`vehicle_enrollments`).
- Full PostgreSQL transmission telemetry persistence (`secure_transmissions`).
- Interactive `Secure Transmission Lab` UI with live KPI metrics, 6 attack demonstrations, repeatable batch experiment runner, and record inspector.
- Complete scientific evaluation documents: `docs/phase-3-implementation-plan.md`, `docs/phase-3-experimental-methodology.md`, `docs/phase-3-results.md`.

### ✅ Phase 4: Blind Quantum Computation (BQC) & Delegated Privacy (Completed)
- Universal Broadbent-Fitzsimons-Kashefi (BFK09) Measurement-Based Quantum Computing protocol.
- Classical Client state rotation blinding + Untrusted Quantum Cloud Server graph state entanglement and projective measurement simulator.
- Private Fleet Depot Selection algorithm preserving vehicle GPS coordinates, internal costs, and route goals.
- Interactive `BQC Privacy Lab` UI with cluster state SVG visualizer, timing comparisons, and total variation distance analysis.
- Complete scientific evaluation documents: `docs/phase-4-bqc-research-design.md`, `docs/phase-4-bqc-architecture.md`, `docs/phase-4-bqc-results.md`.

### ✅ Phase 5: QUBO / Simulated Annealing Fleet Routing & Optimization (Completed)
- Capacitated Multi-Vehicle Routing Problem (CVRP) mathematical formulation.
- Quadratic Unconstrained Binary Optimization (QUBO) Hamiltonian with quadratic capacity, battery range, and workload balance penalties.
- Simulated Annealing optimization engine with Metropolis-Hastings acceptance and temperature decay schedules.
- Comparative evaluation against Classical Greedy Nearest-Neighbor + 2-Opt local search.
- Interactive `QUBO Fleet Routing Lab` UI with visual Chennai map geometry, side-by-side benchmarking matrix, annealing convergence trajectory charts, vehicle stop breakdowns, and JSON/CSV benchmark exports.


