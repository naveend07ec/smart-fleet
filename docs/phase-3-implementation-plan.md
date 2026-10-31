# Phase 3 Implementation Plan: Secure Vehicle-to-Server Data Transmission and Experimental Validation

**Project**: IoT-Driven Smart Transportation and Fleet Management System  
**Author**: Systems Architecture & Cryptography Engineering Team  
**Date**: October 2026  
**Status**: In Progress  

---

## 1. Executive Summary & Objective

The objective of **Phase 3** is to transition the project from standalone cryptographic experimentation in the IBE Lab to a fully integrated, measurable, and scientifically sound **Secure Vehicle-to-Server Data Transmission Architecture**.

Phase 3 establishes an empirical, repeatable communication pipeline comparing:
1. **Mode A — Conventional Baseline**: Vehicle telemetry transmitted as unencrypted JSON over HTTP.
2. **Mode B — IBE-Protected Transmission**: Telemetry encrypted at the vehicular client using audited Identity-Based Key Encapsulation (IBE-KEM over BN128) combined with AES-256-GCM Authenticated Encryption with Associated Data (AEAD), and decrypted at the fleet management server using authorized identity-bound keys.

This implementation plan outlines the existing codebase architecture, reusable components, database schema expansions, security controls, API specifications, scientific benchmarking procedures, and the step-by-step implementation roadmap.

---

## 2. Existing Architecture & Reusable Components

### 2.1 Backend Architecture
- **Framework**: FastAPI (Python 3.11+) with Pydantic v2 validation.
- **ORM & Database**: SQLAlchemy 2.0 with Alembic database migrations. Connected to PostgreSQL 15 (`iot_fleet_postgres` container on host port `5435`, database `fleet_management`).
- **Cryptographic Engine (`backend/app/services/ibe_service.py`)**:
  - BN128 Type-3 optimal Ate pairing ($e: G_2 \times G_1 \to G_T$) via `py_ecc`.
  - Deterministic Try-and-Increment hashing to curve $G_1$ (`_hash_to_g1`).
  - Key derivation via HKDF-SHA256 from pairing element evaluation.
  - Symmetric data encapsulation via AES-256-GCM AEAD.
  - Windows stack size protection (`threading.stack_size(8 * 1024 * 1024)`).
  - Protected local master secret storage in `.ibe_keys/`.
- **Fleet Telemetry Engine (`backend/app/services/simulation_service.py`)**:
  - Background worker generating synthetic kinematic telemetry (GPS coordinates in Chennai region, dynamic speed jitter, battery drain, vehicle status transitions).
- **Existing Models**:
  - `Vehicle`: Fleet vehicle registry (`vehicle_identifier`, `name`, `status`).
  - `Telemetry`: Historical vehicle telemetry records (`latitude`, `longitude`, `speed`, `battery_level`, `status`, `timestamp`).
  - `IBEExperiment`: Standalone lab verification records.

### 2.2 Frontend Architecture
- **Framework**: React 18 with TypeScript and Vite.
- **Styling**: Tailored Vanilla CSS design system with dark-mode glassmorphic aesthetics.
- **Visualizations**: Lucide icons, Chart.js, React-Leaflet maps.
- **Navigation**: Multi-tab interface (`Fleet Dashboard`, `Vehicle Fleet`, `Fleet Analytics`, `IBE Security Lab`, `Simulator Control`).

---

## 3. Cryptographic Design & Documented Limitations

### 3.1 Trust Model & Role Separation
In accordance with findings in [IBE_AUDIT_REPORT.md](file:///d:/students%20projects/iot-trasnport/IBE_AUDIT_REPORT.md):
- **Centralized Private Key Generator (PKG)**: The PKG holds the master secret $s \in \mathbb{Z}_q^*$ and public parameters $P_{pub} = s \cdot G_2$.
- **Key Escrow Property**: As with all classic identity-based cryptosystems, the PKG inherently possesses key escrow capability. In our research model, the fleet management server acts as the trusted infrastructure receiver, and simulated vehicles are enrolled through an explicit trusted registration process.
- **Recipient Identity**: In vehicle-to-server communications, vehicle telemetry is encrypted for the designated server receiver identity (e.g., `fleet-management-server-core` or specific regional hubs).
- **Sender Identity Binding**: The vehicular sender identity (`SIM-VEH-xxx`) is cryptographically authenticated and bound via Authenticated Associated Data (AAD), ensuring cross-vehicle substitution is mathematically detected and rejected.

### 3.2 Scheme Classification
- The scheme is formally an **IBE-KEM + AES-256-GCM DEM Hybrid**.
- It is **not** Boneh–Franklin "FullIdent" (which requires Fujisaki–Okamoto transformation and re-encryption verification).
- Terminology in all documentation and UI reflects this audited classification.

### 3.3 AAD Binding Implementation
To address finding **M-01**, Phase 3 binds transmission metadata into the AES-256-GCM AAD:
$$\text{AAD} = \text{sender\_identity} \parallel \text{recipient\_identity} \parallel \text{message\_id} \parallel \text{timestamp\_iso}$$
Modifying any of these fields in transit invalidates the 16-byte authentication tag, immediately rejecting tampered or substituted requests.

### 3.4 Transport Layer Distinction
- Application-layer IBE encryption provides end-to-end data confidentiality and payload integrity independent of the underlying network transport.
- It is complementary to, not a replacement for, transport-layer security (TLS/HTTPS). In our local research evaluation, transmissions execute over HTTP to isolate and measure application-layer cryptographic overhead without TLS encapsulation noise.

---

## 4. Required Database Expansions (Alembic Migration 003)

To store experiment records and enforce access control without altering existing vehicle or telemetry history:

### 4.1 Table: `vehicle_enrollments`
Enforces trusted vehicle registration before encrypted or plaintext telemetry transmission:
- `id` (Integer, Primary Key, autoincrement)
- `vehicle_identifier` (String(64), Unique, Index, foreign key to `vehicles.vehicle_identifier`)
- `assigned_identity` (String(120), Unique, Index)
- `is_enrolled` (Boolean, default True)
- `enrolled_at` (DateTime(timezone=True), default UTC now)
- `revoked_at` (DateTime(timezone=True), nullable)
- `public_key_fingerprint` (String(64), nullable)
- `notes` (String(255), nullable)

### 4.2 Table: `secure_transmissions`
Stores detailed measurements for every transmission in Mode A and Mode B:
- `id` (Integer, Primary Key, autoincrement)
- `transmission_id` (String(64), Unique, Index) — e.g. `TX-xxxx`
- `batch_id` (String(64), Index, nullable) — groups automated experiment runs
- `vehicle_identifier` (String(64), Index)
- `sender_identity` (String(120), Index)
- `recipient_identity` (String(120), Index)
- `transmission_mode` (String(20), Index) — `plaintext` vs `ibe_protected`
- `payload_category` (String(20)) — `small`, `medium`, `large`
- `original_payload_size_bytes` (Integer)
- `encrypted_envelope_size_bytes` (Integer)
- `payload_expansion_bytes` (Integer)
- `payload_expansion_percent` (Float)
- `encryption_duration_ms` (Float)
- `decryption_duration_ms` (Float)
- `server_processing_duration_ms` (Float)
- `total_duration_ms` (Float)
- `status` (String(20), Index) — `success`, `rejected`, `failed`
- `rejection_reason` (String(255), nullable)
- `tampered_flag` (Boolean, default False)
- `replayed_flag` (Boolean, default False)
- `unauthorized_identity_flag` (Boolean, default False)
- `message_id` (String(64), Index, nullable)
- `message_timestamp` (DateTime(timezone=True), nullable)
- `created_at` (DateTime(timezone=True), Index, default UTC now)

### 4.3 Table: `processed_message_cache`
Supports replay attack detection within a configurable sliding time window (e.g., 300 seconds):
- `id` (Integer, Primary Key, autoincrement)
- `message_id` (String(64), Unique, Index)
- `sender_identity` (String(120), Index)
- `received_at` (DateTime(timezone=True), default UTC now, Index)

---

## 5. Backend API Specifications

The new router `backend/app/api/secure_transmission.py` will expose:

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/secure-transmission/enroll` | Enrolls or validates a vehicle for secure transmission |
| `POST` | `/api/secure-transmission/plaintext` | Mode A: Ingests raw JSON telemetry baseline |
| `POST` | `/api/secure-transmission/encrypted` | Mode B: Ingests IBE-encrypted envelope, verifies AAD, decrypts, and persists telemetry |
| `POST` | `/api/secure-transmission/experiments/run` | Executes automated batch experiments (1, 5, 10, 25 vehicles) across modes |
| `GET` | `/api/secure-transmission/experiments` | Lists transmission records with pagination and filtering |
| `GET` | `/api/secure-transmission/experiments/{id}` | Detailed inspection of an individual transmission record |
| `GET` | `/api/secure-transmission/analytics` | Statistical aggregates (medians, averages, payload expansion, success rates) |
| `GET` | `/api/secure-transmission/security-events` | Dedicated audit log of rejected, tampered, replayed, and unauthorized attempts |

---

## 6. Implementation Sequence

1. **Step 1**: Finalize implementation plan artifact ([docs/phase-3-implementation-plan.md](file:///d:/students%20projects/iot-trasnport/docs/phase-3-implementation-plan.md)).
2. **Step 2**: Create database models (`VehicleEnrollment`, `SecureTransmission`, `ProcessedMessageCache`) in [backend/app/models/secure_transmission.py](file:///d:/students%20projects/iot-trasnport/backend/app/models/secure_transmission.py) and author Alembic migration `003_secure_transmissions.py`. Apply migration to PostgreSQL container.
3. **Step 3**: Develop `SecureTransmissionService` in [backend/app/services/secure_transmission_service.py](file:///d:/students%20projects/iot-trasnport/backend/app/services/secure_transmission_service.py) containing:
   - Vehicle enrollment logic.
   - Mode A baseline transmission pipeline.
   - Mode B IBE-protected envelope encryption & decryption with AAD parameter binding.
   - Strict replay attack detection with a 300-second sliding window.
   - Cross-vehicle identity verification and schema validation.
   - Automated experiment runner with identical payload comparison generators.
4. **Step 4**: Implement FastAPI router in [backend/app/api/secure_transmission.py](file:///d:/students%20projects/iot-trasnport/backend/app/api/secure_transmission.py) with full Pydantic v2 schemas and register in [main.py](file:///d:/students%20projects/iot-trasnport/backend/app/main.py).
5. **Step 5**: Write automated test suite in [backend/tests/test_secure_transmission.py](file:///d:/students%20projects/iot-trasnport/backend/tests/test_secure_transmission.py) covering all security requirements on PostgreSQL.
6. **Step 6**: Update frontend API client and types in [frontend/src/services/api.ts](file:///d:/students%20projects/iot-trasnport/frontend/src/services/api.ts) and [frontend/src/types/index.ts](file:///d:/students%20projects/iot-trasnport/frontend/src/types/index.ts).
7. **Step 7**: Implement frontend `Secure Transmission Lab` page ([SecureTransmissionLabPage.tsx](file:///d:/students%20projects/iot-trasnport/frontend/src/pages/SecureTransmissionLabPage.tsx)), featuring:
   - Batch experiment configuration controls.
   - Real-time progress and status monitors.
   - Interactive security demonstration panel (6 controlled attack tests).
   - Real-time comparison metrics (latency, payload size, expansion %).
   - Real data charts (latency comparison, payload overhead, success/failure).
   - Paginated historical transmissions table with record detail modal.
8. **Step 8**: Add `Secure Transmission Lab` to navigation in [Sidebar.tsx](file:///d:/students%20projects/iot-trasnport/frontend/src/components/Sidebar.tsx) and [App.tsx](file:///d:/students%20projects/iot-trasnport/frontend/src/App.tsx).
9. **Step 9**: Execute real experiments, gather empirical measurements, and author [docs/phase-3-experimental-methodology.md](file:///d:/students%20projects/iot-trasnport/docs/phase-3-experimental-methodology.md) and [docs/phase-3-results.md](file:///d:/students%20projects/iot-trasnport/docs/phase-3-results.md).
10. **Step 10**: Verify and run all tests against PostgreSQL, update [README.md](file:///d:/students%20projects/iot-trasnport/README.md) and [IBE_AUDIT_REPORT.md](file:///d:/students%20projects/iot-trasnport/IBE_AUDIT_REPORT.md), and deliver completion report.
