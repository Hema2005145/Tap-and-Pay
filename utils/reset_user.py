import asyncio
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from utils.db import update_balance, db

async def reset():
    # Set balance directly to $500.00
    await db.users.update_one({"client_id": 109}, {"$set": {"balance_cents": 50000}})
    # Clear transactions
    await db.transactions.delete_many({"client_id": 109})
    print("User 109 reset to $500.00 and history cleared.")

if __name__ == "__main__":
    asyncio.run(reset())
