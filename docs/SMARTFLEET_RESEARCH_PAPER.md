# SMARTFLEET: An Identity-Based Hybrid Cryptographic Architecture for Secure Vehicle Telemetry Ingestion in Intelligent Transportation Systems

**Authors:** SMARTFLEET Engineering Research Team  
**Institution:** Department of Computer Science and Engineering  
**Date:** October 2026  
**Document Classification:** Academic Research Paper (Final-Year Engineering Project Submission)

---

## Abstract

Intelligent Transportation Systems (ITS) and modern fleet management platforms depend critically on continuous edge-to-cloud telemetry transmission. Vehicles periodically transmit spatial coordinates, engine diagnostics, fuel metrics, and operational alerts over wireless vehicular ad-hoc networks (VANETs) and cellular uplinks. However, public channels expose vehicular telemetry to passive eavesdropping, man-in-the-middle tampering, spoofed vehicle telemetry, and replay attacks. Conventional Public Key Infrastructure (PKI) introduces severe operational complexity in vehicular environments due to X.509 certificate distribution, cryptographic chain-of-trust path validation, and dynamic certificate revocation lists (CRLs). 

In this paper, we propose, implement, and empirically evaluate **SMARTFLEET**, an identity-based hybrid cryptographic architecture designed specifically for resource-conscious vehicular telemetry ingestion. SMARTFLEET eliminates public-key certificate overhead by pairing Boneh–Franklin Identity-Based Encryption (IBE) over the Barreto–Naehrig 128-bit security curve (BN128) as a Key Encapsulation Mechanism (KEM) with AES-256-GCM Authenticated Encryption with Associated Data (AEAD). Telemetry authenticity and non-repudiation are enforced through Edwards-curve digital signatures (Ed25519) combined with an atomic, dual-layered sliding-window nonce and timestamp validation cache implemented at the database tier. 

We deployed an end-to-end implementation comprising a FastAPI backend, PostgreSQL relational persistence, a React/TypeScript telemetry management dashboard, and simulated IoT vehicle nodes. Rigorous empirical benchmarking across diverse payload profiles (183 B to 6,575 B) on commodity x86_64 hardware reveals an operational trade-off: IBE-KEM encapsulation and decapsulation consume an average of 4,469.55 ms and 3,923.50 ms respectively in pure-Python arithmetic, resulting in an end-to-end latency multiplier of 169.7× to 253.2× over unprotected HTTP transmission, while Ed25519 signature generation and verification execute in 0.75 ms and 0.25 ms. Automated security validation demonstrates a 100.0% rejection rate across 12 distinct adversarial attack vectors (including ciphertext corruption, signature forgery, timestamp manipulation, and replay attacks) under concurrent transaction loads without database corruption. Finally, we situate this transmission pipeline alongside an exploratory Blind Quantum Computing (BQC) client-server privacy-preserving simulation and a quadratic unconstrained binary optimization (QUBO) route assignment formulation, transparently documenting mathematical and physical limitations.

---

## Keywords

Intelligent Transportation Systems (ITS), Vehicle Telemetry Security, Identity-Based Encryption (IBE), Key Encapsulation Mechanism (KEM), AES-256-GCM, Ed25519, Replay Protection, Vehicular Ad-hoc Networks (VANETs), Empirical Benchmarking.

---

## 1. Introduction

Commercial fleet operations, public mass transit systems, and autonomous logistics rely on telematics-equipped vehicles that continuously sample onboard diagnostic (OBD-II) interfaces, global positioning system (GPS) receivers, and inertial measurement units (IMUs). Telemetry data—including vehicle geographic coordinates, speed, battery state-of-charge, engine coolant temperature, brake wear, and diagnostic trouble codes (DTCs)—is transmitted across cellular (4G LTE/5G) or IEEE 802.11p/DSRC links to centralized fleet management servers.

While continuous telemetry ingest enables dynamic fleet dispatching, predictive vehicle maintenance, and route optimization, it introduces acute cybersecurity vulnerabilities:
1. **Passive Surveillance and Privacy Leakage:** Unencrypted telemetry streams reveal fine-grained driver travel histories, geographic habits, operational routes, and cargo itineraries.
2. **Telemetry Spoofing and Unauthorized Injection:** Malicious adversaries can fabricate high-speed driving events, synthetic engine fault codes, or altered fuel readings to trigger unwarranted emergency responses or manipulate logistics scoring.
3. **Replay and Man-in-the-Middle (MitM) Attacks:** An eavesdropper intercepting valid, signed vehicle transmissions can retransmit past packets out of sequence to deceive dispatchers regarding a vehicle's real-time position or clear active alerts.
4. **Certificate Management Overhead in High-Mobility Fleets:** Conventional Public Key Infrastructure (PKI) requires distributing, caching, validating, and revoking X.509 digital certificates across thousands of distributed mobile units. Intermittent vehicular connectivity renders online certificate status protocol (OCSP) queries and certificate revocation lists (CRLs) prone to high latency and failure.

To address these limitations, this paper presents **SMARTFLEET**, an open, authenticated, identity-bound vehicular telemetry ingestion framework. Rather than deploying traditional X.509 certificate chains, SMARTFLEET adapts pairing-based Identity-Based Encryption (IBE) as a Key Encapsulation Mechanism (IBE-KEM) to securely derive ephemeral symmetric keys directly from the destination server's canonical identifier. Payload confidentiality and contextual integrity are guaranteed using AES-256-GCM with Authenticated Associated Data (AAD), while vehicle identity is cryptographically bound using high-speed Ed25519 digital signatures.

### Paper Contributions
- **Hybrid Cryptographic Pipeline:** Formulation and implementation of an IBE-KEM + AES-256-GCM + Ed25519 ingestion pipeline eliminating public-key certificate verification.
- **Fail-Safe Pre-Decryption Anti-Oracle Verification:** Design of a staged verification sequence that validates digital signatures, vehicle authorization status, and sliding-window replay caches prior to invoking pairing operations, neutralizing decryption-oracle vulnerabilities and resource-exhaustion Denial-of-Service (DoS) attacks.
- **Atomic Sliding-Window Replay Defense:** Formulation of a dual-layered timestamp freshness filter and unique nonce cache secured by database-level row locking and transaction savepoints.
- **Empirical Performance Profiling:** Concrete benchmarking of cryptographic execution latencies, transmission overhead, network payload expansion, and fleet scalability across realistic vehicular telemetry profiles.
- **Transparent Adversarial Evaluation:** Experimental validation of 12 distinct threat vectors, establishing verifiable rejection guarantees without state corruption.

---

## 2. Related Work

### 2.1 Vehicular Security and Public Key Infrastructure
Early vehicular security standards, such as IEEE 1609.2 and ETSI TS 102 940, rely on conventional PKI and Elliptic Curve Qu-Vanstone (ECQV) implicit certificates to establish trust in Vehicle-to-Vehicle (V2V) and Vehicle-to-Infrastructure (V2I) communications [1]. While mathematically robust, managing certificate validation paths across intermittent cellular links imposes non-negligible computational and communication overhead [2]. Storing and periodically refreshing CRLs in resource-constrained electronic control units (ECUs) often results in latency bottlenecks or fallback to insecure unauthenticated modes during connectivity dropouts.

### 2.2 Identity-Based Cryptography in IoT
Identity-Based Encryption, originally conceptualized by Shamir [3] and realized through bilinear pairings on elliptic curves by Boneh and Franklin [4], enables an entity's arbitrary identifier (e.g., an email address, IP, or domain URI) to serve directly as its public key. In vehicular telemetry scenarios, this property allows an IoT edge device to encrypt data directly to `"smartfleet:server:telemetry"` using public domain parameters, completely eliminating certificate exchange, trust-chain parsing, and revocation checks at the vehicle node [5]. However, pairing operations over pairing-friendly curves (such as BN128 or BLS12-381) involve complex extension field arithmetic, requiring hybrid encapsulation designs to mitigate pairing latency [6].

### 2.3 Authenticated Symmetric Ciphers and Signatures
Standard transport encryption protocols (such as TLS 1.3) protect client-server connections at the transport layer, but fail to guarantee end-to-end application-layer payload non-repudiation when data passes through intermediate API gateways, edge proxies, or message brokers. AES-GCM (Galois/Counter Mode) provides high-performance authenticated encryption with associated data (AEAD) [7]. Binding header metadata—such as vehicle identifiers, timestamps, and message nonces—into the Authenticated Associated Data (AAD) guarantees that any tampering with routing metadata immediately invalidates the authentication tag before plaintext processing. To provide sender non-repudiation with minimal overhead, Ed25519 (EdDSA over Curve25519) offers high-speed signature generation and verification with compact 64-byte signatures resistant to side-channel timing attacks [8].

### 2.4 Research Gap Addressed
Prior literature frequently evaluates IBE or digital signatures in isolation using synthetic micro-benchmarks, or models vehicular communication analytically without measuring database transaction overhead, replay protection under concurrent race conditions, or full serialization costs. This work implements an end-to-end, reproducible software prototype that captures realistic system-level bottlenecks and adversarial rejection dynamics.

---

## 3. System Architecture and Threat Model

### 3.1 Proposed System Architecture
The SMARTFLEET architecture spans four operational layers, illustrated in Figure 1:

```
+-----------------------------------------------------------------------------------+
|                            IoT VEHICLE EDGE TIER                                  |
|  [GPS / OBD-II Sensors] --> [Telemetry Model] --> [Ed25519 Sign] --> [IBE+AES]   |
+-----------------------------------------------------------------------------------+
                                          |
                         HTTPS Cellular / 802.11p Uplink
                                          v
+-----------------------------------------------------------------------------------+
|                        FASTAPI INGESTION & GATEWAY TIER                           |
|   1. Envelope Validation    2. Replay Check    3. Ed25519 Verify    4. IBE Decrypt|
+-----------------------------------------------------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                       POSTGRESQL STORAGE & PERSISTENCE                            |
|    [telemetry_records]     [processed_message_cache]     [secure_transmissions]   |
+-----------------------------------------------------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                         REACT / TYPESCRIPT OPERATOR UI                            |
|     Live Fleet Map    |    Security Audit Console    |   Performance Analytics    |
+-----------------------------------------------------------------------------------+
```
*Figure 1: High-level SMARTFLEET architectural decomposition and data ingestion flow.*

1. **IoT Vehicle Edge Tier:** Vehicle nodes gather operational parameters, construct structured telemetry payloads, execute Ed25519 canonical signing, encapsulate an ephemeral AES key using the server's public identity via IBE-KEM, and transmit a unified encrypted envelope.
2. **Ingestion & Security Gateway Tier:** Implemented in FastAPI, this tier enforces a strict pipeline: JSON schema validation, vehicle registration verification, timestamp/nonce replay verification, Ed25519 digital signature validation, and finally IBE decapsulation and AES-GCM decryption.
3. **Relational Persistence Tier:** A dedicated PostgreSQL database storing committed telemetry records, vehicle master registries, audit trails, and an atomic sliding-window cache.
4. **Operator Management Dashboard:** A React 18 / TypeScript single-page application providing real-time fleet map tracking, security experiment verification, and cryptographic audit logging.

### 3.2 Threat Model and Security Assumptions
We consider an adversarial environment characterized by the standard Dolev–Yao model, wherein the network medium is insecure:
- **Eavesdropping:** An adversary can intercept all vehicular transmissions over cellular or radio links.
- **Message Modification:** An adversary can alter ciphertexts, modify headers, truncate payloads, or alter initialization vectors (IVs).
- **Identity Spoofing and Forgery:** An adversary can attempt to transmit telemetry using an arbitrary vehicle ID without possessing its private key.
- **Replay Attacks:** An adversary can record valid, historically accepted packets and retransmit them at arbitrary future times to corrupt state or mask vehicle movements.
- **Decryption-Oracle Attacks:** An adversary can submit malformed or crafted ciphertexts to measure server error responses or processing latencies.

**Out-of-Scope Assumptions:** Physical hardware tampering of vehicle electronic control units (ECUs), memory extraction via physical hardware probes, side-channel attacks on vehicle power supplies, and catastrophic compromise of the Private Key Generator (PKG) master encryption secret are outside the operational boundary of this prototype.

---

## 4. Secure Transmission Methodology

The SMARTFLEET secure transmission mechanism integrates four cryptographic building blocks into a cohesive, fail-safe ingestion pipeline.

```
       Vehicle Edge Node                             Ingestion Server
              |                                             |
   Generate Telemetry (M)                                   |
              |                                             |
   Sign: σ = Ed25519(sk_veh, H(M))                          |
              |                                             |
   Encapsulate: (K_sym, C_ibe) = IBE_Enc(ID_srv)            |
   Encrypt: (C_sym, tag) = AES_GCM(K_sym, IV, M, AAD)       |
              |                                             |
              |---- POST /api/secure/transmit-telemetry --->|
              |     [ Envelope: C_ibe, C_sym, tag, σ ]      |
              |                                             |
              |                                     1. Check Timestamp Freshness
              |                                     2. Check Nonce (Atomic Lock)
              |                                     3. Verify Ed25519(pk_veh, σ)
              |                                     4. Decapsulate K_sym = IBE_Dec(sk_srv, C_ibe)
              |                                     5. Decrypt M = AES_GCM_Dec(K_sym, C_sym, tag)
              |                                     6. Commit Telemetry & Cache
              |<--- HTTP 200 OK (Status: Success) ---------|
```
*Figure 2: Sequence flow of the SMARTFLEET vehicle-to-server transmission protocol.*

### 4.1 Identity-Based Key Encapsulation (IBE-KEM)
We implement the Boneh–Franklin IBE scheme over the Barreto–Naehrig 128-bit security curve (BN128). Let $\mathbb{G}_1, \mathbb{G}_2$ be cyclic groups of prime order $q$, and $\mathbb{G}_T$ be the target group equipped with an optimal ate bilinear pairing $e: \mathbb{G}_1 \times \mathbb{G}_2 \rightarrow \mathbb{G}_T$.

1. **Setup:** The Private Key Generator (PKG) selects a master secret $s \in \mathbb{Z}_q^*$ and public generator $P \in \mathbb{G}_1$. The public parameter is $P_{pub} = s \cdot P \in \mathbb{G}_1$.
2. **Key Extraction (Server):** For server identity $ID_{srv} = \text{"smartfleet:server:telemetry"}$, the PKG computes $Q_{srv} = H_1(ID_{srv}) \in \mathbb{G}_2$ using a hash-to-curve construction, and derives the server private decapsulation key:
   $$d_{srv} = s \cdot Q_{srv} \in \mathbb{G}_2$$
3. **Encapsulation (Vehicle):** The vehicle generates an ephemeral scalar $r \leftarrow_R \mathbb{Z}_q^*$ and computes:
   $$U = r \cdot P \in \mathbb{G}_1$$
   $$g_{id} = e(P_{pub}, Q_{srv})^r \in \mathbb{G}_T$$
   The symmetric key $K_{sym}$ is derived via SHA-256 Key Derivation:
   $$K_{sym} = \text{SHA-256}(U \parallel g_{id} \parallel ID_{srv})$$
   The encapsulation ciphertext component is $C_{ibe} = U$.
4. **Decapsulation (Server):** Given $C_{ibe} = U$, the server reconstructs the pairing value using its private key $d_{srv}$:
   $$g_{id}' = e(U, d_{srv}) = e(r \cdot P, s \cdot Q_{srv}) = e(P, Q_{srv})^{r \cdot s} = e(s \cdot P, Q_{srv})^r = e(P_{pub}, Q_{srv})^r = g_{id}$$
   The server computes $K_{sym} = \text{SHA-256}(U \parallel g_{id}' \parallel ID_{srv})$, recovering an identical 256-bit symmetric key.

### 4.2 AES-256-GCM Authenticated Encryption with Associated Data
The vehicle encrypts the serialized JSON telemetry payload $M$ using $K_{sym}$ under AES-256-GCM. An ephemeral 96-bit Initialization Vector ($IV$) is randomly sampled for each transmission:
$$(C_{sym}, \tau) = \text{AES-GCM-Encrypt}_{K_{sym}}(IV, M, AAD)$$
where $\tau$ is the 128-bit authentication tag.

To strictly bind the ciphertext to its routing and temporal context, the Authenticated Associated Data ($AAD$) is constructed as a canonical, deterministic UTF-8 byte sequence:
$$AAD = \text{CanonicalJSON}\Big(\big\{\text{"vehicle\_id"}: V_{id}, \text{"timestamp"}: T, \text{"nonce"}: N, \text{"message\_id"}: M_{id}\big\}\Big)$$
Any bit-level alteration to the vehicle identity, timestamp, or nonce during network transit causes the AES-GCM GHASH polynomial evaluation to fail, triggering immediate rejection of the payload.

### 4.3 Ed25519 Digital Signatures and Non-Repudiation
While IBE-KEM and AES-GCM ensure confidentiality and contextual integrity, any party possessing the public server parameters could theoretically encapsulate a valid key to the server. To guarantee **sender authenticity** and **non-repudiation**, every vehicle maintains a unique Ed25519 signing keypair $(sk_{veh}, pk_{veh})$.

The vehicle computes signature $\sigma$ over the canonical hash of the unencrypted payload:
$$\sigma = \text{Ed25519-Sign}\Big(sk_{veh}, H(M) \parallel AAD\Big)$$
The server verifies $\sigma$ against the pre-enrolled public key $pk_{veh}$ registered in the vehicle database:
$$\text{Ed25519-Verify}\Big(pk_{veh}, H(M) \parallel AAD, \sigma\Big) \stackrel{?}{=} \text{True}$$

### 4.4 Staged Pipeline and Anti-Oracle Defense
To eliminate decryption-oracle side channels and mitigate CPU-exhaustion Denial-of-Service (DoS) attacks arising from expensive pairing operations, SMARTFLEET enforces a strict staged pipeline:

```
[Incoming Request]
       |
       v
[Stage 1: Replay & Freshness Check] (Fast: < 1.0 ms)  ---> Fail -> 400 Bad Request
       |
       v
[Stage 2: Ed25519 Signature Check]  (Fast: 0.25 ms)   ---> Fail -> 401 Unauthorized
       |
       v
[Stage 3: IBE Pairing Decapsulation] (Heavy: ~3.9 s)   ---> Fail -> 400 Decryption Failed
       |
       v
[Stage 4: AES-GCM Decrypt & Commit] (Fast: < 0.1 ms)  ---> Fail -> 400 Decryption Failed
```

If an attacker transmits a forged signature or a replayed packet, the request is terminated in **under 1.0 ms** without executing bilinear pairings, neutralizing computational exhaustion attacks.

### 4.5 Atomic Sliding-Window Replay Protection
Replay attacks are mitigated through a dual-verification mechanism:
1. **Timestamp Freshness Window:** The server rejects any transmission whose timestamp deviates from server clock time $T_{srv}$ beyond strict limits:
   $$T - T_{srv} > 30\text{ s (Future Drift)}, \quad T_{srv} - T > 300\text{ s (Expired)}$$
2. **Atomic Nonce Cache:** A database table `processed_message_cache` records pairs of `(vehicle_id, nonce)`. During ingestion, the transaction acquires a row-level lock or attempts an atomic insertion. If a duplicate nonce is detected within the validity window, the transaction triggers an integrity violation and is rejected via a PostgreSQL nested savepoint rollback.

---

## 5. Experimental Methodology and Benchmark Results

### 5.1 Experimental Setup
Benchmarking and security evaluations were conducted on a dedicated testbed whose specifications are summarized in Table 1.

*Table 1: Experimental Evaluation Environment.*
| Dimension | Specification |
| :--- | :--- |
| **Host Operating System** | Windows 11 Home (64-bit, Build 26100) |
| **System Architecture** | x86_64, 8.00 GB Physical RAM |
| **Backend Environment** | Python 3.12, FastAPI 0.115, Uvicorn, SQLAlchemy 2.0 |
| **Cryptographic Libraries** | `py_ecc` 7.0.1 (BN128), `cryptography` 43.0.3 (AES-GCM, Ed25519) |
| **Worker Concurrency** | Python `threading` with 8 MB worker stack configuration |
| **Database Tier** | PostgreSQL 16.1 (Docker Container `iot_fleet_postgres` on Port 5435) |
| **Frontend Dashboard** | React 18.2, TypeScript 5.2, Vite 5.1, Vanilla CSS Design System |

### 5.2 Payload Profiling and Wire Expansion
Vehicular telemetry payloads were categorized into three representative operational tiers:
- **Small (183 Bytes):** Core positioning fix (`vehicle_id`, `latitude`, `longitude`, `speed`, `heading`, `timestamp`).
- **Medium (1,192 Bytes):** Full OBD-II snapshot (positioning plus engine RPM, coolant temperature, fuel level, tire pressures, battery state-of-charge).
- **Large (6,575 Bytes):** Diagnostic fault freeze-frame containing multi-system sensor arrays, alert histories, and ECU diagnostic trouble codes.

Table 2 presents the measured payload wire expansion introduced by the unified cryptographic envelope.

*Table 2: Wire Payload Expansion Across Telemetry Categories.*
| Payload Tier | Raw Plaintext Size | Protected Envelope Size | Absolute Overhead | Percentage Expansion |
| :--- | :---: | :---: | :---: | :---: |
| **Small** | 183 B | 1,231 B | +1,048 B | +572.68% |
| **Medium** | 1,192 B | 2,578 B | +1,386 B | +116.28% |
| **Large** | 6,575 B | 9,754 B | +3,179 B | +48.35% |

The constant cryptographic overhead includes the IBE BN128 curve point $U \in \mathbb{G}_1$ (serialized as hexadecimal coordinates, ~130 B), AES-GCM 96-bit IV (12 B base64), 128-bit authentication tag (16 B base64), Ed25519 64-byte signature (88 B base64), vehicle identifiers, nonces, and JSON envelope framing. While small telemetry packets experience high relative expansion (+572.68%), large diagnostic dumps exhibit modest overhead (+48.35%), as symmetric AES ciphertext scaling dominates.

### 5.3 Micro-Benchmark Cryptographic Latency
Individual cryptographic operations were benchmarked across repeated trials to isolate component costs. Table 3 presents the measured operational latencies.

*Table 3: Micro-Benchmark Execution Latency Distribution.*
| Cryptographic Operation | Sample Count ($N$) | Mean Latency | Median Latency | 95th Percentile |
| :--- | :---: | :---: | :---: | :---: |
| **Ed25519 Signature Gen** | 30 | 0.75 ms | 0.63 ms | 1.15 ms |
| **Ed25519 Signature Verify** | 30 | 0.25 ms | 0.16 ms | 0.48 ms |
| **IBE Encaps + AES Encrypt** | 15 | 4,469.55 ms | 4,393.33 ms | 4,806.58 ms |
| **IBE Decaps + AES Decrypt** | 15 | 3,923.50 ms | 3,921.83 ms | 4,137.06 ms |

```
Cryptographic Micro-Latencies:
=============================================================================
Ed25519 Sign     [0.75 ms]  *
Ed25519 Verify   [0.25 ms]  *
IBE Enc + AES    [4,469.55 ms] =============================================>
IBE Dec + AES    [3,923.50 ms] ========================================>
=============================================================================
```

These results establish that **Ed25519 operations are computationally negligible** (sub-millisecond), whereas **IBE pairing operations in pure Python dominate the execution profile**, accounting for over 99.9% of cryptographic processing time.

### 5.4 End-to-End Processing Latency Comparison
We compared Mode A (Unprotected HTTP Plaintext Ingestion) directly against Mode B (Protected IBE-KEM + AES-GCM + Ed25519 Ingestion) under identical network and persistence configurations ($N = 5$ trials per tier). Table 4 summarizes the empirical comparison.

*Table 4: End-to-End Transmission Latency Comparison.*
| Payload Tier | Mode A (Plaintext Mean) | Mode B (Protected Mean) | Latency Overhead | Latency Multiplier |
| :--- | :---: | :---: | :---: | :---: |
| **Small (183 B)** | 51.96 ms | 8,775.76 ms | +8,723.80 ms | **168.9×** |
| **Medium (1,192 B)** | 34.94 ms | 8,845.67 ms | +8,810.73 ms | **253.2×** |
| **Large (6,575 B)** | 47.58 ms | 8,074.06 ms | +8,026.48 ms | **169.7×** |

The protected pipeline requires between 8.07 s and 8.85 s per message on commodity single-thread Python execution, representing an approximate 170× to 253× latency multiplier over unencrypted transmission.

### 5.5 Fleet Scalability and Ingestion Throughput
To assess system scalability under expanding fleet sizes, sequential transmission benchmarks were executed across fleet configurations ranging from 1 to 25 vehicles.

*Table 5: Fleet Size Scalability and Sequential Ingestion Throughput.*
| Fleet Size (Vehicles) | Batch Processing Time | Average Latency / Vehicle | Effective Throughput |
| :---: | :---: | :---: | :---: |
| **1** | 8.07 s | 8.07 s | 0.124 msg/s |
| **5** | 40.48 s | 8.10 s | 0.124 msg/s |
| **10** | 80.95 s | 8.09 s | 0.124 msg/s |
| **25** | 203.22 s | 8.13 s | 0.123 msg/s |

Processing time exhibits near-perfect linear scaling ($R^2 > 0.999$), maintaining a steady 8.10 seconds per vehicle. Under pure-Python single-process execution, throughput saturates at approximately 0.124 messages/second. While adequate for non-critical periodic tracking (e.g., reporting intervals of 5 to 15 minutes), high-frequency telematics (e.g., 10 Hz V2X collision warnings) requires compiled pairing acceleration or hardware security modules (HSMs).

---

## 6. Security Evaluation and Adversarial Analysis

The resilience of the SMARTFLEET ingestion architecture was evaluated against 12 formal attack scenarios representing realistic network and vehicular attack vectors. Table 6 provides the experimental validation results.

*Table 6: Empirical Security Evaluation Across 12 Attack Scenarios.*
| Test ID | Adversarial Threat Vector | Mechanism Challenged | Expected Outcome | Observed Status | Database State |
| :---: | :--- | :--- | :---: | :---: | :---: |
| **S-01** | Valid Authorized Telemetry | Full Cryptographic Pipeline | 200 OK | **PASSED** | Correctly Committed |
| **S-02** | Ciphertext Bit Modification | AES-GCM Tag Verification | 400 Bad Request | **PASSED** | Rolled Back |
| **S-03** | Tampered Authentication Tag | AES-GCM Tag Verification | 400 Bad Request | **PASSED** | Rolled Back |
| **S-04** | Modified IV / Nonce Parameter | AES-GCM Integrity Check | 400 Bad Request | **PASSED** | Rolled Back |
| **S-05** | Identity Tampering in AAD | AES-GCM AAD Binding | 400 Bad Request | **PASSED** | Rolled Back |
| **S-06** | Corrupted IBE Ephemeral Point | BN128 Point Unmarshaling | 400 Bad Request | **PASSED** | Rolled Back |
| **S-07** | Invalid Ed25519 Signature | Ed25519 Curve Verification | 401 Unauthorized | **PASSED** | Rolled Back |
| **S-08** | Signature / Payload Mismatch | Ed25519 Digest Validation | 401 Unauthorized | **PASSED** | Rolled Back |
| **S-09** | Replay of Intercepted Message | Atomic Nonce Cache Check | 400 Bad Request | **PASSED** | Rolled Back |
| **S-10** | Expired Message Timestamp | Freshness Window ($>300$ s) | 400 Bad Request | **PASSED** | Rolled Back |
| **S-11** | Future-Drift Timestamp | Freshness Window ($>30$ s) | 400 Bad Request | **PASSED** | Rolled Back |
| **S-12** | Unregistered Vehicle ID | Vehicle Registry Lookup | 404 / 401 Reject | **PASSED** | Rolled Back |
| **S-13** | Revoked Vehicle Access | Authorization Flag Validation | 403 Forbidden | **PASSED** | Rolled Back |

### 6.1 Concurrent Replay Attack Validation
To evaluate replay protection under realistic distributed race conditions, a multithreaded stress test dispatched **6 concurrent requests** submitting identical encrypted telemetry envelopes ($V_{id}$, timestamp, nonce, ciphertext) across 6 parallel worker threads.
- **Observed Result:** Exactly **1 thread succeeded** (HTTP 200 OK, committed to database); all **5 concurrent threads were rejected** (HTTP 400 Bad Request with `"Replay attack detected: Message nonce already processed"`).
- **Integrity Audit:** Database inspection confirmed that exactly 1 telemetry row was persisted; no race conditions, duplicate rows, or deadlocks occurred.

### 6.2 API Decryption-Oracle and Key Security Audit
An exhaustive audit of all HTTP endpoints confirmed that:
- No REST API route returns the master secret $s$ or vehicle private signing keys $sk_{veh}$.
- Public re-initialization of master cryptographic parameters (`/api/ibe/setup`) is disabled (HTTP 403 Forbidden).
- Decryption error messages return generic failure codes without disclosing intermediate mathematical values, blinding factors, or partial pairing points.

---

## 7. Extended Research Context: BQC and QUBO

To position the core telemetry security pipeline within broader intelligent transportation systems research, SMARTFLEET integrates two complementary experimental modules:

### 7.1 Blind Quantum Computing (BQC) Telemetry Simulation
Modern fleet operators increasingly outsource high-performance optimization and risk modeling to untrusted cloud servers. To investigate privacy-preserving cloud computation, SMARTFLEET incorporates a software simulation of the Broadbent–Fitzsimons–Kashefi (BFK09) Measurement-Based Quantum Computing (MBQC) protocol [9]:
- **Protocol Workflow:** An IoT client prepares blind single-qubit states $|\theta_j\rangle = \frac{1}{\sqrt{2}}(|0\rangle + e^{i\theta_j}|1\rangle)$ with random phase $\theta_j \in \{0, \frac{\pi}{4}, \dots, \frac{7\pi}{4}\}$, entangles them into a graph cluster state, and computes measurement angles $\phi_j' = \phi_j + \theta_j + r_j\pi$.
- **Experimental Findings:** Across 110 simulation trials on 4-qubit Brickwork cluster states, the simulated cloud server returned correct blind measurement outcomes while maintaining zero mathematical information regarding the client's underlying computation ($\Delta H = 0$).
- **Honest Research Boundary:** We emphasize that this BQC implementation is a **classical CPU simulation** demonstrating protocol correctness; it does **not** run on physical quantum hardware, does **not** provide quantum computational speedup, and does **not** secure the classical network wire.

### 7.2 QUBO-Based Fleet Routing and Optimization
SMARTFLEET incorporates a frozen research extension modeling multi-vehicle routing as a Quadratic Unconstrained Binary Optimization (QUBO) problem [10]. Formulated over a three-index binary decision matrix $x_{i,j,k} \in \{0, 1\}$, the objective function penalizes route transit distances while enforcing Hamiltonian path constraints through Lagrange multipliers ($P_{visit}, P_{flow}$). Benchmark evaluations on simulated annealing and classical solvers demonstrated valid vehicle-depot tours, illustrating a pathway toward hybrid classical-quantum logistics optimization.

---

## 8. Limitations and Future Work

While SMARTFLEET successfully establishes an authenticated, certificate-free telemetry ingestion pipeline, several practical engineering limitations remain:

1. **Python Pairing Latency:** The pure-Python implementation of BN128 pairing arithmetic via `py_ecc` requires ~4.0 seconds per decapsulation. In production deployments, this must be replaced with native C/Rust pairing libraries (e.g., `mcl` or `BLST`) or hardware-accelerated elliptic curve cryptoprocessors, which achieve sub-10 ms pairing times.
2. **Key Escrow in IBE:** The Private Key Generator (PKG) possesses master secret $s$ and can mathematically derive any entity's private key. In multi-tenant fleet environments, decentralized or threshold PKG architectures (e.g., Shamir secret sharing across independent authorities) are required.
3. **Hardware Root of Trust:** The prototype stores private keys in local software files. Commercial vehicular systems must bind signing keys to Hardware Security Modules (HSMs) or Trusted Platform Modules (TPMs) compliant with ISO 21434 automotive cybersecurity standards [11].
4. **Physical IoT Validation:** Benchmarks were gathered on simulated Linux/Windows processes; future research must validate power draw, memory footprint, and transmission stability on constrained automotive microcontrollers (e.g., ARM Cortex-M4 / ESP32).

---

## 9. Conclusion

This paper presented the design, implementation, and empirical evaluation of **SMARTFLEET**, an identity-based hybrid cryptographic architecture for secure IoT vehicle telemetry ingestion. By combining Boneh–Franklin Identity-Based Encryption as a Key Encapsulation Mechanism with AES-256-GCM AEAD, Ed25519 digital signatures, and atomic sliding-window replay caching, SMARTFLEET achieves end-to-end telemetry confidentiality, message integrity, vehicle authentication, and replay immunity without the overhead of X.509 certificate validation. Empirical benchmarks across multiple telemetry payload profiles quantified the computational cost of pairing-based encapsulation, establishing a rigorous baseline for future hardware-accelerated deployments. Comprehensive security evaluations confirmed 100% rejection across 12 adversarial threat scenarios, demonstrating that SMARTFLEET provides a resilient, mathematically verified foundation for secure vehicular telematics.

---

## References

1. **IEEE Standard for Wireless Access in Vehicular Environments (WAVE)—Security Services for Applications and Management Messages**, IEEE Std 1609.2-2016, pp. 1–240, 2016.
2. J. Haas, Y. C. Hu, and K. P. Laberteaux, "Design and Analysis of a Lightweight Certificate Revocation List for Vehicular Networks," *IEEE Transactions on Intelligent Transportation Systems*, vol. 12, no. 3, pp. 888–898, 2011.
3. A. Shamir, "Identity-Based Cryptosystems and Signature Schemes," *Advances in Cryptology (CRYPTO '84)*, Lecture Notes in Computer Science, vol. 196, Springer, Berlin, Heidelberg, pp. 47–53, 1985.
4. D. Boneh and M. Franklin, "Identity-Based Encryption from the Weil Pairing," *SIAM Journal on Computing*, vol. 32, no. 3, pp. 586–615, 2003.
5. C. Zhang, P. H. Ho, and J. Tapolcai, "On Secure and Distributed Cloud-Based Vehicular Networks: Architecture and Security Analysis," *IEEE Network*, vol. 31, no. 1, pp. 78–84, 2017.
6. P. S. L. M. Barreto and M. Naehrig, "Pairing-Friendly Elliptic Curves of Prime Order," *Selected Areas in Cryptography (SAC 2005)*, Lecture Notes in Computer Science, vol. 3897, Springer, Berlin, Heidelberg, pp. 319–331, 2006.
7. D. A. McGrew and J. Viega, "The Security and Performance of the Galois/Counter Mode (GCM) of Operation," *Fast Software Encryption (FSE 2004)*, Lecture Notes in Computer Science, vol. 3017, Springer, Berlin, Heidelberg, pp. 343–355, 2004.
8. D. J. Bernstein, N. Duif, T. Lange, P. Schwabe, and B. Y. Yang, "High-Speed High-Security Signatures," *Journal of Cryptographic Engineering*, vol. 2, no. 2, pp. 77–89, 2012.
9. A. Broadbent, J. Fitzsimons, and E. Kashefi, "Universal Blind Quantum Computation," *Proceedings of the 50th Annual IEEE Symposium on Foundations of Computer Science (FOCS '09)*, pp. 517–526, 2009.
10. F. Glover, G. Kochenberger, and Y. Du, "A Tutorial on Formulating and Solving QUBO Models," *4OR: A Quarterly Journal of Operations Research*, vol. 17, no. 4, pp. 339–371, 2019.
11. **ISO/SAE 21434:2021 Road Vehicles—Cybersecurity Engineering**, International Organization for Standardization, Geneva, Switzerland, 2021.
