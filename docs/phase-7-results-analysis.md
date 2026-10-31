# SMARTFLEET — Phase 7: Deep Experimental Results & Statistical Analysis

**Document Version:** 1.0.0  
**Date:** October 31, 2026  
**Primary Dataset Reference:** `step_6_2_benchmark_data.json` & `step_6_1_audit_results.json`  
**Host Environment:** Windows 11 Home (64-bit), 8.00 GB RAM, x86_64 CPU  
**Software:** Python 3.11.9, py_ecc 7.0.1, cryptography 43.0.0, PostgreSQL 16 @ Port 5435  

---

## 1. Overview of Experimental Analysis

This document provides an in-depth statistical analysis of the empirical measurements captured during Phase 6. Every chart, table, and data point in this document is derived directly from the raw benchmark data recorded in `step_6_2_benchmark_data.json`.

In accordance with strict scientific guidelines:
- What is measured and how it was measured are explicitly defined.
- What the result proves and **what cannot be concluded from it** are clearly stated.
- All metrics (Mean, Median, Standard Deviation $\sigma$, and 95th Percentile $P_{95}$) reflect true experimental observations.

---

## 2. Analysis 1: Plaintext (Mode A) vs Protected (Mode B) Transmission Latency

### 2.1 Empirical Data Table
| Payload Category | Plaintext Size | Mode A (Plaintext) Mean | Mode A Median | Mode B (Protected) Mean | Mode B Median | Mode B P95 | Latency Delta | Ratio (B / A) |
|---|---|---|---|---|---|---|---|---|
| **Small** | 183 B | 51.96 ms | 32.52 ms | **8,775.76 ms** | 8,614.03 ms | 9,434.48 ms | +8,723.80 ms | **168.9x** |
| **Medium** | 1,192 B | 34.94 ms | 32.71 ms | **8,845.67 ms** | 8,770.47 ms | 9,586.08 ms | +8,810.73 ms | **253.2x** |
| **Large** | 6,575 B | 35.87 ms | 34.53 ms | **8,074.06 ms** | 8,077.85 ms | 8,092.69 ms | +8,038.19 ms | **225.1x** |

### 2.2 Text Chart: Comparative Latency (Milliseconds)
```
Payload Category       Mode A (Plaintext) vs Mode B (IBE-Protected) Latency (Mean)
-----------------------------------------------------------------------------------------
Small (183 B)    | [52 ms]
                 | =======================================================> [8,776 ms] (169x)
                 |
Medium (1.19 KB) | [35 ms]
                 | ========================================================> [8,846 ms] (253x)
                 |
Large (6.57 KB)  | [36 ms]
                 | =====================================================> [8,074 ms] (225x)
-----------------------------------------------------------------------------------------
Scale: 1 '=' approx 150 ms
```

### 2.3 Scientific Interpretation
- **What is measured:** Wall-clock duration from client telemetry generation to database transaction commit.
- **How it was measured:** High-resolution timers (`time.perf_counter()`) measuring HTTP request-response cycles between edge client and server.
- **What the result means:** Securing telemetry via IBE-KEM, AES-256-GCM, and Ed25519 introduces a ~8.0–8.8 second latency penalty in this pure-Python environment. Plaintext ingestion requires only 30–50 ms.
- **What cannot be concluded:** This does **not** mean Identity-Based Encryption is fundamentally unsuitable for IoT. The 8-second overhead is an artifact of interpreted pure-Python arithmetic (`py_ecc`). Compiled C/Rust implementations (e.g. RELIC/mcl) execute BN128 pairings in 1–5 ms, reducing the protected latency to ~40–60 ms.

---

## 3. Analysis 2: Cryptographic Micro-Component Latency Breakdown

### 3.1 Empirical Data Table
| Component Operation | Mathematical Primitives | Mean (ms) | Median (ms) | Std Dev ($\sigma$) | P95 (ms) | Min (ms) | Max (ms) |
|---|---|---|---|---|---|---|---|
| **Client IBE Encapsulation + AES Encrypt** | $r \cdot G2$ scalar mult + HKDF + AES-GCM | **4,469.55** | 4,393.33 | 195.67 | 4,806.58 | 4,262.28 | 4,893.36 |
| **Server IBE Decryption + AES Decrypt** | $e(P_{\text{pub}}, Q_{ID})^r$ pairing + AES-GCM | **3,923.50** | 3,921.83 | 151.53 | 4,137.06 | 3,615.11 | 4,155.15 |
| **Client Ed25519 Signing** | RFC 8032 SHA-512 PureEdDSA | **0.75** | 0.63 | 0.26 | 1.18 | 0.60 | 1.45 |
| **Server Ed25519 Verification** | RFC 8032 Signature Verification | **0.25** | 0.16 | 0.20 | 0.62 | 0.14 | 0.76 |

### 3.2 Text Chart: Component Execution Time (Log Scale)
```
Component Operation                  Mean Execution Time (Log10 Scale)
-----------------------------------------------------------------------------------------
Ed25519 Verification     (0.25 ms)   | *
Ed25519 Signing          (0.75 ms)   | **
Server IBE Decryption    (3,923 ms)  | ****************************************
Client IBE Encapsulation (4,470 ms)  | *********************************************
-----------------------------------------------------------------------------------------
```

### 3.3 Scientific Interpretation
- **What is measured:** Isolated CPU processing time of individual cryptographic operations.
- **How it was measured:** Direct function-level timers wrapping internal cryptographic routines on vehicle `SIM-VEH-001` over 10 consecutive trials.
- **What the result means:** 
  1. Ed25519 signing (0.75 ms) and verification (0.25 ms) are negligible in cost, running 15,000x faster than elliptic curve pairings.
  2. Pairing operations dominate total processing time (> 99.9%).
  3. Pre-decryption signature verification successfully shields the pairing engine from DoS attacks.
- **What cannot be concluded:** This does not imply that Ed25519 signatures can replace IBE. Ed25519 provides **authenticity and integrity**, but provides zero confidentiality; IBE-KEM provides **confidentiality without certificate management**.

---

## 4. Analysis 3: Payload Size and Wire Expansion Ratio

### 4.1 Empirical Data Table
| Payload Category | Plaintext JSON Bytes | Encrypted Envelope Bytes | Absolute Expansion | Expansion Ratio (%) |
|---|---|---|---|---|
| **Small** | 183 B | 1,231 B | +1,048 B | **+572.68%** |
| **Medium** | 1,192 B | 2,578 B | +1,386 B | **+116.28%** |
| **Large** | 6,575 B | 9,754 B | +3,179 B | **+48.35%** |

### 4.2 Text Chart: Overhead Percentage
```
Payload Category       Payload Expansion Percentage (%)
-----------------------------------------------------------------------------------------
Small (183 B)    | [==================================================] +572.7%
Medium (1.19 KB) | [====================] +116.3%
Large (6.57 KB)  | [========] +48.4%
-----------------------------------------------------------------------------------------
```

### 4.3 Scientific Interpretation
- **What is measured:** Wire footprint in bytes of the JSON payload before and after protection.
- **How it was measured:** Exact byte counting of serialized JSON strings sent across the HTTP interface.
- **What the result means:** The cryptographic envelope imposes a fixed overhead floor (~1,000 bytes) consisting of the base64-encoded $G2$ point (128 bytes raw), 16-byte salt, 12-byte nonce, 16-byte tag, 64-byte Ed25519 signature, and canonical metadata keys. For minimal telemetry (183 B), this represents a 5.7x expansion; for dense multi-sensor payloads (6.5 KB), the overhead drops to +48.4%.
- **What cannot be concluded:** It cannot be concluded that IBE is bandwidth-prohibitive for IoT. Using binary serialization (CBOR/Protobuf) and compressed point representations would reduce the overhead floor to < 250 bytes.

---

## 5. Analysis 4: Fleet Scalability Across Vehicle Counts

### 5.1 Empirical Data Table
| Fleet Size (Vehicles) | Transmissions Sent | Transmissions Succeeded | Total Wall-Clock Time (s) | Effective Throughput (msg/s) | Average Latency per Message (ms) |
|---|---|---|---|---|---|
| **1 Vehicle** | 1 | 1 | 7.96 s | **0.13 msg/s** | 7,964.47 ms |
| **5 Vehicles** | 5 | 5 | 40.37 s | **0.12 msg/s** | 8,074.54 ms |
| **10 Vehicles** | 10 | 10 | 80.45 s | **0.12 msg/s** | 8,044.50 ms |
| **25 Vehicles** | 25 | 25 | 203.35 s | **0.12 msg/s** | 8,134.02 ms |

### 5.2 Text Chart: Wall-Clock Duration vs Vehicle Count
```
Fleet Size (Vehicles)   Total Execution Duration (Seconds)
-----------------------------------------------------------------------------------------
 1 Vehicle   (1 tx)  | [==] 8.0s
 5 Vehicles  (5 tx)  | [==========] 40.4s
10 Vehicles (10 tx)  | [====================] 80.5s
25 Vehicles (25 tx)  | [==================================================] 203.4s
-----------------------------------------------------------------------------------------
Linearity: R^2 > 0.999 | Stable ~8.0s per message
```

### 5.3 Scientific Interpretation
- **What is measured:** Total sequential execution time and throughput for processing batches of up to 25 distinct vehicle telemetry envelopes.
- **How it was measured:** Sequential API transmission calls executed in a loop across enrolled fleet units `SIM-VEH-001` to `SIM-VEH-025`.
- **What the result means:** System throughput under single-threaded synchronous pairing is strictly constant at **0.12–0.13 messages/second** (1 message every ~8.0 seconds). Memory and database connection pools remained completely stable.
- **What cannot be concluded:** This does not represent the maximum throughput of an asynchronous production architecture. With multi-process worker pools (e.g. Celery / Gunicorn workers) and compiled C curve libraries, throughput would scale to hundreds of messages per second on multi-core servers.

---

## 6. Analysis 5: Attack Resilience & Concurrency Verification

### 6.1 Empirical Outcome Summary
- **Total Adversarial Scenarios Evaluated:** 12
- **Attack Vectors Rejected:** 12 / 12 (**100.0% Rejection Rate**)
- **Database Corruptions Detected:** 0
- **Unauthorized Telemetry Rows Persisted:** 0
- **Concurrent Replay Test (6 Workers):** Exactly 1 succeeded, exactly 5 rejected with atomic rollback.

### 6.2 Scientific Interpretation
- **What is measured:** Server rejection behavior and transaction rollback consistency under hostile and malformed inputs.
- **How it was measured:** Injecting bit-flipped ciphertexts, forged Ed25519 keys, corrupted tags, replayed UUIDs, clock-skewed timestamps, and concurrent parallel requests.
- **What the result means:** The defense-in-depth architecture successfully isolates and rejects all attack classes. Database atomicity guarantees that invalid messages leave zero residual artifacts in the database.
- **What cannot be concluded:** Passing 12 test vectors does not constitute a formal mathematical proof of security against arbitrary side-channel or physical fault-injection attacks.
