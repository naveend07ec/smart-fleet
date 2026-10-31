# Phase 3 & 3.1 Scientific Experimental Methodology

**Project**: IoT-Driven Smart Transportation and Fleet Management System  
**Evaluation**: Secure Vehicle-to-Server Data Transmission, Ed25519 Sender Authentication, and Cryptographic Trade-Off Analysis  
**Audit Phase**: Phase 3.1 (Independent Security Validation and Scientific Consistency Audit)  
**Date**: October 2026  
**Status**: Validated for Research Demonstration  

---

## 1. Central Research Question & Hypotheses

### 1.1 Central Research Question
> *"How does a decoupled cryptographic architecture—combining Type-3 BN128 IBE-KEM + AES-256-GCM for telemetry confidentiality and ciphertext integrity with Ed25519 digital signatures for origin authentication—affect transmission security, vehicle impersonation resilience, computational latency, and wire payload overhead compared to a conventional plaintext baseline?"*

### 1.2 Scientific Hypotheses
1. **Hypothesis 1 (Confidentiality & Ciphertext Integrity vs. Sender Authentication)**:
   - *H1.0 (Null)*: Cryptographic encapsulation and AAD binding provide origin authentication against an adversary who generates fresh ciphertexts using server public parameters.
   - *H1.1 (Alternative - Confirmed in Phase 3.1)*: Binding sender identity into AES-256-GCM AAD alone does **not** authenticate the sender because public encryption parameters permit anyone to encrypt to the server. Independent cryptographic sender authentication requires an asymmetric digital signature (Ed25519) covering canonical metadata and the ciphertext envelope.
   
2. **Hypothesis 2 (Communication Wire Overhead)**:
   - *H2.0 (Null)*: Transmission payload size is identical between conventional JSON and encrypted envelopes.
   - *H2.1 (Alternative)*: IBE-protected transmission introduces a constant mathematical framing overhead due to the serialization of the ephemeral public point $U \in G_2$ (four 254-bit coordinate strings in extension field $\mathbb{F}_{p^2}$), Base64 framing, salt, nonce, Ed25519 signature, and JSON headers, resulting in higher percentage overhead for small telemetry packets than for large multi-sensor payloads.

3. **Hypothesis 3 (Computational Latency)**:
   - *H3.0 (Null)*: Cryptographic encapsulation and decapsulation introduce negligible computational latency ($< 1$ ms) relative to plaintext HTTP parsing.
   - *H3.1 (Alternative)*: Pure-Python bilinear pairing evaluation on BN128 dominates the transmission pipeline, creating an empirical latency penalty of several orders of magnitude compared to plaintext baseline HTTP ingestion.

---

## 2. Experimental Setup & System Architecture

### 2.1 Hardware and Runtime Environment
- **Host Operating System**: Microsoft Windows 11 Pro (64-bit, AMD64 architecture).
- **CPU & Memory**: Multi-core x86_64 CPU, 16 GB RAM.
- **Python Execution Environment**: Python 3.11.9 (CPython) with 8MB stack allocation per cryptographic pairing thread (`threading.stack_size(8 * 1024 * 1024)`).
- **Database Engine**: PostgreSQL 15-Alpine running in an isolated Docker container (`iot_fleet_postgres` container mapped to `localhost:5435`).
- **Network Setting**: Local loopback interface (`localhost:8000`). Local transport isolates application-layer cryptographic overhead from network jitter and packet drops.

### 2.2 Cryptographic Scheme Specification
- **Confidentiality / KEM**: Boneh–Franklin Asymmetric Pairing Key Encapsulation Mechanism (IBE-KEM) paired with Authenticated Data Encapsulation Mechanism (DEM).
- **Curve**: Barreto–Naehrig BN128 (`alt_bn128`).
- **Pairing Engine**: Type-3 Optimal Ate pairing $e: G_2 \times G_1 \to G_T$ via `py_ecc` (Ethereum Foundation).
- **Identity Hash**: Deterministic Try-and-Increment SHA-256 to $G_1$ (`_hash_to_g1`).
- **Key Derivation Function**: HKDF-SHA256 deriving a 256-bit symmetric key $K$.
- **Symmetric Cipher**: AES-256-GCM (12-byte random IV, 16-byte authentication tag).
- **AAD Binding (Ciphertext Integrity)**:
  $$\text{AAD} = \text{sender\_identity} \parallel \text{recipient\_identity} \parallel \text{message\_id} \parallel \text{timestamp\_iso}$$
- **Origin Authentication (Sender Authenticity & Non-Repudiation)**:
  - Algorithm: Ed25519 (EdDSA over Curve25519 with SHA-512).
  - Private key: Managed locally per vehicular client (`.ibe_keys/vehicle_signing_keys/`).
  - Public key: Registered in `vehicle_enrollments.signing_public_key`.
  - Canonical Signed Message: Covers sender identity, recipient identity, message UUID, ISO 8601 timestamp, and serialized ciphertext bundle.

---

## 3. Comparison Modes & Telemetry Datasets

### 3.1 Mode A — Conventional Baseline
- Simulated vehicle generates telemetry and serializes it to standard readable JSON.
- Telemetry is transmitted over HTTP to `POST /api/secure-transmission/plaintext`.
- Server records processing duration, checks enrollment, verifies freshness, and stores telemetry.
- **Designation**: Experimental unencrypted baseline for performance comparison.

### 3.2 Mode B — IBE-Protected Secure Transmission with Ed25519 Signing
- Simulated vehicle obtains its provisioned identity from the PKG registry.
- Computes canonical AAD from transmission parameters.
- Computes ephemeral scalar $r$, point $U = r \cdot G_2$, shared secret $g^r = e(P_{pub}, Q_{ID})^r$, and derives AES-256 key via HKDF.
- Encrypts telemetry with AES-256-GCM using AAD.
- Signs canonical metadata and ciphertext bundle with its private Ed25519 key.
- Transmits encrypted and signed envelope to `POST /api/secure-transmission/encrypted`.
- Server validates sender enrollment, verifies Ed25519 digital signature, verifies freshness against sliding window, checks atomic replay cache, derives symmetric key using recipient private key $d_{ID} = s \cdot Q_{ID}$, decrypts and authenticates AAD, and persists telemetry to PostgreSQL.

### 3.3 Payload Scale Classes (Empirically Measured)

| Scale | Real-World Analogue | Mean Plaintext Size ($n$) | Key Telemetry Attributes |
| :--- | :--- | :--- | :--- |
| **Small** | Minimal periodic GPS heartbeat beacon | **203.5 B** ($n=6$) | Coordinates, speed, battery level, operational status |
| **Medium** | Standard fleet tracking with diagnostics | **266.8 B** ($n=18$) | Coordinates, speed, status, battery, engine RPM, coolant temp, 4-wheel tire pressures |
| **Large** | Comprehensive multi-sensor edge buffer | **615.2 B** ($n=6$) | Core metrics, diagnostics, LiDAR/Radar proximity buffers, 3-axis IMU acceleration, historical waypoints |

---

## 4. Controlled Security Scenarios & Attack Vectors

The validation suite incorporates 11 controlled security scenarios:
1. **Valid Authorized**: Legitimate enrolled vehicle submitting authentic ciphertext with valid Ed25519 signature. (Expected: `success`, `persisted=True`).
2. **Attacker Impersonation (Phase 3.1 Critical)**: Adversary generates fresh ciphertext under server public parameters claiming enrolled Vehicle A, but lacks Vehicle A's Ed25519 private key. (Expected: `rejected`, `signature_verified=False`).
3. **Missing Signature**: Enrolled vehicle submits valid encrypted ciphertext with `signature_b64=None`. (Expected: `rejected`, missing signature).
4. **Tampered Signature**: 1 byte corrupted in `signature_b64`. (Expected: `rejected`, `tampered_flag=True`).
5. **Substituted Signature**: Vehicle A's signature attached to Vehicle B's transmission. (Expected: `rejected`, public key mismatch).
6. **Unauthorized Rogue Identity**: Unregistered identity `MALICIOUS-ROGUE-999@attacker.net`. (Expected: `rejected`, access control).
7. **Tampered Ciphertext Body**: 1 bit flipped in AES-GCM ciphertext ($C_0 \oplus 0x01$). (Expected: `rejected`, `tampered_flag=True`).
8. **Tampered Authentication Tag**: 1 bit flipped in 16-byte GHASH authentication tag. (Expected: `rejected`, `tampered_flag=True`).
9. **Exact Duplicate Replay**: Same message submitted twice. (Expected: 1st `success`, 2nd `rejected`, `replayed_flag=True`).
10. **Same UUID, Different Ciphertext**: Reused UUID with new ciphertext payload. (Expected: `rejected`, duplicate UUID).
11. **Future Timestamp / Expired Timestamp**: Clock skew outside sliding window tolerance. (Expected: `rejected`).

---

## 5. Statistical Reporting Methodology

To avoid misleading single-trial reporting, results are evaluated using:
- **Sample Size ($n$)**: All evaluated records in PostgreSQL (`n=30` Mode B, `n=27` Mode A).
- **Non-Parametric Median**: Primary measure of central tendency to resist execution outliers.
- **Parametric Mean & Standard Deviation ($\sigma$)**: Dispersion and variance measures.
- **95th Percentile ($p_{95}$)**: Tail latency bound under pairing thread loads.
- **Minimum and Maximum Bounds**: Strict observed interval.
