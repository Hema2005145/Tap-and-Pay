# QSP3 Tap-and-Pay: Quantum-Secure Peer-to-Peer Payment System

---

## 1. Project Overview

**QSP3 Tap-and-Pay** is a quantum-resistant, offline-capable mobile payment system designed to secure point-of-sale and peer-to-peer financial transactions. The system combines:

- **Post-Quantum Cryptography (PQC):** Kyber-like lattice-based Key Encapsulation Mechanism (ML-KEM) for quantum-resistant session key negotiation.
- **Mutual TLS (mTLS):** Client and server identity validation using X.509 certificates and TLS 1.3 over QUIC.
- **Zero-Knowledge Proofs (ZKP):** Groth16 / Circom balance-check proof verifying that the sender has sufficient funds without revealing their total balance.
- **Behavioral Edge AI:** TensorFlow Lite INT8 autoencoder evaluating device context (gyroscope tilt X/Y/Z, location coordinates, transaction hour) to detect physical theft or anomalous conditions before payment execution.
- **Multi-Party Computation (MPC):** Shamir's Secret Sharing (2-of-3 threshold) securing the master signing key across client and server.
- **Secure QUIC Transport:** Wire-speed encrypted payment execution over UDP port 4433 via `aioquic`.
- **Atomic Cloud Settlement:** MongoDB multi-document ACID transactions ensuring atomic sender debit and receiver credit.
- **Blockchain Audit Trail:** Local Ethereum smart contract (`AuditTrail.sol`) logging cryptographic receipts for immutability.
- **Real-Time Telemetry:** Node.js Socket.IO relay streaming a 12-stage cryptographic pipeline tracker to mobile devices.

### Architecture Flow

```
[Mobile Phone / Browser] (Vite :5173)
       │
       │ HTTP POST /quic/execute-payment
       ▼
[FastAPI Gateway] (:8000)
       │
       │ Spawns PaymentClient (client/quic_client.py)
       │   ├─ Edge AI Anomaly Check (TFLite INT8)
       │   ├─ Groth16 ZKP Proof Generation (npx snarkjs)
       │   ├─ PQC Handshake & AES-256-GCM Encryption
       │   └─ Non-blocking Socket.IO Telemetry Broadcast (:3001)
       ▼
[QUIC Payment Server] (UDP :4433)
       │
       │ Decrypts AES payload, verifies TOTP window (120s)
       │ Verifies Groth16 ZKP Proof (py_ecc native BN128)
       │ Reconstructs Shamir MPC Key (2-of-3 threshold)
       ▼
[Atomic ACID Settlement] (MongoDB Replica Set rs0 :27017)
       │
       │ Atomically: Deducts Sender & Credits Receiver
       ▼
[Blockchain Audit] (Local In-Memory EVM via Web3 / eth-tester)
       │
       │ Mines AuditTrail.sol receipt block
       ▼
[Socket.IO Relay] (:3001) ──► Broadcasts "PAYMENT_ACK" to Phones
```

---

## 2. Prerequisites

| Software | Required Version | Verification Command | Notes |
| :--- | :--- | :--- | :--- |
| **Operating System** | Windows 10/11 (or Linux/macOS) | `[System.Environment]::OSVersion` | Tested primarily on Windows 11 |
| **Python** | 3.10 to 3.13 | `python --version` | Tested on Python 3.13.7 |
| **Node.js** | v18.0.0 or higher | `node --version` | Tested on v22.19.0 |
| **npm** | v9.0.0 or higher | `npm --version` | Tested on 10.9.3 |
| **MongoDB Community** | v6.0+ or v7.0+ | `mongod --version` | **Must run as a replica set** (`rs0`) for ACID transactions |
| **mongosh** | v2.0+ | `mongosh --version` | Tested on 2.5.10 |
| **npx / snarkjs** | `snarkjs@0.7.6` | `npx snarkjs --version` | Runs via `npx` automatically; no global install required |
| **Git** | Any recent version | `git --version` | For repository management |

---

## 3. Repository Structure

```
Tap-and-Pay/
├── blockchain/                      # Blockchain audit layer
│   ├── AuditTrail.sol               # Solidity smart contract for immutable audit records
│   ├── test_blockchain_metrics.py   # Latency, gas, and replay test suite
│   └── web3_integration.py          # Web3.py wrapper with in-memory eth-tester EVM
├── certs/                           # Security, mTLS & key artifacts
│   ├── ca_cert.pem / ca_key.pem     # Root Certificate Authority
│   ├── server_cert.pem / server_key.pem  # Server mTLS cert and key
│   ├── client_cert.pem / client_key.pem  # Client mTLS cert and key
│   ├── client_share.json            # Shamir MPC share for client (x=1)
│   ├── server_share.json            # Shamir MPC share for server (x=2)
│   ├── edge_backup_share.json       # Shamir MPC share for backup (x=3)
│   ├── master_key_hash.txt          # SHA-256 hash of reconstructed master secret
│   ├── server_pqc_keys.json         # Persisted Kyber-like PQC public/private keypair
│   └── generate_certs.py            # Script to recreate X.509 mTLS certificates
├── client/                          # QUIC client & edge intelligence
│   ├── client_fl.py                 # Federated learning edge client (Flower)
│   └── quic_client.py               # PaymentClient: ZKP, AI, PQC, AES & QUIC transmit
├── data/                            # Training & testing datasets for Behavioral AI
│   ├── train_normal.csv             # Normal baseline transaction telemetry
│   └── test_anomalies.csv           # Synthesized anomalous / theft telemetry
├── mobile_ui/                       # Frontend application & relay server
│   ├── package.json                 # React 19, Vite, Socket.IO client dependencies
│   ├── server.cjs                   # Node.js Socket.IO event relay server (Port 3001)
│   ├── vite.config.js               # Vite bundler configuration
│   └── src/
│       ├── App.jsx                  # Main dashboard, 12-stage pipeline, multi-user UI
│       ├── App.css                  # UI layout and styling
│       └── index.css                # Global typography and base styles
├── models/                          # Behavioral AI model artifacts
│   ├── behavioral_ai_quantized.tflite # Quantized INT8 autoencoder model
│   ├── scaler.pkl                   # StandardScaler for normalizing input vectors
│   ├── threshold.txt                # MAE anomaly cutoff threshold (0.1500)
│   └── behavioral_ai_full.keras     # Full Keras model (reference)
├── server/                          # Backend services
│   ├── api_gateway.py               # FastAPI REST API (Port 8000)
│   ├── quic_server.py               # Asynchronous QUIC payment server (UDP Port 4433)
│   └── server_fl.py                 # Federated learning server aggregator (Flower)
├── tests/                           # Automated test suites
│   └── test_phase2_multi_user.py    # Multi-user atomic settlement & audit tests
├── utils/                           # Core utilities and cryptographic primitives
│   ├── binary_payload.py            # 16-byte packed binary struct serialization
│   ├── crypto_payload.py            # AES-256-GCM encryption/decryption
│   ├── db.py                        # MongoDB Motor client & settle_payment_atomic()
│   ├── event_broadcaster.py         # Threaded broadcaster forwarding telemetry to :3001
│   ├── pqc.py                       # Lattice-based Kyber-like key exchange
│   ├── shamir_mpc.py                # Shamir's Secret Sharing polynomial arithmetic
│   ├── totp.py                      # TOTP generation and verification
│   └── zkp_verifier.py              # Native Python Groth16 verifier using py_ecc
├── zkp/                             # Zero-Knowledge Proof circuits & keys
│   ├── balance_check.circom         # Circom circuit: proves balance >= amount
│   ├── balance_check_final.zkey     # Groth16 proving key
│   ├── verification_key.json        # Groth16 verification key used by server
│   ├── pot12_final.ptau             # Powers of Tau phase 1 trusted setup artifact
│   └── balance_check_js/            # Compiled WebAssembly witness calculator
│       ├── balance_check.wasm       # Wasm witness generator
│       └── generate_witness.js      # Node.js witness generator runner
├── requirements.txt                 # Python dependencies
└── start_all.bat                    # 1-click batch launcher (Windows)
```

---

## 4. Initial Project Setup

Run all commands from a **Windows PowerShell** terminal.

### Step 1: Clone and Enter the Repository

```powershell
git clone https://github.com/Hema2005145/Tap-and-Pay.git
cd Tap-and-Pay
git checkout main
```

### Step 2: Create and Activate Python Virtual Environment

From repository root (`c:\Users\HEMA\Tap-and-Pay`):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

*(If PowerShell script execution is restricted, run: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`)*

### Step 3: Install Python Dependencies

```powershell
pip install --upgrade pip
pip install -r requirements.txt
pip install py_ecc
```

*Note: `py_ecc` is required by `utils/zkp_verifier.py` for native Python BN128 elliptic curve pairing.*

### Step 4: Install Frontend & Relay Dependencies

```powershell
cd mobile_ui
npm install
cd ..
```

---

## 5. Configuration

All configuration uses sensible defaults in code. An optional `.env` file can be placed in the repository root if you need to override defaults:

| Variable | File Read In | Default Value | Purpose |
| :--- | :--- | :--- | :--- |
| `MONGODB_ATLAS_URI` | `utils/db.py` | `None` (falls back to `mongodb://localhost:27017`) | MongoDB connection string |
| `DB_NAME` | `utils/db.py` | `qsp3_payment` | Target database name |
| `SOCKET_RELAY_URL` | `utils/event_broadcaster.py` | `http://127.0.0.1:3001/emit` | Target endpoint for telemetry broadcasts |

### Frontend Network Target Configuration

In [`mobile_ui/src/App.jsx`](file:///c:/Users/HEMA/Tap-and-Pay/mobile_ui/src/App.jsx#L6-L7):

```javascript
// Lines 6-7:
const SOCKET_URL = 'http://192.168.1.4:3001';
const API_URL = 'http://192.168.1.4:8000';
```

- **For local-only development on your laptop:** Change both URLs to `http://127.0.0.1:3001` and `http://127.0.0.1:8000`.
- **For physical phone testing over Wi-Fi:** Set both URLs to your laptop's current Wi-Fi LAN IP (e.g., `http://192.168.1.4:3001` and `http://192.168.1.4:8000`).

---

## 6. MongoDB Setup

MongoDB **must be running as a replica set** (e.g., `rs0`) because the atomic payment settlement logic (`settle_payment_atomic()` in `utils/db.py`) uses genuine MongoDB multi-document ACID transactions (`session.start_transaction()`). Standalone MongoDB instances will reject these transactions.

### A. Starting MongoDB with Replica Set Support

If running MongoDB as a standalone service or from the command line:

```powershell
mongod --dbpath "C:\data\db" --replSet rs0 --port 27017
```

*(Ensure the directory `C:\data\db` exists, or specify your preferred database path).*

If MongoDB is installed as a Windows Service, add `replication.replSetName: rs0` to your `mongod.cfg` and restart the service:

```powershell
Restart-Service MongoDB
```

### B. Initiating the Replica Set

Open `mongosh` in a terminal:

```powershell
mongosh
```

Inside `mongosh`, execute:

```javascript
rs.initiate()
```

Verify the replica set status:

```javascript
rs.status().ok
// Expected output: 1
rs.status().members[0].stateStr
// Expected output: "PRIMARY"
```

### C. Database & Demo Accounts

The application uses database `qsp3_payment` and collection `users`.

Connect to the database:

```javascript
use qsp3_payment
```

Ensure the four standard demonstration accounts exist:

```javascript
db.users.bulkWrite([
  {
    updateOne: {
      filter: { client_id: 100 },
      update: { $setOnInsert: { client_id: 100, name: "Customer A", balance_cents: 50000, created_at: new Date() } },
      upsert: true
    }
  },
  {
    updateOne: {
      filter: { client_id: 200 },
      update: { $setOnInsert: { client_id: 200, name: "Customer B", balance_cents: 50000, created_at: new Date() } },
      upsert: true
    }
  },
  {
    updateOne: {
      filter: { client_id: 300 },
      update: { $setOnInsert: { client_id: 300, name: "Customer C", balance_cents: 50000, created_at: new Date() } },
      upsert: true
    }
  },
  {
    updateOne: {
      filter: { client_id: 400 },
      update: { $setOnInsert: { client_id: 400, name: "Merchant A", balance_cents: 10000, created_at: new Date() } },
      upsert: true
    }
  }
])
```

Verify all accounts:

```javascript
db.users.find({}, { _id: 0, client_id: 1, name: 1, balance_cents: 1 })
```

Expected output:
```json
[
  { "client_id": 100, "name": "Customer A", "balance_cents": 50000 },
  { "client_id": 200, "name": "Customer B", "balance_cents": 50000 },
  { "client_id": 300, "name": "Customer C", "balance_cents": 50000 },
  { "client_id": 400, "name": "Merchant A", "balance_cents": 10000 }
]
```

To view transaction history:

```javascript
db.transactions.find().sort({ timestamp: -1 }).limit(5)
```

---

## 7. Security Files & Certificates

All required security and cryptographic artifacts are **already present** in the `certs/` directory:

| Artifact | File Path | Present | Description |
| :--- | :--- | :---: | :--- |
| **Root CA Certificate** | `certs/ca_cert.pem` | Yes | Trusted root certificate for mTLS |
| **Root CA Key** | `certs/ca_key.pem` | Yes | CA private key |
| **Server Certificate** | `certs/server_cert.pem` | Yes | Server mTLS certificate (CN: localhost, SAN: 127.0.0.1) |
| **Server Key** | `certs/server_key.pem` | Yes | Server RSA 2048-bit private key |
| **Client Certificate** | `certs/client_cert.pem` | Yes | Client mTLS certificate (signed by CA) |
| **Client Key** | `certs/client_key.pem` | Yes | Client RSA 2048-bit private key |
| **Server PQC Keys** | `certs/server_pqc_keys.json`| Yes | Persisted Kyber-like lattice public/private keypair |
| **Client MPC Share** | `certs/client_share.json` | Yes | Shamir share (x=1) for 2-of-3 key reconstruction |
| **Server MPC Share** | `certs/server_share.json` | Yes | Shamir share (x=2) for 2-of-3 key reconstruction |
| **Master Key Hash** | `certs/master_key_hash.txt` | Yes | SHA-256 reference hash of the master signing key |

*(Optional)* To regenerate the mTLS certificates from scratch, run:

```powershell
python certs/generate_certs.py
```

---

## 8. ZKP (Zero-Knowledge Proof) Setup

The Groth16 Zero-Knowledge Proof circuit proves that `balance >= amount` without exposing the sender's private balance.

### Artifacts in `zkp/`

All circuit artifacts are **pre-compiled and present in the repository**:
- Circuit: `zkp/balance_check.circom`
- R1CS constraints: `zkp/balance_check.r1cs`
- WebAssembly witness generator: `zkp/balance_check_js/balance_check.wasm`
- Witness calculator runner: `zkp/balance_check_js/generate_witness.js`
- Proving Key: `zkp/balance_check_final.zkey`
- Verification Key: `zkp/verification_key.json`
- Trusted Setup: `zkp/pot12_final.ptau`

### Runtime Execution Commands

When `PaymentClient.generate_zkp()` runs:
1. Writes input vector: `temp_input.json` (`{"amount": amount_cents, "balance": private_balance}`)
2. Calculates witness:
   ```bash
   node balance_check_js/generate_witness.js balance_check_js/balance_check.wasm temp_input.json temp_witness.wtns
   ```
3. Generates Groth16 proof:
   ```bash
   npx snarkjs groth16 prove balance_check_final.zkey temp_witness.wtns temp_proof.json temp_public.json
   ```
4. Server verifies the proof in pure Python memory using `utils/zkp_verifier.py` (via `py_ecc.bn128`).

---

## 9. AI / Behavioral Model Setup

The Edge AI component runs inference locally before transmitting payment packets:

- **Location:** `models/`
- **Artifacts:**
  - `models/behavioral_ai_quantized.tflite`: INT8 quantized autoencoder model (~12 KB).
  - `models/scaler.pkl`: Serialized `StandardScaler` to scale 7 features (`amount, lat, lon, tilt_x, tilt_y, tilt_z, hour`).
  - `models/threshold.txt`: Anomaly threshold floating-point value (`0.1500`).
- **Execution:** Loaded by `BehavioralAI` in `client/quic_client.py`. If the Mean Absolute Error (MAE) of the reconstructed vector exceeds `threshold.txt`, the transaction is blocked immediately (`AI_BLOCKED`) before hitting the network.

---

## 10. Starting the Complete Project

To run the complete system, open **5 separate PowerShell terminal windows**. Ensure your virtual environment is activated in terminals running Python (`.\.venv\Scripts\Activate.ps1`).

---

### TERMINAL 1 — MongoDB Daemon

```powershell
mongod --replSet rs0 --port 27017
```
- **Port:** `27017` (TCP)
- **Directory:** Any (or system service)
- **Expected Output:** `[initandlisten] waiting for connections on port 27017`

---

### TERMINAL 2 — Socket.IO Telemetry Relay

```powershell
cd mobile_ui
node server.cjs
```
- **Port:** `3001` (TCP, HTTP & WebSockets)
- **Directory:** `Tap-and-Pay\mobile_ui`
- **Expected Output:**
  ```
  WebSocket server running on port 3001...
  WebSocket server & Event Relay running on port 3001...
  ```

---

### TERMINAL 3 — QUIC Payment Server

```powershell
python server/quic_server.py
```
- **Port:** `4433` (UDP)
- **Directory:** `Tap-and-Pay` (root)
- **Expected Output:**
  ```
  Blockchain [Web3]: Compiling and deploying AuditTrail.sol to local blockchain...
  Blockchain [Web3]: Contract deployed at 0x...
  Server: Loading persisted PQC Keypair...
  Server [MPC]: Loaded Server Share and Master Key Hash.
  Starting QUIC Payment Server on 0.0.0.0:4433 (mTLS Enabled)...
  ```

---

### TERMINAL 4 — FastAPI API Gateway

```powershell
python -m uvicorn server.api_gateway:app --host 0.0.0.0 --port 8000
```
- **Port:** `8000` (TCP, HTTP)
- **Directory:** `Tap-and-Pay` (root)
- **Expected Output:**
  ```
  INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
  INFO:     Application startup complete.
  ```

---

### TERMINAL 5 — React / Vite Frontend

```powershell
cd mobile_ui
npm run dev -- --host
```
- **Port:** `5173` (TCP, HTTP)
- **Directory:** `Tap-and-Pay\mobile_ui`
- **Expected Output:**
  ```
  VITE v8.0.16  ready in ... ms

  ➜  Local:   http://localhost:5173/
  ➜  Network: http://192.168.1.4:5173/
  ```

---

## 11. Service Verification

Verify that all five services are healthy:

### 1. Verify MongoDB
```powershell
mongosh --eval "rs.status().ok"
```
Expected output: `1`

### 2. Verify Socket.IO Relay
```powershell
curl http://127.0.0.1:3001/health
```
Expected output: `{"status":"ok","service":"QSP3 WebSocket Relay"}`

### 3. Verify FastAPI Gateway
```powershell
curl http://127.0.0.1:8000/
```
Expected output: `{"status":"QSP3 Gateway Online (MongoDB Atlas Connected)","version":"1.0.0"}`

### 4. Verify QUIC Server Daemon
```powershell
curl http://127.0.0.1:8000/quic/status
```
Expected output: `{"quic_server_online":true,"port":4433,"host":"127.0.0.1"}`

### 5. Verify User Balances
```powershell
curl http://127.0.0.1:8000/balance/100
curl http://127.0.0.1:8000/balance/200
```
Expected output: `{"client_id":100,"balance_str":"$500.00","balance_cents":50000}`

---

## 12. Frontend Access

- **Localhost:** `http://localhost:5173`
- **Network / Mobile Access:** `http://<YOUR_LAN_IP>:5173` (e.g., `http://192.168.1.4:5173`)

### Localhost vs. LAN IP
- `127.0.0.1` / `localhost` only functions when accessing the web dashboard from the laptop itself.
- To connect external physical smartphones over Wi-Fi, the URLs in `mobile_ui/src/App.jsx` must point to your laptop's Wi-Fi LAN IP (e.g., `192.168.1.4`), and phones must connect to the same Wi-Fi network.

---

## 13. Two-Phone / LAN Setup

To run a physical payment demonstration between two smartphones:

```
[Phone A: Sender]                          [Phone B: Receiver / Merchant]
  (Browser @ 192.168.1.4:5173)               (Browser @ 192.168.1.4:5173)
       │                                          │
       │ Wi-Fi LAN                                │ Wi-Fi LAN
       ▼                                          ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        LAPTOP (192.168.1.4)                            │
│                                                                        │
│  FastAPI (:8000) ──► PaymentClient ──► QUIC Server (:4433 UDP)        │
│                           │                                            │
│                           ├─► MongoDB Replica Set (:27017)             │
│                           ├─► Blockchain AuditTrail.sol (in-memory)   │
│                           └─► Socket.IO Relay (:3001)                  │
│                                     │                                  │
│                                     └───► Broadcasts Real-Time State   │
└────────────────────────────────────────────────────────────────────────┘
```

> **IMPORTANT:** Smartphones communicate **through the laptop backend services**, not direct phone-to-phone, because modern mobile operating systems restrict direct peer-to-peer NFC data transfer between browsers.

### Setup Instructions

1. Connect your laptop and both phones to the **same Wi-Fi network**.
2. Find your laptop's LAN IP:
   ```powershell
   ipconfig
   ```
   Look for `IPv4 Address` under your active Wi-Fi adapter (e.g., `192.168.1.4`).
3. Ensure [`mobile_ui/src/App.jsx`](file:///c:/Users/HEMA/Tap-and-Pay/mobile_ui/src/App.jsx#L6-L7) has that IP configured for `SOCKET_URL` and `API_URL`.
4. Open **Google Chrome** on both phones:
   - **Phone A:** Navigate to `http://192.168.1.4:5173`
   - **Phone B:** Navigate to `http://192.168.1.4:5173`
5. On **Phone A**, select **Sender** and choose **#200 — Customer B**.
6. On **Phone B**, select **Receiver** (or Merchant Mode) and choose **#300 — Customer C** (or **#400 — Merchant A**).

---

## 14. Demo User Accounts

| Client ID | Display Name | Default Balance | Role | Description |
| :---: | :--- | :---: | :---: | :--- |
| **100** | Customer A | $500.00 (`50000` cents) | customer | Primary sender |
| **200** | Customer B | $500.00 (`50000` cents) | customer | Secondary sender / peer |
| **300** | Customer C | $500.00 (`50000` cents) | customer | Peer receiver |
| **400** | Merchant A | $100.00 (`10000` cents) | merchant | Default point-of-sale merchant |

- **Storage:** MongoDB collection `qsp3_payment.users`
- **Representation:** Balances are stored as integers in **cents** (`balance_cents`). `$500.00` is stored as `50000`.

---

## 15. How to Use the Application

1. Open `http://localhost:5173` (or `http://<LAN_IP>:5173` on mobile).
2. Choose a role:
   - Click **Customer (Sender Mode)** to make payments.
   - Click **Merchant (Terminal Mode)** for a point-of-sale terminal view.
3. In the **Multi-User Wallet** card:
   - Use the **Sender** dropdown to select the paying account (e.g., `#200 — Customer B`).
   - Use the **Receiver** dropdown to select the payee (e.g., `#300 — Customer C`).
4. In the **Payment Amount** input, enter the amount in dollars (e.g., `25.00` or `100.00`).
5. Click **"Execute Secure QUIC Payment"**:
   - The UI locks and displays the 12-stage cryptographic tracker.
   - You will see each stage transition from `WAITING` to `PROCESSING` to `SUCCESS`:
     - `1. QUIC Connection` (UDP 127.0.0.1:4433)
     - `2. mTLS Handshake` (X.509 mutual authentication)
     - `3. PQC Key Exchange` (Kyber-like lattice ML-KEM)
     - `4. PQC Session Active`
     - `5. Behavioral AI Shield` (Edge TFLite model verification)
     - `6. TOTP Verification` (Anti-replay window check)
     - `7. Zero-Knowledge Proof` (Groth16 balance proof generation)
     - `8. Shamir Secret Sharing` (2-of-3 threshold reconstruction)
     - `9. AES-256-GCM Encryption` (16-byte binary payload)
     - `10. Payment ACK Received` (Server confirmation receipt)
     - `11. MongoDB Atomic Settlement` (Multi-document ACID transaction)
     - `12. Blockchain Audit Trail` (Ethereum block minted)
6. Verify that the sender's balance decreases and the receiver's balance increases in real time.
7. Scroll down to the **Audit Trail / Transaction Ledger** to inspect the receipt hash.

---

## 16. Complete Demo: Client 200 → Client 300 ($100.00)

Follow this step-by-step procedure to execute a fully verified payment:

### Step 1: Check Balances Before Payment
In PowerShell:
```powershell
curl http://127.0.0.1:8000/balance/200
curl http://127.0.0.1:8000/balance/300
```
Note the starting balances (e.g., Sender 200: $500.00, Receiver 300: $500.00).

### Step 2: Execute Payment in UI
1. On the dashboard, select **Sender:** `#200 — Customer B`.
2. Select **Receiver:** `#300 — Customer C`.
3. Enter **Amount:** `100.00`.
4. Click **"Execute Secure QUIC Payment"**.

### Step 3: Observe Terminal 3 (QUIC Server) Output
Terminal 3 will log the transaction processing and print the completion banner:

```
Server: Received payment request. Length: ...
Server [AES]: Decrypting for session ...
Server [AES]: Decrypted data: {'amount_cents': 10000, 'sender_id': 200, 'receiver_id': 300, ...}
Server [ZKP]: Verifying Zero-Knowledge Proof (Groth16)...
Server [MPC]: Master Signing Key successfully reconstructed! (2-of-3 threshold met)
DB [ACID Settlement]: Successfully transferred $100.00 from Client 200 to Client 300.
Blockchain [Web3]: Mined Tx ... into Block ...

════════════════════════════════════════════
        QSP3 PAYMENT TRANSACTION
════════════════════════════════════════════
Sender       : Client 200 — Customer B
Receiver     : Client 300 — Customer C
Amount       : $100.00
Status       : SUCCESS
Transaction  : 4a2f8c...
MongoDB      : ATOMIC SETTLEMENT ✓
Blockchain   : AUDIT RECORDED ✓
════════════════════════════════════════════
```

### Step 4: Verify Balances in MongoDB
In `mongosh`:
```javascript
use qsp3_payment
db.users.find({ client_id: { $in: [200, 300] } }, { _id: 0, client_id: 1, name: 1, balance_cents: 1 })
```
Expected result:
- Client 200 balance decreased by exactly $100.00 (`40000` cents).
- Client 300 balance increased by exactly $100.00 (`60000` cents).

---

## 17. Payment Verification

To verify that funds moved and security guarantees were met:

| Layer | Verification Method | Expected Indicator |
| :--- | :--- | :--- |
| **Frontend UI** | Dashboard telemetry cards & transaction ledger | All 12 pipeline stages turn green (`SUCCESS`). Balance cards update. New entry in Audit Ledger. |
| **QUIC Server** | Terminal 3 standard output | `QSP3 PAYMENT TRANSACTION` banner with `Status: SUCCESS`, `MongoDB: ATOMIC SETTLEMENT ✓`, `Blockchain: AUDIT RECORDED ✓`. |
| **FastAPI Gateway** | Terminal 4 standard output | `POST /quic/execute-payment HTTP/1.1 200 OK` |
| **MongoDB Ledger** | `db.transactions.find().sort({timestamp: -1}).limit(1)` | Document with `sender_id: 200`, `receiver_id: 300`, `amount_cents: 10000`, `status: "APPROVED"`. |
| **Blockchain** | `blockchain/test_blockchain_metrics.py` | Smart contract receipt block mined into local EVM. |

---

## 18. Testing

### Run Phase 2 Multi-User Settlement Test Suite

Tests atomic settlement, balance constraints, nonexistent accounts, and dual-party audit trails:

```powershell
python tests/test_phase2_multi_user.py
```
*(Or via pytest: `python -m pytest tests/test_phase2_multi_user.py -v -p asyncio --asyncio-mode=auto`)*

Expected output:
```
==================================================
PHASE 2: MULTI-USER ACID SETTLEMENT TEST SUITE
==================================================
--- TEST 1: Successful Sender -> Receiver Transfer ---
[+] PASS: Sender balance decreased by $75.00
[+] PASS: Receiver balance increased by $75.00

--- TEST 2: Insufficient Sender Funds ---
[+] PASS: Both balances completely untouched

--- TEST 3: Nonexistent Sender ---
[+] PASS: Nonexistent sender rejected cleanly

--- TEST 4: Nonexistent Receiver ---
[+] PASS: Nonexistent receiver rejected cleanly

--- TEST 5: Dual-Party Audit Visibility ---
[+] PASS: Transaction visible in both Sender and Receiver audit trails!
==================================================
ALL PHASE 2 BACKEND SETTLEMENT TESTS PASSED (5/5)!
==================================================
```

### Run Blockchain Integrity & Gas Metrics Test

```powershell
python blockchain/test_blockchain_metrics.py
```
Expected output:
```
--- 1. LATENCY & ENERGY CONSUMPTION ---
[*] Latency: 0.0... seconds per transaction
[*] Energy Consumption Proxy (Gas Used): 71... units
--- 2. INTEGRITY & SECURITY ---
[+] Integrity: PASS (On-chain data exactly matches input)
[+] Replay Attack Blocked: SUCCESS
```

### Validate Frontend Production Build

```powershell
cd mobile_ui
npm run build
cd ..
```
Expected output:
```
✓ built in ...ms
```

---

## 19. Troubleshooting

### 1. MongoDB ACID Transactions Abort
- **Symptom:** `Transaction numbers are only allowed on a replica set member or mongos`.
- **Cause:** MongoDB is running as a standalone server without replica set enabled.
- **Check:** Run `mongosh --eval "rs.status().ok"`. If it returns error code 76, replica sets are disabled.
- **Fix:** Start `mongod` with `--replSet rs0` and run `rs.initiate()` in `mongosh`.

### 2. QUIC Server Shows "Offline" on Frontend
- **Symptom:** Banner displays `QUIC DAEMON OFFLINE: Server unreachable at 127.0.0.1:4433`.
- **Cause:** `server/quic_server.py` is not running.
- **Check:** Run `curl http://127.0.0.1:8000/quic/status`.
- **Fix:** Start Terminal 3: `python server/quic_server.py`.

### 3. ZKP Generation Fails (`snarkjs non-zero exit status 1`)
- **Symptom:** Server logs `Server [Warning]: Client did not send ZKP. Falling back to DB lookup.`
- **Cause:** `snarkjs` is missing from system `PATH` or command formatting failed.
- **Check:** In PowerShell run: `npx snarkjs --version`.
- **Fix:** Ensure Node.js is installed. `quic_client.py` uses `npx snarkjs groth16 prove ...` which resolves automatically.

### 4. Nonexistent Sender / Receiver Error
- **Symptom:** Payment fails with `PAYMENT_ERR: Nonexistent receiver ID 300`.
- **Cause:** Demo account `#300` does not exist in the MongoDB `users` collection.
- **Check:** In `mongosh` run: `db.users.find({ client_id: 300 })`.
- **Fix:** Run the upsert script in Section 6.C to create missing accounts.

### 5. Behavioral AI Blocks Payment (`AI_BLOCKED`)
- **Symptom:** Client logs `BEHAVIORAL ANOMALY DETECTED. Blocking Transaction.`
- **Cause:** Simulated phone tilt variance or context values triggered the autoencoder threshold.
- **Check:** Inspect the `MAE Error Score` in the UI edge telemetry card.
- **Fix:** Reset sensor values to baseline in UI: Tilt X: `0.70`, Tilt Y: `0.20`, Tilt Z: `0.90`.

### 6. Mobile Phone Cannot Connect to Frontend
- **Symptom:** Browser on phone shows `ERR_CONNECTION_TIMED_OUT` or `ERR_CONNECTION_REFUSED`.
- **Cause:** Laptop and phone are on different Wi-Fi networks, or Windows Firewall is blocking inbound port 5173/8000/3001.
- **Check:** Ping laptop LAN IP from another machine on the network.
- **Fix:** Ensure both devices are on the same Wi-Fi. In Windows Firewall, allow inbound traffic for ports `5173`, `8000`, `3001`, and `4433` (UDP).

### 7. Port Already in Use Errors
- **Symptom:** `[Errno 10048] error while attempting to bind on address ('0.0.0.0', 8000)`.
- **Cause:** A previous instance of the server is still running in the background.
- **Check:** Run `Get-Process -Id (Get-NetTCPConnection -LocalPort 8000).OwningProcess`.
- **Fix:** Kill the orphaned process: `Stop-Process -Id <PID> -Force`.

---

## 20. Common Commands

| Task | Command | Working Directory |
| :--- | :--- | :--- |
| **Start MongoDB** | `mongod --replSet rs0 --port 27017` | Root / Any |
| **Open MongoDB Shell** | `mongosh "mongodb://localhost:27017/qsp3_payment"` | Root / Any |
| **Start Socket.IO Relay** | `node server.cjs` | `mobile_ui/` |
| **Start QUIC Server** | `python server/quic_server.py` | Root |
| **Start FastAPI Gateway** | `python -m uvicorn server.api_gateway:app --host 0.0.0.0 --port 8000` | Root |
| **Start Vite Frontend** | `npm run dev -- --host` | `mobile_ui/` |
| **Build Frontend** | `npm run build` | `mobile_ui/` |
| **Run Multi-User Tests** | `python tests/test_phase2_multi_user.py` | Root |
| **Check Port 8000** | `Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue` | Root |
| **Check Port 4433 (UDP)** | `Get-NetUDPEndpoint -LocalPort 4433 -ErrorAction SilentlyContinue` | Root |
| **Check Port 3001** | `Get-NetTCPConnection -LocalPort 3001 -ErrorAction SilentlyContinue` | Root |

---

## 21. Shutdown

To stop the system cleanly:
1. In each of the running terminals (Frontend, FastAPI, QUIC, Socket.IO), press `Ctrl + C`.
2. To shut down MongoDB gracefully:
   ```powershell
   mongosh admin --eval "db.shutdownServer()"
   ```

---

## 22. Quick Start

For developers with all prerequisites and MongoDB already running:

```powershell
# 1. Activate environment
cd Tap-and-Pay
.\.venv\Scripts\Activate.ps1

# 2. Terminal A: Socket.IO Relay
cd mobile_ui; node server.cjs

# 3. Terminal B: QUIC Server
python server/quic_server.py

# 4. Terminal C: FastAPI Backend
python -m uvicorn server.api_gateway:app --host 0.0.0.0 --port 8000

# 5. Terminal D: React Frontend
cd mobile_ui; npm run dev -- --host
```

Open `http://localhost:5173` in your browser.

---

## 23. Known Limitations

- **Browser-Mediated Tap:** Modern Android (Android 10+) and iOS disable direct phone-to-phone Web NFC P2P transfer at the OS kernel level. Hardware tap proximity detection is emulated via the gyroscopic/accelerometer sensor delta variance and WebSockets.
- **In-Memory Blockchain:** The Ethereum blockchain runs on an in-memory EVM (`EthereumTesterProvider`). The transaction audit history resets when `quic_server.py` or `api_gateway.py` restarts. MongoDB transaction logs remain persistent.
- **Local Network Scope:** Physical phone testing requires both the host laptop and phones to be on the same local Wi-Fi subnet with firewall permissions open for ports `5173`, `8000`, `3001`, and `4433` (UDP).
