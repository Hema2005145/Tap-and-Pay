# QSP3 Payment System: Architecture & Technical Documentation

## 1. Core Logic & System Architecture
The QSP3 Payment System is designed as a hybrid offline-first Peer-to-Peer (P2P) settlement layer. The core objective is to execute highly secure, low-latency financial transactions between two individuals in close proximity, heavily fortified by quantum-resistant cryptography, deep learning anomaly detection, and privacy-preserving federated AI models.

**The WebSocket Hybridization Layer:**
Due to strict hardware limitations in modern smartphones (specifically the deprecation of Android Beam in Android 10), active Phone-to-Phone NFC data transfers are blocked at the OS level. To bypass this and maintain a flawless user experience, we built a **Hybridization Bridge**:
1. **The Physical Trigger:** The NFC hardware chip is used exclusively for proximity detection. When the phones touch, the coils interact, triggering the physical "beep" and vibration.
2. **The Data Tunnel:** Simultaneously, the transaction payload is blasted over a Local Area Network (LAN) WebSocket. The Receiver instantly catches the payload from the air, completing the "Tap to Pay" illusion with zero perceived latency.
3. **The Cloud Anchor:** Both phones simultaneously report the settled transaction to a Python/FastAPI backend, which immutably writes the state into a MongoDB database cluster.

---

## 2. Advanced Algorithms & Cryptography

### A. Post-Quantum Cryptography (PQC)
- **Role:** Securing the network layer and data payload against future quantum computer attacks.
- **Core Logic:** Utilizes lattice-based cryptographic algorithms to encapsulate the standard encryption keys. This ensures that transaction payloads transmitted over the WebSocket and anchored in MongoDB cannot be decrypted retroactively ("harvest now, decrypt later") by quantum adversaries.

### B. Payload Encryption & Decryption (E2EE)
- **Role:** End-to-End Encryption of all financial data.
- **Core Logic:** Before the Sender emits the socket payload, the raw transaction data (Amount, Hash, Sender ID) is heavily encrypted using AES-256-GCM. The Receiver and Cloud Backend decrypt the payload using a shared symmetric key that was securely negotiated via the PQC handshake.

### C. Shamir's Secret Sharing (SSC)
- **Role:** Decentralized Key Recovery and Wallet Security.
- **Core Logic:** The user's master private key is mathematically split into multiple "shares" (e.g., using a 3-of-5 threshold scheme). The transaction is only authorized when a threshold of distributed shares are combined, completely eliminating single points of failure and preventing localized wallet theft.

### D. Time-Based One-Time Passwords (TOTP)
- **Role:** Session Authority and Anti-Replay Attack Mechanism.
- **Core Logic:** Every transaction payload is mathematically stamped with a cryptographic TOTP token synced with the backend server's clock. If a malicious actor intercepts a WebSocket payload and attempts a replay attack, the backend rejects it instantly because the TOTP window (e.g., 30 seconds) has expired.

### E. Autoencoders (Cloud Fraud Detection)
- **Role:** Deep Learning Behavioral Anomaly Detection.
- **Core Logic:** An unsupervised neural network (Autoencoder) is trained on the user's historical transactional behavior (amounts, frequency, metadata). The Autoencoder attempts to reconstruct incoming transaction data. If the "Reconstruction Error" is excessively high, the transaction is flagged as highly anomalous and blocked for manual verification.

### F. Federated Learning (Privacy-Preserving AI)
- **Role:** Training global Anti-Fraud AI models without exposing private user data.
- **Core Logic:** Uses the Flower (`flwr`) framework. Instead of uploading sensitive financial data to the cloud, the Autoencoder AI model is trained locally directly on the user's mobile device (`client_fl.py`). The phone then extracts the mathematical "weights" (learned patterns) and sends them to the Aggregation Server (`server_fl.py`). The server uses the **FedAvg (Federated Averaging)** strategy to merge all edge weights into a master model, guaranteeing absolute data privacy.

### G. Edge AI Gyroscopic Anomaly Detection (Anti-Theft)
- **Role:** Physical theft prevention during the point of sale.
- **Core Logic:** The system establishes a stable baseline of the phone's resting orientation (Beta/Pitch and Gamma/Roll). It calculates the real-time delta variance continuously: `Variance = √((currentBeta - baselineBeta)² + (currentGamma - baselineGamma)²)`
- **Execution:** If the variance spikes rapidly (indicating a violent snatch or drop), the AI Anomaly Score skyrockets. The UI instantly turns red and locks the transaction, preventing the encrypted payload from being emitted over the network.

### H. ZKP (Zero-Knowledge Proof) Hashing
- **Role:** Transaction State Anchoring.
- **Core Logic:** Generates a highly secure SHA-256 cryptographic hash representing the valid transaction state. This acts as the immutable receipt anchored in the database without exposing underlying ledger data.

---

## 3. Microservices Backend Architecture

The backend ecosystem is deliberately separated into specialized microservices to guarantee security, isolate heavy computational loads, and maximize network speed.

### A. The Node.js WebSocket Relay Server (The "Bridge")
- **Role:** Ultra-low latency real-time network routing.
- **Why it is necessary:** Because modern Android blocks active phone-to-phone NFC data transfers, we tunnel the payload over the air. Node.js is the optimal technology for handling thousands of simultaneous, lightning-fast WebSocket connections. It performs absolutely no cryptographic or database work; its sole purpose is to catch the payment payload from the Sender and instantly broadcast it to the Receiver in milliseconds.

### B. The Python FastAPI Server (The "Ledger")
- **Role:** Cloud Database Anchor and API Gateway.
- **Why it is necessary:** Once the phones agree on a transaction via the WebSocket, they must report it to a centralized cloud ledger to finalize the settlement. FastAPI receives the encrypted payload, verifies the TOTP session, handles HTTP request traffic, and writes the immutable transaction hash permanently into the MongoDB database cluster.

### C. The Python Federated Learning Server (The "Aggregator")
- **Role:** Orchestrating decentralized AI training.
- **Why it is necessary:** Manages the connection pool of edge devices and securely averages incoming neural network weights (`server_fl.py`) without requiring centralized data storage.

### D. The Dockerized C++ Engine (The "Cryptographer")
- **Role:** High-performance execution of cryptographic algorithms (PQC, SSC).
- **Why it is necessary:** Python and JavaScript are fundamentally too slow to execute complex lattice-based quantum encryption efficiently. By writing the core encryption algorithms in raw C++, and putting that C++ inside a Docker Container, we create a dedicated "high-performance calculator" that runs at bare-metal speeds regardless of the host operating system.

---

## 4. How to Run the Project

You must start the terminal processes to bring the ecosystem online.

**Step 1: Start the Dockerized C++ Cryptographic Engine**
Open a terminal in the folder containing your C++ Dockerfile:
```bash
docker build -t qsp3-cpp-engine .
docker run -d -p 8080:8080 qsp3-cpp-engine
```

**Step 2: Start the Cloud Backend (FastAPI + MongoDB)**
Open a terminal in `C:\Users\matam\qsp3_payment\server`:
```bash
python -m uvicorn api_gateway:app --host 0.0.0.0 --port 8000 --reload
```

**Step 3: Start the WebSocket Relay Server (Node.js)**
Open a terminal in `C:\Users\matam\qsp3_payment\mobile_ui`:
```bash
node server.cjs
```

**Step 4: Start the Frontend UI (React + Vite)**
Open a terminal in `C:\Users\matam\qsp3_payment\mobile_ui`:
```bash
npm run dev -- --host
```

**Step 5: Execute the Hardware Demo**
1. Ensure your laptop and two mobile phones are connected to the exact same Wi-Fi network.
2. Open **Google Chrome** on both mobile phones and navigate to your laptop's IP address (e.g., `http://192.168.0.4:5173`).
3. On Phone 1, select **Receiver**, and tap the pulsing dot to activate the scanner.
4. On Phone 2, select **Sender**, input an amount, and tap **"Tap to Pay"**.
5. Physically tap the phones together to trigger the gyroscopic/NFC logic and execute the transfer.

**Optional: Run the Federated Learning Simulation**
To observe the edge devices training the Autoencoder locally and uploading weights to the `server_fl.py` aggregator:
```bash
python run_fl_simulation.py
```

---

## 5. Known Limitations & The Native Sandbox Failure

While the overarching logic executes perfectly in the browser, compiling the React codebase into a Native Android App (`.apk`) using Capacitor failed at the network layer.

**The Symptom:**
The native `.apk` experienced immediate `xhr poll error` and `timeout` crashes when attempting to connect to the Node.js WebSocket Server.

**The Root Cause:**
Android 9+ enforces a strict **"Cleartext Traffic Restriction"**. Native apps are heavily restricted from making unencrypted HTTP (`http://`) or WebSocket (`ws://`) connections to local area network IPs (like `192.168.0.4`) to prevent malicious background scanning.

**Attempted Fixes:**
1. Injected `android:usesCleartextTraffic="true"` directly into the native OS Kernel `AndroidManifest.xml` to force an override. *(Failed: The OS or Capacitor WebView still silently dropped the packets).*
2. Forced Socket.io to bypass the Capacitor HTTP interceptor by switching exclusively to `transports: ['websocket']`. *(Failed: Resulted in a TCP handshake timeout).*
3. Built a public HTTPS `localtunnel` proxy to completely bypass the local network restriction. *(Failed: The proxy intercepted the WebSocket handshake with an anti-phishing HTML warning screen, breaking the Socket.io logic).*

**The Resolution:**
By abandoning the `.apk` wrapper and running the application through **Mobile Google Chrome**, the system bypasses the native Capacitor Sandbox bugs completely. Chrome natively supports the Web NFC API, the Device Orientation API, and WebSockets without enforcing the strict native `.apk` local-network block.
