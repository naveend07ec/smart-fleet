# SMARTFLEET: Final-Year Project Defense Presentation Outline

**Project Title:** SMARTFLEET: IoT-Driven Smart Transportation and Fleet Management System with Secure Data Transmission and Privacy-Preserving Computation  
**Format:** 18-Slide Academic Defense Presentation  
**Target Audience:** Final-Year Engineering Project Evaluation Committee & External Examiners  
**Duration:** 20 Minutes (15 min presentation + 5 min Q&A)

---

## Slide 1: Title & Project Metadata

- **Slide Title:** SMARTFLEET: IoT-Driven Smart Transportation and Fleet Management System with Secure Data Transmission and Privacy-Preserving Computation
- **Subtitle:** Final-Year Engineering Capstone Project Defense
- **Candidate Details:** Final-Year Computer Science and Engineering Students
- **Supervisor / Institution:** Department of Computer Science and Engineering
- **Date:** October 2026
- **Visual Asset:** High-resolution architectural banner illustrating vehicle-to-cloud cryptographic telemetry pipeline with BN128, AES-GCM, and Ed25519 emblems (`docs/diagrams/01_overall_architecture.md`).
- **Presenter Notes:**
  > "Good morning, respected members of the evaluation committee and external examiners. Today, we present SMARTFLEET, an engineering research project that addresses critical security, identity management, and privacy vulnerabilities in modern IoT-driven fleet management systems. Our central research contribution is an authenticated, certificate-free telemetry transmission framework combining Boneh–Franklin Identity-Based Encryption as a Key Encapsulation Mechanism, AES-256-GCM authenticated encryption, Ed25519 digital signatures, and atomic sliding-window replay protection. We have also integrated a Blind Quantum Computing simulation and a QUBO fleet routing extension to explore future-proof privacy and logistics paradigms."

---

## Slide 2: Introduction & Domain Context

- **Slide Title:** Background: The Growth of Intelligent Fleet Telematics
- **Key Bullet Points:**
  - Fleet management systems track hundreds or thousands of commercial vehicles, public transit buses, and emergency responders in real time.
  - Onboard IoT gateways continuously sample GPS coordinates, vehicle speed, engine diagnostics (OBD-II), fuel levels, and fault codes.
  - Telemetry is transmitted over public, untrusted cellular (4G LTE/5G) and vehicular ad-hoc networks (VANETs).
  - High update frequency (every 5 to 60 seconds per vehicle) creates severe demands on ingestion scalability, confidentiality, and data integrity.
- **Visual Asset:** Infographic showing connected vehicle transmitting diagnostic packets across cellular towers to a centralized cloud fleet dispatch server.
- **Presenter Notes:**
  > "Modern logistics and passenger safety rely on continuous vehicular telematics. IoT sensors embedded across engine control units and GPS receivers generate periodic status updates. Because these transmissions travel over public wireless networks, the underlying transport is inherently exposed to eavesdropping, packet alteration, and unauthorized injection. Securing this pipeline without overwhelming vehicle hardware is our core challenge."

---

## Slide 3: Problem Statement

- **Slide Title:** Problem Statement: The Security-Overhead Dilemma in Vehicular IoT
- **Key Bullet Points:**
  - **Passive Privacy Leakage:** Unencrypted GPS and route traces disclose sensitive driver patterns, cargo value, and logistics itineraries.
  - **Telemetry Tampering & Spoofing:** Adversaries can forge false collision alerts, artificial engine overheating codes, or fake fuel levels.
  - **Replay Attacks:** Recorded valid transmissions can be re-sent out of order to confuse dispatchers about vehicle location.
  - **The PKI Dilemma:** Standard X.509 Public Key Infrastructure requires distributing, verifying, and periodically revoking certificates. In high-mobility vehicular environments with intermittent network drops, validating certificate revocation lists (CRLs) or executing OCSP queries causes latency spikes, connection timeouts, or unsafe fail-open states.
- **Visual Asset:** Threat diagram contrasting passive eavesdropping, active MitM message injection, and CRL validation timeouts on an intermittent cellular connection.
- **Presenter Notes:**
  > "While the need for security is undeniable, conventional solutions like X.509 PKI fail to scale gracefully in vehicular environments. Distributing and maintaining digital certificates across thousands of moving vehicles creates immense administrative overhead. Checking certificate revocation over patchy cellular links leads to delays or failure. We need a cryptographic mechanism that eliminates digital certificates while preserving end-to-end confidentiality, authenticity, and replay resistance."

---

## Slide 4: Research Objectives

- **Slide Title:** Project Research Objectives
- **Key Bullet Points:**
  - **Objective 1:** Formulate and implement an Identity-Based Key Encapsulation Mechanism (IBE-KEM) using Boneh–Franklin over BN128 to eliminate public-key certificate exchange.
  - **Objective 2:** Bind payload confidentiality and metadata integrity using AES-256-GCM with Authenticated Associated Data (AAD).
  - **Objective 3:** Guarantee vehicle authenticity and non-repudiation using Edwards-curve digital signatures (Ed25519).
  - **Objective 4:** Implement an atomic, database-level sliding-window timestamp and nonce filter to eliminate replay attacks under concurrent loads.
  - **Objective 5:** Empirically benchmark execution latency, payload expansion, and throughput across realistic telemetry sizes.
  - **Objective 6:** Conduct a 12-vector adversarial security audit to prove fail-safe rejection without state corruption.
- **Visual Asset:** Milestone checklist graphic showing the 6 research objectives categorized under Design, Implementation, Benchmarking, and Security.
- **Presenter Notes:**
  > "To resolve this challenge, we set six specific engineering objectives: replace X.509 certificates with IBE-KEM, bind routing context using AES-GCM AEAD, enforce vehicle non-repudiation using Ed25519, build atomic sliding-window replay protection into the database layer, rigorously benchmark the latency and bandwidth tradeoffs, and empirically validate the system against 12 formal attack vectors."

---

## Slide 5: Existing System Limitations vs. SMARTFLEET

- **Slide Title:** Architectural Comparison: Conventional vs. SMARTFLEET
- **Comparison Table:**
  | Dimension | Conventional Fleet Systems | PKI-Based Vehicle Systems | Proposed SMARTFLEET Architecture |
  | :--- | :--- | :--- | :--- |
  | **Transport Security** | TLS Only (Point-to-Point) | TLS + X.509 Client Certs | End-to-End Application Cryptographic Envelope |
  | **Key Distribution** | Shared Static API Keys | Heavy X.509 Cert Authority | **Identity-Based Encryption (Server Identity String)** |
  | **Certificate Overhead** | None (Insecure) | 1–3 KB Certs + CRL checks | **Zero Certificate Overhead (Pure Math KEM)** |
  | **Sender Non-Repudiation** | None | RSA / ECDSA Signatures | **Sub-millisecond Ed25519 Digital Signatures** |
  | **Replay Defense** | Ad-hoc / In-memory | Session-bound TLS | **Database-Level Atomic Nonce + Window Cache** |
  | **Tamper Binding** | Hash checks | Message Authentication Code | **AES-256-GCM with Authenticated Associated Data** |
- **Visual Asset:** Side-by-side comparison chart highlighting the transition from certificate chains to direct identity-based encapsulation.
- **Presenter Notes:**
  > "Looking at existing systems, most industrial fleet platforms rely solely on transport-layer TLS and static API keys, which fail once messages pass through intermediate API gateways. Systems that implement full PKI suffer from certificate bloat and CRL lookup delays. SMARTFLEET bridges this gap by using the server's identity string directly as its public key, combining it with high-speed Ed25519 signatures and atomic replay prevention."

---

## Slide 6: Proposed SMARTFLEET Architecture

- **Slide Title:** Overall System Architecture
- **Key Bullet Points:**
  - **Edge Tier:** IoT vehicle nodes generating telemetry (GPS, speed, battery, diagnostic trouble codes).
  - **Gateway / API Tier:** High-performance asynchronous FastAPI service enforcing a strict 4-stage validation pipeline.
  - **Persistence Tier:** PostgreSQL database running on dedicated port 5435, managing persistent vehicle registries, telemetry history, and atomic replay caches.
  - **Management Tier:** Responsive React 18 / TypeScript dashboard with real-time map visualization, security audit controls, and live telemetry feeds.
  - **Research Extensions:** Integrated BQC measurement simulator and QUBO fleet routing module.
- **Visual Asset:** Full architecture diagram from `docs/diagrams/01_overall_architecture.md`.
- **Presenter Notes:**
  > "Here is our four-tier architecture. At the edge, simulated vehicle nodes construct telemetry packets and apply our cryptographic envelope. The FastAPI ingestion gateway receives the payload and executes our multi-stage security pipeline. Accepted telemetry is written to PostgreSQL on port 5435. Operators monitor vehicle status and inspect cryptographic verification logs through our React single-page application."

---

## Slide 7: Secure Ingestion Pipeline & Anti-Oracle Defense

- **Slide Title:** Staged Ingestion Pipeline & Anti-Oracle Defense
- **Key Bullet Points:**
  - Staged design prevents computational Denial-of-Service (DoS) attacks against expensive pairing operations.
  - **Stage 1: Replay & Timestamp Filter (< 1.0 ms):** Discards packets with clock drift > 30 s or age > 300 s; checks atomic nonce uniqueness.
  - **Stage 2: Ed25519 Signature Verification (0.25 ms):** Validates sender authenticity over canonical payload digest.
  - **Stage 3: IBE-KEM Decapsulation (~3.9 s):** Reconstructs symmetric key using BN128 optimal ate pairing.
  - **Stage 4: AES-256-GCM Decryption (< 0.1 ms):** Verifies 128-bit authentication tag and recovers plaintext JSON telemetry.
  - **Anti-Oracle Property:** Invalid signatures or replayed nonces are rejected in under 1 millisecond without touching the pairing engine.
- **Visual Asset:** Staged flowchart from `docs/diagrams/02_secure_transmission_sequence.md` highlighting fast-rejection gates.
- **Presenter Notes:**
  > "A crucial innovation in our design is the staged validation pipeline. Bilinear pairings in IBE require substantial CPU time. If an attacker could force the server to execute pairing operations on arbitrary inputs, they could easily mount a Denial-of-Service attack. SMARTFLEET solves this: timestamps, nonces, and Ed25519 signatures are verified in sub-millisecond time. Malicious, replayed, or forged packets are rejected immediately, protecting the pairing engine."

---

## Slide 8: Cryptographic Foundations: IBE-KEM & AES-256-GCM

- **Slide Title:** Cryptographic Core: IBE-KEM and AES-256-GCM AEAD
- **Mathematical Formulations:**
  - **Bilinear Group:** Optimal ate pairing $e: \mathbb{G}_1 \times \mathbb{G}_2 \rightarrow \mathbb{G}_T$ over Barreto–Naehrig curve (BN128).
  - **Encapsulation (Vehicle):**
    $$U = r \cdot P \in \mathbb{G}_1, \quad g_{id} = e(P_{pub}, Q_{srv})^r \in \mathbb{G}_T$$
    $$K_{sym} = \text{SHA-256}(U \parallel g_{id} \parallel ID_{srv})$$
  - **Decapsulation (Server):**
    $$g_{id}' = e(U, d_{srv}) = e(r \cdot P, s \cdot Q_{srv}) = e(P, Q_{srv})^{r \cdot s} = g_{id}$$
  - **Authenticated Associated Data (AAD):**
    $$AAD = \text{CanonicalJSON}(V_{id}, \text{timestamp}, \text{nonce}, M_{id})$$
    $$(C_{sym}, \tau) = \text{AES-GCM-Encrypt}_{K_{sym}}(IV, M, AAD)$$
- **Visual Asset:** Flowchart from `docs/diagrams/03_ibe_kem_aes_gcm_workflow.md` showing point multiplication, pairing, and AES-GCM wrapping.
- **Presenter Notes:**
  > "On this slide, we show the mathematical formulation of our IBE Key Encapsulation Mechanism. The vehicle samples a random scalar r and multiplies it by generator P to get point U. It then computes the pairing value g_id and derives a 256-bit symmetric key via SHA-256. The server decapsulates this key using its private point d_srv. Because of the bilinearity of the pairing, the server computes the exact same symmetric key. This key then encrypts the telemetry payload using AES-256-GCM, with all routing metadata cryptographically locked inside the Authenticated Associated Data."

---

## Slide 9: Authentication & Replay Protection

- **Slide Title:** Sender Authentication & Atomic Replay Defense
- **Key Mechanisms:**
  - **Vehicle Authentication:** Every vehicle possesses a unique Ed25519 signing keypair. The signature $\sigma$ is computed over $H(M) \parallel AAD$.
  - **Sub-Millisecond Verification:** Ed25519 verifies in 0.25 ms, guaranteeing that only registered fleet vehicles can submit telemetry.
  - **Timestamp Freshness Gate:** Rejects packets with $T - T_{srv} > 30\text{ s}$ (future drift) or $T_{srv} - T > 300\text{ s}$ (historical staleness).
  - **Atomic Nonce Cache:** Table `processed_message_cache` enforces unique constraint on `(vehicle_id, nonce)`.
  - **Nested Savepoint Rollback:** Concurrency conflicts trigger atomic database rollbacks without corrupting active sessions.
- **Visual Asset:** Diagrams from `docs/diagrams/04_ed25519_signature_workflow.md` and `docs/diagrams/05_replay_protection_workflow.md`.
- **Presenter Notes:**
  > "IBE by itself only guarantees confidentiality; any entity can encrypt to the server's identity. To guarantee sender authenticity, each vehicle signs the hash of the payload and the AAD using Ed25519. To eliminate replay attacks, the server maintains an atomic sliding-window cache in PostgreSQL. Even under high-concurrency race conditions, database row locks ensure that a nonce can only be processed once. Duplicate attempts trigger an immediate savepoint rollback."

---

## Slide 10: Exploratory Extension: Blind Quantum Computing (BQC)

- **Slide Title:** Privacy-Preserving Cloud Analytics: BQC Simulation
- **Research Scope & Protocol:**
  - **Model:** Broadbent–Fitzsimons–Kashefi (BFK09) Measurement-Based Quantum Computing (MBQC) protocol.
  - **Scenario:** A resource-constrained fleet client delegates sensitive risk scoring or route analytics to an untrusted quantum cloud server.
  - **Protocol Execution:**
    1. Client prepares blind single qubits: $|\theta_j\rangle = \frac{1}{\sqrt{2}}(|0\rangle + e^{i\theta_j}|1\rangle), \quad \theta_j \in \{0, \frac{\pi}{4}, \dots, \frac{7\pi}{4}\}$
    2. Server entangles qubits into a 2D Brickwork cluster state using Controlled-Z gates.
    3. Client transmits blinded measurement angles: $\phi_j' = \phi_j + \theta_j + r_j\pi$.
    4. Server measures cluster state; client decrypts true output.
  - **Experimental Findings:** 110 simulation trials verified zero server information leakage ($\Delta H = 0$).
  - **Honest Academic Boundary:** Pure classical CPU simulation of the BFK09 protocol; does **not** run on physical quantum hardware and does **not** secure the telemetry transmission channel.
- **Visual Asset:** BQC client-server sequence diagram from `docs/diagrams/07_bqc_architecture.md`.
- **Presenter Notes:**
  > "As an exploratory research extension, we investigated how future fleet systems could outsource privacy-preserving analytics to an untrusted quantum cloud. We implemented a software simulation of the BFK09 Measurement-Based Blind Quantum Computing protocol. The client blinds qubit phases and measurement angles, ensuring the server computes the correct result while learning zero information about the algorithm or data. We emphasize that this is a classical software simulation demonstrating protocol correctness, not a physical quantum computer."

---

## Slide 11: Frozen Extension: QUBO Fleet Optimization

- **Slide Title:** Route Optimization Extension: QUBO Formulation
- **Mathematical Model:**
  - Formulated multi-vehicle routing as Quadratic Unconstrained Binary Optimization (QUBO).
  - Decision variables: $x_{i,j,k} \in \{0, 1\}$ indicating whether vehicle $k$ travels from location $i$ to location $j$.
  - **Hamiltonian Objective:**
    $$H(x) = \sum_{k} \sum_{i,j} d_{i,j} x_{i,j,k} + P_{visit} \sum_{i} \Big(1 - \sum_{k,j} x_{i,j,k}\Big)^2 + P_{flow} \sum_{k,i} \Big(\sum_{j} x_{i,j,k} - \sum_{j} x_{j,i,k}\Big)^2$$
  - Solved using Classical Simulated Annealing and greedy baseline solvers.
  - Preserved in repository as a frozen research extension; operates independently of the core security transmission pipeline.
- **Visual Asset:** Graph visualization of a 5-node vehicle routing problem mapped to a binary constraint matrix.
- **Presenter Notes:**
  > "In Phase 5, we explored route optimization by formulating the multi-vehicle routing problem as a QUBO Hamiltonian. Binary decision variables represent vehicle edge transitions, while penalty multipliers enforce complete node visits and flow conservation. This module was evaluated using simulated annealing. As per our project design, this module remains a frozen research extension, clearly separated from the telemetry security pipeline."

---

## Slide 12: System Implementation & UI Demonstration

- **Slide Title:** Full-Stack Implementation & Dashboard
- **Key Implementation Highlights:**
  - **Backend:** FastAPI async web framework with modular routers, SQLAlchemy 2.0 ORM, and custom 8 MB thread stack configuration for deep recursive BN128 point arithmetic.
  - **Frontend:** React 18, TypeScript, and custom Vanilla CSS design system.
  - **Key Modules in UI:**
    - Live Fleet Map tracking simulated vehicles across synthetic urban routes.
    - Real-time Telemetry Inspector displaying raw OBD-II and battery status.
    - Cryptographic Security Console allowing operators to trigger legitimate transmissions and test attack vectors interactively.
    - Experimental Analytics dashboard displaying empirical benchmark charts.
- **Visual Asset:** Composite screenshot of the SMARTFLEET web dashboard showing the live fleet map, vehicle detail cards, and the security audit console.
- **Presenter Notes:**
  > "Here is our full-stack implementation. The backend is built with FastAPI and PostgreSQL, featuring an 8 MB worker stack to support BN128 curve recursion. The frontend is built in React 18 with a custom dark-mode design system. Operators can monitor live vehicle locations, inspect incoming telemetry, execute authorized secure transmissions, and deliberately inject attack vectors to verify server rejection in real time."

---

## Slide 13: Experimental Methodology & Test Setup

- **Slide Title:** Experimental Benchmarking Methodology
- **Testbed Environment:**
  - **Host Hardware:** Windows 11 Home (64-bit), x86_64 architecture, 8.00 GB RAM.
  - **Backend Stack:** Python 3.12, FastAPI 0.115, `py_ecc` 7.0.1, `cryptography` 43.0.3.
  - **Database:** PostgreSQL 16.1 running on dedicated port 5435.
- **Payload Test Profiles:**
  - **Small (183 B):** Core GPS coordinates, velocity, heading, and vehicle ID.
  - **Medium (1,192 B):** Complete OBD-II diagnostics, engine RPM, coolant, and tire pressure.
  - **Large (6,575 B):** Diagnostic trouble codes, alert logs, and system freeze-frame data.
- **Measurement Metrics:** Component micro-latencies, end-to-end ingest time, wire expansion, fleet scaling throughput, and concurrent attack resistance.
- **Visual Asset:** Diagram from `docs/diagrams/08_experimental_evaluation_workflow.md`.
- **Presenter Notes:**
  > "To evaluate performance, we established a strict benchmarking methodology on an 8 GB x86_64 testbed with PostgreSQL on port 5435. We defined three standardized payload sizes representing real-world vehicle telematics: small GPS updates, medium OBD-II diagnostic sets, and large fault freeze-frames. We conducted separate micro-benchmarks for individual cryptographic primitives and end-to-end benchmarks across varying fleet sizes."

---

## Slide 14: Empirical Results: Latency & Payload Expansion

- **Slide Title:** Benchmark Results: Execution Latency & Overhead
- **Key Empirical Data:**
  - **Micro-Latencies:**
    - Ed25519 Sign: **0.75 ms** | Ed25519 Verify: **0.25 ms**
    - IBE Encapsulation + AES: **4,469.55 ms** (Mean)
    - IBE Pairing Decapsulation + AES: **3,923.50 ms** (Mean)
  - **End-to-End Latency Comparison ($N=5$ trials):**
    - Small Payload (183 B): Plaintext = **51.96 ms** vs. Protected = **8,775.76 ms** (168.9×)
    - Medium Payload (1,192 B): Plaintext = **34.94 ms** vs. Protected = **8,845.67 ms** (253.2×)
    - Large Payload (6,575 B): Plaintext = **47.58 ms** vs. Protected = **8,074.06 ms** (169.7×)
  - **Wire Expansion:**
    - Small: 183 B $\rightarrow$ 1,231 B (+572.7%) | Large: 6,575 B $\rightarrow$ 9,754 B (+48.4%)
- **Visual Asset:** Dual bar chart comparing plaintext vs. protected latency alongside a payload expansion breakdown.
- **Presenter Notes:**
  > "Here are our empirical results. Ed25519 signatures execute in under one millisecond. However, IBE pairing operations in pure Python require approximately 3.9 to 4.4 seconds. This results in an end-to-end protected transmission time of approximately 8.0 to 8.8 seconds, representing a 170× to 253× latency multiplier over unencrypted transmission. Wire expansion is 1,048 bytes of constant cryptographic metadata, which represents a 572% increase for small GPS packets, but drops to just 48% overhead for large diagnostic dumps."

---

## Slide 15: Empirical Results: Fleet Scalability & Security Audit

- **Slide Title:** Fleet Scalability & Adversarial Attack Resilience
- **Scalability Metrics:**
  - Batch transmission across 1 to 25 vehicles exhibits strict linear scaling ($R^2 > 0.999$).
  - Per-vehicle processing latency remains constant at **8.10 seconds**.
  - Single-process Python throughput saturates at **0.124 messages/second**.
- **Adversarial Evaluation (12 Scenarios):**
  - **Rejection Rate: 100.0% (12 of 12 attacks successfully rejected).**
  - Tampered ciphertext, corrupted tags, modified IVs, and invalid AAD $\rightarrow$ **HTTP 400 (Rolled Back)**.
  - Forged signatures and payload mismatches $\rightarrow$ **HTTP 401 (Rolled Back)**.
  - Replayed nonces, expired timestamps, and future clock drift $\rightarrow$ **HTTP 400 (Rolled Back)**.
  - **6-Worker Concurrency Replay Test:** Exactly 1 accepted, 5 rejected; 0 duplicate database rows.
- **Visual Asset:** Summary score card showing 12/12 attack rejections alongside the 6-worker concurrency test timeline.
- **Presenter Notes:**
  > "When scaling from 1 to 25 vehicles, batch processing time scales perfectly linearly at 8.1 seconds per vehicle, resulting in a throughput of 0.12 messages per second in pure Python. Crucially, our security evaluation against 12 distinct attack scenarios achieved a 100% rejection rate. Every rejected transmission triggered a complete database rollback, leaving zero corrupted records. In our 6-worker concurrent replay test, race conditions were successfully locked: exactly one request succeeded, five were rejected, and no duplicate rows were created."

---

## Slide 16: Research Limitations & Candid Assessment

- **Slide Title:** Research Limitations & Practical Constraints
- **Key Limitations:**
  - **Pure-Python Pairing Bottleneck:** `py_ecc` execution latency (~4 seconds) is unsuited for real-time collision-avoidance V2X (requires < 100 ms).
  - **Key Escrow in IBE:** The Private Key Generator (PKG) knows the master secret $s$ and can mathematically decrypt all server traffic.
  - **Software Key Storage:** The current prototype stores vehicle private keys in filesystem configs rather than Hardware Security Modules (HSMs).
  - **Simulated Testbed:** Benchmarks were performed on virtualized processes rather than physical automotive microcontrollers (e.g., ARM Cortex-M4 / ESP32).
  - **Simulated Quantum Computation:** BQC and QUBO demonstrate mathematical protocol correctness, not physical quantum hardware execution.
- **Visual Asset:** Table categorizing limitations by Domain, Impact Level, and Proposed Engineering Resolution.
- **Presenter Notes:**
  > "We maintain rigorous academic honesty regarding our prototype's limitations. First, the 4-second pairing latency in pure Python is too slow for real-time safety-critical V2X messaging, though acceptable for periodic fleet check-ins. Second, standard IBE has a known key escrow limitation at the PKG. Third, private keys currently reside in software files rather than physical hardware security modules. Finally, our experiments were conducted on simulated nodes rather than physical vehicular ECUs."

---

## Slide 17: Conclusion & Future Work

- **Slide Title:** Conclusion & Future Research Directions
- **Key Achievements:**
  - Successfully demonstrated an authenticated, identity-based telemetry ingestion pipeline that eliminates X.509 certificate overhead.
  - Integrated AES-256-GCM AEAD, sub-millisecond Ed25519 signatures, and atomic sliding-window replay protection.
  - Empirically documented performance trade-offs and verified 100% rejection across 12 adversarial attack scenarios.
- **Future Research Directions:**
  - **Native Pairing Acceleration:** Re-implement BN128 / BLS12-381 pairings using compiled Rust (`BLST`) or C (`mcl`) to reduce pairing latency below 10 ms.
  - **Hardware Root of Trust:** Integrate automotive HSMs and TPM 2.0 chips compliant with ISO/SAE 21434.
  - **Threshold IBE:** Implement distributed multi-authority PKGs using Shamir secret sharing to resolve key escrow.
  - **Physical Microcontroller Deployment:** Port client edge code to automotive-grade microcontrollers (ESP32-S3 / ARM Cortex-M4).
- **Visual Asset:** Roadmap diagram showing planned transition from Python prototype to Rust/HSM automotive implementation.
- **Presenter Notes:**
  > "In conclusion, SMARTFLEET proves that identity-based cryptography can eliminate the certificate management bottleneck in vehicular IoT while guaranteeing confidentiality, integrity, authenticity, and replay protection. In future work, replacing Python pairing arithmetic with compiled Rust libraries will reduce latency from seconds to milliseconds, and binding keys to automotive HSMs will provide physical tamper resistance. Thank you. We are now ready to answer your questions."

---

## Slide 18: References & Defense Q&A

- **Slide Title:** Selected References & Committee Discussion
- **Key Bibliographic Citations:**
  - [1] IEEE Std 1609.2-2016: *Standard for Wireless Access in Vehicular Environments—Security Services*, 2016.
  - [2] D. Boneh and M. Franklin, "Identity-Based Encryption from the Weil Pairing," *SIAM J. Comput.*, 2003.
  - [3] D. A. McGrew and J. Viega, "The Security and Performance of the Galois/Counter Mode (GCM)," *FSE 2004*, 2004.
  - [4] D. J. Bernstein et al., "High-Speed High-Security Signatures (Ed25519)," *J. Cryptographic Engineering*, 2012.
  - [5] A. Broadbent, J. Fitzsimons, and E. Kashefi, "Universal Blind Quantum Computation," *FOCS '09*, 2009.
  - [6] ISO/SAE 21434:2021: *Road Vehicles—Cybersecurity Engineering*, 2021.
- **Open Floor:** "We invite questions, observations, and feedback from the examination committee."
- **Presenter Notes:**
  > "These are our primary academic references, spanning foundational standards in vehicular security, pairing-based cryptography, symmetric authenticated encryption, and blind quantum computing. We welcome your questions."
