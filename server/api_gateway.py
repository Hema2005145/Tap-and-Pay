from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from utils.db import UserProfile, TransactionRecord, get_user, create_user, update_balance, log_transaction, db
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
    # Log to MongoDB
    await log_transaction(tx)
    # Update balance atomically
    await update_balance(tx.client_id, -tx.amount_cents)
    # Log to Blockchain
    await log_to_blockchain(tx.tx_hash, tx.client_id, tx.amount_cents, tx.status)
    return {"status": "Transaction logged and balance updated"}

@app.get("/audit/{client_id}")
async def get_audit_trail(client_id: int):
    # Retrieve last 10 transactions
    cursor = db.transactions.find({"client_id": client_id}).sort("timestamp", -1).limit(10)
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
        client_id = int(req.get("client_id", 1))
        lat = float(req.get("lat", 12.9716))
        lon = float(req.get("lon", 77.5946))
        tilt_x = float(req.get("tilt_x", 0.70))
        tilt_y = float(req.get("tilt_y", 0.20))
        tilt_z = float(req.get("tilt_z", 0.90))
        private_balance = req.get("private_balance_cents")
        if private_balance is not None:
            private_balance = int(private_balance)
        else:
            user = await get_user(client_id)
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
            ack = await client.pay(amount_cents, client_id, behavior_data, private_balance=private_balance)
            ack_str = ack.decode("utf-8") if isinstance(ack, bytes) else str(ack)
            return {"status": "SUCCESS", "ack": ack_str}
    except Exception as e:
        broadcast_quic_event("QUIC_CONNECTION", "OFFLINE", {
            "error": f"QUIC Daemon Offline (127.0.0.1:4433 unreachable): {str(e)}"
        })
        return {"status": "OFFLINE", "error": f"QUIC Server unreachable: {str(e)}"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

