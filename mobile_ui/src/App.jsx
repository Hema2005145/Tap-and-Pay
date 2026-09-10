import { useState, useEffect, useRef } from 'react';
import { io } from 'socket.io-client';
import './App.css';

// WebSocket connection for fallback/confirmation syncing & real QUIC telemetry
const SOCKET_URL = 'http://127.0.0.1:3001';
const API_URL = 'http://127.0.0.1:8000';

const socket = io(SOCKET_URL, {
  reconnectionAttempts: 10,
  timeout: 5000,
});

const INITIAL_PIPELINE = {
  quicConnection: { status: 'WAITING', endpoint: '127.0.0.1:4433 (UDP)', protocol: 'aioquic' },
  mtls: { status: 'WAITING', clientCert: 'client_cert.pem', caCert: 'ca_cert.pem', cipher: 'TLS 1.3' },
  pqcKeyExchange: { status: 'WAITING', algorithm: 'Kyber-like / Custom PQC', step: 'WAITING FOR EVENT' },
  pqcSession: { status: 'WAITING', session_id: null },
  behavioralAi: { status: 'WAITING', model: 'TFLite INT8 Quantized', mae_error: null, threshold: null, is_anomaly: null },
  totp: { status: 'WAITING', validation_status: null, window_tolerance: '120s' },
  zkp: { status: 'WAITING', proof_system: 'Groth16 (bn128)', funds_proven: null, amount_cents: null },
  shamirMpc: { status: 'WAITING', threshold_scheme: '2-of-3 Threshold', key_matched: null },
  aesGcm: { status: 'WAITING', cipher: 'AES-256-GCM', iv_length: '12-byte' },
  paymentAck: { status: 'WAITING', tx_hash: null, amount_str: null, ack_raw: null },
  mongoUpdate: { status: 'WAITING', db_status: null, record_id: null },
  blockchainAudit: { status: 'WAITING', smart_contract: 'AuditTrail.sol', block_number: null, status_on_chain: null }
};

function App() {
  const [role, setRole] = useState('selection'); // 'selection' | 'sender' | 'receiver'
  
  // Sender State (Client 1)
  const [status, setStatus] = useState('idle');
  const [statusMsg, setStatusMsg] = useState('');
  const [amount, setAmount] = useState('25.00');
  const [balance, setBalance] = useState(500.00);
  const [txSpeed, setTxSpeed] = useState(null);
  const [transactions, setTransactions] = useState([]);

  // Hardware Context Sensor State (Edge AI)
  const [lat, setLat] = useState(12.97);
  const [lon, setLon] = useState(77.59);
  const [tiltX, setTiltX] = useState(0.70);
  const [tiltY, setTiltY] = useState(0.20);
  const [tiltZ, setTiltZ] = useState(0.90);
  const [aiScore, setAiScore] = useState(0.00);
  const [hardwareActive, setHardwareActive] = useState(false);
  const [nfcStatus, setNfcStatus] = useState('Checking Hardware...');
  const [socketStatus, setSocketStatus] = useState('Connecting to Network...');

  // Receiver State (Client 2)
  const [receiverBalance, setReceiverBalance] = useState(0.00);
  const [receiverStatus, setReceiverStatus] = useState('waiting');
  const [receiverReceivedAmount, setReceiverReceivedAmount] = useState(0);
  const [receiverTransactions, setReceiverTransactions] = useState([]);

  // Real QUIC Telemetry State
  const [quicPipeline, setQuicPipeline] = useState(INITIAL_PIPELINE);
  const [quicLogs, setQuicLogs] = useState([]);
  const [quicServerOnline, setQuicServerOnline] = useState(null);
  const [isQuicExecuting, setIsQuicExecuting] = useState(false);
  const [quicExecutionBanner, setQuicExecutionBanner] = useState(null);
  const terminalEndRef = useRef(null);

  // Auto-scroll terminal
  useEffect(() => {
    terminalEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [quicLogs]);

  // Check QUIC server and FastAPI connectivity
  const checkBackendHealth = async () => {
    try {
      const res = await fetch(`${API_URL}/quic/status`, { signal: AbortSignal.timeout(2000) });
      if (res.ok) {
        const data = await res.json();
        setQuicServerOnline(data.quic_server_online);
      } else {
        setQuicServerOnline(false);
      }
    } catch {
      setQuicServerOnline(false);
    }
  };

  useEffect(() => {
    checkBackendHealth();
    const interval = setInterval(checkBackendHealth, 8000);
    return () => clearInterval(interval);
  }, []);

  const fetchCloudData = async () => {
    try {
      if (role === 'sender' || role === 'selection') {
        const balRes = await fetch(`${API_URL}/balance/1`);
        if (balRes.ok) {
          const balData = await balRes.json();
          setBalance(balData.balance_cents / 100);
        }
        
        const audRes = await fetch(`${API_URL}/audit/1`);
        if (audRes.ok) {
          const audData = await audRes.json();
          setTransactions(audData.history.map(tx => ({
            id: tx._id,
            title: 'QSP3 Secure Tx',
            hash: tx.tx_hash ? (tx.tx_hash.substring(0, 14) + '...') : 'N/A',
            fullHash: tx.tx_hash || '',
            amount: `-$${(tx.amount_cents / 100).toFixed(2)}`
          })));
        }
      } 
      if (role === 'receiver' || role === 'selection') {
        const balRes = await fetch(`${API_URL}/balance/2`);
        if (balRes.ok) {
          const balData = await balRes.json();
          setReceiverBalance(balData.balance_cents / 100);
        }
        
        const audRes = await fetch(`${API_URL}/audit/2`);
        if (audRes.ok) {
          const audData = await audRes.json();
          setReceiverTransactions(audData.history.map(tx => ({
            id: tx._id,
            title: 'Customer Payment',
            hash: tx.tx_hash ? (tx.tx_hash.substring(0, 14) + '...') : 'N/A',
            fullHash: tx.tx_hash || '',
            amount: `+$${(tx.amount_cents / 100).toFixed(2)}`
          })));
        }
      }
    } catch (e) {
      console.log("Cloud Backend Offline. Using Local Fallback.", e);
    }
  };

  useEffect(() => {
    fetchCloudData();
  }, [role]);

  // SOCKET NETWORK STATUS & REAL QUIC EVENTS
  useEffect(() => {
    socket.on('connect', () => setSocketStatus('🟢 Socket Connected'));
    socket.on('disconnect', () => setSocketStatus('🔴 Socket Disconnected'));
    socket.on('connect_error', (err) => setSocketStatus(`🔴 Socket Error: ${err.message}`));
    
    if (socket.connected) setSocketStatus('🟢 Socket Connected');

    // Real QUIC pipeline event listener
    socket.on('quic_event', (eventData) => {
      if (!eventData || !eventData.stage) return;

      const timeStr = new Date(eventData.timestamp ? eventData.timestamp * 1000 : Date.now()).toLocaleTimeString('en-US', {
        hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit', fractionalSecondDigits: 3
      });

      // Append to live terminal log
      setQuicLogs(prev => [
        ...prev.slice(-99),
        {
          id: `${Date.now()}-${Math.random()}`,
          time: timeStr,
          stage: eventData.stage,
          status: eventData.status,
          details: eventData.details || {}
        }
      ]);

      // Update the 12-stage pipeline model strictly with real values
      setQuicPipeline(prev => {
        const next = { ...prev };
        const details = eventData.details || {};

        switch (eventData.stage) {
          case 'QUIC_SERVER_STATUS':
            if (eventData.status === 'ONLINE') setQuicServerOnline(true);
            break;

          case 'QUIC_CONNECTION':
            next.quicConnection = {
              status: eventData.status,
              endpoint: details.endpoint || '127.0.0.1:4433 (UDP)',
              error: details.error || null
            };
            if (eventData.status === 'SUCCESS') setQuicServerOnline(true);
            if (eventData.status === 'FAILED' || eventData.status === 'OFFLINE') setQuicServerOnline(false);
            break;

          case 'MTLS_VERIFICATION':
            next.mtls = {
              status: eventData.status,
              clientCert: details.cert || 'client_cert.pem',
              cipher: 'TLS 1.3 (Mutual Auth)'
            };
            break;

          case 'PQC_KEY_EXCHANGE':
            next.pqcKeyExchange = {
              status: eventData.status,
              algorithm: details.algorithm || 'Kyber-like / Custom PQC',
              step: details.step || (eventData.status === 'SUCCESS' ? 'Shared Secret Derived' : 'In Progress')
            };
            break;

          case 'SESSION_ESTABLISHED':
            next.pqcSession = {
              status: eventData.status,
              session_id: details.session_id || 'NOT EXPOSED'
            };
            break;

          case 'BEHAVIORAL_AI':
            next.behavioralAi = {
              status: eventData.status, // 'NORMAL' or 'ANOMALY'
              model: 'TFLite INT8 Quantized Autoencoder',
              mae_error: details.mae_error !== undefined ? details.mae_error : null,
              threshold: details.threshold !== undefined ? details.threshold : null,
              is_anomaly: details.is_anomaly
            };
            break;

          case 'TOTP_VERIFICATION':
            // CRITICAL: Per rule #2, NEVER expose the secret or token, only validation status and window
            next.totp = {
              status: eventData.status,
              validation_status: details.status || (eventData.status === 'SUCCESS' ? 'VERIFIED' : 'FAILED'),
              window_valid: details.window_valid !== undefined ? details.window_valid : true,
              window_tolerance: '120s'
            };
            break;

          case 'ZKP_GENERATION':
          case 'ZKP_VERIFICATION':
            next.zkp = {
              status: eventData.status,
              proof_system: details.proof_system || 'Groth16 (bn128)',
              funds_proven: details.funds_proven !== undefined ? details.funds_proven : (eventData.status === 'SUCCESS'),
              amount_cents: details.amount_cents || null
            };
            break;

          case 'SHAMIR_MPC':
            next.shamirMpc = {
              status: eventData.status,
              threshold_scheme: details.threshold || '2-of-3 Threshold',
              key_matched: details.key_hash_matched !== undefined ? details.key_hash_matched : (eventData.status === 'SUCCESS')
            };
            break;

          case 'AES_ENCRYPTION':
          case 'AES_DECRYPTION':
            next.aesGcm = {
              status: eventData.status,
              cipher: details.cipher || 'AES-256-GCM',
              iv_length: '12-byte IV / 16-byte Tag'
            };
            break;

          case 'PAYMENT_ACK':
          case 'PAYMENT_ACK_RECEIVED':
            next.paymentAck = {
              status: eventData.status,
              tx_hash: details.tx_hash || null,
              amount_str: details.amount_str || (details.amount_cents ? `$${(details.amount_cents / 100).toFixed(2)}` : null),
              ack_raw: details.raw_ack || (eventData.status === 'SUCCESS' ? 'PAYMENT_ACK: Success' : 'ERROR')
            };
            fetchCloudData();
            break;

          case 'MONGODB_UPDATE':
            next.mongoUpdate = {
              status: eventData.status,
              db_status: details.status || (eventData.status === 'SUCCESS' ? 'COMMITTED' : 'FAILED'),
              tx_hash: details.tx_hash || null
            };
            break;

          case 'BLOCKCHAIN_AUDIT':
            next.blockchainAudit = {
              status: eventData.status,
              smart_contract: 'AuditTrail.sol',
              status_on_chain: details.status || (eventData.status === 'SUCCESS' ? 'MINED_ON_CHAIN' : 'FAILED'),
              tx_hash: details.tx_hash || null
            };
            break;

          default:
            break;
        }

        return next;
      });
    });

    return () => {
      socket.off('connect');
      socket.off('disconnect');
      socket.off('connect_error');
      socket.off('quic_event');
    };
  }, []);

  // LIVE HARDWARE INTEGRATION (Browser DeviceOrientation)
  useEffect(() => {
    const handleOrientation = (event) => {
      if (event.beta !== null) {
        setHardwareActive(true);
        setTiltX(Math.abs(event.beta) / 180);
        setTiltY(Math.abs(event.gamma) / 90);
        setTiltZ(Math.abs(event.alpha) / 360);
      }
    };

    if (window.DeviceOrientationEvent) {
      window.addEventListener('deviceorientation', handleOrientation);
    }

    if ('NDEFReader' in window) {
      setNfcStatus('Hardware Supported (Web NFC)');
    } else {
      setNfcStatus('Web NFC Not Available in Browser');
    }

    socket.on('payment_received', (payload) => {
      if (role === 'receiver' || role === 'selection') {
        processIncomingPayment(payload.amount, payload.hash);
      }
    });

    return () => {
      window.removeEventListener('deviceorientation', handleOrientation);
      socket.off('payment_received');
    };
  }, [role]);

  const activateNfcScanner = async () => {
    if (!('NDEFReader' in window)) return;
    try {
      const nfcReader = new window.NDEFReader();
      await nfcReader.scan();
      setNfcStatus('🟢 Scanning Active');
      nfcReader.onreading = event => {
        const decoder = new TextDecoder();
        for (const record of event.message.records) {
          const rawPayload = decoder.decode(record.data);
          try {
            const parsed = JSON.parse(rawPayload);
            if (parsed.type === 'QSP3_PAYMENT_INIT') {
              processIncomingPayment(parsed.amount, parsed.hash);
            }
          } catch (e) {
            console.error(e);
          }
        }
      };
    } catch (err) {
      setNfcStatus(`🔴 Denied: ${err.message}`);
    }
  };

  const processIncomingPayment = async (incAmount, incHash) => {
    setReceiverStatus('received');
    setReceiverReceivedAmount(incAmount);
    
    setReceiverBalance(prev => prev + incAmount);
    setReceiverTransactions(prev => [{
      id: Date.now(),
      title: 'Customer: Hardware NFC / Socket Tap',
      hash: incHash ? (incHash.substring(0, 14) + '...') : '0x...',
      amount: `+$${incAmount.toFixed(2)}`
    }, ...prev].slice(0, 5));
    
    setTimeout(() => {
      setReceiverStatus('waiting');
      fetchCloudData();
    }, 4000);
  };

  // -------------------------------------------------------------
  // BROWSER PAYMENT DEMO (Existing Tap to Pay flow)
  // -------------------------------------------------------------
  const handleTap = async () => {
    if (status === 'processing') return;
    setTxSpeed(null);
    
    if (!amount || isNaN(amount) || parseFloat(amount) <= 0) {
      setStatus('error');
      setStatusMsg('Please enter a valid amount.');
      setTimeout(() => setStatus('idle'), 3000);
      return;
    }

    const simAmount = parseFloat(amount);
    
    if (simAmount > balance && balance > 0) {
      setStatus('error');
      setStatusMsg('DECLINED LOCALLY: Insufficient funds.');
      setTxSpeed('0.0010s');
      setTimeout(() => { setStatus('idle'); setStatusMsg(''); setTxSpeed(null); }, 4000);
      return;
    }

    setStatus('processing');
    setStatusMsg('Browser Demo: Evaluating Heuristic Risk & Pushing REST Tx...');
    
    const latError = Math.abs(lat - 12.97) * 10;
    const lonError = Math.abs(lon - 77.59) * 10;
    const tiltError = Math.abs(tiltX - 0.7) + Math.abs(tiltY - 0.2) + Math.abs(tiltZ - 0.9);
    const amountFactor = simAmount / 500; 
    
    const calculatedScore = (latError + lonError + (tiltError * 2) + amountFactor) / 4;
    setAiScore(calculatedScore);
    
    const AI_THRESHOLD = 0.75;
    const isAnomaly = calculatedScore > AI_THRESHOLD;
    const speedMs = isAnomaly ? 5 : 713;
    
    setTimeout(async () => {
      setTxSpeed(`${(speedMs / 1000).toFixed(4)}s`);
      
      if (isAnomaly) {
        setStatus('error');
        setStatusMsg(`AI_BLOCKED: Local Heuristic Score = ${calculatedScore.toFixed(2)} (> 0.75 threshold)`);
      } else {
        setStatus('success');
        setStatusMsg(`PAYMENT_ACK: Success. Sent $${simAmount.toFixed(2)} via Browser Demo.`);
        
        const newHash = '0x' + Math.random().toString(16).substring(2, 12) + '...';
        
        try {
          await fetch(`${API_URL}/transaction`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              tx_hash: newHash,
              client_id: 1,
              amount_cents: Math.round(simAmount * 100),
              status: "SUCCESS",
              zkp_proof_id: "browser_demo_" + Date.now()
            })
          });
        } catch(e) { 
          console.log("Cloud Push failed, local fallback only", e); 
        }

        fetchCloudData();

        if ('NDEFReader' in window) {
          try {
            const ndef = new window.NDEFReader();
            ndef.write({
              records: [{
                recordType: "text",
                data: JSON.stringify({ type: 'QSP3_PAYMENT_INIT', amount: simAmount, hash: newHash })
              }]
            }).catch(() => console.log("NFC Write resolved with expected P2P block"));
          } catch {
            console.log("NFC hardware busy");
          }
        }
        
        socket.emit('payment_sent', { amount: simAmount, hash: newHash });
      }
      
      setTimeout(() => {
        setStatus('idle');
        setStatusMsg('');
        setTxSpeed(null);
      }, 4000);
      
    }, speedMs);
  };

  // -------------------------------------------------------------
  // REAL SECURE QUIC PAYMENT EXECUTION
  // -------------------------------------------------------------
  const executeSecureQuicPayment = async () => {
    if (isQuicExecuting) return;
    setIsQuicExecuting(true);
    setQuicExecutionBanner('Initializing Secure QUIC Session to 127.0.0.1:4433...');

    // Reset pipeline display to waiting
    setQuicPipeline(INITIAL_PIPELINE);

    try {
      const simAmountCents = Math.round(parseFloat(amount || '25') * 100);
      const res = await fetch(`${API_URL}/quic/execute-payment`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          amount_cents: simAmountCents,
          client_id: 1,
          lat, lon,
          tilt_x: tiltX,
          tilt_y: tiltY,
          tilt_z: tiltZ,
          private_balance_cents: Math.round(balance * 100)
        })
      });

      const result = await res.json();
      if (result.status === 'SUCCESS') {
        setQuicExecutionBanner(`SECURE QUIC PAYMENT SETTLED: ${result.ack}`);
        setQuicServerOnline(true);
        fetchCloudData();
      } else if (result.status === 'OFFLINE') {
        setQuicExecutionBanner(`QUIC DAEMON OFFLINE: ${result.error || 'Server unreachable at 127.0.0.1:4433'}. Run quic_server.py in terminal.`);
        setQuicServerOnline(false);
      } else {
        setQuicExecutionBanner(`QUIC EXECUTION RESULT: ${result.error || JSON.stringify(result)}`);
      }
    } catch (err) {
      setQuicExecutionBanner(`BACKEND UNREACHABLE: Failed to connect to API gateway (${API_URL}): ${err.message}`);
      setQuicServerOnline(false);
    } finally {
      setIsQuicExecuting(false);
      setTimeout(() => setQuicExecutionBanner(null), 8000);
    }
  };

  const clearLog = () => setQuicLogs([]);

  // RENDER: Role Selection Hub
  if (role === 'selection') {
    return (
      <div className="app-wrapper">
        <header className="dashboard-header">
          <div className="brand-section">
            <div className="brand-logo">Q3</div>
            <div className="brand-title">QSP3 <span>Quantum Settlement Platform</span></div>
          </div>
          <div className="telemetry-pills">
            <div className="telemetry-pill">
              <span className={`status-dot ${socketStatus.includes('Connected') ? 'online' : 'offline'}`}></span>
              <span>{socketStatus}</span>
            </div>
            <div className="telemetry-pill">
              <span className={`status-dot ${quicServerOnline === true ? 'online' : (quicServerOnline === false ? 'offline' : 'waiting')}`}></span>
              <span>QUIC :4433 {quicServerOnline === true ? 'ONLINE' : (quicServerOnline === false ? 'OFFLINE' : 'CHECKING')}</span>
            </div>
          </div>
        </header>

        <div className="role-hub-screen">
          <div className="role-hub-header">
            <h1 className="role-hub-title">Select Terminal <span>Profile</span></h1>
            <p className="role-hub-subtitle">High-throughput Quantum-Resistant P2P Financial Settlement Layer</p>
          </div>

          <div className="role-cards-container">
            <div className="role-hub-card" onClick={() => setRole('sender')}>
              <div className="role-card-icon">📱</div>
              <div className="role-card-name">Customer Terminal (Sender)</div>
              <div className="role-card-desc">
                Primary client wallet. Supports Browser NFC Demo, real-time hardware orientation feeds, local heuristic scoring, and real Quantum-Resistant QUIC transactions.
              </div>
              <div className="role-card-features">
                <div>▸ Client ID: 1 (Alexander D.)</div>
                <div>▸ Mode: Payment Originator</div>
                <div>▸ Security: mTLS + Kyber-like PQC + ZKP + Shamir MPC</div>
              </div>
            </div>

            <div className="role-hub-card receiver-card" onClick={() => setRole('receiver')}>
              <div className="role-card-icon">🏪</div>
              <div className="role-card-name">Merchant POS Terminal (Receiver)</div>
              <div className="role-card-desc">
                Point-of-Sale listening station. Features low-latency WebSocket / Web NFC broadcast reception, instant credit notifications, and automated ledger anchoring.
              </div>
              <div className="role-card-features">
                <div>▸ Client ID: 2 (Store #9942-A)</div>
                <div>▸ Mode: Payment Settlement Node</div>
                <div>▸ Security: Immutable MongoDB & Blockchain Audit</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // RENDER: Main Desktop Dashboard
  return (
    <div className="app-wrapper">
      {/* Top Header */}
      <header className="dashboard-header">
        <div className="brand-section">
          <div className="brand-logo">Q3</div>
          <div className="brand-title">
            QSP3 <span>Quantum Settlement Dashboard</span>
          </div>
        </div>

        <div className="telemetry-pills">
          <div className={`telemetry-pill ${socketStatus.includes('Connected') ? 'active' : 'error'}`}>
            <span className={`status-dot ${socketStatus.includes('Connected') ? 'online' : 'offline'}`}></span>
            <span>{socketStatus}</span>
          </div>
          <div className={`telemetry-pill ${quicServerOnline === true ? 'active' : (quicServerOnline === false ? 'error' : 'warning')}`}>
            <span className={`status-dot ${quicServerOnline === true ? 'online' : (quicServerOnline === false ? 'offline' : 'waiting')}`}></span>
            <span>QUIC :4433 {quicServerOnline === true ? 'ONLINE' : (quicServerOnline === false ? 'OFFLINE' : 'CHECKING')}</span>
          </div>
          <div className="telemetry-pill">
            <span className="status-dot online"></span>
            <span>{nfcStatus}</span>
          </div>
        </div>

        <div className="header-actions">
          <div className={`mode-badge ${role === 'receiver' ? 'receiver-mode' : ''}`}>
            {role === 'sender' ? 'CUSTOMER WALLET (CLIENT #1)' : 'MERCHANT POS (CLIENT #2)'}
          </div>
          <button className="profile-switch-btn" onClick={() => setRole(role === 'sender' ? 'receiver' : 'sender')}>
            ⇄ Switch to {role === 'sender' ? 'Merchant' : 'Customer'}
          </button>
          <button className="profile-switch-btn" onClick={() => setRole('selection')}>
            Profile Selection
          </button>
        </div>
      </header>

      {/* Main 3-Column Command Grid */}
      <main className="command-grid">
        
        {/* ============================================================== */}
        {/* COLUMN 1: BROWSER PAYMENT DEMO (Left Panel)                    */}
        {/* ============================================================== */}
        <section className="dashboard-panel">
          <div className="panel-header">
            <div>
              <div className="panel-title">💳 Customer Wallet</div>
              <div className="panel-subtitle">Browser Proximity Payment Engine</div>
            </div>
            <span className="panel-tag demo-tag">Browser Demo</span>
          </div>

          {/* Virtual Card */}
          <div className="virtual-card">
            <div className="card-top-row">
              <div className="chip-graphic"></div>
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="var(--primary-color)" strokeWidth="2"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm5 11h-4v4h-2v-4H7v-2h4V7h2v4h4v2z"/></svg>
            </div>
            <div className="card-number-display">**** **** **** 3094</div>
            <div className="card-bottom-row">
              <div>
                <div style={{fontSize: '0.68rem', color: 'var(--text-dim)', textTransform: 'uppercase'}}>Card Holder</div>
                <div className="card-holder-name">ALEXANDER D.</div>
              </div>
              <div className="card-balance-display">
                <div style={{fontSize: '0.68rem', color: 'var(--text-dim)', textTransform: 'uppercase'}}>Available Balance</div>
                <div className="card-balance-value">${balance.toFixed(2)}</div>
              </div>
            </div>
          </div>

          {/* Amount Input */}
          <div className="payment-input-group">
            <label style={{fontSize: '0.78rem', color: 'var(--text-dim)', textTransform: 'uppercase'}}>Payment Amount</label>
            <div className="amount-input-wrapper">
              <span className="currency-symbol">$</span>
              <input 
                type="number" 
                className="amount-field" 
                value={amount} 
                onChange={(e) => setAmount(e.target.value)} 
                placeholder="0.00" 
                step="0.01"
              />
            </div>
            <div className="preset-pills">
              {['10.00', '25.00', '50.00', '100.00'].map(p => (
                <button key={p} className={`preset-pill ${amount === p ? 'active' : ''}`} onClick={() => setAmount(p)}>
                  ${p}
                </button>
              ))}
            </div>
          </div>

          {/* Context Sensors & Local Heuristic Risk */}
          <div className="sensor-hud">
            <div className="sensor-hud-header">
              <span>Device Context {hardwareActive ? '(LIVE 📡)' : '(SIMULATION)'}</span>
              <span style={{color: aiScore > 0.75 ? 'var(--danger-color)' : 'var(--success-color)', fontWeight: 700}}>
                Score: {aiScore.toFixed(2)}
              </span>
            </div>

            <div className="sensor-control-row">
              <span className="sensor-name">Lat</span>
              <input type="range" min="10" max="15" step="0.01" className="sensor-slider-control" value={lat} onChange={(e) => setLat(parseFloat(e.target.value))} />
              <span className="sensor-val">{lat.toFixed(2)}</span>
            </div>
            <div className="sensor-control-row">
              <span className="sensor-name">Tilt X</span>
              <input type="range" min="0" max="1" step="0.01" className="sensor-slider-control" value={tiltX} onChange={(e) => setTiltX(parseFloat(e.target.value))} disabled={hardwareActive} />
              <span className="sensor-val">{tiltX.toFixed(2)}</span>
            </div>
            <div className="sensor-control-row">
              <span className="sensor-name">Tilt Y</span>
              <input type="range" min="0" max="1" step="0.01" className="sensor-slider-control" value={tiltY} onChange={(e) => setTiltY(parseFloat(e.target.value))} disabled={hardwareActive} />
              <span className="sensor-val">{tiltY.toFixed(2)}</span>
            </div>

            <div className="risk-meter-container">
              <div style={{display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem', color: 'var(--text-dim)'}}>
                <span>Risk Threshold: 0.75</span>
                <span>{aiScore > 0.75 ? '⚠️ ANOMALY DETECTED' : '✅ NORMAL'}</span>
              </div>
              <div className="risk-bar">
                <div 
                  className="risk-fill" 
                  style={{
                    width: `${Math.min(aiScore * 100, 100)}%`,
                    backgroundColor: aiScore > 0.75 ? 'var(--danger-color)' : 'var(--success-color)'
                  }}
                ></div>
              </div>
            </div>
          </div>

          {/* Tap to Pay Primary Trigger (Browser Demo) */}
          <div className="tap-action-zone">
            <div className={`tap-circle-btn ${status}`} onClick={handleTap}>
              {status === 'idle' && (
                <>
                  <svg width="34" height="34" viewBox="0 0 24 24" fill="none" stroke="var(--primary-color)" strokeWidth="2"><path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>
                  <span className="tap-btn-label">TAP TO PAY</span>
                </>
              )}
              {status === 'processing' && (
                <svg width="34" height="34" viewBox="0 0 24 24" fill="none" stroke="var(--warning-color)" strokeWidth="2" style={{animation: 'spin 1s linear infinite'}}><path d="M21 12a9 9 0 1 1-6.219-8.56"/></svg>
              )}
              {status === 'success' && (
                <svg width="34" height="34" viewBox="0 0 24 24" fill="none" stroke="var(--success-color)" strokeWidth="2.5"><polyline points="20 6 9 17 4 12"/></svg>
              )}
              {status === 'error' && (
                <svg width="34" height="34" viewBox="0 0 24 24" fill="none" stroke="var(--danger-color)" strokeWidth="2.5"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
              )}
            </div>

            <div className={`tap-feedback-banner ${status}`}>
              <div>{statusMsg || 'Ready for Tap (Browser NFC / Local Heuristic)'}</div>
              {txSpeed && <div style={{color: 'var(--primary-color)', fontFamily: 'monospace', marginTop: '2px'}}>⚡ Latency: {txSpeed}</div>}
            </div>
          </div>

          {/* Secure QUIC Payment Call-to-Action */}
          <button 
            className="quic-trigger-btn" 
            onClick={executeSecureQuicPayment}
            disabled={isQuicExecuting}
          >
            {isQuicExecuting ? '⚡ EXECUTING QUIC PIPELINE...' : '🚀 EXECUTE SECURE QUIC PAYMENT'}
          </button>
          {quicExecutionBanner && (
            <div style={{fontSize: '0.74rem', padding: '6px 10px', background: 'rgba(0, 242, 254, 0.08)', border: '1px solid rgba(0, 242, 254, 0.2)', borderRadius: '6px', color: 'var(--text-light)', fontFamily: 'JetBrains Mono'}}>
              {quicExecutionBanner}
            </div>
          )}
        </section>

        {/* ============================================================== */}
        {/* COLUMN 2: SECURE QUIC PAYMENT PIPELINE (Center Panel)          */}
        {/* ============================================================== */}
        <section className="dashboard-panel">
          <div className="panel-header">
            <div>
              <div className="panel-title">🛡️ Secure QUIC Payment Pipeline</div>
              <div className="panel-subtitle">Live Cryptographic & AI Engine Telemetry</div>
            </div>
            <span className="panel-tag quic-tag">Live QUIC Feed</span>
          </div>

          <div className="quic-pipeline-container">
            {/* Stage 1: QUIC Connection */}
            <div className={`quic-stage-card status-${quicPipeline.quicConnection.status}`}>
              <div className="stage-card-header">
                <div className="stage-title-wrap">
                  <div className="stage-index-badge">1</div>
                  <div className="stage-name">QUIC Connection Handshake</div>
                </div>
                <span className={`stage-status-badge ${quicPipeline.quicConnection.status.toLowerCase()}`}>
                  {quicPipeline.quicConnection.status}
                </span>
              </div>
              <div className="stage-meta-grid">
                <div className="meta-item"><span className="meta-label">Target:</span><span className="meta-value">{quicPipeline.quicConnection.endpoint}</span></div>
                <div className="meta-item"><span className="meta-label">Protocol:</span><span className="meta-value">{quicPipeline.quicConnection.protocol || 'aioquic UDP'}</span></div>
                {quicPipeline.quicConnection.error && (
                  <div className="meta-item" style={{gridColumn: '1 / -1'}}><span className="meta-label">Error:</span><span className="meta-value highlight-red">{quicPipeline.quicConnection.error}</span></div>
                )}
              </div>
            </div>

            {/* Stage 2: mTLS Certificate Verification */}
            <div className={`quic-stage-card status-${quicPipeline.mtls.status}`}>
              <div className="stage-card-header">
                <div className="stage-title-wrap">
                  <div className="stage-index-badge">2</div>
                  <div className="stage-name">mTLS Certificate Verification</div>
                </div>
                <span className={`stage-status-badge ${quicPipeline.mtls.status.toLowerCase()}`}>
                  {quicPipeline.mtls.status}
                </span>
              </div>
              <div className="stage-meta-grid">
                <div className="meta-item"><span className="meta-label">Client Cert:</span><span className="meta-value">{quicPipeline.mtls.clientCert}</span></div>
                <div className="meta-item"><span className="meta-label">Cipher:</span><span className="meta-value">{quicPipeline.mtls.cipher}</span></div>
              </div>
            </div>

            {/* Stage 3: PQC Key Exchange */}
            <div className={`quic-stage-card status-${quicPipeline.pqcKeyExchange.status}`}>
              <div className="stage-card-header">
                <div className="stage-title-wrap">
                  <div className="stage-index-badge">3</div>
                  <div className="stage-name">PQC Key Exchange</div>
                </div>
                <span className={`stage-status-badge ${quicPipeline.pqcKeyExchange.status.toLowerCase()}`}>
                  {quicPipeline.pqcKeyExchange.status}
                </span>
              </div>
              <div className="stage-meta-grid">
                <div className="meta-item"><span className="meta-label">Algorithm:</span><span className="meta-value highlight-cyan">{quicPipeline.pqcKeyExchange.algorithm}</span></div>
                <div className="meta-item"><span className="meta-label">Exchange:</span><span className="meta-value">{quicPipeline.pqcKeyExchange.step}</span></div>
              </div>
            </div>

            {/* Stage 4: Session Established */}
            <div className={`quic-stage-card status-${quicPipeline.pqcSession.status}`}>
              <div className="stage-card-header">
                <div className="stage-title-wrap">
                  <div className="stage-index-badge">4</div>
                  <div className="stage-name">PQC Session Established</div>
                </div>
                <span className={`stage-status-badge ${quicPipeline.pqcSession.status.toLowerCase()}`}>
                  {quicPipeline.pqcSession.status}
                </span>
              </div>
              <div className="stage-meta-grid">
                <div className="meta-item" style={{gridColumn: '1 / -1'}}>
                  <span className="meta-label">Session ID:</span>
                  <span className="meta-value highlight-cyan">
                    {quicPipeline.pqcSession.session_id || 'WAITING FOR BACKEND EVENT'}
                  </span>
                </div>
              </div>
            </div>

            {/* Stage 5: Behavioral AI Analysis */}
            <div className={`quic-stage-card status-${quicPipeline.behavioralAi.status}`}>
              <div className="stage-card-header">
                <div className="stage-title-wrap">
                  <div className="stage-index-badge">5</div>
                  <div className="stage-name">Behavioral AI Analysis</div>
                </div>
                <span className={`stage-status-badge ${quicPipeline.behavioralAi.status.toLowerCase()}`}>
                  {quicPipeline.behavioralAi.status}
                </span>
              </div>
              <div className="stage-meta-grid">
                <div className="meta-item"><span className="meta-label">Model:</span><span className="meta-value">{quicPipeline.behavioralAi.model}</span></div>
                <div className="meta-item">
                  <span className="meta-label">MAE Error:</span>
                  <span className={`meta-value ${quicPipeline.behavioralAi.is_anomaly ? 'highlight-red' : 'highlight-green'}`}>
                    {quicPipeline.behavioralAi.mae_error !== null ? quicPipeline.behavioralAi.mae_error : 'WAITING FOR BACKEND EVENT'}
                  </span>
                </div>
                <div className="meta-item">
                  <span className="meta-label">Threshold:</span>
                  <span className="meta-value">
                    {quicPipeline.behavioralAi.threshold !== null ? quicPipeline.behavioralAi.threshold : 'WAITING FOR BACKEND EVENT'}
                  </span>
                </div>
                <div className="meta-item">
                  <span className="meta-label">Verdict:</span>
                  <span className="meta-value">
                    {quicPipeline.behavioralAi.is_anomaly === true ? '🚨 ANOMALY BLOCKED' : (quicPipeline.behavioralAi.is_anomaly === false ? '✅ NORMAL CONTEXT' : 'WAITING')}
                  </span>
                </div>
              </div>
            </div>

            {/* Stage 6: TOTP Session Verification */}
            <div className={`quic-stage-card status-${quicPipeline.totp.status}`}>
              <div className="stage-card-header">
                <div className="stage-title-wrap">
                  <div className="stage-index-badge">6</div>
                  <div className="stage-name">TOTP Session Verification</div>
                </div>
                <span className={`stage-status-badge ${quicPipeline.totp.status.toLowerCase()}`}>
                  {quicPipeline.totp.status}
                </span>
              </div>
              <div className="stage-meta-grid">
                <div className="meta-item">
                  <span className="meta-label">TOTP Status:</span>
                  <span className={`meta-value ${quicPipeline.totp.status === 'SUCCESS' ? 'highlight-green' : (quicPipeline.totp.status === 'FAILED' ? 'highlight-red' : '')}`}>
                    {quicPipeline.totp.validation_status || 'WAITING FOR BACKEND EVENT'}
                  </span>
                </div>
                <div className="meta-item"><span className="meta-label">Window Tolerance:</span><span className="meta-value">±{quicPipeline.totp.window_tolerance}</span></div>
              </div>
            </div>

            {/* Stage 7: Zero-Knowledge Proof (ZKP) */}
            <div className={`quic-stage-card status-${quicPipeline.zkp.status}`}>
              <div className="stage-card-header">
                <div className="stage-title-wrap">
                  <div className="stage-index-badge">7</div>
                  <div className="stage-name">ZKP Balance Verification (Groth16)</div>
                </div>
                <span className={`stage-status-badge ${quicPipeline.zkp.status.toLowerCase()}`}>
                  {quicPipeline.zkp.status}
                </span>
              </div>
              <div className="stage-meta-grid">
                <div className="meta-item"><span className="meta-label">Prover:</span><span className="meta-value">{quicPipeline.zkp.proof_system}</span></div>
                <div className="meta-item">
                  <span className="meta-label">Funds Proven:</span>
                  <span className={`meta-value ${quicPipeline.zkp.funds_proven === true ? 'highlight-green' : (quicPipeline.zkp.funds_proven === false ? 'highlight-red' : '')}`}>
                    {quicPipeline.zkp.funds_proven === true ? 'PROVEN WITHOUT DISCLOSURE' : (quicPipeline.zkp.funds_proven === false ? 'PROOF FAILED' : 'WAITING FOR BACKEND EVENT')}
                  </span>
                </div>
              </div>
            </div>

            {/* Stage 8: Shamir Secret Sharing (MPC) */}
            <div className={`quic-stage-card status-${quicPipeline.shamirMpc.status}`}>
              <div className="stage-card-header">
                <div className="stage-title-wrap">
                  <div className="stage-index-badge">8</div>
                  <div className="stage-name">Shamir Secret Sharing (MPC)</div>
                </div>
                <span className={`stage-status-badge ${quicPipeline.shamirMpc.status.toLowerCase()}`}>
                  {quicPipeline.shamirMpc.status}
                </span>
              </div>
              <div className="stage-meta-grid">
                <div className="meta-item"><span className="meta-label">Threshold:</span><span className="meta-value">{quicPipeline.shamirMpc.threshold_scheme}</span></div>
                <div className="meta-item">
                  <span className="meta-label">Key Recombined:</span>
                  <span className="meta-value">
                    {quicPipeline.shamirMpc.key_matched === true ? 'RECONSTRUCTED (2-OF-3)' : (quicPipeline.shamirMpc.key_matched === false ? 'FAILED' : 'WAITING FOR BACKEND EVENT')}
                  </span>
                </div>
              </div>
            </div>

            {/* Stage 9: AES-256-GCM Encryption */}
            <div className={`quic-stage-card status-${quicPipeline.aesGcm.status}`}>
              <div className="stage-card-header">
                <div className="stage-title-wrap">
                  <div className="stage-index-badge">9</div>
                  <div className="stage-name">AES-256-GCM Encryption / Decryption</div>
                </div>
                <span className={`stage-status-badge ${quicPipeline.aesGcm.status.toLowerCase()}`}>
                  {quicPipeline.aesGcm.status}
                </span>
              </div>
              <div className="stage-meta-grid">
                <div className="meta-item"><span className="meta-label">Cipher:</span><span className="meta-value highlight-cyan">{quicPipeline.aesGcm.cipher}</span></div>
                <div className="meta-item"><span className="meta-label">Spec:</span><span className="meta-value">{quicPipeline.aesGcm.iv_length}</span></div>
              </div>
            </div>

            {/* Stage 10: Payment Transmission & ACK */}
            <div className={`quic-stage-card status-${quicPipeline.paymentAck.status}`}>
              <div className="stage-card-header">
                <div className="stage-title-wrap">
                  <div className="stage-index-badge">10</div>
                  <div className="stage-name">Secure Transmission & Payment ACK</div>
                </div>
                <span className={`stage-status-badge ${quicPipeline.paymentAck.status.toLowerCase()}`}>
                  {quicPipeline.paymentAck.status}
                </span>
              </div>
              <div className="stage-meta-grid">
                <div className="meta-item">
                  <span className="meta-label">Tx Hash:</span>
                  <span className="meta-value highlight-cyan">
                    {quicPipeline.paymentAck.tx_hash ? `${quicPipeline.paymentAck.tx_hash.substring(0, 16)}...` : 'WAITING FOR BACKEND EVENT'}
                  </span>
                </div>
                <div className="meta-item">
                  <span className="meta-label">ACK:</span>
                  <span className={`meta-value ${quicPipeline.paymentAck.status === 'SUCCESS' ? 'highlight-green' : ''}`}>
                    {quicPipeline.paymentAck.ack_raw || 'WAITING FOR BACKEND EVENT'}
                  </span>
                </div>
              </div>
            </div>

            {/* Stage 11: MongoDB Ledger Update */}
            <div className={`quic-stage-card status-${quicPipeline.mongoUpdate.status}`}>
              <div className="stage-card-header">
                <div className="stage-title-wrap">
                  <div className="stage-index-badge">11</div>
                  <div className="stage-name">Database Ledger Update (MongoDB)</div>
                </div>
                <span className={`stage-status-badge ${quicPipeline.mongoUpdate.status.toLowerCase()}`}>
                  {quicPipeline.mongoUpdate.status}
                </span>
              </div>
              <div className="stage-meta-grid">
                <div className="meta-item"><span className="meta-label">Database:</span><span className="meta-value">MongoDB (Collection: transactions)</span></div>
                <div className="meta-item">
                  <span className="meta-label">Commit Status:</span>
                  <span className={`meta-value ${quicPipeline.mongoUpdate.status === 'SUCCESS' ? 'highlight-green' : ''}`}>
                    {quicPipeline.mongoUpdate.db_status || 'WAITING FOR BACKEND EVENT'}
                  </span>
                </div>
              </div>
            </div>

            {/* Stage 12: Blockchain Immutable Audit */}
            <div className={`quic-stage-card status-${quicPipeline.blockchainAudit.status}`}>
              <div className="stage-card-header">
                <div className="stage-title-wrap">
                  <div className="stage-index-badge">12</div>
                  <div className="stage-name">Blockchain Audit Logging</div>
                </div>
                <span className={`stage-status-badge ${quicPipeline.blockchainAudit.status.toLowerCase()}`}>
                  {quicPipeline.blockchainAudit.status}
                </span>
              </div>
              <div className="stage-meta-grid">
                <div className="meta-item"><span className="meta-label">Smart Contract:</span><span className="meta-value highlight-cyan">{quicPipeline.blockchainAudit.smart_contract}</span></div>
                <div className="meta-item">
                  <span className="meta-label">Ledger State:</span>
                  <span className={`meta-value ${quicPipeline.blockchainAudit.status === 'SUCCESS' ? 'highlight-green' : ''}`}>
                    {quicPipeline.blockchainAudit.status_on_chain || 'WAITING FOR BACKEND EVENT'}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* ============================================================== */}
        {/* COLUMN 3: SETTLEMENT & SECURITY LEDGER (Right Panel)           */}
        {/* ============================================================== */}
        <section className="dashboard-panel">
          <div className="panel-header">
            <div>
              <div className="panel-title">📑 Transaction & Audit Ledger</div>
              <div className="panel-subtitle">Audited Records (MongoDB & Blockchain)</div>
            </div>
            <button className="clear-log-btn" onClick={fetchCloudData}>↻ Refresh</button>
          </div>

          {/* Merchant POS Widget (If in merchant mode or split view) */}
          <div className="merchant-pos-box">
            <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}>
              <span className="pos-revenue-label">🏪 Store #9942-A (Receiver)</span>
              <span style={{fontSize: '0.75rem', color: 'var(--text-dim)'}}>POS Terminal 01</span>
            </div>
            <div className="pos-revenue-val">${receiverBalance.toFixed(2)}</div>
            
            {receiverStatus === 'waiting' ? (
              <div className="nfc-radar-zone" onClick={activateNfcScanner}>
                <div className="pulsing-dot"></div>
                <div style={{fontSize: '0.8rem', color: 'var(--text-light)', fontWeight: 600}}>POS Listening Active</div>
                <div style={{fontSize: '0.72rem', color: 'var(--text-dim)'}}>Tap here to enable Web NFC scanner or broadcast via Socket</div>
              </div>
            ) : (
              <div className="incoming-banner">
                <div style={{fontSize: '1.2rem', fontWeight: 800}}>+${receiverReceivedAmount.toFixed(2)}</div>
                <div style={{fontSize: '0.75rem'}}>Payment Credited & Settled to Ledger</div>
              </div>
            )}
          </div>

          {/* Blockchain Explorer Card */}
          <div className="blockchain-explorer-card">
            <div className="explorer-header">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/></svg>
              <span>Web3 Immutable Blockchain Status</span>
            </div>
            <div style={{fontSize: '0.74rem', fontFamily: 'JetBrains Mono', color: 'var(--text-dim)'}}>
              <div>• Contract: AuditTrail.sol</div>
              <div>• Network: Local EVM Test Ledger</div>
              <div>• Audit Proof: SHA-256 Hash Anchoring</div>
            </div>
          </div>

          {/* MongoDB Transaction Stream */}
          <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '6px'}}>
            <span style={{fontSize: '0.78rem', color: 'var(--text-dim)', textTransform: 'uppercase', fontWeight: 600}}>
              {role === 'receiver' ? 'Merchant Audit Stream' : 'Customer Transaction Stream'}
            </span>
            <span style={{fontSize: '0.72rem', color: 'var(--primary-color)', fontFamily: 'JetBrains Mono'}}>
              {(role === 'receiver' ? receiverTransactions : transactions).length} Records
            </span>
          </div>

          <div className="ledger-stream">
            {(role === 'receiver' ? receiverTransactions : transactions).length === 0 ? (
              <div style={{textAlign: 'center', padding: '30px 10px', color: 'var(--text-dim)', fontSize: '0.8rem'}}>
                No ledger transactions recorded yet.
              </div>
            ) : (
              (role === 'receiver' ? receiverTransactions : transactions).map((tx) => (
                <div className="ledger-item" key={tx.id}>
                  <div className="ledger-item-left">
                    <span className="ledger-item-title">{tx.title}</span>
                    <span className="ledger-item-hash">{tx.hash}</span>
                  </div>
                  <span className={`ledger-item-amount ${tx.amount.startsWith('+') ? 'positive' : 'negative'}`}>
                    {tx.amount}
                  </span>
                </div>
              ))
            )}
          </div>
        </section>
      </main>

      {/* ============================================================== */}
      {/* BOTTOM PANEL: LIVE SYSTEM TELEMETRY EVENT TERMINAL             */}
      {/* ============================================================== */}
      <footer className="telemetry-terminal-panel">
        <div className="terminal-header">
          <div className="terminal-title">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="4 17 10 11 4 5"/><line x1="12" y1="19" x2="20" y2="19"/></svg>
            <span>LIVE SYSTEM TELEMETRY STREAM (REAL BACKEND EVENTS)</span>
          </div>
          <div className="terminal-actions">
            <span style={{fontSize: '0.72rem', color: 'var(--text-dim)', fontFamily: 'JetBrains Mono'}}>
              {quicLogs.length} events
            </span>
            <button className="clear-log-btn" onClick={clearLog}>Clear Terminal</button>
          </div>
        </div>

        <div className="terminal-log-stream">
          {quicLogs.length === 0 ? (
            <div style={{color: 'var(--text-dim)', fontStyle: 'italic'}}>
              Terminal standby. Awaiting live QUIC / Cryptographic events from backend...
            </div>
          ) : (
            quicLogs.map((log) => (
              <div className="log-entry" key={log.id}>
                <span className="log-time">[{log.time}]</span>
                <span className={`log-tag tag-${log.stage}`}>[{log.stage}]</span>
                <span className="log-msg">
                  status={log.status} {Object.keys(log.details).length > 0 ? JSON.stringify(log.details) : ''}
                </span>
              </div>
            ))
          )}
          <div ref={terminalEndRef} />
        </div>
      </footer>
    </div>
  );
}

export default App;
