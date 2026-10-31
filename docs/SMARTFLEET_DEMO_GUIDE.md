# SMARTFLEET: Comprehensive Project Demonstration Guide

**Project Title:** SMARTFLEET: IoT-Driven Smart Transportation and Fleet Management System with Secure Data Transmission and Privacy-Preserving Computation  
**Target Duration:** 10–15 Minutes  
**Audience:** Project Evaluation Committee, External Examiners, and Academic Evaluators  
**System Prerequisites:** Docker Desktop running, PostgreSQL on port 5435, Python virtual environment, Node.js.

---

## 1. Demonstration Overview & Timing Breakdown

| Stage | Activity | Key Features Highlighted | Allocated Time |
| :---: | :--- | :--- | :---: |
| **Stage 1** | System Startup & Health Verification | Port 5435 verification, FastAPI docs, React frontend | 2 Minutes |
| **Stage 2** | Live Fleet Operations & Telemetry | Live map, GPS updates, OBD-II telemetry inspection | 3 Minutes |
| **Stage 3** | Authorized Secure Telemetry Transmission | IBE-KEM encapsulation, AES-GCM, Ed25519 signing | 3 Minutes |
| **Stage 4** | Adversarial Attack Defense & Replay Testing | Ciphertext tampering, signature forgery, replay rejection | 3 Minutes |
| **Stage 5** | Empirical Benchmarks & BQC Simulation | Performance tradeoffs, latency multipliers, BFK09 MBQC | 3 Minutes |
| **Stage 6** | Honest Academic Boundary & Q&A Transition | Python pairing bottleneck, HSM roadmap, Q&A | 1 Minute |

> [!IMPORTANT]
> **Safety Notice:** Do NOT run database migrations, wipe historical tables, or execute destructive reset scripts prior to or during the demonstration. All existing records (vehicles, telemetry, security audit logs, BQC trials, QUBO benchmarks) must remain intact.

---

## 2. Step-by-Step Demonstration Sequence

### Step 1: System Startup & Health Verification (2 min)

#### 1.1 Verify PostgreSQL Container on Port 5435
Open PowerShell and verify the dedicated container is running and healthy:
```powershell
docker ps --filter "name=iot_fleet_postgres"
```
*Expected Output:* Container `iot_fleet_postgres` with status `Up` and port mapping `0.0.0.0:5435->5432/tcp`.

#### 1.2 Start the FastAPI Backend
In Terminal 1:
```powershell
cd "d:\students projects\iot-trasnport"
& ".\.venv\Scripts\Activate.ps1"
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
*What to highlight to examiners:*
- FastAPI initializes with modular routers: `/api/vehicles`, `/api/telemetry`, `/api/secure`, `/api/ibe`, `/api/bqc`, `/api/optimization`.
- Note the thread stack configuration: 8 MB stack allocated for BN128 recursive point arithmetic.
- Open Swagger API documentation at: `http://localhost:8000/docs`.

#### 1.3 Start the React Management Frontend
In Terminal 2:
```powershell
cd "d:\students projects\iot-trasnport\frontend"
npm run dev
```
*Expected Output:* Vite dev server running at `http://localhost:5173/`. Open in your browser.

---

### Step 2: Live Fleet Dashboard & Telemetry Inspection (3 min)

#### 2.1 Navigate the Operator Interface
- Open `http://localhost:5173/` in Google Chrome or Edge.
- Show the **Dashboard Overview**:
  - Point out the active vehicle count (37 registered fleet vehicles).
  - Show the live status cards: Total Mileage, Average Speed, Active Alerts, and Cryptographic Security Status (`ENABLED`).

#### 2.2 Live Fleet Map & Simulation Movement
- Click on the **"Live Fleet Map"** view (`http://localhost:5173/fleet`).
- Observe vehicle markers navigating along synthetic urban road networks.
- Click on a specific vehicle (e.g., `VEH-001` or `VEH-002`):
  - Point out real-time coordinate updates (Latitude, Longitude, Heading, Velocity).
  - Open the **Telemetry Detail Drawer**:
    - **Engine RPM:** (e.g., 2,250 RPM)
    - **Coolant Temperature:** (e.g., 88°C)
    - **Battery State-of-Charge:** (e.g., 94%)
    - **Diagnostic Trouble Codes:** (Normal / P0000)
- *Talking Point for Examiners:*
  > "This interface simulates our active IoT vehicular edge nodes. Under normal operations, telematics data is periodically ingested and displayed in real time. We will now inspect how this transmission is cryptographically protected against network adversaries."

---

### Step 3: Authorized Secure Telemetry Transmission (3 min)

#### 3.1 Open the Cryptographic Security Console
- Navigate to the **"Security & Cryptography"** tab in the sidebar (`http://localhost:5173/security` or `/security-experiment`).
- Point out the cryptographic configuration summary:
  - **KEM Scheme:** Boneh–Franklin Identity-Based Encryption (BN128 curve).
  - **Recipient Public Identity:** `"smartfleet:server:telemetry"`.
  - **Symmetric Cipher:** AES-256-GCM with Authenticated Associated Data (AAD).
  - **Signature Scheme:** Ed25519 (Edwards-curve Digital Signature).
  - **Replay Protection:** Dual-window (30 s future / 300 s staleness) + Database-level unique nonce cache.

#### 3.2 Trigger an Authorized Secure Ingestion
- Select Vehicle: `VEH-001`.
- Payload Tier: Select **"Medium (OBD-II Diagnostic Snapshot)"**.
- Click **"Execute Secure Transmission"**.
- Observe the live execution timeline in the UI:
  1. *Step 1:* Vehicle signs canonical payload hash using Ed25519 ($\sim 0.75$ ms).
  2. *Step 2:* Vehicle generates ephemeral scalar $r$, computes BN128 curve point $U$, and derives $K_{sym}$ via pairing ($\sim 4.4$ s).
  3. *Step 3:* Payload encrypted via AES-256-GCM; IV, tag, and AAD assembled.
  4. *Step 4:* Server receives envelope, validates freshness (< 1 ms), verifies Ed25519 signature (0.25 ms), decapsulates $K_{sym}$ via pairing ($\sim 3.9$ s), decrypts AES-GCM, and commits to PostgreSQL.
- Verify status card: **Status: 200 OK — Successfully Committed**.
- Inspect the persisted record: Show the newly generated transmission ID and database commit timestamp.

---

### Step 4: Adversarial Attack Defense & Replay Testing (3 min)

Demonstrate that the server actively rejects malicious, corrupted, or replayed transmissions.

#### 4.1 Demonstrate Attack Vector 1: Ciphertext Bit Corruption
- In the Security Console, locate the **"Adversarial Attack Simulator"** panel.
- Select Attack: **"Tampered Ciphertext (Single Bit Flip)"**.
- Click **"Inject Adversarial Payload"**.
- *Observed Result:*
  - Server returns **HTTP 400 Bad Request**.
  - Error Details: `"AES-GCM decryption failed: Invalid authentication tag"`.
  - Database rollback triggered; 0 telemetry records persisted.

#### 4.2 Demonstrate Attack Vector 2: Signature Forgery
- Select Attack: **"Forged Ed25519 Signature"**.
- Click **"Inject Adversarial Payload"**.
- *Observed Result:*
  - Server returns **HTTP 401 Unauthorized**.
  - Latency: **< 1.0 millisecond**.
  - *Talking Point for Examiners:*
    > "Notice the sub-millisecond response time! The server's pre-decryption anti-oracle defense verified the signature first. Because the signature was invalid, the server terminated the connection immediately without executing the 4-second pairing decapsulation. This completely immunizes our server against pairing-exhaustion Denial-of-Service attacks."

#### 4.3 Demonstrate Attack Vector 3: Replay Attack
- Select Attack: **"Replay Intercepted Valid Message"**.
- Click **"Inject Adversarial Payload"**.
- *Observed Result:*
  - Server returns **HTTP 400 Bad Request**.
  - Error Details: `"Replay attack detected: Message nonce already processed in sliding window"`.
  - Database inspection confirms that the replayed message was rejected by the `processed_message_cache` unique index.

---

### Step 5: Empirical Benchmark Analytics & BQC Simulation (3 min)

#### 5.1 Inspect Empirical Performance Analytics
- Navigate to the **"Performance Analytics"** dashboard (`http://localhost:5173/analytics`).
- Present the empirical findings gathered during Phase 6:
  - **Plaintext vs. Protected Latency:** Point out the contrast between Mode A (~40 ms) and Mode B (~8,500 ms), explaining the 200× latency multiplier resulting from interpreted Python pairing arithmetic.
  - **Component Breakdown:** Show that Ed25519 consumes < 1 ms while BN128 pairing consumes 99.9% of processing time.
  - **Wire Expansion:** Explain why small packets expand by +572% while large diagnostic dumps experience only +48% expansion due to constant envelope framing.
  - **Attack Resilience Scorecard:** Show 100% rejection rate across all 12 formal attack scenarios.

#### 5.2 Demonstrate the BQC Simulation Module
- Navigate to the **"Quantum Privacy (BQC)"** view (`http://localhost:5173/bqc`).
- Select Simulation Mode: **"4-Qubit Brickwork Cluster State"**.
- Click **"Run Blind Computation Simulation"**.
- Walk through the visual animation:
  1. Client generates blind qubit states with random phase angles $\theta_j$.
  2. Server creates entangled cluster graph.
  3. Client calculates blinded measurement angles $\phi_j'$.
  4. Server performs measurements and returns blinded bits.
  5. Client decrypts true output.
- Show the mathematical information leakage metric: **$\Delta H = 0.00$ bits (Zero Server Knowledge)**.

---

### Step 6: Honest Academic Boundary & Conclusion (1 min)

Conclude the demonstration by presenting the project's engineering boundaries:
- **Core Contribution:** An authenticated, certificate-free vehicular telemetry ingestion pipeline using IBE-KEM, AES-256-GCM, Ed25519, and atomic replay protection.
- **Academic Prototype vs. Production:**
  - Python pairing latency (~4.0 s) will be reduced to < 5 ms in production by migrating to compiled Rust/C pairing libraries (`BLST`).
  - Vehicle private keys will be anchored in automotive Hardware Security Modules (HSMs) compliant with ISO/SAE 21434.
  - BQC is a classical CPU simulation demonstrating privacy protocol mathematics, not physical quantum hardware execution.

Open the floor for questions from the evaluation committee.

---

## 3. Quick Reference: Terminal Commands for Demo Troubleshooting

If a service needs to be checked during the viva, use these verified commands:

```powershell
# Check Docker PostgreSQL Status
docker ps --filter "name=iot_fleet_postgres"

# Check Database Row Counts
& "d:\students projects\iot-trasnport\.venv\Scripts\python.exe" -c "from app.core.database import SessionLocal; from app.models.vehicle import Vehicle; from app.models.telemetry import TelemetryRecord; db=SessionLocal(); print('Vehicles:', db.query(Vehicle).count(), 'Telemetry:', db.query(TelemetryRecord).count()); db.close()"

# Run Fast Security Audit Verification
& "d:\students projects\iot-trasnport\.venv\Scripts\python.exe" "C:\Users\acer\.gemini\antigravity-ide\brain\5fc1d6eb-c072-4f5a-9d66-7c9d5621bc5a\scratch\audit_security_scenarios.py"
```
