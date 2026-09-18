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
    sender_id: Optional[int] = None
    receiver_id: Optional[int] = None
    amount_cents: int
    status: str # "APPROVED", "FLAGGED", "BLOCKED"
    blockchain_hash: Optional[str] = None
    timestamp: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=5, minutes=30))))

# --- DATABASE OPERATIONS ---

# Local Balance Cache (Priority 13: Hot Storage)
balance_cache = {}

async def get_next_tx_id() -> int:
    """
    Returns the next sequential transaction ID using MongoDB's atomic findOneAndUpdate.
    The counter document is stored in the 'counters' collection and persists across restarts.
    Concurrent payments cannot get the same ID due to MongoDB's atomic $inc operation.
    """
    result = await db.counters.find_one_and_update(
        {"_id": "tx_id"},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=True  # Return the document AFTER the update
    )
    return result["seq"]

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
    # Atomic update
    result = await db.users.update_one(
        {"client_id": client_id},
        {"$inc": {"balance_cents": amount_change_cents}}
    )
    if client_id in balance_cache:
        del balance_cache[client_id]
    return result.modified_count > 0

async def log_transaction(tx: TransactionRecord):
    tx_data = tx.model_dump() if hasattr(tx, "model_dump") else tx.dict()
    await db.transactions.insert_one(tx_data)

async def settle_payment_atomic(sender_id: int, receiver_id: int, amount_cents: int, tx_hash: str, status: str = "APPROVED"):
    """
    Genuine MongoDB Multi-Document ACID Transaction:
    Atomically deducts sender and credits receiver within a single database transaction.
    Guarantees that either BOTH balances update or NEITHER updates.
    """
    if amount_cents <= 0:
        return False, "Amount must be strictly positive"

    if sender_id == receiver_id:
        return False, "Self-payment is not allowed. Sender and receiver must be different."

    try:
        async with await client.start_session() as session:
            async with session.start_transaction():
                # 1. Validate sender exists
                sender = await db.users.find_one({"client_id": sender_id}, session=session)
                if not sender:
                    raise ValueError(f"Sender client ID {sender_id} does not exist")

                # 2. Validate receiver exists
                receiver = await db.users.find_one({"client_id": receiver_id}, session=session)
                if not receiver:
                    raise ValueError(f"Receiver client ID {receiver_id} does not exist")

                # 3. Check sender balance
                sender_bal = sender.get("balance_cents", 0)
                if sender_bal < amount_cents:
                    raise ValueError(f"Insufficient funds: Sender {sender_id} has ${sender_bal/100:.2f}, requires ${amount_cents/100:.2f}")

                # 4. Atomic conditional deduction from sender
                deduct_result = await db.users.update_one(
                    {"client_id": sender_id, "balance_cents": {"$gte": amount_cents}},
                    {"$inc": {"balance_cents": -amount_cents}},
                    session=session
                )
                if deduct_result.modified_count == 0:
                    raise ValueError("Concurrent race condition or balance changed during execution")

                # 5. Atomic credit to receiver
                credit_result = await db.users.update_one(
                    {"client_id": receiver_id},
                    {"$inc": {"balance_cents": amount_cents}},
                    session=session
                )
                if credit_result.modified_count == 0:
                    raise ValueError(f"Failed to credit receiver {receiver_id}")

                # 6. Record transaction
                record = TransactionRecord(
                    tx_hash=tx_hash,
                    client_id=sender_id,
                    sender_id=sender_id,
                    receiver_id=receiver_id,
                    amount_cents=amount_cents,
                    status=status
                )
                record_data = record.model_dump() if hasattr(record, "model_dump") else record.dict()
                await db.transactions.insert_one(record_data, session=session)

        # Invalidate RAM cache for both parties after successful commit
        if sender_id in balance_cache: del balance_cache[sender_id]
        if receiver_id in balance_cache: del balance_cache[receiver_id]

        print(f"DB [ACID Settlement]: Successfully transferred ${amount_cents/100:.2f} from Client {sender_id} to Client {receiver_id}.")
        return True, "SUCCESS"

    except Exception as e:
        print(f"DB [ACID Settlement Aborted]: {e}")
        return False, str(e)
