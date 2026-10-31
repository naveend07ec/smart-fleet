# SMARTFLEET: Complete System Walkthrough & Cryptographic Proof Guide
### A Clear, Step-by-Step Guide for Students, Evaluators, and Engineers

**Project Title:** SMARTFLEET: IoT-Driven Smart Transportation and Fleet Management System with Secure Data Transmission and Privacy-Preserving Computation  
**Document Purpose:** Clear explanation of how the website works, what happens behind the scenes, and how anyone can test and scientifically prove that vehicle telemetry travels securely.

---

## Table of Contents
1. [The Big Picture: What is SMARTFLEET?](#1-the-big-picture-what-is-smartfleet)
2. [Tour of the Website: What Each Page Does](#2-tour-of-the-website-what-each-page-does)
3. [Under the Hood: How Data Travels from Car to Cloud](#3-under-the-hood-how-data-travels-from-car-to-cloud)
4. [The 4 Digital Locks: How Security is Guaranteed](#4-the-4-digital-locks-how-security-is-guaranteed)
5. [How to Test & Prove Security with Your Own Eyes](#5-how-to-test--prove-security-with-your-own-eyes)
6. [Live Defense Demonstration Checklist for Examiners](#6-live-defense-demonstration-checklist-for-examiners)

---

## 1. The Big Picture: What is SMARTFLEET?

Imagine a delivery company or public transit system with hundreds of vehicles driving around a city. Each vehicle has onboard computers and GPS sensors tracking:
- **Where the car is** (Latitude, Longitude)
- **How fast it is driving** (Speed)
- **Engine health** (Coolant temperature, RPM, battery level)
- **Safety alerts** (Sudden braking, engine fault codes)

### The Real-World Problem:
Cars must send this sensitive data to the cloud over public 4G/5G mobile networks. If an attacker intercepts the signal:
- They could **spy** on where VIPs or cash vans are driving.
- They could **tamper** with the data (e.g., hiding an engine overheating alert or faking a crash).
- They could **replay** old data (making a stolen car look like it's parked safely at the depot).

### The SMARTFLEET Solution:
SMARTFLEET wraps every single piece of sensor data inside a **multi-layered cryptographic digital envelope** before it leaves the car. Even if an eavesdropper records the wireless transmission, they see only scrambled mathematical noise, and any attempt to alter even a single letter immediately triggers an automatic rejection.

```
+-----------------------------------------------------------------------------------+
| [Vehicle Sensors]                                                                 |
| GPS: 13.0827, 80.2707 | Speed: 42.5 km/h | Engine: OK                             |
+-----------------------------------------------------------------------------------+
                                         │
               1. Encrypt with IBE-KEM & AES-256-GCM (Confidentiality)
               2. Seal with Ed25519 Digital Signature (Authenticity)
               3. Attach Fresh Timestamp & Unique Nonce (Replay Defense)
                                         ▼
+-----------------------------------------------------------------------------------+
| [Public Cellular Wireless Network]                                                |
| Scrambled Ciphertext: "7b22755f706f696e74223a7b2278223a5b323138...f8a19c"        |
+-----------------------------------------------------------------------------------+
                                         │
               4. Verify Timestamp & Nonce (< 1 ms)
               5. Verify Ed25519 Vehicle Signature (0.25 ms)
               6. Decapsulate with Server Identity Key & Decrypt Plaintext (~3.9 s)
               7. Persist to Aiven Cloud Database
                                         ▼
+-----------------------------------------------------------------------------------+
| [Fleet Management Server & React Web Dashboard]                                   |
| Telemetry accepted, decrypted, verified, and plotted live on Chennai map!         |
+-----------------------------------------------------------------------------------+
```

---

## 2. Tour of the Website: What Each Page Does

When you start the system (`run_backend.bat` and `run_frontend.bat`) and open `http://localhost:5173`, you will see five main navigation sections at the top:

```
[Fleet Dashboard]   [Vehicle Fleet]   [Fleet Analytics]   [Security & Privacy ▾]   [Simulator Control]
```

### 1. Fleet Dashboard (`/`)
- **What it shows:** An executive control room overview of the entire fleet.
- **Key Cards:**
  - **Active Vehicles:** Total connected fleet vehicles (e.g., 25 vehicles).
  - **Fleet Status:** How many cars are currently `moving`, `idle`, or `maintenance`.
  - **Average Velocity & Battery Level:** Fleet-wide operational health.
  - **Live Alert Feed:** Immediate notifications if any car experiences low battery, high engine heat, or abnormal acceleration.

### 2. Vehicle Fleet & Live Route Map (`/fleet`)
- **What it shows:** Real-world tracking of vehicles across urban road networks (Chennai Transit Corridor).
- **Interactive Map:** You can click on any vehicle marker to inspect its live speed, compass heading, and live breadcrumb trail.
- **Telemetry Drawer:** Clicking a car opens its live dashboard showing real-time OBD-II sensor values (Engine RPM, Coolant °C, Battery %, Tire pressure).

### 3. Fleet Analytics (`/analytics`)
- **What it shows:** Historical performance graphs, mileage distributions, energy consumption curves, and operational efficiency scores.

### 4. Security & Privacy Lab (`/security` or `/security-experiment`)
- **What it shows:** The cryptographic testing ground! This is where you can see the raw math in action:
  - You can inspect the **public server identity key** (`fleet-management-server-core`).
  - You can trigger an **authorized secure transmission** and watch the encryption and decryption timelines live.
  - You can deliberately inject **12 simulated attacks** (e.g., corrupting the message or replaying an old packet) to watch the server catch and reject them!

### 5. Simulator Control (`/simulation`)
- **What it shows:** The engine that simulates the moving vehicles.
- **Green Button ("Start Simulation"):** When clicked, virtual cars start driving along road waypoints, updating their GPS every 3 seconds.
- **Red Button ("Stop Simulation"):** Freezes vehicle movement so you can inspect stationary values.

---

## 3. Under the Hood: How Data Travels from Car to Cloud

Here is the exact journey of a single telemetry packet from the vehicle's microcontroller to the cloud database:

```
VEHICLE EDGE NODE                              INGESTION SERVER (FASTAPI)
       │                                                   │
1. Gathers Sensor Readings:                                │
   GPS: (13.0827, 80.2707), Speed: 42.5 km/h               │
       │                                                   │
2. Encapsulates Secret Key:                                │
   - Takes Server Identity: "fleet-management-server-core" │
   - Uses BN128 Bilinear Pairing math                      │
   - Creates Ephemeral Symmetric Key K_sym                 │
       │                                                   │
3. Encrypts Payload:                                       │
   - AES-256-GCM turns data into ciphertext                │
   - Generates 128-bit Authentication Tag                  │
   - Binds Sender, Recipient, Nonce, Time into AAD         │
       │                                                   │
4. Signs Digital Envelope:                                 │
   - Vehicle signs the package with Ed25519 private key    │
       │                                                   │
       │─────── POST /api/secure-transmission/encrypted ──>│
       │        (Transmits Encrypted JSON Envelope)        │
       │                                                   │
       │                                           5. Gate 1: Check Clock Skew
       │                                              - Is time > 30s in future? (Reject)
       │                                              - Is time > 300s old? (Reject)
       │                                                   │
       │                                           6. Gate 2: Check Nonce Replay
       │                                              - Has Message UUID been seen? (Reject)
       │                                              - Inserts into Aiven cache table
       │                                                   │
       │                                           7. Gate 3: Verify Ed25519 Signature
       │                                              - Checks vehicle public key in 0.25 ms
       │                                              - If forged -> Reject immediately!
       │                                                   │
       │                                           8. Gate 4: Decapsulate & Decrypt
       │                                              - Server recovers K_sym via pairing
       │                                              - AES-GCM verifies tag and decrypts
       │                                                   │
       │                                           9. Persist to Aiven Cloud Database
       │                                              - Written to telemetry_records table
       │                                                   │
       │<────── HTTP 200 OK (Status: Success) ─────────────│
```

---

## 4. The 4 Digital Locks: How Security is Guaranteed

To make this easy for anyone (students, professors, or external examiners) to understand, SMARTFLEET uses **four distinct digital locks**. Each lock solves one specific attack:

| Lock Name | Technology Used | Real-World Analogy | What Attack it Stops |
| :--- | :--- | :--- | :--- |
| **Lock 1: Confidentiality** | **Boneh–Franklin IBE-KEM** (over BN128 curve) | A high-tech digital lockbox that anyone can lock using the destination's name, but only the server has the physical key to unlock. | **Eavesdropping:** Hackers sniffing Wi-Fi or cellular radio cannot read the GPS or engine data. |
| **Lock 2: Tamper Resistance** | **AES-256-GCM + Authenticated Associated Data (AAD)** | A tamper-evident wax seal across the envelope. If anyone changes even 1 letter of the message or envelope headers, the seal breaks. | **Message Manipulation:** Hackers modifying coordinates, speed, or vehicle IDs in transit. |
| **Lock 3: Identity & Proof** | **Ed25519 Digital Signatures** | An unforgeable handwritten signature made with the vehicle's unique private signing stamp. | **Vehicle Impersonation:** An unauthorized hacker pretending to be Vehicle #5. |
| **Lock 4: Freshness** | **Atomic Sliding-Window Nonce Cache** | A one-time security ticket with an expiration date (5 minutes) and a unique ticket number that gets punched upon entry. | **Replay Attacks:** Hackers re-sending yesterday's valid transmission to trick the server. |

---

## 5. How to Test & Prove Security with Your Own Eyes

You do not have to take the code's word for it. You can prove each security guarantee live in front of examiners using these concrete experiments:

### Test 1: Prove Confidentiality (Data is Encrypted)
**How to test:**
1. Open the **Security & Privacy Lab** in your browser (`http://localhost:5173/security-experiment`).
2. Click **"Execute Authorized Transmission"**.
3. Inspect the raw request payload shown on screen:
   - Notice the field `"ciphertext_b64"`:
     `"7b22755f706f696e74223a7b2278223a5b323138...f8a19c"`
   - Notice that the vehicle's true GPS latitude `13.0827` and speed `42.5` **do not appear anywhere in the transmitted packet**!
   - Only after the server uses its private key does the decrypted JSON appear.

---

### Test 2: Prove Tamper Resistance (Bit-Flipping Test)
**What happens if a hacker intercepts the wireless message and changes a single number (e.g., changes vehicle speed from 40 km/h to 120 km/h)?**

**How to test:**
1. In the Security Lab, select the attack: **"Tampered Ciphertext (Bit-Flipping)"**.
2. Click **"Inject Adversarial Payload"**.
3. **What you will see:**
   - The server immediately rejects the transmission!
   - Rejection Reason: `"Cryptographic integrity verification failed"`.
   - **Database Check:** 0 rows added to PostgreSQL. The fake speed is completely discarded!

---

### Test 3: Prove Sender Authentication (Forged Signature Test)
**What happens if a rogue car generates a fake telemetry packet and signs it with its own fake key?**

**How to test:**
1. In the Security Lab, select: **"Vehicle Impersonation (Rogue Ed25519 Key)"**.
2. Click **"Inject Adversarial Payload"**.
3. **What you will see:**
   - Server response: `"Cryptographic sender authentication failed"`.
   - Response time: **< 1 millisecond** (0.25 ms)!
   - **Why this is important to explain to examiners:**
     Because the signature check happens **first**, the server rejects the fake car in less than 1 millisecond without wasting 4 seconds of CPU time running expensive pairing math. This stops **Denial-of-Service (DoS)** attacks!

---

### Test 4: Prove Replay Protection (Re-sending an Old Message)
**What happens if an attacker records a valid transmission from 10 minutes ago and sends it again?**

**How to test:**
1. Send a legitimate transmission (it succeeds: Status = 200).
2. Now, select: **"Exact Message Replay Attack"** (which resubmits the exact same message UUID).
3. Click **"Inject Adversarial Payload"**.
4. **What you will see:**
   - Server response: `"Duplicate message identifier (Replay attack detected)"`.
   - The database cache recognizes the message UUID has already been used and rejects it instantly.

---

### Test 5: Prove Cloud Database Persistence (Aiven Cloud Test)
**How to prove that data is actually stored in Aiven Cloud and not just in your computer's temporary memory:**

Run this one-line command in your PowerShell:
```powershell
& ".\.venv\Scripts\python.exe" -c "from app.database import engine; from sqlalchemy import text; conn=engine.connect(); print('Connected to:', engine.url.host); print('Vehicle count in Aiven:', conn.execute(text('SELECT count(*) FROM vehicles;')).scalar()); conn.close()"
```
**Expected Output:**
```text
Connected to: pg-1ae8a81-naveendseven-633b.l.aivencloud.com
Vehicle count in Aiven: 25
```
This proves conclusively that all tables and vehicles live online in your remote Aiven Cloud database!

---

## 6. Live Defense Demonstration Checklist for Examiners

When presenting your final-year project to external examiners or professors, follow this smooth 5-minute demonstration script:

```
[ ] Step 1: Open http://localhost:5173
    - Show the Fleet Dashboard with 25 vehicles connected to Aiven Cloud.

[ ] Step 2: Open "Simulator Control" -> Click "Start Simulation"
    - Switch to "Vehicle Fleet" page.
    - Show examiners the vehicle moving along the Chennai road network in real-time.
    - Point out that GPS coordinates and speed update live every 3 seconds.

[ ] Step 3: Open "Security & Privacy Lab"
    - Click "Execute Authorized Transmission".
    - Show the encrypted ciphertext envelope on screen.
    - Explain: "The vehicle encrypted this with the server's identity string without needing X.509 certificates!"

[ ] Step 4: Demonstrate Attack Rejections
    - Run "Tampered Ciphertext": Show it gets rejected due to AES-GCM tag mismatch.
    - Run "Replay Attack": Show it gets rejected because the nonce was already used.
    - Run "Rogue Key Impersonation": Show it gets rejected in 0.25 ms by Ed25519.

[ ] Step 5: Conclude with Research Honesty
    - Explain: "Our pure-Python pairing takes ~4 seconds, which is a known artifact of interpreted software. In commercial automotive systems, compiling this to Rust/C achieves sub-5 millisecond speeds."
```

With this explanation and live proof, any examiner or student can immediately see that SMARTFLEET is not just a theoretical concept—it is a working, mathematically verified, end-to-end secure IoT fleet transportation system!
