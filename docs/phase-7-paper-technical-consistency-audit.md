# SMARTFLEET — Research Paper Technical Consistency Audit

**Audit Date:** October 2026  
**Audited Document:** [docs/SMARTFLEET_RESEARCH_PAPER.md](file:///d:/students%20projects/iot-trasnport/docs/SMARTFLEET_RESEARCH_PAPER.md)  
**Audit Scope:** Verification against backend source code, SQLAlchemy database models, raw benchmark dataset (`scratch/step_6_2_benchmark_data.json`), and security evaluation logs (`scratch/step_6_1_audit_results.json`).  
**Audit Mode:** Read-Only Audit (no production code, migrations, or database records modified).

---

## 1. Executive Summary

A comprehensive line-by-line audit of the academic research paper ([docs/SMARTFLEET_RESEARCH_PAPER.md](file:///d:/students%20projects/iot-trasnport/docs/SMARTFLEET_RESEARCH_PAPER.md)) was performed against the actual SMARTFLEET implementation in `backend/app/`, the test harnesses, and raw empirical benchmark files.

The core cryptographic architecture (IBE-KEM + AES-256-GCM + Ed25519 + replay protection) is verified, functional, and empirically benchmarked. However, the audit revealed several significant technical discrepancies between the paper's theoretical exposition and the actual implementation:

1. **Curve Group Assignment Inversion:** The paper claims $P_{pub}, U \in \mathbb{G}_1$ and $Q_{srv}, d_{srv} \in \mathbb{G}_2$. The actual implementation in `ibe_service.py` assigns $Q_{ID}, d_{ID} \in \mathbb{G}_1$ and $P_{pub}, U \in \mathbb{G}_2$, utilizing asymmetric Type-3 pairing `pairing(G2_point, G1_point)`.
2. **KDF Construction Discrepancy:** The paper claims direct SHA-256 key derivation over $U \parallel g_{id} \parallel ID_{srv}$. The implementation uses **HKDF-SHA256** with a random 16-byte salt, fixed `info=b"IBE-TELEMETRY-AES256GCM"`, and stringified FQ12 pairing output without $U$ or $ID_{srv}$.
3. **Signed Data Discrepancy:** The paper claims Ed25519 signs the unencrypted payload hash $H(M) \parallel AAD$. The actual code (`secure_transmission_service.py`) signs the **ciphertext bundle JSON envelope** alongside transmission metadata (`SENDER`, `RECIPIENT`, `MSGID`, `TS`), never hashing the unencrypted plaintext at the signature layer.
4. **AAD Format Discrepancy:** The paper claims AAD is a canonical JSON dictionary containing `vehicle_id`, `timestamp`, `nonce`, and `message_id`. The actual code constructs a colon-separated UTF-8 byte string: `f"{sender}:{recipient}:{msg_id}:{ts}".encode("utf-8")`.
5. **Replay Cache & Locking Mechanics:** The paper claims a compound unique index on `(vehicle_id, nonce)` with explicit row-level locks. The actual database table `processed_message_cache` enforces a unique constraint on `message_id` alone and relies on **PostgreSQL nested transaction savepoints (`db.begin_nested()`)**, not row-level locking.
6. **API Response Code Discrepancy:** The paper's Table 6 reports HTTP 400 and HTTP 401 response codes for rejected attacks. The actual API returns **HTTP 200 OK** with a JSON envelope containing `status: "rejected"`, `rejection_reason: "..."`, and `telemetry_persisted: false` to allow persistent audit logging of attack attempts in `secure_transmissions`.
7. **Empirical Benchmark Latency Discrepancy:** For large payloads, the paper reports a plaintext latency of **47.58 ms** and a multiplier of **169.7×**. The raw benchmark dataset (`step_6_2_benchmark_data.json`) records a plaintext latency of **35.87 ms**, which yields an actual multiplier of **225.1×** ($8,074.06 / 35.87$).
8. **Python Runtime Version:** The paper claims Python 3.12; the benchmark metadata explicitly records Python 3.11.9.

---

## 2. Verified Implementation Facts

### 2.1 IBE-KEM Implementation (`backend/app/services/ibe_service.py`)

- **Elliptic Curve:** Barreto–Naehrig 128-bit security curve (`alt_bn128` / BN128) via `py_ecc.bn128`.
- **Curve Groups:**
  - $\mathbb{G}_1$: Curve $y^2 = x^3 + 3$ over base prime field $\mathbb{F}_p$ (`FQ`). Generator: `G1`.
  - $\mathbb{G}_2$: Twist curve over extension field $\mathbb{F}_{p^2}$ (`FQ2`). Generator: `G2`.
  - $\mathbb{G}_T$: Target group in extension field $\mathbb{F}_{p^{12}}$ (`FQ12`).
  - Order: Prime $q = \text{curve\_order} = 21888242871839275222246405745257275088548364400416034343698204186575808495617$.
- **Hash-to-Curve ($H_1$):**
  - Function: `_hash_to_g1(identity: str) -> Tuple[FQ, FQ]`.
  - Input: String `identity`.
  - Output: Point $Q_{ID} \in \mathbb{G}_1$.
  - Algorithm: Deterministic Try-and-Increment using SHA-256 digests of `f"IBE-HASH-G1:{identity}:{counter}"`. Computes $x = \text{digest} \pmod p$, evaluates $y^2 = x^3 + 3 \pmod p$, tests Euler's criterion, and takes modular square root $y = (y^2)^{(p+1)/4} \pmod p$.
- **Master Keys:**
  - Master Secret: Scalar $s \leftarrow_R [2, q - 1]$ stored locally in `.ibe_keys/master_secret.key`.
  - Master Public Key: $P_{pub} = s \cdot G_2 \in \mathbb{G}_2$ (`multiply(G2, s)`).
  - Private Key Derivation: $d_{ID} = s \cdot Q_{ID} \in \mathbb{G}_1$ (`multiply(Q_id, s)`).
- **Encapsulation:**
  - Ephemeral scalar: $r \leftarrow_R [2, q - 1]$.
  - Ephemeral public point: $U = r \cdot G_2 \in \mathbb{G}_2$ (`multiply(G2, r)`).
  - Pairing computation: `pair_val = pairing(P_pub, Q_id)` where $P_{pub} \in \mathbb{G}_2, Q_{ID} \in \mathbb{G}_1$.
  - Shared pairing secret: $g^r = (\text{pair\_val})^r \in \mathbb{G}_T$.
- **Decapsulation:**
  - Reconstructs $U \in \mathbb{G}_2$ and retrieves private key $d_{ID} \in \mathbb{G}_1$.
  - Computes pairing: $\text{pair\_val} = \text{pairing}(U, d_{ID}) = e(r \cdot G_2, s \cdot Q_{ID}) = e(G_2, Q_{ID})^{rs} = e(s \cdot G_2, Q_{ID})^r = g^r$.
- **py_ecc Pairing Argument Order:**
  - Function signature: `pairing(Q, P)` where $Q \in \mathbb{G}_2$ and $P \in \mathbb{G}_1$.
- **Pairing Output Serialization:**
  - Serialized via standard Python string conversion: `pairing_bytes = str(shared_pairing_elem).encode("utf-8")`.
- **Key Derivation Function (KDF):**
  - Implements **HKDF-SHA256** from `cryptography.hazmat.primitives.kdf.hkdf.HKDF`.
  - Salt: Ephemeral 16-byte random token (`secrets.token_bytes(16)`), base64-encoded into `salt_b64`.
  - Info: Fixed byte string `b"IBE-TELEMETRY-AES256GCM"`.
  - Derived Key: 32 bytes (256-bit AES key).

### 2.2 Ed25519 Digital Signatures (`backend/app/services/secure_transmission_service.py`)

- **Fields Included in Signature:**
  Constructed by `compute_canonical_signature_message()`:
  ```
  SENDER:{sender_identity}
  RECIPIENT:{recipient_identity}
  MSGID:{message_id}
  TS:{timestamp_str}
  CT:{canonical_bundle}
  ```
  where `canonical_bundle` is deterministic canonical JSON (`sort_keys=True, separators=(",", ":")`) of the `ciphertext_bundle` dict containing:
  - `u_point`: BN128 coordinate dict `{"x": [...], "y": [...]}`
  - `salt_b64`: Base64 salt string
  - `nonce_b64`: Base64 12-byte AES IV
  - `ciphertext_b64`: Base64 AES-256-GCM ciphertext + 16-byte tag
  - `payload_size_bytes`, `ciphertext_size_bytes`, `encryption_duration_ms`
- **Plaintext Coverage:** The unencrypted telemetry plaintext is **NOT** included in the signature. The signature cryptographically binds the metadata and the encrypted envelope.
- **Verification Sequence:** Ed25519 verification occurs in **Stage 2**, strictly **before** IBE decapsulation (Stage 4).

### 2.3 AES-256-GCM & Replay Protection (`secure_transmission_service.py` & `models/secure_transmission.py`)

- **Authenticated Associated Data (AAD):**
  - Exact construction: `f"{sender_identity}:{recipient_identity}:{message_id}:{timestamp_str}".encode("utf-8")`.
  - Fields bound: `sender_identity`, `recipient_identity`, `message_id`, `timestamp`.
- **Timestamp Limits:**
  - Future Drift: `MAX_FUTURE_SKEW_SECONDS = 30.0` (max 30 seconds ahead of server clock).
  - Past Staleness: `MAX_TIMESTAMP_SKEW_SECONDS = 300` (max 5 minutes behind server clock).
- **Replay Protection Mechanics:**
  - Table: `processed_message_cache`.
  - Columns: `id` (PK), `message_id` (VARCHAR(64), `unique=True`, indexed), `sender_identity` (VARCHAR(120)), `received_at` (TIMESTAMP WITH TIME ZONE).
  - Uniqueness constraint: On `message_id` alone.
  - Concurrency control: Executes an atomic insert inside a SQLAlchemy nested savepoint (`with db.begin_nested():`). If another transaction has inserted the same `message_id`, PostgreSQL raises a unique constraint violation, which is caught and cleanly rolled back without aborting the parent transaction.
  - Row-Level Locking: **No** explicit `SELECT ... FOR UPDATE` row locks are acquired; concurrency safety relies strictly on PostgreSQL's unique constraint and transaction savepoints.
- **Concurrent Replay Test:**
  - Dispatched 6 simultaneous parallel worker threads with identical payload and `message_id`.
  - Recorded Result: Exactly 1 succeeded (persisted), exactly 5 rejected with `"Replay attack detected: Message nonce already processed"`. Zero duplicate rows created.

### 2.4 Blind Quantum Computing & QUBO Implementations

- **BQC Implementation (`backend/app/services/bqc/`):**
  - Protocol: BFK09 Measurement-Based Blind Quantum Computing (MBQC).
  - Simulated Cluster Topologies:
    - 2 Candidates ($M=2$): **4-qubit linear cluster state** (`edges = [(0, 1), (1, 2), (2, 3)]`).
    - 4 Candidates ($M=4$): **6-qubit ladder cluster state** (`edges = [(0, 1), (1, 2), (3, 4), (4, 5), (1, 4)]`).
  - Meaning of $\Delta H = 0$: In `bqc_orchestrator.py`, Shannon entropy of transmitted blinded angles $\delta_j$ evaluates to $H(\delta) \approx 3.0$ bits across the 8-angle set $\Theta = \{k\pi/4 \mid k \in [0, 7]\}$. $\Delta H = 0$ signifies zero empirical divergence from the theoretical maximum entropy ($\log_2(8) = 3.0$), indicating that the server's view of blinded angles is uniformly distributed.
  - Proof of Blindness: Broadbent et al. (2009) established the theoretical proof; this repository provides an empirical software simulation, not a formal mechanical code verification.
- **QUBO Implementation (`backend/app/services/routing/qubo_routing_service.py`):**
  - Decision Variables: $x_{v, i, t} \in \{0, 1\}$ representing vehicle $v$ visiting waypoint $i$ at tour step $t$.
  - Matrix Size: $M = V \times N \times T$ where $V$ is vehicles, $N$ is destinations, and $T$ is max steps.
  - Index bijection: $u = v \cdot (N \cdot T) + i \cdot T + t$.
  - Constraints & Penalties:
    - Destination visitation: $P_{visit} \sum_i (\sum_{v,t} x_{v,i,t} - 1)^2$
    - Slot uniqueness: $P_{slot} \sum_{v,t} \sum_{i < j} x_{v,i,t} x_{v,j,t}$
    - Route contiguity: $P_{contig} \sum_v \sum_{t < T-1} [\dots]$
    - Vehicle capacity: Soft quadratic penalty $P_{cap} \sum_v \sum_{i < j} \sum_{t, t'} \frac{q_i q_j}{C_v^2} x_{v,i,t} x_{v,j,t'}$
  - Nature of Constraints: All constraints are **soft penalties** in an unconstrained quadratic Hamiltonian objective, as required by QUBO.

---

## 3. Incorrect or Unsupported Paper Claims

The following table itemizes every statement in [docs/SMARTFLEET_RESEARCH_PAPER.md](file:///d:/students%20projects/iot-trasnport/docs/SMARTFLEET_RESEARCH_PAPER.md) that is inaccurate, inverted, or unsupported by the verified codebase:

| Ref # | Paper Section & Claim | Actual Implementation Fact | Impact / Severity |
| :---: | :--- | :--- | :--- |
| **C-01** | **Section 4.1:** States $P_{pub} \in \mathbb{G}_1$, $Q_{srv} \in \mathbb{G}_2$, $d_{srv} \in \mathbb{G}_2$, $U \in \mathbb{G}_1$. | In `ibe_service.py`, $Q_{ID} \in \mathbb{G}_1$, $d_{ID} \in \mathbb{G}_1$, $P_{pub} \in \mathbb{G}_2$, and $U \in \mathbb{G}_2$. | **High:** Cryptographic equation inversion. |
| **C-02** | **Section 4.1:** States KDF is $K_{sym} = \text{SHA-256}(U \parallel g_{id} \parallel ID_{srv})$. | Implementation uses `HKDF(algorithm=SHA256, length=32, salt=salt, info=b"IBE-TELEMETRY-AES256GCM").derive(str(shared_pairing_elem).encode("utf-8"))`. Neither $U$ nor $ID$ is fed into HKDF. | **High:** Inaccurate KDF specification. |
| **C-03** | **Section 4.2:** States AAD is `CanonicalJSON({"vehicle_id": ..., "timestamp": ..., "nonce": ..., "message_id": ...})`. | Implementation computes colon-separated string: `f"{sender}:{recipient}:{message_id}:{timestamp}".encode("utf-8")`. | **Medium:** Inaccurate wire format. |
| **C-04** | **Section 4.3:** States signature is $\sigma = \text{Ed25519-Sign}(sk_{veh}, H(M) \parallel AAD)$. | Implementation signs canonical string covering metadata and the ciphertext bundle JSON: `SENDER:...\nRECIPIENT:...\nMSGID:...\nTS:...\nCT:{canonical_bundle}`. Plaintext $M$ is not hashed. | **High:** Inaccurate signing equation. |
| **C-05** | **Section 4.5:** States cache has compound unique constraint on `(vehicle_id, nonce)`. | Model `ProcessedMessageCache` has unique constraint on `message_id` alone. | **Medium:** Inaccurate database schema claim. |
| **C-06** | **Section 4.5:** Claims database-level row locking (`SELECT FOR UPDATE`). | Implementation uses nested savepoint `with db.begin_nested():` and catches unique constraint violations on `db.flush()`. No row locks used. | **Medium:** Technical mechanism misstatement. |
| **C-07** | **Section 5.1 (Table 1):** States runtime is Python 3.12. | Raw benchmark metadata records Python 3.11.9. | **Low:** Minor version discrepancy. |
| **C-08** | **Section 5.3 (Table 3):** States micro-benchmark sample count $N=30$ for signatures and $N=15$ for IBE. | Script `run_step_6_2_benchmarks.py` ran `TRIALS = 10` for all micro-benchmarks. | **Low:** Sample count discrepancy. |
| **C-09** | **Section 5.3 (Table 3):** Signature P95 latencies reported as 1.15 ms (sign) and 0.48 ms (verify). | Raw JSON records P95 as 1.18 ms (sign) and 0.62 ms (verify). | **Low:** Minor rounding / historical discrepancy. |
| **C-10** | **Section 5.4 (Table 4):** Reports large-payload plaintext mean latency as 47.58 ms and multiplier as 169.7×. | Raw JSON records large plaintext mean as **35.87 ms**, yielding an actual multiplier of **225.1×** ($8,074.06 / 35.87$). | **Medium:** Quantitative data discrepancy. |
| **C-11** | **Section 5.5 (Table 5):** Fleet scalability times reported as 8.07s, 40.48s, 80.95s, 203.22s. | Raw JSON records 7.96s (1 veh), 40.37s (5 veh), 80.45s (10 veh), 203.35s (25 veh). | **Low:** Minor decimal discrepancy. |
| **C-12** | **Section 6 (Table 6):** Reports HTTP 400 and 401 response codes for rejected attack vectors. | Ingestion route `/api/secure-transmission/encrypted` returns **HTTP 200 OK** with JSON body `{status: "rejected", rejection_reason: "...", telemetry_persisted: false}`. | **High:** HTTP protocol behavior discrepancy. |
| **C-13** | **Section 7.1:** Claims BQC simulation runs on "4-qubit Brickwork cluster states". | Implemented topologies are a 4-qubit linear cluster state ($M=2$) and a 6-qubit ladder cluster state ($M=4$). | **Medium:** Graph topology misstatement. |
| **C-14** | **Section 7.2:** Formulates QUBO variables as edge transitions $x_{i,j,k} \in \{0, 1\}$. | Implementation uses tour-step variables $x_{v,i,t} \in \{0, 1\}$ (vehicle $v$ visits waypoint $i$ at step $t$). | **Medium:** Inaccurate mathematical formulation. |

---

## 4. Exact Mathematical Equations for Paper Correction

To make the research paper mathematically and technically exact, the equations in Section 4 and Section 7 must be replaced as follows:

### 4.1 IBE-KEM Formulation (Replacing Section 4.1)

Let $\mathbb{G}_1, \mathbb{G}_2, \mathbb{G}_T$ be cyclic groups of prime order $q$ defined over the Barreto–Naehrig curve (BN128), equipped with an asymmetric optimal ate pairing:
$$e: \mathbb{G}_2 \times \mathbb{G}_1 \rightarrow \mathbb{G}_T$$
where $G_1 \in \mathbb{G}_1$ and $G_2 \in \mathbb{G}_2$ are canonical generators.

1. **Setup:**
   $$\text{Master Secret } s \leftarrow_R \mathbb{Z}_q^*$$
   $$\text{Master Public Parameter } P_{pub} = s \cdot G_2 \in \mathbb{G}_2$$
2. **Key Extraction:**
   For recipient identity $ID \in \{0, 1\}^*$, map to curve point $Q_{ID} = H_1(ID) \in \mathbb{G}_1$ using try-and-increment hashing over $y^2 = x^3 + 3 \pmod p$. The private decapsulation key is:
   $$d_{ID} = s \cdot Q_{ID} \in \mathbb{G}_1$$
3. **Encapsulation:**
   The sender samples ephemeral scalar $r \leftarrow_R \mathbb{Z}_q^*$ and computes:
   $$U = r \cdot G_2 \in \mathbb{G}_2$$
   $$g_{id} = e(P_{pub}, Q_{ID})^r \in \mathbb{G}_T$$
   The symmetric key $K_{sym}$ is derived via HKDF-SHA256:
   $$K_{sym} = \text{HKDF-SHA256}\Big(\text{IKM}=\text{str}(g_{id}), \text{salt}=\text{salt}_{16}, \text{info}=\text{"IBE-TELEMETRY-AES256GCM"}\Big)$$
   The encapsulation ciphertext component is $C_{ibe} = (U, \text{salt}_{16})$.
4. **Decapsulation:**
   The server recovers the pairing element using its private key $d_{ID} \in \mathbb{G}_1$:
   $$g_{id}' = e(U, d_{ID}) = e(r \cdot G_2, s \cdot Q_{ID}) = e(G_2, Q_{ID})^{rs} = e(s \cdot G_2, Q_{ID})^r = e(P_{pub}, Q_{ID})^r = g_{id}$$
   $$K_{sym} = \text{HKDF-SHA256}\Big(\text{IKM}=\text{str}(g_{id}'), \text{salt}=\text{salt}_{16}, \text{info}=\text{"IBE-TELEMETRY-AES256GCM"}\Big)$$

---

### 4.2 Authenticated Associated Data (AAD) Construction (Replacing Section 4.2)

$$AAD = \text{UTF8}\Big(V_{sender} \parallel \text{":"} \parallel V_{recipient} \parallel \text{":"} \parallel M_{id} \parallel \text{":"} \parallel T\Big)$$
$$(C_{sym}, \tau) = \text{AES-GCM-Encrypt}_{K_{sym}}(IV_{96}, M, AAD)$$

---

### 4.3 Ed25519 Digital Signature Construction (Replacing Section 4.3)

Let $B_{ct}$ be the canonical JSON serialization of the complete ciphertext bundle dictionary (containing $U$, $\text{salt}$, $IV$, $C_{sym}$, and metadata). The data string to sign is constructed as:
$$\text{DataToSign} = \text{"SENDER:"} \parallel V_{sender} \parallel \text{"\nRECIPIENT:"} \parallel V_{recipient} \parallel \text{"\nMSGID:"} \parallel M_{id} \parallel \text{"\nTS:"} \parallel T \parallel \text{"\nCT:"} \parallel B_{ct}$$
$$\sigma = \text{Ed25519-Sign}\Big(sk_{veh}, \text{DataToSign}\Big)$$

The recipient verifies:
$$\text{Ed25519-Verify}\Big(pk_{veh}, \text{DataToSign}, \sigma\Big) \stackrel{?}{=} \text{True}$$

---

### 4.4 QUBO Decision Variables & Hamiltonian (Replacing Section 7.2)

Let $x_{v, i, t} \in \{0, 1\}$ be binary decision variables indicating whether vehicle $v \in \{0, \dots, V-1\}$ visits waypoint $i \in \{0, \dots, N-1\}$ at tour step $t \in \{0, \dots, T-1\}$.

The Hamiltonian objective function is:
$$\begin{aligned}
H(x) = &\sum_{v=0}^{V-1} \sum_{i=0}^{N-1} d_{depot, i} \cdot x_{v, i, 0} + \sum_{v=0}^{V-1} \sum_{t=0}^{T-2} \sum_{i=0}^{N-1} \sum_{j=0}^{N-1} d_{i, j} \cdot x_{v, i, t} \cdot x_{v, j, t+1} + \sum_{v=0}^{V-1} \sum_{i=0}^{N-1} d_{i, depot} \cdot x_{v, i, T-1} \\
&+ P_{visit} \sum_{i=0}^{N-1} \Big(\sum_{v=0}^{V-1} \sum_{t=0}^{T-1} x_{v, i, t} - 1\Big)^2 + P_{slot} \sum_{v=0}^{V-1} \sum_{t=0}^{T-1} \sum_{i < j} x_{v, i, t} \cdot x_{v, j, t} \\
&+ P_{contig} \sum_{v=0}^{V-1} \sum_{t=0}^{T-2} \Big(\sum_{i=0}^{N-1} x_{v, i, t+1} - \sum_{i=0}^{N-1} \sum_{j=0}^{N-1} x_{v, i, t+1} \cdot x_{v, j, t}\Big) \\
&+ P_{cap} \sum_{v=0}^{V-1} \sum_{i < j} \sum_{t=0}^{T-1} \sum_{t'=0}^{T-1} \frac{q_i \cdot q_j}{C_v^2} \cdot x_{v, i, t} \cdot x_{v, j, t'}
\end{aligned}$$

---

## 5. Benchmark Discrepancies & Raw-Data Resolutions

The following table presents the authoritative reconciliation between raw empirical data (`scratch/step_6_2_benchmark_data.json`) and the values currently published in the research paper:

| Benchmark Metric | Current Paper Value | Raw Dataset Value | Resolution / Authoritative Statement |
| :--- | :---: | :---: | :--- |
| **Python Version** | Python 3.12 | Python 3.11.9 | Resolve to **Python 3.11.9** (exact environment used during trial execution). |
| **Micro-Benchmark Samples** | $N=30$ / $N=15$ | $N=10$ trials | Resolve to **$N=10$** trials (matches `TRIALS = 10` in benchmark script). |
| **Signature Verify P95** | 0.48 ms | 0.62 ms | Resolve to **0.62 ms** (exact percentile in raw JSON). |
| **Signature Sign P95** | 1.15 ms | 1.18 ms | Resolve to **1.18 ms** (exact percentile in raw JSON). |
| **Small Plaintext Mean** | 51.96 ms | 51.96 ms | Verified (matches raw data; median = 32.52 ms). |
| **Small Protected Mean** | 8,775.76 ms | 8,775.76 ms | Verified (matches raw data; multiplier = **168.9×**). |
| **Medium Plaintext Mean** | 34.94 ms | 34.94 ms | Verified (matches raw data; median = 32.71 ms). |
| **Medium Protected Mean** | 8,845.67 ms | 8,845.67 ms | Verified (matches raw data; multiplier = **253.2×**). |
| **Large Plaintext Mean** | **47.58 ms** | **35.87 ms** | **Discrepancy:** The paper copied an unverified historical value (47.58 ms). The raw benchmark data records **35.87 ms** (median = 34.53 ms, min = 30.44 ms, max = 46.42 ms). |
| **Large Latency Multiplier** | **169.7×** | **225.1×** | **Discrepancy:** With raw plaintext mean 35.87 ms, the true multiplier is $8,074.06 / 35.87 = \mathbf{225.09\times}$ (approx **225.1×**). |
| **1-Vehicle Scaling Time** | 8.07 s | 7.96 s | Raw JSON records **7.96 s** (throughput = 0.13 msg/s, avg latency = 7,964.47 ms). |
| **5-Vehicle Scaling Time** | 40.48 s | 40.37 s | Raw JSON records **40.37 s** (throughput = 0.12 msg/s, avg latency = 8,074.54 ms). |
| **10-Vehicle Scaling Time** | 80.95 s | 80.45 s | Raw JSON records **80.45 s** (throughput = 0.12 msg/s, avg latency = 8,044.50 ms). |
| **25-Vehicle Scaling Time** | 203.22 s | 203.35 s | Raw JSON records **203.35 s** (throughput = 0.12 msg/s, avg latency = 8,134.02 ms). |
| **Wire Expansion Small** | +572.68% | +572.68% | Verified (183 B $\rightarrow$ 1,231 B, +1,048 B). |
| **Wire Expansion Medium** | +116.28% | +116.28% | Verified (1,192 B $\rightarrow$ 2,578 B, +1,386 B). |
| **Wire Expansion Large** | +48.35% | +48.35% | Verified (6,575 B $\rightarrow$ 9,754 B, +3,179 B). |

---

## 6. Security-Test Traceability Matrix

The table below maps the 13 attack scenarios described in the paper against the actual test implementation in `scratch/audit_security_scenarios.py` and `scratch/step_6_1_audit_results.json`:

| Scenario ID | Paper Attack Name | Actual Test Implementation | Adversarial Input | Paper Expected Status | Actual Observed API Status | Actual Rejection Reason Recorded | DB Integrity Checked? |
| :---: | :--- | :--- | :--- | :---: | :---: | :--- | :---: |
| **S-01** | Valid Authorized Telemetry | `Authorized Vehicle Transmission` | Valid envelope with correct Ed25519 signature & IBE ciphertext | 200 OK | **HTTP 200** | `status: "success"` (Telemetry persisted) | Yes (+1 row) |
| **S-02** | Ciphertext Bit Modification | `Ciphertext Body Bit-Flipping Tampering` | Bit flipped in `ciphertext_b64` | 400 Bad Request | **HTTP 200** | `status: "rejected"`, `reason: "Cryptographic integrity verification failed: Invalid, forged, or tampered Ed25519 signature / envelope."` *(Caught by Ed25519 first!)* | Yes (0 rows added) |
| **S-03** | Tampered Authentication Tag | `AES-GCM Authentication Tag Tampering` | Corrupted trailing 16 bytes of ciphertext bundle | 400 Bad Request | **HTTP 200** | `status: "rejected"`, `reason: "Cryptographic integrity verification failed: Invalid, forged, or tampered Ed25519 signature / envelope."` *(Caught by Ed25519 first!)* | Yes (0 rows added) |
| **S-04** | Modified IV / Nonce Parameter | Tested via unit test `test_tampered_envelope` | Modified `nonce_b64` in bundle | 400 Bad Request | **HTTP 200** | `status: "rejected"`, caught by Ed25519 envelope signature check | Yes (0 rows added) |
| **S-05** | Identity Tampering in AAD | `Cross-Vehicle Identity Substitution` | Sender identity differs from enrolled vehicle ID | 400 Bad Request | **HTTP 200** | `status: "rejected"`, `reason: "Cross-vehicle identity substitution detected: claimed 'SIM-VEH-002' does not match authenticated identity 'SIM-VEH-001'."` | Yes (0 rows added) |
| **S-06** | Corrupted IBE Ephemeral Point | Tested in `test_ibe_service.py` | Invalid FQ2 coordinates in `u_point` | 400 Bad Request | **HTTP 200** | `status: "rejected"`, caught by Ed25519 signature or point unmarshaling error | Yes (0 rows added) |
| **S-07** | Invalid Ed25519 Signature | `Corrupted / Invalid Ed25519 Signature` | Arbitrary garbage bytes in `signature_b64` | 401 Unauthorized | **HTTP 200** | `status: "rejected"`, `reason: "Cryptographic integrity verification failed: Invalid, forged, or tampered Ed25519 signature / envelope."` | Yes (0 rows added) |
| **S-08** | Signature / Payload Mismatch | `Vehicle Impersonation (Rogue Ed25519 Key)` | Valid signature from non-enrolled private key | 401 Unauthorized | **HTTP 200** | `status: "rejected"`, `reason: "Cryptographic integrity verification failed: Invalid, forged, or tampered Ed25519 signature / envelope."` | Yes (0 rows added) |
| **S-09** | Replay of Intercepted Message | `Exact Message Replay Attack` | Duplicate resubmission of accepted legitimate envelope | 400 Bad Request | **HTTP 200** | `status: "rejected"`, `reason: "Duplicate message identifier '...' (Replay attack detected)."` | Yes (0 rows added) |
| **S-10** | Expired Message Timestamp | `Expired / Stale Timestamp (> 300s window)` | Timestamp 600 seconds in past | 400 Bad Request | **HTTP 200** | `status: "rejected"`, `reason: "Message timestamp outside permitted freshness window (604.7s skew > 300s)."` | Yes (0 rows added) |
| **S-11** | Future-Drift Timestamp | `Excessive Future Timestamp (> 30s drift)` | Timestamp 120 seconds in future | 400 Bad Request | **HTTP 200** | `status: "rejected"`, `reason: "Message timestamp is in the future (114.7s ahead > 30.0s max skew tolerance)."` | Yes (0 rows added) |
| **S-12** | Unregistered Vehicle ID | `Unregistered / Unauthorized Vehicle` | `ROGUE-VEHICLE@external.attacker.net` | 404 / 401 Reject | **HTTP 200** | `status: "rejected"`, `reason: "Unauthorized sender identity (identity not registered in vehicle enrollments)."` | Yes (0 rows added) |
| **S-13** | Revoked Vehicle Access / Unauthorized API | `Unauthorized Master Secret Reinitialization` | POST to `/api/security/ibe/setup?force_reinit=true` | 403 Forbidden | **HTTP 403** | `detail: "Unrestricted master key reinitialization is disabled via the public API..."` | Yes (0 rows added) |

### Key Traceability Finding on Attack Interception:
Because Ed25519 signs the canonical ciphertext envelope (`canonical_bundle`), attacks S-02 (Ciphertext Bit Modification) and S-03 (Tag Modification) are intercepted at **Stage 2 (Ed25519 Signature Verification)** in **0.25 ms**, *before* reaching the AES-GCM decryption engine. This confirms the operation of the Pre-Decryption Anti-Oracle gate, but contradicts the paper's claim that S-02 and S-03 were rejected by the AES-GCM engine.

---

## 7. Recommended Paper Corrections

When updating [docs/SMARTFLEET_RESEARCH_PAPER.md](file:///d:/students%20projects/iot-trasnport/docs/SMARTFLEET_RESEARCH_PAPER.md), apply the following specific corrections:

1. **Update Section 4.1 (IBE Mathematical Formulation):**
   - Correct the group assignments: state that identity $Q_{ID} \in \mathbb{G}_1$, private key $d_{ID} \in \mathbb{G}_1$, master public parameter $P_{pub} \in \mathbb{G}_2$, and ephemeral public point $U \in \mathbb{G}_2$.
   - Specify the asymmetric pairing order: $e(P_{pub}, Q_{ID})$ and $e(U, d_{ID})$ where the first argument is in $\mathbb{G}_2$ and the second is in $\mathbb{G}_1$.
   - Replace the direct SHA-256 equation with HKDF-SHA256, detailing the 16-byte random salt, the fixed `info=b"IBE-TELEMETRY-AES256GCM"`, and stringified FQ12 pairing input.
2. **Update Section 4.2 (AAD Construction):**
   - Replace the JSON dictionary equation with the colon-separated byte string format: `f"{sender}:{recipient}:{message_id}:{timestamp}".encode("utf-8")`.
3. **Update Section 4.3 (Ed25519 Signature Formulation):**
   - Correct the signing equation: state that Ed25519 signs the canonical metadata string concatenating the deterministic JSON of `ciphertext_bundle`, rather than $H(M) \parallel AAD$.
   - Explain the security benefit: signing the ciphertext envelope enables sub-millisecond rejection of tampered ciphertexts and tags at the signature stage, protecting the pairing engine from DoS.
4. **Update Section 4.5 (Replay Protection Mechanism):**
   - Clarify that the unique constraint is on `message_id` in `processed_message_cache`.
   - Explain that concurrency protection relies on PostgreSQL nested savepoints (`db.begin_nested()`) and atomic insert flushes rather than explicit row-level locks.
5. **Update Section 5.1 & Section 5.3 (Benchmark Environment & Samples):**
   - Correct Python version from 3.12 to **3.11.9**.
   - Correct micro-benchmark trial count to $N=10$ trials.
   - Update signature P95 latencies to 1.18 ms (sign) and 0.62 ms (verify).
6. **Update Section 5.4 (End-to-End Latency Table 4):**
   - Replace the large-payload plaintext latency of 47.58 ms with the raw measurement of **35.87 ms**.
   - Update the large-payload latency multiplier from 169.7× to **225.1×** ($8,074.06 / 35.87$).
7. **Update Section 5.5 (Fleet Scalability Table 5):**
   - Update wall-clock times to match raw JSON: 7.96 s (1 veh), 40.37 s (5 veh), 80.45 s (10 veh), 203.35 s (25 veh).
8. **Update Section 6 (Security Evaluation Table 6):**
   - Clarify API status codes: explain that telemetry ingestion returns HTTP 200 with `{status: "rejected", telemetry_persisted: false}` to allow persistent audit logging of attack attempts, while administrative re-initialization returns HTTP 403 Forbidden.
   - Correct the mechanism for S-02 and S-03: note that tampered ciphertexts and tags are rejected by the Ed25519 envelope signature check in < 1 ms before reaching AES-GCM.
9. **Update Section 7.1 & 7.2 (BQC & QUBO Extensions):**
   - State that BQC simulations evaluated 4-qubit linear and 6-qubit ladder cluster states.
   - Correct the QUBO Hamiltonian to reflect tour-step decision variables $x_{v,i,t} \in \{0, 1\}$ and soft quadratic capacity penalties.
