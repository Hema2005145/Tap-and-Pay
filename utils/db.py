import os
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field
from typing import Optional
import datetime
from dotenv import load_dotenv
import urllib.parse

# Load environment variables
load_dotenv()

MONGO_URL = os.getenv("MONGODB_ATLAS_URI")
DB_NAME = os.getenv("DB_NAME", "qsp3_payment")

client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

# --- SCHEMAS ---

class UserProfile(BaseModel):
    client_id: int = Field(..., example=109)
    name: str
    balance_cents: int = Field(default=0)
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)

class TransactionRecord(BaseModel):
    tx_hash: str
    client_id: int
    amount_cents: int
    status: str # "APPROVED", "FLAGGED", "BLOCKED"
    timestamp: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)

# --- DATABASE OPERATIONS ---

# Local Balance Cache (Priority 13: Hot Storage)
balance_cache = {}

async def get_user(client_id: int):
    return await db.users.find_one({"client_id": client_id})

async def get_balance_optimized(client_id: int):
    """
    Optimized Fetch: Uses MongoDB Projections to only fetch the balance field.
    Also checks local cache first.
    """
    if client_id in balance_cache:
        # Check if cache is older than 5 seconds
        cached_val, timestamp = balance_cache[client_id]
        if (datetime.datetime.now() - timestamp).total_seconds() < 5:
            print(f"DB [Cache]: Hit for Client {client_id}. Serving from RAM.")
            return cached_val

    # Projection: 1 means include, 0 means exclude
    user = await db.users.find_one({"client_id": client_id}, {"balance_cents": 1, "_id": 0})
    if user:
        balance = user.get("balance_cents", 0)
        balance_cache[client_id] = (balance, datetime.datetime.now())
        return balance
    return None

async def create_user(user: UserProfile):
    # Using model_dump() for Pydantic V2 compatibility
    user_data = user.model_dump() if hasattr(user, "model_dump") else user.dict()
    await db.users.insert_one(user_data)
    return user

async def update_balance(client_id: int, amount_change_cents: int):
    # Atomic update to prevent race conditions
    result = await db.users.update_one(
        {"client_id": client_id},
        {"$inc": {"balance_cents": amount_change_cents}}
    )
    return result.modified_count > 0

async def log_transaction(tx: TransactionRecord):
    tx_data = tx.model_dump() if hasattr(tx, "model_dump") else tx.dict()
    await db.transactions.insert_one(tx_data)
