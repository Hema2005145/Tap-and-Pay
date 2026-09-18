from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from utils.db import UserProfile, TransactionRecord, get_user, create_user, update_balance, log_transaction, settle_payment_atomic, db
import uvicorn
import os
import datetime
from blockchain.web3_integration import log_to_blockchain

app = FastAPI(title="QSP3-Advanced API Gateway")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"status": "QSP3 Gateway Online (MongoDB Atlas Connected)", "version": "1.0.0"}

@app.post("/register")
async def register_user(user: UserProfile):
    existing = await get_user(user.client_id)
    if existing:
        raise HTTPException(status_code=400, detail="User already exists")
    await create_user(user)
    return {"message": f"User {user.client_id} registered successfully"}

@app.get("/balance/{client_id}")
async def check_balance(client_id: int):
    user = await get_user(client_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"client_id": client_id, "balance_str": f"${user['balance_cents'] / 100:.2f}", "balance_cents": user['balance_cents']}

@app.post("/transaction")
async def record_transaction(tx: TransactionRecord):
    sender_id = tx.sender_id if tx.sender_id is not None else tx.client_id
    receiver_id = tx.receiver_id if tx.receiver_id is not None else 2
    success, msg = await settle_payment_atomic(sender_id, receiver_id, tx.amount_cents, tx.tx_hash, tx.status)
    if not success:
        raise HTTPException(status_code=400, detail=msg)
    # Log to Blockchain
    await log_to_blockchain(tx.tx_hash, sender_id, tx.amount_cents, tx.status)
    return {"status": "Transaction settled atomically and balance updated"}

@app.get("/audit/{client_id}")
async def get_audit_trail(client_id: int):
    # Retrieve last 10 transactions where client is either sender or receiver
    cursor = db.transactions.find({
        "$or": [
            {"client_id": client_id},
            {"sender_id": client_id},
            {"receiver_id": client_id}
        ]
    }).sort("timestamp", -1).limit(10)
    history = await cursor.to_list(length=10)
    # Clean up _id for JSON serialization
    for tx in history:
        tx["_id"] = str(tx["_id"])
    return {"client_id": client_id, "history": history}

@app.get("/quic/status")
async def get_quic_status():
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(0.5)
    is_online = False
    try:
        # Check if UDP port 4433 is listening
        s.connect(("127.0.0.1", 4433))
        is_online = True
    except Exception:
        is_online = False
    finally:
        s.close()
    return {"quic_server_online": is_online, "port": 4433, "host": "127.0.0.1"}

@app.post("/quic/execute-payment")
async def execute_quic_payment(req: dict):
    from utils.event_broadcaster import broadcast_quic_event
    try:
        from client.quic_client import PaymentClient, BehavioralAI, QuicConfiguration
        import ssl

        amount_cents = int(req.get("amount_cents", 2500))
        sender_id = int(req.get("sender_id", req.get("client_id", 1)))
        receiver_id = int(req.get("receiver_id", 2))
        lat = float(req.get("lat", 12.9716))
        lon = float(req.get("lon", 77.5946))
        tilt_x = float(req.get("tilt_x", 0.70))
        tilt_y = float(req.get("tilt_y", 0.20))
        tilt_z = float(req.get("tilt_z", 0.90))
        private_balance = req.get("private_balance_cents")
        if private_balance is not None:
            private_balance = int(private_balance)
        else:
            user = await get_user(sender_id)
            private_balance = user["balance_cents"] if user else 50000

        behavior_data = {
            "lat": lat, "lon": lon,
            "tilt_x": tilt_x, "tilt_y": tilt_y, "tilt_z": tilt_z,
            "hour": datetime.datetime.now().hour
        }

        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        cert_dir = os.path.join(project_root, "certs")
        model_dir = os.path.join(project_root, "models")

        configuration = QuicConfiguration(is_client=True, server_name="localhost")
        configuration.verify_mode = ssl.CERT_NONE
        configuration.load_cert_chain(
            os.path.join(cert_dir, "client_cert.pem"),
            os.path.join(cert_dir, "client_key.pem")
        )

        totp_secret = b"QSP3_SHARED_SECRET_KEY"
        try:
            ai_shield = BehavioralAI(model_dir)
        except Exception:
            ai_shield = None

        async with PaymentClient(configuration, totp_secret, cert_dir, ai_shield) as client:
            ack = await client.pay(amount_cents, sender_id, behavior_data, private_balance=private_balance, receiver_id=receiver_id)
            ack_str = ack.decode("utf-8") if isinstance(ack, bytes) else str(ack)
            if "PAYMENT_ERR" in ack_str or "DECLINED" in ack_str or "AI_BLOCKED" in ack_str:
                return {"status": "FAILED", "ack": ack_str}
            return {"status": "SUCCESS", "ack": ack_str}
    except Exception as e:
        err_msg = str(e)
        is_conn_error = any(term in err_msg.lower() for term in ["unreachable", "connection refused", "timeout", "errno 10061"])
        event_status = "OFFLINE" if is_conn_error else "FAILED"
        broadcast_quic_event("QUIC_CONNECTION", event_status, {
            "error": f"QUIC execution error: {err_msg}"
        })
        return {"status": "OFFLINE" if is_conn_error else "FAILED", "error": f"QUIC Server unreachable: {err_msg}" if is_conn_error else f"Payment error: {err_msg}"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

