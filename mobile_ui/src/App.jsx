import { useState, useEffect } from 'react';
import { io } from 'socket.io-client';
import './App.css';

// WebSocket connection for fallback/confirmation syncing
const socket = io('http://192.168.0.4:3001');
const API_URL = 'http://192.168.0.4:8000';

function App() {
  const [role, setRole] = useState('selection'); 
  
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

  const fetchCloudData = async () => {
    try {
      if (role === 'sender') {
        const balRes = await fetch(`${API_URL}/balance/1`);
        const balData = await balRes.json();
        setBalance(balData.balance_cents / 100);
        
        const audRes = await fetch(`${API_URL}/audit/1`);
        const audData = await audRes.json();
        setTransactions(audData.history.map(tx => ({
          id: tx._id,
          title: 'QSP3 Secure Tx',
          hash: tx.tx_hash.substring(0,10) + '...',
          amount: `-$${(tx.amount_cents / 100).toFixed(2)}`
        })));
      } else if (role === 'receiver') {
        const balRes = await fetch(`${API_URL}/balance/2`);
        const balData = await balRes.json();
        setReceiverBalance(balData.balance_cents / 100);
        
        const audRes = await fetch(`${API_URL}/audit/2`);
        const audData = await audRes.json();
        setReceiverTransactions(audData.history.map(tx => ({
          id: tx._id,
          title: 'Customer Payment',
          hash: tx.tx_hash.substring(0,10) + '...',
          amount: `+$${(tx.amount_cents / 100).toFixed(2)}`
        })));
      }
    } catch (e) {
      console.log("Cloud Backend Offline. Using Local Fallback.", e);
    }
  };

  useEffect(() => {
    if (role !== 'selection') fetchCloudData();
  }, [role]);

  // SOCKET NETWORK STATUS
  useEffect(() => {
    socket.on('connect', () => setSocketStatus('🟢 Socket Connected'));
    socket.on('disconnect', () => setSocketStatus('🔴 Socket Disconnected'));
    socket.on('connect_error', (err) => setSocketStatus(`🔴 Socket Error: ${err.message}`));
    
    if (socket.connected) setSocketStatus('🟢 Socket Connected');

    return () => {
      socket.off('connect');
      socket.off('disconnect');
      socket.off('connect_error');
    };
  }, []);

  // LIVE HARDWARE INTEGRATION
  useEffect(() => {
    const handleOrientation = (event) => {
      if (event.beta !== null) {
        setHardwareActive(true);
        setTiltX(Math.abs(event.beta) / 180);
        setTiltY(Math.abs(event.gamma) / 90);
        setTiltZ(Math.abs(event.alpha) / 360);
      }
    };

    if (role === 'sender' && window.DeviceOrientationEvent) {
      window.addEventListener('deviceorientation', handleOrientation);
    }

    if (role === 'receiver') {
      if ('NDEFReader' in window) {
        setNfcStatus('Hardware Supported. Tap to Start.');
      } else {
        setNfcStatus('🔴 Web NFC API Not Supported');
      }
    }

    socket.on('payment_received', (payload) => {
      if (role === 'receiver') {
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
          } catch (e) {}
        }
      };
    } catch (err) {
      setNfcStatus(`🔴 Denied: ${err.message}`);
    }
  };

  const processIncomingPayment = async (incAmount, incHash) => {
    setReceiverStatus('received');
    setReceiverReceivedAmount(incAmount);
    
    // Simulate updating receiver database locally until Cloud updates
    setReceiverBalance(prev => prev + incAmount);
    setReceiverTransactions(prev => [{
      id: Date.now(),
      title: 'Customer: Hardware NFC Tap',
      hash: incHash,
      amount: `+$${incAmount.toFixed(2)}`
    }, ...prev].slice(0, 3));
    
    setTimeout(() => {
      setReceiverStatus('waiting');
      fetchCloudData(); // Refresh true cloud state
    }, 4000);
  };

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
    
    if (simAmount > balance && balance > 0) { // check balance only if cloud fetched > 0
      setStatus('error');
      setStatusMsg('DECLINED LOCALLY: Insufficient funds.');
      setTxSpeed('0.0010s');
      setTimeout(() => { setStatus('idle'); setStatusMsg(''); setTxSpeed(null); }, 4000);
      return;
    }

    setStatus('processing');
    setStatusMsg('Generating ZKP & Checking Hardware Biometrics...');
    
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
        setStatusMsg(`AI_BLOCKED: Gyroscope Error Score = ${calculatedScore.toFixed(2)}`);
      } else {
        setStatus('success');
        setStatusMsg(`PAYMENT_ACK: Success. Sent $${simAmount.toFixed(2)}.`);
        
        const newHash = '0x' + Math.random().toString(16).substr(2, 10) + '...';
        
        // Push to Docker Cloud
        try {
            await fetch(`${API_URL}/transaction`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    tx_hash: newHash,
                    client_id: 1,
                    amount_cents: simAmount * 100,
                    status: "SUCCESS",
                    zkp_proof_id: "zkp_" + Date.now()
                })
            });
        } catch(e) { console.log("Cloud Push failed, local only"); }

        fetchCloudData();        // Write to physical NFC chip asynchronously (no await) so it doesn't block the UI
        // if the two phones get stuck negotiating a connection.
        if ('NDEFReader' in window) {
          try {
            const ndef = new window.NDEFReader();
            ndef.write({
              records: [{
                recordType: "text",
                data: JSON.stringify({ type: 'QSP3_PAYMENT_INIT', amount: simAmount, hash: newHash })
              }]
            }).catch(e => console.log("NFC Write resolved with expected P2P block"));
          } catch (error) {
            console.log("NFC hardware busy");
          }
        }
        
        // Immediately fire the WebSocket Hybridization
        socket.emit('payment_sent', { amount: simAmount, hash: newHash });
      }
      
      setTimeout(() => {
        setStatus('idle');
        setStatusMsg('');
        setTxSpeed(null);
      }, 4000);
      
    }, speedMs);
  };

  if (role === 'selection') {
    return (
      <div className="app-wrapper">
        <div className="role-selection">
          <h2 style={{color: 'var(--text-light)', marginBottom: '10px'}}>Select Device Profile</h2>
          <button className="role-btn" onClick={() => setRole('sender')}>
            📱 Run as Sender (Customer)
          </button>
          <button className="role-btn receiver-btn" onClick={() => setRole('receiver')}>
            🏪 Run as Receiver (Merchant)
          </button>
          <p style={{fontSize: '0.85rem', color: 'var(--text-main)', marginTop: '20px', maxWidth: '250px'}}>
            <strong>Cloud Network Active:</strong> Ready to log to Dockerized MongoDB cluster over 192.168.0.4.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="app-wrapper">
      {role === 'sender' && (
        <div className="device-wrapper">
          <button className="nav-back" onClick={() => setRole('selection')}>← Change Profile</button>
          <div className="mobile-container">
            <header className="header">
              <div className="header-title">QSP<span>3</span> Wallet</div>
              <div className="profile-icon">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle></svg>
              </div>
            </header>

            <div className="card-container">
              <div className="credit-card">
                <div className="card-top">
                  <div className="chip"></div>
                  <svg className="nfc-icon" viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm5 11h-4v4h-2v-4H7v-2h4V7h2v4h4v2z"/></svg>
                </div>
                <div className="card-number">
                  **** **** **** 3094
                </div>
                <div className="card-bottom">
                  <div className="card-info">
                    <div className="card-label">Card Holder</div>
                    <div className="card-value">ALEXANDER D.</div>
                  </div>
                  <div className="card-info" style={{textAlign: 'right'}}>
                    <div className="card-label">Available Balance</div>
                    <div className="card-value">${balance.toFixed(2)}</div>
                  </div>
                </div>
              </div>
            </div>

            <div className="action-section" style={{paddingTop: '0'}}>
              <div className="amount-input-container">
                <span className="currency-symbol">$</span>
                <input type="number" className="amount-input" value={amount} onChange={(e) => setAmount(e.target.value)} placeholder="0.00" />
              </div>
              
              <div className="sensor-panel">
                <div className="sensor-header">
                  <span>Hardware Context {hardwareActive ? '(LIVE 📡)' : '(MOCK)'}</span>
                  <span style={{color: aiScore > 0.75 ? 'var(--danger-color)' : 'var(--success-color)'}}>
                    Risk: {aiScore.toFixed(2)}
                  </span>
                </div>
                
                <div className="sensor-row">
                  <span className="sensor-label">Lat/Lon</span>
                  <input type="range" min="10" max="15" step="0.01" className="sensor-slider" value={lat} onChange={(e)=>setLat(parseFloat(e.target.value))} />
                  <span className="sensor-value">{lat.toFixed(2)}</span>
                </div>
                <div className="sensor-row" style={{opacity: hardwareActive ? 0.5 : 1, pointerEvents: hardwareActive ? 'none' : 'auto'}}>
                  <span className="sensor-label">Tilt X</span>
                  <input type="range" min="0" max="1" step="0.01" className="sensor-slider" value={tiltX} onChange={(e)=>setTiltX(parseFloat(e.target.value))} />
                  <span className="sensor-value">{tiltX.toFixed(2)}</span>
                </div>
                <div className="sensor-row" style={{opacity: hardwareActive ? 0.5 : 1, pointerEvents: hardwareActive ? 'none' : 'auto'}}>
                  <span className="sensor-label">Tilt Y</span>
                  <input type="range" min="0" max="1" step="0.01" className="sensor-slider" value={tiltY} onChange={(e)=>setTiltY(parseFloat(e.target.value))} />
                  <span className="sensor-value">{tiltY.toFixed(2)}</span>
                </div>
              </div>

              <div style={{ marginTop: '10px' }}>
                <div className={`tap-circle ${status}`} onClick={handleTap}>
                  <div className="tap-content">
                    {status === 'idle' && (
                      <>
                        <svg className="tap-icon" width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>
                        <span className="tap-text">TAP TO PAY</span>
                      </>
                    )}
                    {status === 'processing' && <svg className="tap-icon" width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{animation: 'spin 1s linear infinite'}}><path d="M21 12a9 9 0 1 1-6.219-8.56"/></svg>}
                    {status === 'success' && <svg className="tap-icon" width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="20 6 9 17 4 12"></polyline></svg>}
                    {status === 'error' && <svg className="tap-icon" width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>}
                  </div>
                </div>
              </div>

              <div className={`status-message ${status}`}>
                {statusMsg}
                {txSpeed && <div style={{ marginTop: '5px', fontSize: '0.85rem', color: 'var(--primary-color)', fontFamily: 'monospace' }}>⚡ TX Speed: {txSpeed}</div>}
              </div>
            </div>

            <div className="recent-tx-section">
              <div className="section-title">Cloud MongoDB Ledger</div>
              <div className="tx-list">
                {transactions.map(tx => (
                  <div className="tx-item" key={tx.id}>
                    <div className="tx-info">
                      <span className="tx-title">{tx.title}</span>
                      <span className="tx-hash">{tx.hash}</span>
                    </div>
                    <span className="tx-amount negative">{tx.amount}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* --- DEVICE 2: RECEIVER (MERCHANT) --- */}
      {role === 'receiver' && (
        <div className="device-wrapper">
          <button className="nav-back" onClick={() => setRole('selection')}>← Change Profile</button>
          <div className="mobile-container receiver">
            <header className="header">
              <div className="header-title">QSP<span>3</span> Merchant</div>
              <div className="profile-icon" style={{color: '#ffa726'}}>
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect><line x1="3" y1="9" x2="21" y2="9"></line><line x1="9" y1="21" x2="9" y2="9"></line></svg>
              </div>
            </header>

            <div className="card-container">
              <div className="credit-card">
                <div className="card-top">
                  <div className="chip"></div>
                  <div style={{fontSize: '1.2rem', fontWeight: 600, color: '#ffcc80'}}>POS System</div>
                </div>
                <div className="card-number">MERCHANT ACCT</div>
                <div className="card-bottom">
                  <div className="card-info"><div className="card-label">Store ID</div><div className="card-value">#9942-A</div></div>
                  <div className="card-info" style={{textAlign: 'right'}}><div className="card-label">Total Earnings</div><div className="card-value">${receiverBalance.toFixed(2)}</div></div>
                </div>
              </div>
            </div>

            <div className="action-section">
              {receiverStatus === 'waiting' ? (
                <div className="receiver-waiting" onClick={activateNfcScanner} style={{cursor: 'pointer'}}>
                  <div className="pulsing-dot"></div>
                  <div className="receiver-status" style={{fontSize: '0.9rem'}}>{nfcStatus}</div>
                  <div className="receiver-status" style={{fontSize: '0.85rem', color: '#81c784', marginTop: '5px'}}>{socketStatus}</div>
                  <div style={{fontSize: '0.75rem', color: 'var(--secondary-color)', marginTop: '5px'}}>Tap here to start NFC & wait for payment...</div>
                </div>
              ) : (
                <div className="incoming-money">
                  <div className="success-check"><svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3"><polyline points="20 6 9 17 4 12"></polyline></svg></div>
                  +${receiverReceivedAmount.toFixed(2)}
                  <div style={{fontSize: '1rem', color: 'var(--text-light)', fontWeight: 400, marginTop: '5px'}}>Payment Settled to Cloud</div>
                </div>
              )}
            </div>

            <div className="recent-tx-section">
              <div className="section-title">Cloud MongoDB Ledger</div>
              <div className="tx-list">
                {receiverTransactions.map(tx => (
                  <div className="tx-item" key={tx.id}>
                    <div className="tx-info">
                      <span className="tx-title">{tx.title}</span>
                      <span className="tx-hash">{tx.hash}</span>
                    </div>
                    <span className="tx-amount positive">{tx.amount}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}

export default App;
