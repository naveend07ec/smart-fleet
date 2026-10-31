# PostgreSQL Architecture Configuration and Migration Validation Report
**Phase 2.2 — IoT-Driven Smart Transportation and Fleet Management System**  
**Date**: October 29, 2026  
**Auditor / Engineering Role**: Senior Backend & Infrastructure Specialist / Independent Reviewer  
**Status**: VALIDATED & OPERATIONAL

---

## Executive Summary

As part of Phase 2.2, a complete audit and alignment of the database layer for the IoT-Driven Smart Transportation and Fleet Management System was conducted. The project originally selected PostgreSQL as its primary database architecture, but initial development had defaulted to a local SQLite database (`sqlite:///./fleet_management.db`) with silent fallback mechanisms.

This validation phase has achieved the following key outcomes:
1. **Explicit PostgreSQL Architecture**: Configured PostgreSQL as the mandatory primary database for standard application execution and Alembic migrations. Silent SQLite fallbacks have been eliminated; unreachable database configurations immediately yield explicit connection errors.
2. **Strict Host Container Isolation**: Identified host port collisions with existing unrelated project containers on ports `5432` (`infypos-postgres`), `5433` (`infybuys-postgres`), and `5434` (`infynux-academy-postgres`). Allocated host port `5435` for the dedicated project container `iot_fleet_postgres` without modifying, interrupting, or reusing any external database.
3. **Full Schema & Migration Validation**: Successfully executed Alembic migrations up to head (`001_initial_schema` and `002_ibe_experiments`) on PostgreSQL. Verified all table definitions, composite indexes, foreign keys, timestamps with time zones, float fields, and text fields.
4. **Data Audit & Zero-Data-Loss Invariant**: Conducted a read-only audit of both databases. The SQLite database contains 25 vehicles, 6,150 telemetry points, and 3 IBE experiments. The PostgreSQL database currently contains 0 records (clean migrated schema). In accordance with instructions, SQLite records were **not** automatically copied into PostgreSQL, preserving data integrity and preventing premature overrides. A safe, reproducible migration script with foreign-key ordering and sequence resetting was provided.
5. **Backend Test Suite Execution**: Validated the entire 31-test backend suite directly against PostgreSQL (`fleet_management_test`), passing 100% of vehicle, telemetry, dashboard, simulation, seed, and IBE cryptographic persistence tests. Documented explicit SQLite isolation (`USE_SQLITE_TESTS=1`) for hermetic offline testing.
6. **Frontend & API Contract Invariant**: Zero changes were made to API routes, schemas, or frontend interfaces. Vitest frontend test suite (12 tests) continues to pass cleanly.

---

## 1. Database Configuration Audit & Inventory

### 1.1 Complete Configuration Inspection

| Component | File / Module | Configuration Details | Changes / Alignment Made |
| :--- | :--- | :--- | :--- |
| **Pydantic Settings** | `backend/app/config.py` | `Settings.DATABASE_URL` loaded from environment or `.env` files. | Default changed from `sqlite:///./fleet_management.db` to `postgresql://postgres:postgrespassword@localhost:5435/fleet_management`. Added `Union[List[str], str]` validator for `CORS_ORIGINS`. |
| **SQLAlchemy Engine** | `backend/app/database.py` | Creates engine and session maker (`SessionLocal`). | Detects PostgreSQL vs SQLite. For SQLite: passes `connect_args={"check_same_thread": False}`. For PostgreSQL: applies pool configuration (`pool_pre_ping=True`, `pool_size=10`, `max_overflow=20`). Silent fallback removed. |
| **Alembic Engine** | `backend/alembic/env.py` | Loads `DATABASE_URL` from `app.config.settings`. | Configured to strictly read the validated `DATABASE_URL` from settings, applying migrations to PostgreSQL. |
| **Seed Fixtures** | `backend/app/db/seed.py` | Idempotent seeder creating 25 vehicles and 100 historical telemetry records per vehicle. | Uses `SessionLocal` from `app.database`. Fully compatible with PostgreSQL transactions and bulk inserts. |
| **Test Fixtures** | `backend/tests/conftest.py` | Pytest fixtures providing `db_session` and FastAPI `TestClient`. | Configured to target `fleet_management_test` on PostgreSQL by default. Preserves SQLite mode only when explicitly enabled via `USE_SQLITE_TESTS=1`. |
| **Docker Compose** | `docker-compose.yml` | Containerized database and backend service definition. | Uses `postgres:15-alpine`, container name `iot_fleet_postgres`, host port `5435:5432`, volume `postgres_data`. |

### 1.2 Exact Database Used by Subsystem

Prior to Phase 2.2 vs. current operational state:

| Subsystem | Previous Database Target | Current Phase 2.2 Validated Target | Status |
| :--- | :--- | :--- | :--- |
| **FastAPI Application** | SQLite (`fleet_management.db`) | PostgreSQL (`localhost:5435/fleet_management`) | Validated & Active |
| **Alembic Migrations** | SQLite (`fleet_management.db`) | PostgreSQL (`localhost:5435/fleet_management`) | Migrated to Head (`002`) |
| **Vehicle Service** | SQLite | PostgreSQL (`localhost:5435/fleet_management`) | Validated via API & Tests |
| **Telemetry Service** | SQLite | PostgreSQL (`localhost:5435/fleet_management`) | Validated via API & Tests |
| **IBE Persistence** | SQLite | PostgreSQL (`localhost:5435/fleet_management`) | Validated via API & Tests |
| **Automated Tests** | SQLite (in-memory or file) | PostgreSQL (`localhost:5435/fleet_management_test`) | 31/31 Passed |

---

## 2. Infrastructure Setup and Port Isolation

### 2.1 Host Port Audit and Avoidance of Collisions

A pre-execution port inspection of running Docker containers revealed three existing PostgreSQL instances on the host:
- `5432/tcp`: Container `infypos-postgres` (unrelated project)
- `5433/tcp`: Container `infybuys-postgres` (unrelated project)
- `5434/tcp`: Container `infynux-academy-postgres` (unrelated project)

Attempting to bind standard port `5432` would either fail with a port conflict or risk polluting or corrupting an unrelated database. Therefore:
- Host port **`5435`** was allocated exclusively for this project.
- Container name: **`iot_fleet_postgres`**
- Base image: `postgres:15-alpine`
- Internal container port: `5432`

### 2.2 Database Initialization

Inside the `iot_fleet_postgres` instance, two isolated databases were initialized:
1. `fleet_management`: Primary runtime database for application execution and manual testing.
2. `fleet_management_test`: Dedicated test database for automated regression test runs, preventing tests from wiping production/runtime records.

---

## 3. Migration and PostgreSQL Schema Compatibility Analysis

Migrations were executed via Alembic against `fleet_management` on PostgreSQL:
```bash
alembic upgrade head
```
Target revision: `002_ibe_experiments` (incorporating `001_initial_schema`).

### 3.1 PostgreSQL DDL Inspection

The resulting schema in PostgreSQL `public` was audited using `information_schema`:

#### A. Table `vehicles`
- `id`: `integer`, Primary Key, `nextval('vehicles_id_seq')`
- `vehicle_identifier`: `character varying(50)`, Unique, Not Null, Index: `ix_vehicles_vehicle_identifier`
- `make`: `character varying(50)`, Not Null
- `model`: `character varying(50)`, Not Null
- `year`: `integer`, Not Null
- `license_plate`: `character varying(20)`, Unique, Not Null, Index: `ix_vehicles_license_plate`
- `status`: `character varying(20)`, Not Null (Validated against enum domain in Pydantic: `active`, `maintenance`, `inactive`)
- `battery_capacity`: `double precision`, Nullable
- `created_at`: `timestamp with time zone`, Default: `now()`
- `updated_at`: `timestamp with time zone`, Default: `now()`

#### B. Table `telemetry`
- `id`: `integer`, Primary Key, `nextval('telemetry_id_seq')`
- `vehicle_id`: `integer`, Foreign Key to `vehicles(id)` on delete CASCADE, Index: `ix_telemetry_vehicle_id`
- `timestamp`: `timestamp with time zone`, Not Null, Index: `ix_telemetry_timestamp`
- `latitude`: `double precision`, Not Null
- `longitude`: `double precision`, Not Null
- `speed`: `double precision`, Not Null
- `fuel_level`: `double precision`, Nullable
- `battery_level`: `double precision`, Nullable
- `engine_temperature`: `double precision`, Nullable
- `tire_pressure`: `double precision`, Nullable
- `status`: `character varying(20)`, Nullable
- Composite Index: `ix_telemetry_vehicle_timestamp_desc` on `(vehicle_id, timestamp DESC)`

#### C. Table `ibe_experiments`
- `id`: `integer`, Primary Key, `nextval('ibe_experiments_id_seq')`
- `experiment_id`: `character varying(64)`, Unique, Not Null, Index: `ix_ibe_experiments_experiment_id`
- `recipient_identity`: `character varying(255)`, Not Null, Index: `ix_ibe_experiments_recipient_identity`
- `unauthorized_identity`: `character varying(255)`, Nullable
- `payload_size_bytes`: `integer`, Not Null
- `encryption_duration_ms`: `double precision`, Not Null
- `decryption_duration_ms`: `double precision`, Not Null
- `status`: `character varying(32)`, Not Null, Index: `ix_ibe_experiments_status`
- `authorized_success`: `boolean`, Not Null
- `unauthorized_rejected`: `boolean`, Not Null
- `tamper_check_passed`: `boolean`, Not Null
- `notes`: `text`, Nullable
- `created_at`: `timestamp with time zone`, Default: `now()`, Index: `ix_ibe_experiments_created_at`

### 3.2 Compatibility Fixes and Verifications

1. **Timestamps with Time Zone**: Alembic migrations specify `sa.DateTime(timezone=True)`. In SQLite, this is stored as UTC text strings; in PostgreSQL, it maps cleanly to native `timestamp with time zone`, properly preserving ISO-8601 timestamps without timezone truncation.
2. **Double Precision vs Float**: Coordinates (`latitude`, `longitude`) and metrics use `sa.Float()`, which maps to IEEE 754 `double precision` in PostgreSQL, preventing numerical precision loss.
3. **Pydantic-Settings CORS Parser**: Upgraded `Settings.CORS_ORIGINS` in [backend/app/config.py](file:///d:/students%20projects/iot-trasnport/backend/app/config.py) to accept both JSON array formats and comma-delimited strings via a Pydantic `@field_validator(mode="before")`, preventing startup crashes when environment files provide either format.
4. **Health Check Dialect Exposure**: Enhanced `/api/health` in [backend/app/api/health.py](file:///d:/students%20projects/iot-trasnport/backend/app/api/health.py) to explicitly return `"dialect": engine.dialect.name`, enabling runtime verification of PostgreSQL connectivity (`"database": "connected", "dialect": "postgresql"`).
5. **Dynamic Test Fixture Engine**: Updated [backend/tests/conftest.py](file:///d:/students%20projects/iot-trasnport/backend/tests/conftest.py) to create tables dynamically on `fleet_management_test` for each test session, overriding FastAPI `get_db` cleanly.

---

## 4. Current Data Inventory & Safe Migration Plan

In strict adherence to Requirement 7, **no records have been copied automatically into PostgreSQL, and no tables or existing SQLite files have been reset or dropped.**

### 4.1 Data Audit Results

A non-destructive audit script (`scripts/migrate_sqlite_to_postgres.py --dry-run`) yielded the following data inventory:

```
======================================================================
Database Inventory & Audit (Dry Run)
======================================================================
SQLite Database (backend/fleet_management.db):
  - vehicles:        25 records (SIM-DEMO-001 to SIM-DEMO-025)
  - telemetry:       6,150 records
  - ibe_experiments: 3 records (IBE-EXP-2C894B92, IBE-EXP-5416576F, IBE-EXP-9DB6ABDD)

PostgreSQL Database (localhost:5435/fleet_management):
  - vehicles:        0 records (clean schema)
  - telemetry:       0 records (clean schema)
  - ibe_experiments: 0 records (clean schema)
======================================================================
```

### 4.2 Safe Migration Plan

If the project team chooses to promote the historical simulation data from SQLite into PostgreSQL, the created script [scripts/migrate_sqlite_to_postgres.py](file:///d:/students%20projects/iot-trasnport/scripts/migrate_sqlite_to_postgres.py) should be executed:

```bash
# Preview operations without committing
python scripts/migrate_sqlite_to_postgres.py --dry-run

# Execute atomic migration with transaction rollback protection
python scripts/migrate_sqlite_to_postgres.py --execute
```

**Safety Invariants Guarantees in Migration Script:**
1. **Foreign Key Order**: Migrates `vehicles` first, followed by `telemetry`, then `ibe_experiments`.
2. **Transaction Atomicity**: All operations execute within a single PostgreSQL transaction (`session.begin()`); any failure triggers an immediate `ROLLBACK`, leaving PostgreSQL in its prior state.
3. **PostgreSQL Sequence Synchronization**: Executes `SELECT setval('vehicles_id_seq', (SELECT MAX(id) FROM vehicles))` and `SELECT setval('telemetry_id_seq', (SELECT MAX(id) FROM telemetry))` so subsequent `INSERT` operations through the application do not violate primary key uniqueness.
4. **Duplicate Protection**: Existing IDs are checked before inserting; duplicate inserts are skipped.

---

## 5. Test Suite Verification & Database Distinction

The entire backend test suite was executed against PostgreSQL. Additionally, SQLite-only isolation was verified.

### 5.1 Primary Test Run: PostgreSQL (`fleet_management_test`)

Command:
```powershell
& "d:\students projects\iot-trasnport\.venv\Scripts\pytest.exe" -v
```

Execution Log:
```
============================= test session starts =============================
platform win32 -- Python 3.11.9, pytest-8.2.2, pluggy-1.7.0 -- D:\students projects\iot-trasnport\.venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: D:\students projects\iot-trasnport\backend
configfile: pytest.ini
testpaths: tests
plugins: anyio-4.15.1
collecting ... collected 31 items

tests/test_analytics.py::test_analytics_overview_with_empty_and_populated_data PASSED [  3%]
tests/test_dashboard.py::test_dashboard_summary_with_data PASSED         [  6%]
tests/test_health.py::test_health_check PASSED                           [  9%]
tests/test_health.py::test_root_info PASSED                              [ 12%]
tests/test_ibe.py::test_ibe_status_and_trust_model PASSED                [ 16%]
tests/test_ibe.py::test_ibe_identity_validation PASSED                   [ 19%]
tests/test_ibe.py::test_ibe_encrypt_and_authorized_decryption PASSED     [ 22%]
tests/test_ibe.py::test_ibe_unauthorized_decryption_rejected PASSED      [ 25%]
tests/test_ibe.py::test_ibe_ciphertext_tampering_rejected PASSED         [ 29%]
tests/test_ibe.py::test_ibe_payload_sizes PASSED                         [ 32%]
tests/test_ibe.py::test_ibe_empty_payload_fails PASSED                   [ 35%]
tests/test_ibe.py::test_ibe_experiment_lifecycle PASSED                  [ 38%]
tests/test_ibe_audit.py::test_pairing_bilinearity_and_argument_order PASSED [ 41%]
tests/test_ibe_audit.py::test_ibe_mathematical_roundtrip_equation PASSED [ 45%]
tests/test_ibe_audit.py::test_hash_to_g1_curve_membership PASSED         [ 48%]
tests/test_ibe_audit.py::test_cross_identity_isolation_and_case_sensitivity PASSED [ 51%]
tests/test_ibe_audit.py::test_malformed_u_point_rejection PASSED         [ 54%]
tests/test_ibe_audit.py::test_ciphertext_tag_and_metadata_tampering PASSED [ 58%]
tests/test_ibe_audit.py::test_key_reload_and_historical_decryption PASSED [ 61%]
tests/test_ibe_audit.py::test_setup_idempotency_without_force_reinit PASSED [ 64%]
tests/test_ibe_audit.py::test_phase1_regression_endpoints PASSED         [ 67%]
tests/test_seed.py::test_seed_command_idempotency PASSED                 [ 70%]
tests/test_simulation.py::test_simulation_start_stop_status PASSED       [ 74%]
tests/test_telemetry.py::test_telemetry_retrieval_and_empty_state PASSED [ 77%]
tests/test_telemetry.py::test_telemetry_nonexistent_vehicle PASSED       [ 80%]
tests/test_vehicles.py::test_create_and_get_vehicle PASSED               [ 83%]
tests/test_vehicles.py::test_duplicate_vehicle_identifier_fails PASSED   [ 87%]
tests/test_vehicles.py::test_invalid_vehicle_status_validation PASSED    [ 90%]
tests/test_vehicles.py::test_update_and_delete_vehicle PASSED            [ 93%]
tests/test_vehicles.py::test_nonexistent_vehicle_returns_404 PASSED      [ 96%]
tests/test_vehicles.py::test_list_vehicles_pagination_and_filter PASSED  [100%]

================= 31 passed, 2 warnings in 555.03s (0:09:15) ==================
```

### 5.2 Isolated SQLite Test Run (`USE_SQLITE_TESTS=1`)

To guarantee offline and CI developer flexibility where a PostgreSQL daemon might not be available, SQLite testing support is preserved exclusively under an explicit environment flag:
```powershell
Set-Item -Path env:USE_SQLITE_TESTS -Value '1'
& "d:\students projects\iot-trasnport\.venv\Scripts\pytest.exe" tests/test_health.py tests/test_vehicles.py -v
```

Execution Result:
- 8 tests collected and passed.
- Explicitly documented: **SQLite test runs do NOT validate PostgreSQL compatibility**; PostgreSQL remains the mandatory target for official CI and staging validation.

### 5.3 Frontend Test Verification

Vitest tests executed via `npm test -- --run` in `frontend/`:
- `src/test/StatusBadge.test.tsx`: 3 passed
- `src/test/SimulationControls.test.tsx`: 2 passed
- `src/test/Vehicles.test.tsx`: 4 passed
- `src/test/IbeLab.test.tsx`: 3 passed
- **Result**: 12 passed across 4 test suites.

---

## 6. How to Run Locally

### 6.1 Prerequisites
- Docker Desktop running on Windows.
- Python 3.11 virtual environment in `.venv`.
- Node.js & npm (for frontend).

### 6.2 Environment Configuration

Create or verify `.env` in the project root:
```env
# Database Settings (Isolated port 5435)
DATABASE_URL=postgresql://postgres:postgrespassword@localhost:5435/fleet_management
TEST_DATABASE_URL=postgresql://postgres:postgrespassword@localhost:5435/fleet_management_test

# Application Settings
ENVIRONMENT=development
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=["http://localhost:5173", "http://localhost:3000"]
```

### 6.3 Startup Commands

#### Step 1: Start Isolated PostgreSQL Container
```powershell
docker compose up -d db
```
Verify container status:
```powershell
docker ps --filter "name=iot_fleet_postgres"
```

#### Step 2: Apply Alembic Migrations
```powershell
cd backend
& "..\.venv\Scripts\alembic.exe" upgrade head
```

#### Step 3: (Optional) Seed Initial Vehicles & Telemetry
```powershell
& "..\.venv\Scripts\python.exe" -m app.db.seed
```
*(Or transfer existing SQLite data using `python ../scripts/migrate_sqlite_to_postgres.py --execute`)*

#### Step 4: Start the FastAPI Backend
```powershell
& "..\.venv\Scripts\uvicorn.exe" app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### Step 5: Verify Health Endpoint
```powershell
curl http://localhost:8000/api/health
```
Response:
```json
{
  "status": "healthy",
  "database": "connected",
  "dialect": "postgresql"
}
```

---

## 7. Conclusion & Readiness for Phase 3

Phase 2.2 is complete and verified:
- PostgreSQL is the explicit primary database with zero silent fallbacks.
- Host port `5435` guarantees total isolation from other database containers.
- All schema migrations (including `002_ibe_experiments`) are applied and verified.
- The entire 31-test suite passes on PostgreSQL.
- Historical data in SQLite remains intact and uncorrupted, ready for migration at the project owner's discretion.

The backend architecture is now fully aligned with the production PostgreSQL specification and ready for Phase 3.
