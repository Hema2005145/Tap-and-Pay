import asyncio
import os
import sys
import hashlib

# Ensure project root is in sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from utils.db import db, settle_payment_atomic, get_user, create_user, UserProfile, balance_cache

async def setup_test_users():
    """Initializes clean test accounts."""
    # Sender: Client 100 with $500.00 (50000 cents)
    await db.users.delete_many({"client_id": {"$in": [100, 200, 300]}})
    await db.transactions.delete_many({"$or": [{"sender_id": {"$in": [100, 200, 300]}}, {"receiver_id": {"$in": [100, 200, 300]}}]})
    
    balance_cache.clear()

    await create_user(UserProfile(client_id=100, name="Test Sender", balance_cents=50000))
    # Receiver: Client 200 with $100.00 (10000 cents)
    await create_user(UserProfile(client_id=200, name="Test Receiver", balance_cents=10000))

async def test_successful_transfer():
    print("\n--- TEST 1: Successful Sender -> Receiver Transfer ---")
    await setup_test_users()
    
    sender_before = (await get_user(100))["balance_cents"]
    receiver_before = (await get_user(200))["balance_cents"]
    
    transfer_amount = 7500 # $75.00
    tx_hash = hashlib.sha256(b"tx_success_1").hexdigest()
    
    success, msg = await settle_payment_atomic(100, 200, transfer_amount, tx_hash, "APPROVED")
    assert success is True, f"Expected success but got: {msg}"
    
    sender_after = (await get_user(100))["balance_cents"]
    receiver_after = (await get_user(200))["balance_cents"]
    
    assert sender_after == sender_before - transfer_amount, f"Sender balance mismatch: expected {sender_before - transfer_amount}, got {sender_after}"
    assert receiver_after == receiver_before + transfer_amount, f"Receiver balance mismatch: expected {receiver_before + transfer_amount}, got {receiver_after}"
    print(f"[+] PASS: Sender balance decreased by ${transfer_amount/100:.2f} (now ${sender_after/100:.2f})")
    print(f"[+] PASS: Receiver balance increased by ${transfer_amount/100:.2f} (now ${receiver_after/100:.2f})")

async def test_insufficient_funds():
    print("\n--- TEST 2: Insufficient Sender Funds (No Partial Modification) ---")
    await setup_test_users()
    
    sender_before = (await get_user(100))["balance_cents"]
    receiver_before = (await get_user(200))["balance_cents"]
    
    transfer_amount = 999999 # $9999.99 (exceeds balance)
    tx_hash = hashlib.sha256(b"tx_insufficient_1").hexdigest()
    
    success, msg = await settle_payment_atomic(100, 200, transfer_amount, tx_hash, "APPROVED")
    assert success is False, "Expected failure for insufficient funds"
    assert "Insufficient funds" in msg
    
    sender_after = (await get_user(100))["balance_cents"]
    receiver_after = (await get_user(200))["balance_cents"]
    
    assert sender_after == sender_before, "Sender balance must not change on failure"
    assert receiver_after == receiver_before, "Receiver balance must not change on failure"
    print(f"[+] PASS: Transaction rejected cleanly ({msg})")
    print(f"[+] PASS: Both balances completely untouched (Sender: ${sender_after/100:.2f}, Receiver: ${receiver_after/100:.2f})")

async def test_nonexistent_sender():
    print("\n--- TEST 3: Nonexistent Sender ---")
    await setup_test_users()
    
    receiver_before = (await get_user(200))["balance_cents"]
    tx_hash = hashlib.sha256(b"tx_no_sender").hexdigest()
    
    # Client 999 does not exist
    success, msg = await settle_payment_atomic(999, 200, 2500, tx_hash, "APPROVED")
    assert success is False, "Expected failure for nonexistent sender"
    
    receiver_after = (await get_user(200))["balance_cents"]
    assert receiver_after == receiver_before, "Receiver balance must not change"
    print(f"[+] PASS: Nonexistent sender rejected cleanly ({msg})")

async def test_nonexistent_receiver():
    print("\n--- TEST 4: Nonexistent Receiver ---")
    await setup_test_users()
    
    sender_before = (await get_user(100))["balance_cents"]
    tx_hash = hashlib.sha256(b"tx_no_receiver").hexdigest()
    
    # Client 888 does not exist
    success, msg = await settle_payment_atomic(100, 888, 2500, tx_hash, "APPROVED")
    assert success is False, "Expected failure for nonexistent receiver"
    
    sender_after = (await get_user(100))["balance_cents"]
    assert sender_after == sender_before, "Sender balance must not change"
    print(f"[+] PASS: Nonexistent receiver rejected cleanly ({msg})")

async def test_audit_visibility():
    print("\n--- TEST 5: Dual-Party Audit Visibility ---")
    await setup_test_users()
    
    tx_hash = hashlib.sha256(b"tx_audit_dual_1").hexdigest()
    await settle_payment_atomic(100, 200, 3000, tx_hash, "APPROVED")
    
    # Check sender query
    sender_txs = await db.transactions.find({
        "$or": [{"client_id": 100}, {"sender_id": 100}, {"receiver_id": 100}]
    }).to_list(10)
    assert any(tx["tx_hash"] == tx_hash for tx in sender_txs), "Sender audit trail missing transaction"
    
    # Check receiver query
    receiver_txs = await db.transactions.find({
        "$or": [{"client_id": 200}, {"sender_id": 200}, {"receiver_id": 200}]
    }).to_list(10)
    assert any(tx["tx_hash"] == tx_hash for tx in receiver_txs), "Receiver audit trail missing transaction"
    
    print("[+] PASS: Transaction visible in both Sender and Receiver audit trails!")

async def main():
    print("==================================================")
    print("PHASE 2: MULTI-USER ACID SETTLEMENT TEST SUITE")
    print("==================================================")
    
    await test_successful_transfer()
    await test_insufficient_funds()
    await test_nonexistent_sender()
    await test_nonexistent_receiver()
    await test_audit_visibility()
    
    print("\n==================================================")
    print("ALL PHASE 2 BACKEND SETTLEMENT TESTS PASSED (5/5)!")
    print("==================================================")

if __name__ == "__main__":
    asyncio.run(main())

