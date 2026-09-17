# QSP3 TAP-AND-PAY: MASTER TECHNICAL ARCHITECTURE & SYSTEM DOCUMENTATION

> **Project Title:** Quantum-Secure Peer-to-Peer Mobile Payment System (QSP3)
> **Repository:** `Tap-and-Pay`
> **Branch:** `main`
> **Target Audience:** Technical Evaluation Committee, Project Examiners, Core Engineering Team
> **Documentation Scope:** Exhaustive, code-verified technical documentation of the live, working implementation as it exists on disk. No conceptual speculation; every claim, command, port, and data structure is mapped directly to actual repository source code.

---

## TABLE OF CONTENTS
1. [Executive Summary & Core Philosophy](#1-executive-summary--core-philosophy)
2. [High-Level System Architecture & Component Interactions](#2-high-level-system-architecture--component-interactions)
3. [End-to-End Payment Pipeline: The Life of a Transaction ($100: Client 200 → Client 300)](#3-end-to-end-payment-pipeline-the-life-of-a-transaction-100-client-200--client-300)
4. [Frontend Architecture & State Machine (`mobile_ui/src/App.jsx`)](#4-frontend-architecture--state-machine-mobile_uisrcappjsx)
5. [API Gateway Microservice (`server/api_gateway.py`)](#5-api-gateway-microservice-serverapi_gatewaypy)
6. [Real-Time Telemetry & Socket.IO Relay (`mobile_ui/server.cjs`)](#6-real-time-telemetry--socketio-relay-mobile_uiservercjs)
7. [Secure QUIC Transport Layer (`server/quic_server.py` & `client/quic_client.py`)](#7-secure-quic-transport-layer-serverquic_serverpy--clientquic_clientpy)
8. [Compact Binary Payment Payload (`utils/binary_payload.py`)](#8-compact-binary-payment-payload-utilsbinary_payloadpy)
9. [Post-Quantum Cryptography (PQC) Subsystem (`utils/pqc.py`)](#9-post-quantum-cryptography-pqc-subsystem-utilspqcpy)
10. [Authenticated Symmetric Encryption: AES-256-GCM (`utils/crypto_payload.py`)](#10-authenticated-symmetric-encryption-aes-256-gcm-utilscrypto_payloadpy)
11. [Mutual TLS (mTLS) Identity Layer (`certs/`)](#11-mutual-tls-mtls-identity-layer-certs)
12. [Anti-Replay Security: TOTP Protocol (`utils/totp.py`)](#12-anti-replay-security-totp-protocol-utilstotppy)
13. [Zero-Knowledge Privacy: Groth16 zk-SNARK Balance Prover (`zkp/` & `utils/zkp_verifier.py`)](#13-zero-knowledge-privacy-groth16-zk-snark-balance-prover-zkp--utilszkp_verifierpy)
14. [Multi-Party Key Protection: Shamir's Secret Sharing (`utils/shamir_mpc.py`)](#14-multi-party-key-protection-shamirs-secret-sharing-utilsshamir_mpcpy)
15. [Edge Behavioral Intelligence: Quantized Autoencoder Anomaly Shield (`models/`)](#15-edge-behavioral-intelligence-quantized-autoencoder-anomaly-shield-models)
16. [Database Persistence & ACID Atomic Settlement (`utils/db.py`)](#16-database-persistence--acid-atomic-settlement-utilsdbpy)
17. [Decentralized Audit Trail: Ethereum Smart Contract (`blockchain/`)](#17-decentralized-audit-trail-ethereum-smart-contract-blockchain)
18. [Multi-User Identity & Account Management](#18-multi-user-identity--account-management)
19. [Two-Phone Physical Demonstration Network Topology](#19-two-phone-physical-demonstration-network-topology)
20. [12-Stage Cryptographic Telemetry Pipeline](#20-12-stage-cryptographic-telemetry-pipeline)
21. [System Error Handling, Invariant Enforcement & Rollback Mechanics](#21-system-error-handling-invariant-enforcement--rollback-mechanics)
22. [Automated Testing Framework & Verification Metrics](#22-automated-testing-framework--verification-metrics)
23. [Verified Production Milestones vs. Planned Scope](#23-verified-production-milestones-vs-planned-scope)
24. [Complete File-by-File Repository Blueprint](#24-complete-file-by-file-repository-blueprint)
25. [Exhaustive Viva & Defense Question Bank (20 Specialized Domains)](#25-exhaustive-viva--defense-question-bank-20-specialized-domains)
26. [Final Comprehensive Flow Summary](#26-final-comprehensive-flow-summary)

---

## 1. EXECUTIVE SUMMARY & CORE PHILOSOPHY

The **QSP3 (Quantum-Secure Peer-to-Peer Payment System)** is an advanced financial transaction platform designed to solve a fundamental contradiction in mobile financial technologies: **maximizing physical point-of-sale speed while guaranteeing post-quantum cryptographic security, zero-knowledge financial privacy, and multi-document database atomicity.**

Traditional tap-to-pay rails (e.g., NFC EMV, centralized QR-wallets) suffer from four systemic vulnerabilities:
1. **Quantum Vulnerability:** Reliance on classical RSA and ECC (Elliptic Curve Cryptography) that will be broken by Shor's algorithm on cryptanalytically relevant quantum computers (CRQCs).
2. **Privacy Leakage:** Transaction verification traditionally requires disclosing the customer's total bank balance or account number to verifying nodes or merchants.
3. **Physical Theft Exploitation:** Possession of an unlocked phone allows unauthorized proximity tap payments without contextual physical verification.
4. **Network & Transport Latency:** Multi-round-trip TCP + TLS 1.3 handshakes introduce human-perceptible delays and head-of-line blocking under volatile mobile wireless connections.

QSP3 addresses all four vectors simultaneously:
- It replaces TCP/TLS with **UDP-based QUIC** (`aioquic`), achieving 0-RTT/1-RTT connection setup and eliminating head-of-line blocking.
- It introduces a **hybrid lattice-based Post-Quantum Cryptography (PQC)** Key Encapsulation Mechanism (Ring-LWE parameters $N=256, Q=3329$) to establish session keys resilient against "Harvest Now, Decrypt Later" quantum attacks.
- It embeds a **Groth16 Zero-Knowledge Proof (ZKP)** circuit into the client, enabling senders to cryptographically prove $\text{balance} \ge \text{amount}$ without exposing their balance.
- It executes **on-device edge AI inference** using an INT8-quantized TensorFlow Lite neural autoencoder that inspects physical device gyroscopic tilt and coordinate vectors to detect device snatches or abnormal contextual signatures.
- It secures transaction settlement using **genuine multi-document MongoDB ACID transactions** across a replica set (`rs0`) combined with an **in-memory Ethereum blockchain audit trail** (`AuditTrail.sol`).

---

## 2. HIGH-LEVEL SYSTEM ARCHITECTURE & COMPONENT INTERACTIONS

The QSP3 ecosystem is architected as a set of synchronized microservices communicating over loopback and local area networks.

### Architectural Component Topology

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                   CLIENT DEVICES (Physical Phones)                               │
│                                                                                                  │
│   [Phone A: Sender #200]                                       [Phone B: Receiver #300]          │
│   Chrome Browser @ http://192.168.1.4:5173                     Chrome Browser @ 192.168.1.4:5173  │
│   - Multi-User Wallet UI                                       - Merchant/Peer POS Dashboard     │
│   - Sensor Telemetry (Tilt X/Y/Z)                              - Live Balance & Audit Display    │
└──────────────────┬─────────────────────────────────────────────────────────────┬─────────────────┘
                   │                                                             │
                   │ HTTP POST (Port 8000)                                       │ Socket.IO (Port 3001)
                   │ Socket.IO (Port 3001)                                       │
                   ▼                                                             ▼
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    HOST GATEWAY & RELAY (Laptop)                                 │
│                                                                                                  │
│   ┌──────────────────────────────────────────────┐    ┌──────────────────────────────────────┐   │
│   │ Node.js Event Relay (mobile_ui/server.cjs)   │    │ FastAPI Gateway (server/api_gateway) │   │
│   │ Port: 3001 (TCP/HTTP + WebSockets)           │    │ Port: 8000 (TCP/HTTP)                │   │
│   │ - Broadcasts real-time quic_event telemetry  │    │ - /quic/execute-payment              │   │
│   │ - Synchronizes ledger across phones          │◄───┤ - /balance/{id} & /audit/{id}        │   │
│   └──────────────────────────────────────────────┘    └──────────────────┬───────────────────┘   │
│                                                                          │ Spawns Execution Loop │
│                                                                          ▼                       │
│                                                       ┌──────────────────────────────────────┐   │
│                                                       │ PaymentClient (client/quic_client.py)│   │
│                                                       │ - Edge AI (TFLite Quantized)         │   │
│                                                       │ - Groth16 Prover (npx snarkjs)       │   │
│                                                       │ - PQC Key Encapsulation (Ring-LWE)   │   │
│                                                       │ - 16-Byte Struct Packing             │   │
│                                                       │ - AES-256-GCM Encryption             │   │
│                                                       └──────────────────┬───────────────────┘   │
└──────────────────────────────────────────────────────────────────────────┼───────────────────────┘
                                                                           │
                                                                           │ UDP Packets (Port 4433)
                                                                           │ mTLS (TLS 1.3 over QUIC)
                                                                           ▼
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              SECURE QUIC SERVER (server/quic_server.py)                          │
│                              Port: 4433 (UDP / aioquic Protocol)                                 │
│                                                                                                  │
│   1. mTLS Verification        ──► Authenticates client_cert.pem against ca_cert.pem              │
│   2. AES-256-GCM Decryption   ──► Decrypts 16-byte binary payload using PQC shared secret        │
│   3. Deserialization          ──► Unpacks: amount_cents, sender_id, receiver_id, totp, timestamp │
│   4. TOTP Anti-Replay Check   ──► Validates 6-digit token within ±120s tolerance window          │
│   5. Groth16 ZKP Verification ──► Verifies proof in Python RAM via py_ecc BN128 pairing          │
│   6. Shamir MPC 2-of-3 Check  ──► Reconstructs master signing secret from distributed shares     │
│   7. Transaction Dispatch     ──► Generates SHA-256 tx_hash and returns PAYMENT_ACK over QUIC    │
└───────────────────────────────────┬──────────────────────────────────────┬───────────────────────┘
                                    │                                      │
                                    │ Asynchronous Background Settlement   │ Immutable Receipt Mining
                                    ▼                                      ▼
┌──────────────────────────────────────────────────┐   ┌───────────────────────────────────────────┐
│     MONGODB REPLICA SET (rs0 : localhost:27017)  │   │   LOCAL ETHEREUM BLOCKCHAIN (Web3/EVM)    │
│                                                  │   │                                           │
│  utils/db.py :: settle_payment_atomic()          │   │  blockchain/web3_integration.py           │
│  - Begins ACID Session: client.start_session()   │   │  - Contract: AuditTrail.sol               │
│  - Atomic Sender Deduction ($inc: -amount)       │   │  - Provider: EthereumTesterProvider       │
│  - Atomic Receiver Credit ($inc: +amount)        │   │  - Method: logTransaction(tx_hash,        │
│  - Appends Transaction Record                    │   │                           client_id, ...) │
│  - session.commit_transaction()                  │   │  - Mines local block & records gas used   │
└──────────────────────────────────────────────────┘   └───────────────────────────────────────────┘
```

---

## 3. END-TO-END PAYMENT PIPELINE: THE LIFE OF A TRANSACTION ($100: CLIENT 200 → CLIENT 300)

Here is the exact step-by-step trace of a **$100.00** transaction from **Customer B (Client #200)** to **Customer C (Client #300)**:

```
[Customer B clicks "Execute Secure QUIC Payment"]
                       │
                       ▼
Stage 1: Frontend Dispatch (App.jsx :: executeSecureQuicPayment)
  - Selected Sender: 200 | Receiver: 300 | Amount: $100.00 (10000 cents)
  - Fetches current private balance for Client 200: $500.00 (50000 cents)
  - Collects gyroscopic tilt: tiltX=0.70, tiltY=0.20, tiltZ=0.90
  - Sends HTTP POST to http://192.168.1.4:8000/quic/execute-payment
                       │
                       ▼
Stage 2: API Gateway Ingestion (api_gateway.py :: execute_quic_payment)
  - Parses JSON request into local parameters:
      amount_cents = 10000
      sender_id = 200
      receiver_id = 300
      private_balance = 50000
  - Configures aioquic QuicConfiguration with client certificates:
      client_cert.pem, client_key.pem (mTLS)
  - Instantiates BehavioralAI and PaymentClient
  - Invokes: await client.pay(10000, 200, behavior_data, private_balance=50000, receiver_id=300)
                       │
                       ▼
Stage 3: Edge Behavioral AI Verification (quic_client.py :: BehavioralAI.check_anomaly)
  - Input Vector: [amount=10000, lat=12.9716, lon=77.5946, tiltX=0.70, tiltY=0.20, tiltZ=0.90, hour=current]
  - Transforms vector using MinMaxScaler from models/scaler.pkl
  - Quantizes float32 vector into INT8 range [-128, 127]
  - Invokes TFLite Interpreter on models/behavioral_ai_quantized.tflite
  - Computes Mean Absolute Error (MAE) of reconstruction
  - Threshold check: MAE (e.g. 0.042) <= threshold.txt (0.1500)
  - Result: SUCCESS (Not anomalous). Broadcasts BEHAVIORAL_AI -> SUCCESS
                       │
                       ▼
Stage 4: Groth16 Zero-Knowledge Proof Generation (quic_client.py :: generate_zkp)
  - Validates private balance locally: 50000 >= 10000 (Sufficient funds)
  - Writes zkp/temp_input.json: {"amount": 10000, "balance": 50000}
  - Step 4A (Witness Calculation):
      node balance_check_js/generate_witness.js balance_check.wasm temp_input.json temp_witness.wtns
  - Step 4B (Groth16 Prover):
      npx snarkjs groth16 prove balance_check_final.zkey temp_witness.wtns temp_proof.json temp_public.json
  - Reads generated proof dictionary: {"pi_a": [...], "pi_b": [...], "pi_c": [...]}
  - Deletes temporary files (temp_input.json, temp_witness.wtns, temp_proof.json, temp_public.json)
  - Broadcasts ZKP_GENERATION -> SUCCESS
                       │
                       ▼
Stage 5: QUIC Session Establishment & PQC Handshake (quic_client.py :: _ensure_session)
  - Client connects to UDP 127.0.0.1:4433 over QUIC with mTLS
  - Opens QUIC stream, sends: GET_PUBKEY
  - Server returns its persisted PQC Public Key: (pub_a, pub_t)
  - Client runs pqc.encapsulate((pub_a, pub_t)):
      - Generates 32 random bytes (session key)
      - Samples noise polynomials r, e1, e2
      - Computes ciphertext: u = a*r + e1, v = t*r + e2 + m
      - Derives shared_secret = SHA256(session_key)
  - Client sends: ESTABLISH_SESSION:{"u": u, "v": v}
  - Server runs pqc.decapsulate((u, v), priv_s):
      - Recovers session key m and derives identical shared_secret
      - Returns: SESSION_ESTABLISHED:{"session_id": "<hex>"}
  - Both parties now share a 256-bit quantum-resistant symmetric key.
                       │
                       ▼
Stage 6: TOTP Generation & Compact Binary Packing (quic_client.py :: pay)
  - Generates RFC 6238 TOTP token using shared secret b"QSP3_SHARED_SECRET_KEY":
      interval = current_epoch / 30 -> e.g., token = "496194"
  - Packs 16-byte Big-Endian binary struct (utils/binary_payload.py :: serialize_payment):
      struct.pack(">IHHII", 10000, 200, 300, 496194, epoch_time)
      [4 bytes: amount][2 bytes: sender][2 bytes: receiver][4 bytes: totp][4 bytes: time]
                       │
                       ▼
Stage 7: AES-256-GCM Payload Encryption (utils/crypto_payload.py :: encrypt_payload)
  - Generates 12-byte random Initialization Vector (IV)
  - Encrypts 16-byte binary payload under shared_secret
  - Produces 16-byte authentication tag
  - Wire Encrypted Payload = IV (12B) + Tag (16B) + Ciphertext (16B) = 44 bytes
  - Constructs JSON envelope:
      {
        "session_id": "...",
        "encrypted_payload": "<44 bytes hex>",
        "zk_proof": { ... },
        "mpc_share": { "x": 1, "y": ... }
      }
  - Encodes packet: SECURE_PAYMENT:<json_string>
                       │
                       ▼
Stage 8: QUIC Network Transmission (client/quic_client.py)
  - Stream ID allocated via QuicConnection.get_next_available_stream_id()
  - QuicConnection.send_stream_data(stream_id, request_msg, end_stream=True)
  - QuicConnection.transmit() sends UDP datagrams to 127.0.0.1:4433
                       │
                       ▼
Stage 9: QUIC Server Decryption & Invariant Validation (server/quic_server.py)
  - Parses packet, extracts session_id and encrypted_payload
  - Recovers shared_secret from active_sessions table
  - AES-256-GCM decrypts payload, validating 16-byte authentication tag
  - Deserializes binary struct into Python dictionary:
      {'amount_cents': 10000, 'sender_id': 200, 'receiver_id': 300, 'totp_token': '496194', 'timestamp': ...}
  - Invariant Checks:
      1. Verifies Client 200 exists in MongoDB (utils/db.py :: get_user) -> FOUND
      2. Verifies Client 300 exists in MongoDB (utils/db.py :: get_user) -> FOUND
      3. Verifies TOTP token within window tolerance (120 seconds) -> VALID
                       │
                       ▼
Stage 10: Server ZKP Verification & MPC Reconstruction (server/quic_server.py)
  - Extracts zk_proof from payload
  - Invokes Native Python Groth16 Verifier (utils/zkp_verifier.py :: verify_proof):
      - Computes BN128 bilinear pairings using py_ecc:
          e(B, A) == e(alpha, beta) * e(IC_x, gamma) * e(C, delta)
      - Returns: True (Funds proven cryptographically without querying balance!)
  - Extracts client MPC share (x=1)
  - Combines with server MPC share (x=2) using Lagrange interpolation over 127-bit Mersenne prime:
      - Reconstructs master key integer
      - Compares SHA-256(master_key) against certs/master_key_hash.txt -> MATCH
  - Generates tx_hash = SHA256(sender_id : receiver_id : amount : timestamp)
  - Sends immediate QUIC response: PAYMENT_ACK:SUCCESS | TX: <tx_hash>
  - Client receives ACK, broadcasts PAYMENT_ACK -> SUCCESS
                       │
                       ▼
Stage 11: Asynchronous Atomic MongoDB ACID Settlement (server/quic_server.py -> utils/db.py)
  - Server spawns background task: log_audit_trail()
  - Executes utils/db.py :: settle_payment_atomic(200, 300, 10000, tx_hash, "APPROVED")
  - Inside MongoDB Transaction Session (client.start_session() -> session.start_transaction()):
      1. Reads Client 200 balance inside session: $500.00 (50000 cents)
      2. Reads Client 300 balance inside session: $500.00 (50000 cents)
      3. Conditioned update: db.users.update_one(
             {"client_id": 200, "balance_cents": {"$gte": 10000}},
             {"$inc": {"balance_cents": -10000}}, session=session) -> Modified: 1
      4. Crediting update: db.users.update_one(
             {"client_id": 300},
             {"$inc": {"balance_cents": 10000}}, session=session) -> Modified: 1
      5. Appends record to db.transactions collection
      6. Commits transaction session.
  - Client 200 balance is now exactly $400.00 (40000 cents).
  - Client 300 balance is now exactly $600.00 (60000 cents).
  - Both RAM caches invalidated. Broadcasts MONGODB_UPDATE -> SUCCESS.
                       │
                       ▼
Stage 12: Decentralized Blockchain Audit Logging (blockchain/web3_integration.py)
  - Invokes log_to_blockchain(tx_hash, 200, 10000, "APPROVED")
  - Calls Solidity contract function: AuditContract.functions.logTransaction(tx_hash, 200, 10000, "APPROVED").transact()
  - EVM mines transaction into next block on EthereumTesterProvider
  - Prints: Blockchain [Web3]: Mined Tx <tx_hash[:10]>... into Block N (Gas Used: 71...)
  - Broadcasts BLOCKCHAIN_AUDIT -> SUCCESS
                       │
                       ▼
Stage 13: Terminal Summary & UI State Refresh (quic_server.py & App.jsx)
  - Server terminal prints formatted transaction banner:
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
  - Socket.IO relay transmits final telemetry events to all connected browsers.
  - Both phones automatically trigger fetchCloudData():
      - Phone A displays: Sender Balance: $400.00
      - Phone B displays: Receiver Balance: $600.00
      - Audit trail displays new debit/credit entries for both clients.
```

---

## 4. FRONTEND ARCHITECTURE & STATE MACHINE (`mobile_ui/src/App.jsx`)

The frontend is a single-page React 19 application bundled with Vite. It maintains strict local reactive state while syncing asynchronously with the backend.

### Key State Variables

| State Variable | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `role` | `string` | `'selection'` | Active view: `'selection'`, `'sender'` (Customer), or `'receiver'` (Merchant POS). |
| `selectedSenderId` | `number` | `100` | Current paying account ID (Customer A, B, or C). |
| `selectedReceiverId`| `number` | `400` | Current payee account ID (Merchant A or peer customer). |
| `balance` | `number` | `500.00` | Verified cloud balance of selected sender. |
| `receiverBalance` | `number` | `100.00` | Verified cloud balance of selected receiver. |
| `amount` | `string` | `'25.00'` | User-input payment amount in dollars. |
| `quicPipeline` | `object` | `INITIAL_PIPELINE` | Reactive state tracking the 12 cryptographic pipeline stages. |
| `quicLogs` | `array` | `[]` | Rolling log of timestamped backend telemetry events (up to 100 items). |
| `isQuicExecuting` | `boolean`| `false` | Mutex flag disabling the UI while a payment is in flight. |

### Available User Definitions

Declared in `App.jsx` (lines 29–34):
```javascript
const AVAILABLE_USERS = [
  { id: 100, name: 'Customer A', role: 'customer' },
  { id: 200, name: 'Customer B', role: 'customer' },
  { id: 300, name: 'Customer C', role: 'customer' },
  { id: 400, name: 'Merchant A', role: 'merchant' },
];
```

### Critical Methods in `App.jsx`

#### 1. `fetchCloudData(senderId, receiverId)` (lines 104–165)
Triggered on initial load, user selection change, or transaction completion.
- Executes `GET /balance/${senderId}` and `GET /audit/${senderId}` for the sender.
- Executes `GET /balance/${receiverId}` and `GET /audit/${receiverId}` for the receiver.
- Automatically maps positive/negative amounts in the ledger depending on whether the current user was the debiting party (`sender_id`) or crediting party (`receiver_id`).

#### 2. `executeSecureQuicPayment()` (lines 506–550)
The primary entrypoint for live quantum payments.
- Sets `isQuicExecuting = true` and resets pipeline to `INITIAL_PIPELINE`.
- Dispatches HTTP POST to `${API_URL}/quic/execute-payment` with JSON body:
  ```json
  {
    "amount_cents": 10000,
    "sender_id": 200,
    "receiver_id": 300,
    "lat": 12.97,
    "lon": 77.59,
    "tilt_x": 0.70,
    "tilt_y": 0.20,
    "tilt_z": 0.90,
    "private_balance_cents": 50000
  }
  ```
- Evaluates HTTP response:
  - If `status === 'SUCCESS'`: Displays green execution banner with raw `ack` string and refreshes cloud balances.
  - If `status === 'OFFLINE'`: Displays red alert indicating QUIC daemon is offline.
  - Releases execution lock after 8 seconds.

---

## 5. API GATEWAY MICROSERVICE (`server/api_gateway.py`)

The API Gateway is built on **FastAPI** running over Uvicorn on port `8000`. It serves as the HTTP ingestion bridge between mobile browsers and the low-level QUIC UDP client.

### Endpoints Specification

| Method | Endpoint | Request Body | Response Structure | Purpose |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/` | None | `{"status": "...", "version": "1.0.0"}` | Gateway liveness probe. |
| `POST` | `/register` | `UserProfile` JSON | `{"message": "User registered..."}` | Idempotent user profile creation. |
| `GET` | `/balance/{client_id}` | Path parameter | `{"client_id": int, "balance_str": "$...", "balance_cents": int}` | Reads current balance from MongoDB. |
| `POST` | `/transaction` | `TransactionRecord` JSON | `{"status": "Transaction settled..."}` | Legacy HTTP settlement endpoint. |
| `GET` | `/audit/{client_id}` | Path parameter | `{"client_id": int, "history": [...]}` | Retrieves last 10 transactions where client is sender or receiver. |
| `GET` | `/quic/status` | None | `{"quic_server_online": bool, "port": 4433, "host": "127.0.0.1"}` | Probes UDP port 4433 via socket connect to check if QUIC server is up. |
| `POST` | `/quic/execute-payment`| Payment dictionary | `{"status": "SUCCESS" \| "FAILED" \| "OFFLINE", "ack": "..."}` | Spawns `PaymentClient` to execute the full QUIC security pipeline. |

---

## 6. REAL-TIME TELEMETRY & SOCKET.IO RELAY (`mobile_ui/server.cjs`)

Built with Node.js and the `socket.io` library, running on port `3001`.

### Why Socket.IO Is Required
QUIC operates over UDP between the Python backend client and server. Browsers executing client-side JavaScript cannot directly open raw UDP QUIC connections or read internal Python cryptographic states. The Node.js Socket.IO server acts as an asynchronous **event bridge**:
1. Python backend processes call `utils/event_broadcaster.py :: broadcast_quic_event()`.
2. `broadcast_quic_event()` sends a background HTTP POST to `http://127.0.0.1:3001/emit`.
3. `server.cjs` receives the payload and immediately executes `io.emit("quic_event", eventData)`.
4. All connected mobile browsers receive the event in real time and advance their 12-stage pipeline visualizer.

### Server Endpoints & Socket Events

- **HTTP `POST /emit` or `/api/quic-event`:** Ingests telemetry payloads from Python and broadcasts them over WebSockets.
- **HTTP `GET /health`:** Returns `{"status": "ok", "service": "QSP3 WebSocket Relay"}`.
- **Socket Event `payment_sent`:** Broadcasts `payment_received` globally to all connected devices.
- **Socket Event `quic_event_forward`:** Relays client-originated QUIC events.

---

## 7. SECURE QUIC TRANSPORT LAYER (`server/quic_server.py` & `client/quic_client.py`)

QSP3 uses **QUIC** (RFC 9000) implemented via the Python `aioquic` library over **UDP port 4433**.

### Advantages of QUIC over Standard HTTPS/TCP
1. **Zero Head-of-Line Blocking:** In TCP, a dropped packet stalls all multiplexed streams. QUIC multiplexes independent bidirectional streams over UDP; a lost packet in stream 4 does not block stream 8.
2. **Connection Migration:** QUIC identifies connections via a 64-bit Connection ID (CID), not the 4-tuple (source IP, source port, dest IP, dest port). If a mobile device transitions from Wi-Fi to 5G, the payment session survives without renegotiation.
3. **Integrated Security:** QUIC mandates TLS 1.3 encryption directly inside the transport header; no unencrypted plaintext headers exist on the wire.

### Wire Protocol Messages

The communication on QUIC streams uses colon-prefixed text frames:

| Direction | Message Frame | Payload Content | Purpose |
| :--- | :--- | :--- | :--- |
| Client → Server | `GET_PUBKEY` | None | Requests the server's PQC public key. |
| Server → Client | `PUBKEY:<json>` | `{"a": [...], "t": [...]}` | Transmits server's lattice public key. |
| Client → Server | `ESTABLISH_SESSION:<json>` | `{"u": [...], "v": [...]}` | Transmits encapsulated PQC ciphertext. |
| Server → Client | `SESSION_ESTABLISHED:<json>`| `{"session_id": "<hex>"}` | Acknowledges session key derivation. |
| Client → Server | `SECURE_PAYMENT:<json>` | `{"session_id": "...", "encrypted_payload": "...", "zk_proof": {...}, "mpc_share": {...}}` | Submits encrypted payment struct. |
| Server → Client | `PAYMENT_ACK:<string>` | `SUCCESS \| TX: <hash>` or `FAILED \| <reason>` | Returns final settlement receipt. |

---

## 8. COMPACT BINARY PAYMENT PAYLOAD (`utils/binary_payload.py`)

To minimize over-the-air latency and reduce encryption overhead, financial transaction data is packed into a **compact 16-byte binary structure** using Python's `struct` module.

### Memory Layout & Byte Alignment (Format: `>IHHII`)

```
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                       amount_cents (4 bytes)                  |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|       sender_id (2 bytes)     |      receiver_id (2 bytes)    |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                        totp_token (4 bytes)                   |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                        timestamp (4 bytes)                    |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
Total: Exactly 16 Bytes (Big-Endian network byte order)
```

### Field Breakdown

1. `amount_cents` (`>I`, unsigned 32-bit integer): Transaction amount in integer cents. Range: $0 to $42,949,672.95.
2. `sender_id` (`>H`, unsigned 16-bit short): Client ID of the paying party. Range: 0 to 65,535.
3. `receiver_id` (`>H`, unsigned 16-bit short): Client ID of the payee party. Range: 0 to 65,535.
4. `totp_token` (`>I`, unsigned 32-bit integer): 6-digit dynamic authentication token.
5. `timestamp` (`>I`, unsigned 32-bit integer): Unix epoch timestamp in seconds.

### Backwards Compatibility
The deserializer (`deserialize_payment()`) dynamically inspects the byte length:
- If `len(data) == 16`: Unpacks full 5-field multi-user payload.
- If `len(data) == 14`: Unpacks legacy 4-field payload (`amount_cents, client_id, totp_token, timestamp`) and defaults `receiver_id = 2`.

---

## 9. POST-QUANTUM CRYPTOGRAPHY (PQC) SUBSYSTEM (`utils/pqc.py`)

> **EXACT IMPLEMENTATION STATUS:** The PQC module implements a **custom didactic Ring-LWE (Learning With Errors over Rings) key exchange mechanism** inspired by the mathematical structure of CRYSTALS-Kyber (NIST FIPS 203). It is **not** the compiled C reference implementation of NIST FIPS 203 ML-KEM, but a custom, pure-Python / C-accelerated Ring-LWE scheme operating on the polynomial ring $R_q = \mathbb{Z}_q[X] / (X^{256} + 1)$.

### Mathematical Parameters
- **Degree $N$:** 256
- **Modulus $Q$:** 3329 (same prime modulus as Kyber)
- **Ring:** $R_q = \mathbb{Z}_{3329}[X] / (X^{256} + 1)$
- **Error Distribution $\chi$:** Small ternary polynomial with coefficients sampled uniformly from $\{-1, 0, 1\} \pmod Q$.

### Key Operations

#### 1. Key Generation (`generate_keypair()`)
- Samples random public polynomial $a \leftarrow \mathcal{U}(R_q)$.
- Samples private secret polynomial $s \leftarrow \chi$ and error polynomial $e \leftarrow \chi$.
- Computes public polynomial $t = a \cdot s + e \pmod{X^{256}+1, Q}$.
- **Public Key:** $(a, t)$
- **Private Key:** $s$

#### 2. Encapsulation (`encapsulate(public_key)`)
- Generates 32 random bytes $m \in \{0, 1\}^{256}$.
- Encodes message $m$ into a polynomial where bit 1 becomes $\lfloor Q/2 \rfloor = 1664$ and bit 0 becomes $0$.
- Samples ephemeral noise polynomials $r, e_1, e_2 \leftarrow \chi$.
- Computes ciphertext vector:
  $$u = a \cdot r + e_1 \pmod{X^{256}+1, Q}$$
  $$v = t \cdot r + e_2 + m \pmod{X^{256}+1, Q}$$
- Derives symmetric key: $\text{shared\_secret} = \text{SHA-256}(m)$.
- Returns ciphertext $(u, v)$ and `shared_secret`.

#### 3. Decapsulation (`decapsulate(ciphertext, private_key)`)
- Computes difference polynomial:
  $$w = v - u \cdot s = (t \cdot r + e_2 + m) - (a \cdot r + e_1) \cdot s = m + (e \cdot r + e_2 - e_1 \cdot s)$$
- Because error terms are small, $w \approx m$.
- Decodes each coefficient by testing proximity to $1664$ vs. $0 \pmod{3329}$.
- Recovers message $m$ and derives $\text{shared\_secret} = \text{SHA-256}(m)$.

---

## 10. AUTHENTICATED SYMMETRIC ENCRYPTION: AES-256-GCM (`utils/crypto_payload.py`)

All transaction payloads transmitted over QUIC are encrypted using **AES-256 in Galois/Counter Mode (GCM)** via the `cryptography` library.

### Why AES-GCM?
AES-GCM is an **Authenticated Encryption with Associated Data (AEAD)** cipher. It provides both confidentiality (via counter mode encryption) and integrity/authenticity (via a Galois field polynomial evaluation tag). Any bit-flipping attack on the ciphertext causes the 16-byte authentication tag verification to fail, throwing an `InvalidTag` exception before decryption.

### Wire Serialization
```
┌────────────────────────┬────────────────────────┬────────────────────────┐
│  IV / Nonce (12 Bytes) │  Auth Tag (16 Bytes)   │  Ciphertext (16 Bytes) │
└────────────────────────┴────────────────────────┴────────────────────────┘
Total: 44 Bytes
```

- **Key:** Derived directly from the PQC shared secret (SHA-256 output, exactly 32 bytes / 256 bits).
- **IV:** 12 cryptographically secure random bytes generated per transaction via `os.urandom(12)`.
- **Decryption Enforcement:** `decrypt_payload()` checks `len(encrypted_data) >= 28`. If the tag does not match the ciphertext and IV, decryption fails instantly.

---

## 11. MUTUAL TLS (mTLS) IDENTITY LAYER (`certs/`)

mTLS operates at the QUIC transport layer to authenticate the client device and server before any application data is exchanged.

### Certificate Hierarchy

```
               ┌────────────────────────┐
               │    Root CA Certificate │
               │     certs/ca_cert.pem  │
               └───────────┬────────────┘
                           │ Signs
            ┌──────────────┴──────────────┐
            ▼                             ▼
┌────────────────────────┐   ┌────────────────────────┐
│   Server Certificate   │   │   Client Certificate   │
│  certs/server_cert.pem │   │  certs/client_cert.pem │
│  CN: localhost         │   │  CN: localhost         │
│  SAN: 127.0.0.1        │   │  Organization: QSP3    │
└────────────────────────┘   └────────────────────────┘
```

### Verification Flow
1. The server loads `certs/ca_cert.pem` via `QuicConfiguration.load_verify_locations()`.
2. The server sets `configuration.verify_mode = True`, requiring every connecting client to present an X.509 certificate signed by the Root CA.
3. The client loads `certs/client_cert.pem` and `certs/client_key.pem`.
4. If an unauthorized client connects without a valid CA-signed certificate, the QUIC TLS handshake aborts immediately at the transport level.

---

## 12. ANTI-REPLAY SECURITY: TOTP PROTOCOL (`utils/totp.py`)

To prevent replay attacks—where an adversary captures an encrypted payload and retransmits it later—every payment incorporates a **Time-Based One-Time Password (TOTP)** conforming to **RFC 6238**.

### Implementation Details
- **Shared Secret:** `b"QSP3_SHARED_SECRET_KEY"`
- **Time Step:** 30 seconds
- **Hash Function:** HMAC-SHA1
- **Code Length:** 6 digits (decimal)
- **Validation Window:** Window parameter `window=1` in `verify_totp_token()`. The server checks $T-1, T, T+1$, tolerating up to $\pm 30$ seconds of clock skew.
- **Server Timestamp Check:** In `quic_server.py` line 171, the server additionally enforces:
  ```python
  is_time_valid = abs(time.time() - decrypted_data["timestamp"]) <= 120
  ```
  Transactions older than 120 seconds are rejected as `PAYMENT_ERR: Stale Timestamp`.

---

## 13. ZERO-KNOWLEDGE PRIVACY: GROTH16 ZK-SNARK BALANCE PROVER (`zkp/` & `utils/zkp_verifier.py`)

### The Privacy Problem
In traditional banking, proving that a customer has sufficient funds requires the verifying party (bank or merchant) to inspect the customer's account balance. In QSP3, the customer proves:
$$\text{balance} \ge \text{amount}$$
**without revealing the value of $\text{balance}$.**

### Circom Circuit Specification (`zkp/balance_check.circom`)

```circom
pragma circom 2.0.0;

template Num2Bits(n) { ... }
template LessThan(n) { ... }
template GreaterEqThan(n) {
    signal input in[2];
    signal output out;
    component lt = LessThan(n);
    lt.in[0] <== in[0];
    lt.in[1] <== in[1];
    out <== 1 - lt.out;
}

template BalanceProof(nBits) {
    signal input amount;
    signal input balance;
    signal output is_sufficient;

    component gte = GreaterEqThan(nBits);
    gte.in[0] <== balance;
    gte.in[1] <== amount;

    is_sufficient <== gte.out;
    is_sufficient === 1;
}

component main {public [amount]} = BalanceProof(32);
```

- **Public Input:** `amount` (visible to the verifier and matching the payment struct).
- **Private Input:** `balance` (known only to the client device).
- **Constraint:** `is_sufficient === 1`. Proves that in 32-bit unsigned arithmetic, `balance - amount >= 0`.

### Client Proof Generation
The client invokes the compiled WebAssembly witness generator and SnarkJS:
```powershell
node balance_check_js/generate_witness.js balance_check_js/balance_check.wasm temp_input.json temp_witness.wtns
npx snarkjs groth16 prove balance_check_final.zkey temp_witness.wtns temp_proof.json temp_public.json
```

### Pure Python Native Verifier (`utils/zkp_verifier.py`)
Rather than spawning Node.js on the server (which introduces latency and external dependencies), the server verifies the Groth16 proof purely in Python using the `py_ecc.bn128` elliptic curve library:

1. Parses proof points $A \in G_1, B \in G_2, C \in G_1$.
2. Computes the public input linear combination:
   $$vk_x = IC[0] + IC[1] \cdot \text{amount}$$
3. Evaluates the Groth16 pairing equation:
   $$e(B, A) == e(\beta, \alpha) \cdot e(\gamma, vk_x) \cdot e(\delta, C)$$
4. Returns `True` if the pairings match. The verification takes ~15–25ms in memory.

---

## 14. MULTI-PARTY KEY PROTECTION: SHAMIR'S SECRET SHARING (`utils/shamir_mpc.py`)

To prevent localized wallet theft or single points of compromise, the master transaction authorization key is mathematically divided using **Shamir's Secret Sharing over a 127-bit Mersenne Prime field**.

### Mathematical Parameters
- **Prime $P$:** $2^{127} - 1 = 170141183460469231731687303715884105727$
- **Scheme:** 2-of-3 Threshold
- **Polynomial:** $f(x) = S + a_1 x \pmod P$, where $S$ is the 120-bit master secret and $a_1$ is a random coefficient.

### Share Distribution

| Share Index | Location | File Path | Holder |
| :---: | :--- | :--- | :--- |
| **Share 1 ($x=1$)** | Client Phone | `certs/client_share.json` | Sender device |
| **Share 2 ($x=2$)** | Server Vault | `certs/server_share.json` | Cloud settling authority |
| **Share 3 ($x=3$)** | Edge Backup | `certs/edge_backup_share.json` | Cold recovery storage |

### Reconstruction (`reconstruct_secret()`)
During payment execution, the client attaches its share $(1, y_1)$ to the payload. The server retrieves its share $(2, y_2)$ and executes Lagrange interpolation at $x=0$:
$$S = \left(y_1 \frac{0 - 2}{1 - 2} + y_2 \frac{0 - 1}{2 - 1}\right) \pmod P = (2 y_1 - y_2) \pmod P$$
The server hashes the reconstructed secret:
$$\text{hash} = \text{SHA-256}(S)$$
If $\text{hash} == \text{content of } \texttt{certs/master\_key\_hash.txt}$, the 2-of-3 threshold is met, proving joint authorization.

---

## 15. EDGE BEHAVIORAL INTELLIGENCE: QUANTIZED AUTOENCODER ANOMALY SHIELD (`models/`)

QSP3 executes real-time fraud and physical theft detection on the device before allowing a payment to proceed.

### Model Architecture
- **Model Type:** Deep Neural Autoencoder (TFLite INT8 Quantized)
- **Input Vector (7 Features):**
  1. `amount_cents`: Transaction amount
  2. `lat`: Device latitude coordinate
  3. `lon`: Device longitude coordinate
  4. `tilt_x`: Accelerometer/Gyroscopic pitch axis
  5. `tilt_y`: Accelerometer/Gyroscopic roll axis
  6. `tilt_z`: Accelerometer/Gyroscopic yaw/vertical axis
  7. `hour`: Local hour of the transaction (0–23)

```
[Input: 7] ──► [Dense 16, ReLU] ──► [Dense 8, ReLU] ──► [Dense 4, ReLU] (Bottleneck)
                                                              │
[Output: 7] ◄── [Dense 16, ReLU] ◄── [Dense 8, ReLU] ◄────────┘ (Decoder)
```

### Anomaly Scoring Mechanism
1. Normal user behavior is trained to reconstruct inputs with very low error.
2. During inference, the device normalizes inputs via `models/scaler.pkl` and runs the INT8 model `models/behavioral_ai_quantized.tflite`.
3. The Mean Absolute Error (MAE) between the input and reconstructed output is computed:
   $$\text{MAE} = \frac{1}{7} \sum_{i=1}^{7} |x_i - \hat{x}_i|$$
4. **Cutoff Threshold (`models/threshold.txt`):** `0.1500`
5. If $\text{MAE} > 0.1500$ (e.g., erratic device tilt from a physical snatch or sudden anomalous geolocation), the transaction is blocked locally:
   ```
   AI_BLOCKED: Suspicious context. Requesting PIN/Biometric override.
   ```

---

## 16. DATABASE PERSISTENCE & ACID ATOMIC SETTLEMENT (`utils/db.py`)

### MongoDB Schema

#### 1. Collection: `users`
```json
{
  "_id": ObjectId("..."),
  "client_id": 200,
  "name": "Customer B",
  "balance_cents": 50000,
  "created_at": ISODate("2026-09-17T10:00:00Z")
}
```

#### 2. Collection: `transactions`
```json
{
  "_id": ObjectId("..."),
  "tx_hash": "4a2f8c...",
  "client_id": 200,
  "sender_id": 200,
  "receiver_id": 300,
  "amount_cents": 10000,
  "status": "APPROVED",
  "timestamp": ISODate("2026-09-17T10:30:00Z")
}
```

### Multi-Document ACID Atomic Settlement (`settle_payment_atomic`)

A critical requirement of financial ledgers is **isolation and atomicity**: money must never leave the sender without arriving at the receiver, even if the database crashes mid-operation.

```python
async def settle_payment_atomic(sender_id: int, receiver_id: int, amount_cents: int, tx_hash: str, status: str = "APPROVED"):
    async with await client.start_session() as session:
        async with session.start_transaction():
            # 1. Validate sender exists
            sender = await db.users.find_one({"client_id": sender_id}, session=session)
            if not sender: raise ValueError(...)

            # 2. Validate receiver exists
            receiver = await db.users.find_one({"client_id": receiver_id}, session=session)
            if not receiver: raise ValueError(...)

            # 3. Check sender balance
            if sender.get("balance_cents", 0) < amount_cents: raise ValueError(...)

            # 4. Atomic conditional deduction from sender
            deduct_result = await db.users.update_one(
                {"client_id": sender_id, "balance_cents": {"$gte": amount_cents}},
                {"$inc": {"balance_cents": -amount_cents}},
                session=session
            )
            if deduct_result.modified_count == 0: raise ValueError(...)

            # 5. Atomic credit to receiver
            credit_result = await db.users.update_one(
                {"client_id": receiver_id},
                {"$inc": {"balance_cents": amount_cents}},
                session=session
            )
            if credit_result.modified_count == 0: raise ValueError(...)

            # 6. Record dual-party transaction audit
            record = TransactionRecord(...)
            await db.transactions.insert_one(record_data, session=session)
```

- **Rollback Guarantee:** If step 5 fails or the server loses power before commit, MongoDB rolls back step 4 automatically. Neither balance is modified.

---

## 17. DECENTRALIZED AUDIT TRAIL: ETHEREUM SMART CONTRACT (`blockchain/`)

> **EXACT IMPLEMENTATION STATUS:** The blockchain layer is implemented as an **in-memory lightweight EVM instance** using `web3.py` with `EthereumTesterProvider`. It compiles and deploys an actual Solidity smart contract (`AuditTrail.sol`) using `py-solc-x` (version `0.8.0`). It is **not** connected to the public Ethereum Mainnet or a public testnet (Sepolia/Goerli), which eliminates gas costs and external RPC dependencies during demonstration.

### Solidity Smart Contract (`blockchain/AuditTrail.sol`)

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract AuditTrail {
    struct Transaction {
        string txHash;
        uint256 clientId;
        uint256 amountCents;
        string status;
        uint256 timestamp;
    }

    mapping(string => Transaction) public transactions;
    mapping(string => bool) public transactionExists;

    event TransactionLogged(string txHash, uint256 clientId, uint256 amountCents, string status, uint256 timestamp);

    function logTransaction(string memory _txHash, uint256 _clientId, uint256 _amountCents, string memory _status) public {
        require(!transactionExists[_txHash], "Transaction hash already logged");
        transactions[_txHash] = Transaction(_txHash, _clientId, _amountCents, _status, block.timestamp);
        transactionExists[_txHash] = true;
        emit TransactionLogged(_txHash, _clientId, _amountCents, _status, block.timestamp);
    }
}
```

- **Immutability:** The `require(!transactionExists[_txHash])` guard prevents replay or modification of an existing receipt hash.
- **Gas Profiling:** Tested in `blockchain/test_blockchain_metrics.py`, logging transactions consumes ~71,000 gas units per receipt with execution latency < 2ms in memory.

---

## 18. MULTI-USER IDENTITY & ACCOUNT MANAGEMENT

The system provides out-of-the-box support for four demonstration accounts:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        DEMONSTRATION ACCOUNTS                          │
├───────────┬──────────────┬──────────────────┬───────────┬──────────────┤
│ Client ID │ Name         │ Default Balance  │ Role      │ Usage        │
├───────────┼──────────────┼──────────────────┼───────────┼──────────────┤
│    100    │ Customer A   │ $500.00 (50000¢) │ customer  │ Primary P2P  │
│    200    │ Customer B   │ $500.00 (50000¢) │ customer  │ P2P Sender   │
│    300    │ Customer C   │ $500.00 (50000¢) │ customer  │ P2P Receiver │
│    400    │ Merchant A   │ $100.00 (10000¢) │ merchant  │ Retail POS   │
└───────────┴──────────────┴──────────────────┴───────────┴──────────────┘
```

- **Dynamic Switching:** Selecting a different sender or receiver in the UI dropdown immediately dispatches a request to `/balance/{id}` and `/audit/{id}`, dynamically binding the cryptographic proof and settlement to that specific client ID.

---

## 19. TWO-PHONE PHYSICAL DEMONSTRATION NETWORK TOPOLOGY

During live evaluations, the system can be operated using two physical mobile smartphones connected to the host laptop over Wi-Fi.

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                   WI-FI LOCAL AREA NETWORK                             │
│                                  Subnet: 192.168.1.0/24                                │
│                                                                                        │
│   ┌───────────────────────────┐                     ┌──────────────────────────────┐   │
│   │   Phone A: Sender #200    │                     │   Phone B: Receiver #300     │   │
│   │   IP: 192.168.1.15        │                     │   IP: 192.168.1.16           │   │
│   │   Google Chrome Browser   │                     │   Google Chrome Browser      │   │
│   └─────────────┬─────────────┘                     └──────────────┬───────────────┘   │
│                 │                                                  │                   │
│                 │ HTTP :8000 & WS :3001                            │ WS :3001          │
│                 ▼                                                  ▼                   │
│   ┌────────────────────────────────────────────────────────────────────────────────┐   │
│   │                         HOST LAPTOP (IP: 192.168.1.4)                          │   │
│   │                                                                                │   │
│   │   - Vite Dev Server         ──► Port 5173 (TCP)                                │   │
│   │   - FastAPI Backend Gateway ──► Port 8000 (TCP)                                │   │
│   │   - Socket.IO Relay Server  ──► Port 3001 (TCP)                                │   │
│   │   - Secure QUIC Daemon      ──► Port 4433 (UDP)                                │   │
│   │   - MongoDB Replica Set     ──► Port 27017 (TCP, Loopback)                     │   │
│   └────────────────────────────────────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

> **CRITICAL ARCHITECTURAL REALITY:** The phones do **not** communicate directly phone-to-phone over raw radio signals. Modern mobile OS kernels (Android 10+ and iOS) block peer-to-peer NFC data exchange between mobile web browsers. Therefore, Phone A dispatches the transaction to the host laptop's FastAPI gateway, which initiates the QUIC security pipeline. The result is then broadcast via Socket.IO to Phone B.

---

## 20. 12-STAGE CRYPTOGRAPHIC TELEMETRY PIPELINE

The frontend dashboard displays a 12-stage interactive pipeline tracking every phase of execution:

```
[1. QUIC_CONNECTION]
     │ Success: UDP connection established to 127.0.0.1:4433
     ▼
[2. MTLS_VERIFICATION]
     │ Success: Client and server X.509 certificates verified against Root CA
     ▼
[3. PQC_KEY_EXCHANGE]
     │ Success: Kyber-like lattice encapsulation; shared secret derived
     ▼
[4. SESSION_ESTABLISHED]
     │ Success: Session ID allocated; symmetric cipher initialized
     ▼
[5. BEHAVIORAL_AI]
     │ Success: On-device TFLite INT8 autoencoder MAE <= 0.1500
     ▼
[6. TOTP_VERIFICATION]
     │ Success: RFC 6238 6-digit token valid within 120s tolerance window
     ▼
[7. ZKP_GENERATION]
     │ Success: Groth16 proof generated proving balance >= amount
     ▼
[8. SHAMIR_MPC]
     │ Success: 2-of-3 secret shares combined; master key hash verified
     ▼
[9. AES_ENCRYPTION]
     │ Success: 16-byte binary payload encrypted via AES-256-GCM
     ▼
[10. PAYMENT_ACK_RECEIVED]
     │ Success: QUIC server verifies ZKP & emits PAYMENT_ACK receipt
     ▼
[11. MONGODB_UPDATE]
     │ Success: Atomic multi-document ACID transaction debits sender & credits receiver
     ▼
[12. BLOCKCHAIN_AUDIT]
     │ Success: Transaction hash and metadata mined into AuditTrail.sol smart contract
```

---

## 21. SYSTEM ERROR HANDLING, INVARIANT ENFORCEMENT & ROLLBACK MECHANICS

| Failure Mode | Detection Point | Technical Cause | System Reaction & User Experience | State Rollback Behavior |
| :--- | :--- | :--- | :--- | :--- |
| **Insufficient Funds** | Client (`quic_client.py:272`) or Server (`db.py:108`) | Local balance < amount or MongoDB conditional update fails | Transaction aborted with `DECLINED_LOCALLY: Insufficient funds` | **Zero state change.** No database writes or network packets emitted. |
| **Nonexistent Account** | Server (`quic_server.py:152`) | `sender_id` or `receiver_id` missing from `db.users` | Server returns `PAYMENT_ERR: Nonexistent receiver ID 300` | **Zero state change.** Stream terminated with error ACK. |
| **Physical Theft / Anomaly** | Client (`quic_client.py:266`) | TFLite autoencoder MAE > 0.1500 (erratic tilt/location) | UI displays `AI_BLOCKED: Suspicious context` | **Immediate halt.** Payment packet never leaves client device. |
| **Replay / Stale Packet** | Server (`quic_server.py:171`) | TOTP token expired or packet timestamp > 120s old | Server returns `PAYMENT_ERR: Stale Timestamp` | **Rejected.** Settlement aborted. |
| **ZKP Fraud Attempt** | Server (`zkp_verifier.py:64`) | Public amount does not match circuit constraints | Pairing check fails: $e(B, A) \ne \text{RHS}$ | **Rejected.** Server flags proof verification failure. |
| **Invalid mTLS Certificate**| Server (`quic_server.py:325`) | Connecting client lacks valid cert signed by `ca_cert.pem` | QUIC transport handshake fails | **Connection dropped.** No stream established. |
| **Mid-Transfer Database Crash**| MongoDB Engine | Hardware failure during sender deduction | MongoDB ACID transaction aborts | **Automatic Rollback.** MongoDB restores both account balances. |

---

## 22. AUTOMATED TESTING FRAMEWORK & VERIFICATION METRICS

The repository contains automated test suites verifying backend atomicity, cryptography, and blockchain metrics.

### 1. Multi-User ACID Settlement Suite (`tests/test_phase2_multi_user.py`)
Executed via:
```powershell
python tests/test_phase2_multi_user.py
```
- **Test 1: Successful Transfer:** Client 100 ($500) transfers $75 to Client 200 ($100). Verifies sender decreases to $425 and receiver increases to $175.
- **Test 2: Insufficient Funds:** Client 100 attempts to transfer $9,999.99. Verifies transaction rejection and confirms both balances remain unchanged.
- **Test 3: Nonexistent Sender:** Client 999 attempts transfer. Verifies clean rejection.
- **Test 4: Nonexistent Receiver:** Transfer directed to Client 888. Verifies clean rejection.
- **Test 5: Dual-Party Audit Visibility:** Verifies the transaction is queryable under both the sender's and receiver's audit trails.
- **Result:** **5/5 Tests Passed.**

### 2. Blockchain Integrity & Metrics Suite (`blockchain/test_blockchain_metrics.py`)
Executed via:
```powershell
python blockchain/test_blockchain_metrics.py
```
- Validates contract deployment, execution latency (< 0.005s), gas consumption (~71,000 gas units), on-chain record retrieval, and replay attack prevention.
- **Result:** **All assertions passed.**

---

## 23. VERIFIED PRODUCTION MILESTONES VS. PLANNED SCOPE

| Component | Status | Codebase Evidence |
| :--- | :---: | :--- |
| **Multi-User Dynamic UI** | **IMPLEMENTED & VERIFIED** | `mobile_ui/src/App.jsx` supports Accounts 100, 200, 300, 400 with live selector switching. |
| **QUIC 4433 UDP Transport** | **IMPLEMENTED & VERIFIED** | `server/quic_server.py` & `client/quic_client.py` using `aioquic`. |
| **mTLS Authentication** | **IMPLEMENTED & VERIFIED** | Validated via `certs/ca_cert.pem`, `server_cert.pem`, `client_cert.pem`. |
| **Custom Ring-LWE PQC** | **IMPLEMENTED & VERIFIED** | `utils/pqc.py` executes lattice key encapsulation establishing shared AES keys. |
| **Groth16 Zero-Knowledge Proof** | **IMPLEMENTED & VERIFIED** | `zkp/` circuit generates proof via `npx snarkjs`; verified natively by `utils/zkp_verifier.py`. |
| **Shamir 2-of-3 Secret Sharing** | **IMPLEMENTED & VERIFIED** | `utils/shamir_mpc.py` reconstructs master signing key from client/server shares. |
| **Edge Behavioral AI** | **IMPLEMENTED & VERIFIED** | `models/behavioral_ai_quantized.tflite` runs inference on 7 gyroscopic/context features. |
| **MongoDB Replica-Set ACID Settlement**| **IMPLEMENTED & VERIFIED** | `utils/db.py :: settle_payment_atomic()` executes genuine multi-document transactions on `rs0`. |
| **Ethereum Smart Contract Audit** | **IMPLEMENTED & VERIFIED** | `blockchain/web3_integration.py` compiles and mines `AuditTrail.sol` receipts in memory. |
| **Socket.IO Telemetry Relay** | **IMPLEMENTED & VERIFIED** | `mobile_ui/server.cjs` broadcasts events to frontend pipeline visualizer. |
| **Federated Learning Simulation** | **STANDALONE SIMULATION** | `run_fl_simulation.py`, `client/client_fl.py`, and `server/server_fl.py` exist as an offline research simulation; not in live payment path. |
| **Native Android APK Wrapper** | **DEPRECATED / SHELVED** | Capacitor native build failed due to Android OS cleartext restrictions; replaced by Google Chrome Mobile Web App. |

---

## 24. COMPLETE FILE-BY-FILE REPOSITORY BLUEPRINT

| File Path | Primary Responsibility | Key Classes / Functions | Invoked By | Live Payment Flow? |
| :--- | :--- | :--- | :--- | :---: |
| `client/quic_client.py` | QUIC client, AI inference, ZKP prover, AES encryption | `PaymentClient`, `BehavioralAI`, `pay()`, `generate_zkp()` | `api_gateway.py` | **YES** |
| `server/quic_server.py` | Asynchronous QUIC payment daemon | `PaymentServerProtocol`, `handle_payment_request()`, `log_audit_trail()` | Standalone Daemon | **YES** |
| `server/api_gateway.py` | FastAPI REST microservice | `execute_quic_payment()`, `check_balance()`, `get_audit_trail()` | Frontend `App.jsx` | **YES** |
| `mobile_ui/server.cjs` | Socket.IO event relay server | Express-like HTTP server, `io.emit()` | `event_broadcaster.py` | **YES** |
| `mobile_ui/src/App.jsx` | Main React dashboard UI | `executeSecureQuicPayment()`, `fetchCloudData()` | Mobile Browser | **YES** |
| `utils/binary_payload.py`| 16-byte binary struct serialization | `serialize_payment()`, `deserialize_payment()` | `quic_client.py`, `quic_server.py` | **YES** |
| `utils/crypto_payload.py`| AES-256-GCM encryption/decryption | `encrypt_payload()`, `decrypt_payload()` | `quic_client.py`, `quic_server.py` | **YES** |
| `utils/db.py` | Motor MongoDB client & ACID settlement | `settle_payment_atomic()`, `get_user()`, `get_balance_optimized()` | `quic_server.py`, `api_gateway.py` | **YES** |
| `utils/event_broadcaster.py`| Threaded telemetry HTTP forwarder | `broadcast_quic_event()` | Client and Server modules | **YES** |
| `utils/pqc.py` | Custom Ring-LWE Key Encapsulation | `generate_keypair()`, `encapsulate()`, `decapsulate()` | `quic_client.py`, `quic_server.py` | **YES** |
| `utils/shamir_mpc.py` | Shamir's Secret Sharing arithmetic | `split_secret()`, `reconstruct_secret()` | `quic_client.py`, `quic_server.py` | **YES** |
| `utils/totp.py` | RFC 6238 TOTP generator/verifier | `get_totp_token()`, `verify_totp_token()` | `quic_client.py`, `quic_server.py` | **YES** |
| `utils/zkp_verifier.py` | Native Python BN128 Groth16 verifier | `verify_proof()`, `parse_g1()`, `parse_g2()` | `quic_server.py` | **YES** |
| `blockchain/web3_integration.py`| Solidity compiler & EVM logger | `log_to_blockchain()`, `compile_contract()` | `quic_server.py`, `api_gateway.py` | **YES** |
| `blockchain/AuditTrail.sol` | Solidity smart contract | `logTransaction()`, `getTransaction()` | `web3_integration.py` | **YES** |
| `zkp/balance_check.circom` | Groth16 balance verification circuit | `BalanceProof(32)` | SnarkJS Compiler | **YES** |
| `models/behavioral_ai_quantized.tflite` | Quantized INT8 autoencoder weights | Model weights | `quic_client.py` | **YES** |
| `tests/test_phase2_multi_user.py` | Multi-user settlement automated tests | `test_successful_transfer()`, `test_insufficient_funds()` | Pytest / CLI Runner | **TEST** |
| `client/client_fl.py` | Federated learning edge client | Flower NumPy client | `run_fl_simulation.py` | **SIMULATION ONLY** |
| `server/server_fl.py` | Federated learning aggregator | Flower FedAvg strategy | `run_fl_simulation.py` | **SIMULATION ONLY** |
| `run_fl_simulation.py` | FL simulation orchestration script | Subprocess launcher | CLI Runner | **SIMULATION ONLY** |

---

## 25. EXHAUSTIVE VIVA & DEFENSE QUESTION BANK (20 SPECIALIZED DOMAINS)

### Domain A: High-Level Architecture & Motivation
**Q1: What is the core problem that QSP3 solves?**
*What is tested:* Understanding the motivation and engineering trade-offs.
*Answer:* QSP3 solves the security and privacy vulnerabilities of proximity tap payments by introducing post-quantum lattice cryptography (PQC), zero-knowledge balance verification (ZKP), edge AI anti-theft anomaly detection, and atomic multi-document database settlement over an ultra-low latency QUIC transport layer.
*Relevant Files:* `DOCUMENTATION.md`, `client/quic_client.py`, `server/quic_server.py`.

**Q2: Why is the system divided into FastAPI, QUIC Server, and Socket.IO Relay instead of a single monolith?**
*What is tested:* Microservices design rationale.
*Answer:* Separation of concerns and transport protocol specialization. Browsers cannot open direct UDP QUIC connections; FastAPI acts as an HTTP gateway. QUIC handles the high-performance encrypted payment stream over UDP. Socket.IO provides bi-directional WebSocket broadcasting of telemetry events to multiple connected mobile clients.
*Relevant Files:* `server/api_gateway.py`, `server/quic_server.py`, `mobile_ui/server.cjs`.

---

### Domain B: QUIC Transport Protocol
**Q3: Why did you choose QUIC over standard HTTP/2 or WebSockets for payment transmission?**
*What is tested:* Knowledge of transport protocols (RFC 9000).
*Answer:* QUIC runs over UDP and integrates TLS 1.3 directly. It eliminates TCP Head-of-Line blocking (a dropped packet on one stream does not block unrelated streams) and supports Connection Migration via 64-bit Connection IDs, allowing payments to survive mobile network handoffs between Wi-Fi and 5G.
*Relevant Files:* `client/quic_client.py`, `server/quic_server.py`.

**Q4: What library implements QUIC in your codebase, and on what port does it listen?**
*What is tested:* Implementation familiarity.
*Answer:* The project uses `aioquic` (version 1.3.0), an asynchronous Python implementation of QUIC. It listens on UDP port `4433`.
*Relevant Files:* `requirements.txt`, `server/quic_server.py:364`.

---

### Domain C: Post-Quantum Cryptography (PQC)
**Q5: Is your PQC implementation standard NIST FIPS 203 ML-KEM (Kyber)?**
*What is tested:* Academic honesty and technical depth.
*Answer:* No. It is a custom didactic Ring-LWE (Learning With Errors over Rings) Key Encapsulation Mechanism using Kyber parameters ($N=256, Q=3329$). It demonstrates the mathematical principles of lattice-based cryptography—sampling noise polynomials from a small ternary distribution and decoding via half-modulus rounding—without claims of official FIPS certification.
*Relevant Files:* `utils/pqc.py`.

**Q6: What happens during PQC Key Encapsulation and Decapsulation?**
*What is tested:* Cryptographic mathematical comprehension.
*Answer:* During encapsulation, the client encodes 32 random bytes $m$ into a polynomial in $R_q$ and masks it with the server's public key $(a, t)$ using ephemeral noise polynomials $r, e_1, e_2$ to create ciphertext $(u, v)$. During decapsulation, the server computes $w = v - u \cdot s = m + \text{noise}$, rounds each coefficient to the nearest signal level ($0$ or $\lfloor Q/2 \rfloor$), and recovers $m$. Both parties take $\text{SHA-256}(m)$ as the shared 256-bit AES key.
*Relevant Files:* `utils/pqc.py:119-155`.

---

### Domain D: Symmetric Payload Encryption (AES-GCM)
**Q7: Why is AES-256-GCM used instead of AES-CBC?**
*What is tested:* Knowledge of authenticated encryption (AEAD).
*Answer:* AES-CBC provides confidentiality but no authentication, making it vulnerable to padding oracle attacks and bit-flipping. AES-GCM is an AEAD cipher that computes a 16-byte Galois authentication tag over the ciphertext and IV. If an attacker modifies even a single bit of the encrypted payment payload, decryption fails immediately.
*Relevant Files:* `utils/crypto_payload.py`.

**Q8: What is the exact wire structure of the encrypted payload?**
*What is tested:* Exact low-level memory and serialization understanding.
*Answer:* Exactly 44 bytes: a 12-byte random IV, followed by a 16-byte authentication tag, followed by the 16-byte encrypted binary payment struct.
*Relevant Files:* `utils/crypto_payload.py:19-20`.

---

### Domain E: Mutual TLS (mTLS)
**Q9: What is the difference between mTLS and standard TLS?**
*What is tested:* Network security fundamentals.
*Answer:* In standard TLS, only the server proves its identity to the client. In mutual TLS (mTLS), both the client and server present X.509 certificates signed by a trusted Root CA. The server rejects any connection from an untrusted client before any QUIC stream data is accepted.
*Relevant Files:* `certs/generate_certs.py`, `server/quic_server.py:324-326`.

**Q10: Where are certificates loaded in the QUIC server?**
*What is tested:* Code verification.
*Answer:* In `server/quic_server.py` inside `main()`: `configuration.load_cert_chain("server_cert.pem", "server_key.pem")` and `configuration.load_verify_locations("ca_cert.pem")` with `configuration.verify_mode = True`.
*Relevant Files:* `server/quic_server.py:319-326`.

---

### Domain F: Zero-Knowledge Proofs (ZKP)
**Q11: What statement is being proven by the Groth16 circuit?**
*What is tested:* Zero-knowledge statement formulation.
*Answer:* The prover proves knowledge of a private input `balance` such that `balance >= amount` for a publicly specified `amount`, without revealing the numerical value of `balance`.
*Relevant Files:* `zkp/balance_check.circom`.

**Q12: How is the ZKP verified on the server without Node.js?**
*What is tested:* Architecture optimization and performance knowledge.
*Answer:* The server uses `utils/zkp_verifier.py`, which executes BN128 elliptic curve pairing checks purely in Python using the `py_ecc` library. It parses $A \in G_1, B \in G_2, C \in G_1$ from JSON and checks the Groth16 pairing equation in memory, eliminating the latency of spawning a Node.js child process.
*Relevant Files:* `utils/zkp_verifier.py:26-68`.

---

### Domain G: Multi-Party Computation (Shamir MPC)
**Q13: What prime field is used for Shamir's Secret Sharing?**
*What is tested:* Algebraic precision.
*Answer:* The 127-bit Mersenne Prime: $P = 2^{127} - 1 = 170141183460469231731687303715884105727$.
*Relevant Files:* `utils/shamir_mpc.py:6`.

**Q14: How does Shamir's Secret Sharing authorize a transaction?**
*What is tested:* Authorization logic.
*Answer:* The client sends Share 1 ($x=1$). The server combines it with Share 2 ($x=2$) stored in its secure vault using Lagrange polynomial interpolation. If $\text{SHA-256}(\text{reconstructed secret}) == \text{master\_key\_hash.txt}$, the 2-of-3 threshold is satisfied, proving that the client and server co-authorize the payment.
*Relevant Files:* `utils/shamir_mpc.py:33-52`, `server/quic_server.py:214-227`.

---

### Domain H: Edge Behavioral AI
**Q15: What neural network architecture is used for anomaly detection?**
*What is tested:* Machine learning specifics.
*Answer:* A deep neural autoencoder with an input dimension of 7, an encoder compression path of Dense(16) $\to$ Dense(8) $\to$ Dense(4), and a symmetric decoder Dense(8) $\to$ Dense(16) $\to$ Dense(7). It is quantized into an INT8 TensorFlow Lite model (`behavioral_ai_quantized.tflite`).
*Relevant Files:* `utils/train_ai_model.py:29-39`, `models/behavioral_ai_quantized.tflite`.

**Q16: What features are fed into the autoencoder, and what is the anomaly threshold?**
*What is tested:* Feature engineering and operational metrics.
*Answer:* 7 features: `[amount_cents, lat, lon, tilt_x, tilt_y, tilt_z, hour]`. The anomaly cutoff threshold is `0.1500` Mean Absolute Error (MAE), stored in `models/threshold.txt`.
*Relevant Files:* `client/quic_client.py:257-268`, `models/threshold.txt`.

---

### Domain I: Database & ACID Atomicity
**Q17: Why must MongoDB run as a replica set (`rs0`)?**
*What is tested:* Database internals and consistency guarantees.
*Answer:* Standalone MongoDB instances do not support multi-document transactions. To execute `client.start_session()` and `session.start_transaction()` in `utils/db.py`, MongoDB requires an active replica set (e.g., `rs0`) to maintain an oplog for transactional rollback.
*Relevant Files:* `utils/db.py:93-94`.

**Q18: What happens in MongoDB if a sender has $50 and tries to send $100?**
*What is tested:* Concurrency and invariant enforcement.
*Answer:* The update query specifies `{"client_id": sender_id, "balance_cents": {"$gte": amount_cents}}`. Since 5000 is not $\ge$ 10000, `modified_count` returns 0. The Python code raises a `ValueError`, aborting the transaction session. Neither the sender nor receiver balance is altered.
*Relevant Files:* `utils/db.py:107-118`.

---

### Domain J: Blockchain & Decentralized Audits
**Q19: What role does the blockchain play if MongoDB already stores transactions?**
*What is tested:* Understanding dual-ledger immutability.
*Answer:* MongoDB provides high-throughput mutable state and balance updates. The blockchain contract (`AuditTrail.sol`) provides an append-only, tamper-proof cryptographic audit trail where transaction hashes cannot be deleted or overwritten, even by database administrators.
*Relevant Files:* `blockchain/AuditTrail.sol`, `blockchain/web3_integration.py`.

**Q20: What blockchain network is currently used?**
*What is tested:* Implementation accuracy.
*Answer:* An in-memory lightweight Ethereum Virtual Machine (EVM) provided by `web3.py`'s `EthereumTesterProvider`. It compiles and executes `AuditTrail.sol` in Python memory without requiring an external RPC node or testnet faucets.
*Relevant Files:* `blockchain/web3_integration.py:33`.

---

## 26. FINAL COMPREHENSIVE FLOW SUMMARY

```
[1. User Tap in React UI]
           │
           ▼
[2. Frontend App.jsx] ──► Validates inputs & extracts sensor tilt
           │
           ▼
[3. FastAPI Gateway] ──► /quic/execute-payment initializes PaymentClient
           │
           ▼
[4. Behavioral AI] ──► TFLite INT8 autoencoder checks device context (MAE <= 0.1500)
           │
           ▼
[5. Groth16 ZKP Prover] ──► SnarkJS generates proof: balance >= amount
           │
           ▼
[6. PQC Key Exchange] ──► Ring-LWE encapsulation establishes 256-bit shared secret
           │
           ▼
[7. Binary Struct Pack] ──► 16-byte payload packed (>IHHII: amount, sender, receiver, totp, time)
           │
           ▼
[8. AES-256-GCM] ──► Encrypts 16-byte payload with 12-byte IV + 16-byte Auth Tag
           │
           ▼
[9. QUIC Transport] ──► Transmits encrypted stream over UDP port 4433 with mTLS
           │
           ▼
[10. QUIC Server Decrypt] ──► Decrypts AES, validates TOTP window and account existence
           │
           ▼
[11. ZKP & MPC Verify] ──► Verifies Groth16 proof in RAM; reconstructs 2-of-3 Shamir key
           │
           ▼
[12. QUIC ACK Returned] ──► Sends PAYMENT_ACK:SUCCESS to client
           │
           ▼
[13. MongoDB Settlement] ──► Multi-document ACID transaction debits sender and credits receiver
           │
           ▼
[14. Blockchain Audit] ──► Mines receipt into AuditTrail.sol smart contract
           │
           ▼
[15. Socket.IO Broadcast] ──► Relays real-time telemetry to mobile devices
           │
           ▼
[16. Cloud Balance Refresh] ──► Both phones update balances and ledger automatically
```

---
*Document Authenticated: September 17, 2026 | QSP3 Core Engineering Group*
