# Identity-Based Encryption (IBE) for IoT Vehicle Telemetry
## Phase 2 Cryptographic Research Documentation & Evaluation

**Project**: IoT-Driven Smart Transportation and Fleet Management System  
**Module**: Identity-Based Encryption (IBE) Research Lab  
**Scheme**: Boneh-Franklin IBE KEM over Barreto-Naehrig Curve BN128 + AES-256-GCM (Hybrid KEM/DEM)  
**Evaluation Date**: October 2026 (Audited & Validated Phase 2.1)  

---

## 1. Executive Summary & Objective

In modern smart transportation and connected vehicle architectures, vehicle telemetry (containing real-time GPS coordinates, speed, route information, and diagnostic indicators) is transmitted over cellular and wireless vehicular networks to multiple recipients (traffic operations centers, regional transit hubs, fleet dispatchers, and emergency responders).

Traditional Public Key Infrastructure (PKI) requires resource-constrained vehicular nodes to store, validate, and verify X.509 digital certificates and query Certificate Revocation Lists (CRLs) or Online Certificate Status Protocol (OCSP) responders for each recipient prior to transmission. This introduces substantial certificate storage overhead, handshake latency, and network round-trips.

**Identity-Based Encryption (IBE)** resolves this operational challenge:
- Any arbitrary public string uniquely identifying the intended recipient (such as `"traffic-control-hub-01"`, `"emergency-response-east"`, or `"dept-of-transportation/corridor-4"`) serves directly as their **public encryption key**.
- Senders (vehicles) can encrypt telemetry payloads immediately without prior certificate lookup or handshake.
- A trusted **Private Key Generator (PKG)** computes and issues the corresponding identity-specific private decryption key to the recipient out-of-band or upon identity verification.

This research module implements a genuine, mathematically verified IBE construction, demonstrates recipient key isolation, detects ciphertext corruption, and scientifically benchmarks performance. Full cryptographic audit findings and technical limitations are detailed in [IBE_AUDIT_REPORT.md](file:///d:/students%20projects/iot-trasnport/docs/IBE_AUDIT_REPORT.md).

---

## 2. Selected Cryptographic Construction & Dependencies

### 2.1 Scheme Selection: Boneh-Franklin IBE KEM over BN128

| Property | Selected Construction | Rationale & Standards Compliance |
| :--- | :--- | :--- |
| **IBE Scheme** | Boneh-Franklin KEM / AES-GCM Hybrid (BF01 KEM analogue) | Foundational pairing-based IBE scheme under Bilinear Diffie-Hellman (BDH). Note: Implements KEM/DEM hybrid rather than FullIdent (no Fujisaki-Okamoto transform). |
| **Bilinear Pairing Curve** | BN128 (`alt_bn128` / Barreto-Naehrig) | Asymmetric Type-3 pairing $e: G_2 \times G_1 \to G_T$, 254-bit prime order, ~128-bit security level. Standardized in Ethereum EIP-197. |
| **Underlying Groups** | $G_1 \subset E(\mathbb{F}_p)$, $G_2 \subset E'(\mathbb{F}_{p^2})$, $G_T \subset \mathbb{F}_{p^{12}}^\times$ | Efficient pairing evaluation via optimal Ate pairing. |
| **Hash-to-Curve ($H_1$)** | Try-and-Increment with SHA-256 into $G_1$ | Deterministically maps arbitrary identity strings $ID \in \{0, 1\}^*$ to a valid point $Q_{ID} \in G_1$ satisfying curve equation $y^2 = x^3 + 3$. |
| **Key Encapsulation (KEM)** | $K = \text{HKDF-SHA256}(e(P_{pub}, Q_{ID})^r, \text{salt})$ | Extracts a 256-bit symmetric key from the pairing value $g_{ID}^r \in G_T$. |
| **Data Encapsulation (DEM)**| **AES-256-GCM** (NIST SP 800-38D) | Authenticated encryption with associated data (AEAD) ensuring confidentiality and plaintext integrity. |

### 2.2 Dependency Evaluation

- **`py_ecc` (v8.0.0)**: Maintained by the Ethereum Foundation; provides reference implementations of BN128, BLS12-381, and Secp256k1 with pairing engines. No compiled C/Rust dependencies required for installation across Windows/Linux environments.
- **`cryptography` (v50.0.2)**: Industry-standard OpenSSL-backed cryptographic library; provides HKDF-SHA256 and authenticated AES-256-GCM.

---

## 3. Mathematical Workflow

```text
       +-------------------------------------------------------------+
       |               Private Key Generator (PKG)                   |
       |  Setup: s in Z_q* (Master Secret), P_pub = s * P_2 in G_2   |
       +-------------------------------------------------------------+
                                      |
         Extract Key d_ID = s * Q_ID  |   (Recipient Identity ID)
                                      v
       +-------------------------------------------------------------+
       |                  Authorized Recipient                       |
       |  Receives d_ID in G_1, verifies identity                    |
       +-------------------------------------------------------------+
                                      ^
                                      | Ciphertext Bundle:
                                      |   - Ephemeral Point U in G_2
                                      |   - AES-GCM Ciphertext + Tag
                                      |   - Salt & Nonce
       +-------------------------------------------------------------+
       |               Simulated Vehicle (Sender)                    |
       |  1. Q_ID = H_1(ID) in G_1                                   |
       |  2. Choose r in Z_q*, compute U = r * P_2 in G_2             |
       |  3. Compute pairing shared secret g = e(P_pub, Q_ID)^r      |
       |  4. Key = HKDF(g), Ciphertext = AES-256-GCM(Key, Telemetry) |
       +-------------------------------------------------------------+
```

### 3.1 Setup (PKG)
1. Select generator $P_1 \in G_1$ and generator $P_2 \in G_2$.
2. Choose master secret scalar $s \in_R \mathbb{Z}_q^*$.
3. Compute master public key $P_{pub} = s \cdot P_2 \in G_2$.
4. Publish public parameters $(G_1, G_2, G_T, e, q, P_1, P_2, P_{pub}, H_1)$. Securely retain $s$.

### 3.2 Key Extraction (PKG $\to$ Recipient)
1. For recipient identity $ID \in \{0, 1\}^*$, compute identity point $Q_{ID} = H_1(ID) \in G_1$.
2. Compute private decryption key:
   $$d_{ID} = s \cdot Q_{ID} \in G_1$$
3. Deliver $d_{ID}$ to the authenticated holder of $ID$.

### 3.3 Encryption (Vehicle $\to$ Recipient Identity)
1. Map recipient identity to curve: $Q_{ID} = H_1(ID) \in G_1$.
2. Select random ephemeral scalar $r \in_R \mathbb{Z}_q^*$.
3. Compute ephemeral curve point:
   $$U = r \cdot P_2 \in G_2$$
4. Compute bilinear pairing element:
   $$g = e(P_{pub}, Q_{ID})^r \in G_T$$
5. Derive 256-bit symmetric key via HKDF:
   $$K = \text{HKDF-SHA256}(g, \text{salt})$$
6. Encrypt telemetry payload using AES-256-GCM:
   $$C = \text{AES-GCM-Encrypt}_K(M)$$
7. Output ciphertext bundle $(U, \text{salt}, \text{nonce}, C)$.

### 3.4 Decryption (Recipient using $d_{ID}$)
1. Compute pairing of ephemeral point $U \in G_2$ and recipient private key $d_{ID} \in G_1$:
   $$g' = e(U, d_{ID}) = e(r \cdot P_2, s \cdot Q_{ID}) = e(P_2, Q_{ID})^{r \cdot s} = e(s \cdot P_2, Q_{ID})^r = e(P_{pub}, Q_{ID})^r = g$$
2. Derive identical symmetric key:
   $$K' = \text{HKDF-SHA256}(g', \text{salt})$$
3. Decrypt and verify ciphertext:
   $$M = \text{AES-GCM-Decrypt}_{K'}(C)$$
   If authentication tag verification fails (e.g. wrong key, corrupted ciphertext), AES-GCM aborts safely.

---

## 4. Security Model, Trust Assumptions & Key Escrow

### 4.1 Threat Model
- **Confidentiality**: An eavesdropper observing network traffic between vehicle and recipient learns nothing about telemetry values (GPS, speed, diagnostic alerts).
- **Cross-Identity Isolation**: An adversary holding private key $d_{ID_B}$ cannot decrypt telemetry encrypted for identity $ID_A$.
- **Integrity & Authenticity**: Tampering with either the ephemeral point $U$ or ciphertext $C$ is immediately detected by AES-GCM authentication tag verification.

### 4.2 Critical Limitation: The PKG Key-Escrow Problem
> [!WARNING]
> **Key Escrow Disclosure**: A standard centralized PKG holding the master secret scalar $s$ can derive private decryption keys $d_{ID} = s \cdot Q_{ID}$ for **any** identity in the system.
>
> Therefore, standard IBE does not provide forward secrecy against a compromised PKG or immunity from insider surveillance.

**Mitigations for Production Architectures**:
1. **Threshold PKG**: Distribute the master secret $s$ across $n$ independent authorities using Shamir's Secret Sharing ($k$-of-$n$ threshold), requiring cooperation of multiple nodes to extract a key.
2. **Certificateless Public Key Cryptography (CLC)**: Combines user-generated partial secrets with PKG partial keys so the PKG alone cannot decrypt ciphertexts.
3. **Identity Scoping with Expiration**: Append temporal validity periods to identities (e.g., `traffic-control-east:2026-10`), limiting key lifetime without requiring revocation lists.

---

## 5. What is Encrypted vs. What Remains Visible

In this architecture:
- **Plaintext / Visible to Intermediate Routers**:
  - Vehicle identifier (`vehicle_id`)
  - Target recipient identity string (`recipient_identity`)
  - Message timestamp and routing envelope
  - Ephemeral public curve coordinates ($U \in G_2$)
- **Encrypted (Confidential to Recipient Only)**:
  - Precise GPS coordinates (`latitude`, `longitude`)
  - Speed, acceleration, and heading
  - Operational status (`moving`, `idle`, `offline`, `breakdown`)
  - Engine diagnostics, battery/power indicators, and trip logs

---

## 6. Empirical Scientific Evaluation & Benchmarks

Scientific evaluation trials were audited and executed against exact UTF-8 byte payloads of 128 B, 512 B, and 2,048 B ($N=5$ trials per payload size). All trials completed with 100% authorized decryption success and 100% unauthorized/tamper rejection.

### 6.1 Audited Multi-Trial Benchmark Table ($N=5$ Trials Per Category)

| Metric | 128 B Exact Payload | 512 B Exact Payload | 2 KB Exact Payload (2,048 B) |
| :--- | :--- | :--- | :--- |
| **Plaintext Length** | **128 bytes** | **512 bytes** | **2,048 bytes** |
| **Raw AES-GCM Ciphertext** | 144 bytes | 528 bytes | 2,064 bytes |
| **Raw DEM Expansion** | +16 bytes (Tag) | +16 bytes (Tag) | +16 bytes (Tag) |
| **Complete JSON Bundle Size** | **822 bytes** | **1,335 bytes** | **3,385 bytes** |
| **True Transmission Overhead**| **+694 bytes (+542.2%)**| **+823 bytes (+160.7%)**| **+1,337 bytes (+65.3%)**|
| **Encryption Median Time** | **5,349.73 ms** | **5,377.61 ms** | **4,962.34 ms** |
| **Encryption Mean Time** | 5,312.67 ms | 5,388.34 ms | 4,936.73 ms |
| **Encryption Std Dev ($\sigma$)**| 151.20 ms | 215.47 ms | 137.37 ms |
| **Decryption Median Time** | **4,684.07 ms** | **4,726.55 ms** | **4,424.23 ms** |
| **Decryption Mean Time** | 4,680.79 ms | 4,671.32 ms | 4,436.85 ms |
| **Decryption Std Dev ($\sigma$)**| 28.23 ms | 241.05 ms | 59.54 ms |
| **Authorized Decrypt** | **✓ SUCCESS (100%)** | **✓ SUCCESS (100%)** | **✓ SUCCESS (100%)** |
| **Unauthorized Rejection**| **✓ REJECTED (100%)** | **✓ REJECTED (100%)** | **✓ REJECTED (100%)** |
| **Tamper Resistance** | **✓ REJECTED (100%)** | **✓ REJECTED (100%)** | **✓ REJECTED (100%)** |

### 6.2 Analysis of Results
1. **DEM Overhead vs. Bundle Overhead**: The symmetric AES-256-GCM ciphertext expands by exactly 16 bytes (the authentication tag). However, the complete transmitted JSON bundle introduces +694 to +1,337 bytes of network transmission overhead due to ephemeral point coordinates ($U \in G_2$), base64 framing, and JSON metadata.
2. **Computational Dominance**: In pure-Python execution (`py_ecc`), optimal Ate pairing evaluation accounts for >99.9% of total run time (~4.5s to ~5.4s). The symmetric AES-256-GCM encryption/decryption takes <0.05 ms.
3. **Security Invariants**: In all trials, attempting decryption with an unauthorized recipient key or modifying any ciphertext bit resulted in an immediate, safe cryptographic rejection (`InvalidTag`).

---

## 7. Database Migration & Schema Design

Experiment results are stored in the database table `ibe_experiments` managed by Alembic migration `002_ibe_experiments.py`.

### 7.1 Schema Fields
- `id` (INTEGER, Primary Key)
- `experiment_id` (VARCHAR(64), Unique, Indexed)
- `timestamp` (DATETIME, Indexed)
- `scheme` (VARCHAR(100))
- `recipient_identity` (VARCHAR(255), Indexed)
- `unauthorized_identity` (VARCHAR(255))
- `payload_size_bytes` (INTEGER)
- `ciphertext_size_bytes` (INTEGER)
- `encryption_duration_ms` (FLOAT)
- `decryption_duration_ms` (FLOAT)
- `authorized_success` (BOOLEAN)
- `unauthorized_rejected` (BOOLEAN)
- `tamper_check_passed` (BOOLEAN)
- `status` (VARCHAR(50))
- `error_category` (VARCHAR(100), Nullable)
- `notes` (TEXT, Nullable)

> [!IMPORTANT]
> **No Key Material Persisted**: Neither master secret scalar $s$ nor recipient private keys $d_{ID}$ are stored in the experiment database. Master keys reside strictly in the local development key store (`.ibe_keys/`).

---

## 8. Verification & Execution Commands

### 8.1 Windows PowerShell Backend Testing
```powershell
# Activate Python virtual environment
.\.venv\Scripts\Activate.ps1

# Run full backend test suite (Phase 1 + Phase 2 IBE tests)
pytest backend -v

# Run only IBE cryptographic tests
pytest backend/tests/test_ibe.py -v
```

### 8.2 Windows PowerShell Frontend Testing & Build
```powershell
cd frontend

# Set temporary directory to drive with sufficient space
$env:TEMP = "D:\students projects\iot-trasnport\.tmp"
$env:TMP = "D:\students projects\iot-trasnport\.tmp"

# Run Vitest test suite
npm test -- --run

# Run TypeScript check and production build
npm run build
```

### 8.3 Live Application Launch
```powershell
# Terminal 1: Backend
$env:DATABASE_URL = "sqlite:///./fleet_management.db"
.\.venv\Scripts\uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

# Terminal 2: Frontend
cd frontend
npm run dev
```

Navigate to:
- **Interactive Fleet Dashboard**: `http://localhost:5173/`
- **IBE Security Lab**: `http://localhost:5173/` (Select **"IBE Security Lab"** from sidebar)
- **FastAPI Interactive Docs**: `http://localhost:8000/docs`
