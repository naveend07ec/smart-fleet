# SMARTFLEET — Phase 6: Security, Cryptographic & BQC Limitations

**Document Version:** 1.0.0  
**Date:** October 31, 2026  
**Scope:** Rigorous distinction between verified protections and research limitations  

---

## 1. Introduction

A key requirement of engineering research is establishing clear boundaries around what a system does and does not protect. This document provides an honest, technical accounting of the cryptographic, architectural, and quantum-simulation limitations of SMARTFLEET Phase 6.

---

## 2. Cryptographic Architecture Limitations

### 2.1 Centralized Key Escrow (Inherent to Boneh-Franklin IBE)
- **Mechanism:** In the implemented Boneh-Franklin Identity-Based Encryption protocol over the BN128 curve, the Private Key Generator (PKG) generates and holds the master secret scalar $s \in [2, r-1]$. Any vehicle private key $d_{ID}$ is computed directly as:
  $$d_{ID} = s \cdot Q_{ID} \in G1$$
- **Limitation:** The PKG inherently possesses unconditional key escrow. A compromised PKG or an insider with access to `master_secret.key` can derive the decryption key for any registered identity in the fleet and decrypt all past, present, and future telemetry ciphertexts.
- **Academic Alternative:** Production deployments require either **Certificateless Public Key Cryptography (CL-PKC)**, where the private key is a combination of a PKG partial key and an edge-generated secret value, or a **Threshold Distributed PKG** using Shamir Secret Sharing across multiple independent authorities.

### 2.2 Key Storage Without Hardware Security Modules (HSM / TPM)
- **Mechanism:** Vehicle Ed25519 private signing keys are serialized to PEM files in `.ibe_keys/vehicle_signing_keys/{vehicle_identifier}.key`, and the server master secret is stored in `.ibe_keys/master_secret.key`.
- **Limitation:** The current implementation relies entirely on filesystem-level access permissions. It does not utilize Hardware Security Modules (HSM), Trusted Platform Modules (TPM 2.0), or ARM TrustZone / Secure Enclaves. If the host operating system is compromised with root/administrator access, all stored private keys are exposed.
- **Production Requirement:** In real-world automotive IoT (e.g. ISO 21434 / UNECE R155), private signing keys must be held within an on-board Hardware Security Module (HSM) or secure automotive MCU (e.g., Infineon AURIX, NXP S32K) where private key material is non-exportable.

### 2.3 Identity Revocation & Epoch Management
- **Mechanism:** Public keys in IBE are arbitrary identity strings (e.g. `SIM-VEH-001@fleet.iot.local`).
- **Limitation:** Traditional Certificate Revocation Lists (CRLs) or OCSP stapling do not exist in basic IBE because there are no digital certificates. If a vehicle's private signing key or identity is compromised, the public identity cannot be revoked retroactively without changing the identity string itself.
- **Mitigation Pattern:** The standard workaround is epoch-based identity concatenation (e.g., `SIM-VEH-001@fleet.iot.local/2026-W44`). This forces all vehicles to re-extract keys periodically from the PKG. However, this introduces frequent client-to-PKG communication overhead.

### 2.4 Pure-Python Elliptic Curve Arithmetic & Thread Recursion Workaround
- **Mechanism:** Elliptic curve arithmetic and Weil/Tate pairings over the BN128 curve are executed via the pure Python library `py_ecc`.
- **Limitation:**
  1. **Latency:** Each pairing and point multiplication requires ~3.9 to 4.4 seconds of CPU time on the host x86_64 processor. By comparison, optimized native C/Rust cryptographic libraries (such as RELIC, mcl, or blst) execute BN128 and BLS12-381 pairings in **1 to 5 milliseconds** (> 800x faster).
  2. **Stack Depth on Windows:** The Miller loop in pure Python pairing routines involves deeply nested recursive function calls. Under standard Python thread stack allocations (typically 1–2 MB on Windows), concurrent pairing computations trigger `RecursionError` or thread stack overflow.
  3. **Implemented Workaround:** In `ibe_service.py`, pairings are dispatched to a dedicated background worker thread configured with an explicit 8 MB stack allocation (`threading.stack_size(8 * 1024 * 1024)`). While this stabilizes execution and prevents crashes, it is an engineering workaround for pure-Python overhead, not a production architectural solution.

### 2.5 Canonical JSON Serialization vs Binary Framing
- **Mechanism:** Signatures cover metadata and ciphertext serialized via `json.dumps(..., sort_keys=True, separators=(',', ':'))`.
- **Limitation:** While canonical JSON is human-readable and deterministic, it is susceptible to subtle unicode normalization mismatches and whitespace variations across different programming language JSON encoders. Production IoT standards typically enforce binary deterministic encodings such as ASN.1 DER, Canonical CBOR (RFC 8949), or Protocol Buffers.

---

## 3. Evaluation & Boundaries of Blind Quantum Computing (BQC)

SMARTFLEET Phase 4 incorporated a simulated Broadbent-Fitzsimons-Kashefi (BFK09) Measurement-Based Quantum Computing (MBQC) protocol. Phase 6 independently evaluated its technical implementation and boundaries.

### 3.1 What the BQC Implementation IS
1. **Valid Algorithmic MBQC Simulation:** The client prepares nominal measurement angles and masks them with secret random phases $\theta_j \in \{0, \frac{\pi}{4}, \dots, \frac{7\pi}{4}\}$ and secret one-time pads $r_j \in \{0, 1\}$.
2. **Adaptive Measurement Tracking:** The simulated server creates an $N$-qubit cluster state vector in $\mathbb{C}^{2^N}$ using Controlled-Z (CZ) entangling operators. The client computes adaptive blinded angles $\delta_j = (-1)^{s_x} \phi_j + \theta_j + r_j \pi$ based on previous measurement outcomes.
3. **Information Hiding (Within Simulation):** An audit of server visibility confirms that the simulated server observes only the blinded angles $\delta_j$ and raw measurement bits $b_j$. It does not observe client GPS coordinates, individual candidate depot costs, or the final winning depot assignment.
4. **Shannon Entropy Audit:** The transmitted measurement angles exhibit an empirical Shannon entropy of **1.50 bits** (over 4 qubits), confirming non-trivial phase dispersion.

### 3.2 What the BQC Implementation is NOT (Strict Scientific Boundaries)
1. **Classical Simulation on CPU:** The quantum state vector $\mathbb{C}^{2^N}$ is simulated entirely using classical complex arithmetic (`cmath`) on an x86_64 CPU. It **does NOT** utilize physical quantum processors, photonic quantum emitters, or superconducting qubits.
2. **No Quantum Advantage Claim:** The system achieves **zero quantum speedup**. In fact, classical brute-force minimum finding executes in **0.02 ms**, whereas the 6-qubit BQC simulation requires **~4.5 ms** on CPU.
3. **No Network Security for Telemetry:** The BQC simulation is an experiment in **delegated computation privacy**, **NOT** a transmission security protocol for vehicle-to-server telemetry. 
   > [!IMPORTANT]
   > The vehicle telemetry transmission channel is secured exclusively by classical **IBE-KEM + AES-256-GCM + Ed25519**. The BQC simulation does not encrypt, authenticate, or protect telemetry data in transit.
4. **Physical Noise vs Simulated Noise:** In the simulation, noise is modeled by applying depolarizing or phase-flip channels during state collapse. In physical quantum cloud computing, fiber-optic attenuation, photon loss, and detector dark counts require active quantum error correction or fault-tolerant verification traps (such as Fitzsimons-Kashefi verification), which are not implemented here.

---

## 4. Summary Table: Implemented Protections vs Documented Limitations

| Dimension | Implemented Protection | Documented Research Limitation | Proposed Production Path |
|---|---|---|---|
| **Confidentiality** | AES-256-GCM with HKDF-derived 256-bit symmetric keys. | Basic Boneh-Franklin IBE incurs centralized PKG key escrow. | Certificateless Public Key Cryptography (CL-PKC) or 3-of-5 Threshold PKG. |
| **Sender Authentication** | Ed25519 digital signatures verified prior to decryption. | Key material stored in plaintext `.key` files on disk. | Hardware Security Module (HSM) or TPM 2.0 automotive chips. |
| **Replay Protection** | Timestamp sliding window (-300s to +30s) + atomic DB cache. | Replay cache grows indefinitely without scheduled pruning. | Automated cron job for Redis/PostgreSQL TTL partition dropping. |
| **Integrity & Binding** | AES-GCM Authenticated Associated Data (AAD) binds sender, recipient, UUID, and timestamp. | Canonical JSON serialization rather than binary framing. | Canonical CBOR (RFC 8949) or ASN.1 DER encoding. |
| **Pairing Performance** | Correct Boneh-Franklin KEM over BN128 curve. | Pure Python `py_ecc` takes ~4 seconds per pairing. | Compiled C/Rust bindings (RELIC, mcl, blst) for 1–5 ms pairings. |
| **Blind Quantum Computing** | BFK09 MBQC simulation hiding telemetry inputs from server. | Classical CPU simulation; does not secure the transmission wire. | Keep BQC strictly as an isolated delegated computing experiment. |

---

## 5. Conclusion

SMARTFLEET achieves its stated research objective: validating identity-based secure telemetry transmission with cryptographic sender authentication and replay defense. The documented limitations reflect deliberate research scoping choices (such as pure-Python execution and CPU simulation) rather than architectural flaws. All limitations are fully documented for future engineering extensions.
