import urllib.request
import json
import threading
import time
import os

RELAY_URL = os.getenv("SOCKET_RELAY_URL", "http://127.0.0.1:3001/emit")

def broadcast_quic_event(stage: str, status: str, details: dict = None):
    """
    Non-blocking broadcast of real QUIC pipeline events to the Node.js / Socket.IO relay.
    - stage: string identifying pipeline stage (e.g. QUIC_CONNECTION, MTLS_VERIFICATION, PQC_KEY_EXCHANGE, etc.)
    - status: status string (e.g. WAITING, PROCESSING, SUCCESS, FAILED, ANOMALY)
    - details: dictionary containing actual technical values (never fabricated)
    """
    safe_details = {}
    if details:
        for k, v in details.items():
            # Security Rule: Never leak raw TOTP tokens, private keys, or shared secrets
            if "totp_token" in k.lower() or "secret" in k.lower() or "private" in k.lower():
                continue
            safe_details[k] = v

    payload = {
        "event": "quic_event",
        "data": {
            "stage": stage,
            "status": status,
            "details": safe_details,
            "timestamp": time.time()
        }
    }
    
    def _send():
        try:
            req = urllib.request.Request(
                RELAY_URL,
                data=json.dumps(payload).encode('utf-8'),
                headers={'Content-Type': 'application/json'}
            )
            with urllib.request.urlopen(req, timeout=1.5) as response:
                pass
        except Exception:
            pass  # Non-fatal if relay is offline
            
    thread = threading.Thread(target=_send, daemon=True)
    thread.start()

