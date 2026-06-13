from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from utils.db import UserProfile, TransactionRecord, get_user, create_user, update_balance, log_transaction, db
import uvicorn
import os
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

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
