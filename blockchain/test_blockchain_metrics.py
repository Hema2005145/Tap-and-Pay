import asyncio
import time
import hashlib
import os

from web3_integration import log_to_blockchain, audit_trail, w3

async def test_latency_and_energy():
    print("\n" + "="*50)
    print("--- 1. LATENCY & ENERGY CONSUMPTION ---")
    tx_hash = hashlib.sha256(b"test_latency_energy_1").hexdigest()
    client_id = 101
    amount = 500
    
    start_time = time.time()
    success = await log_to_blockchain(tx_hash, client_id, amount, "APPROVED")
    end_time = time.time()
    
    latency = end_time - start_time
    print(f"[*] Latency: {latency:.4f} seconds per transaction")
    
    if success:
        # Get gas used from the latest block
        block_num = w3.eth.block_number
        block = w3.eth.get_block(block_num)
        gas_used = block.gasUsed
        print(f"[*] Energy Consumption Proxy (Gas Used): {gas_used} units")
    else:
        print("[!] Transaction failed.")

async def test_integrity_and_security():
    print("\n" + "="*50)
    print("--- 2. INTEGRITY & SECURITY ---")
    tx_hash = hashlib.sha256(b"test_integrity_security_1").hexdigest()
    
    # 1. Write original tx
    await log_to_blockchain(tx_hash, 102, 1000, "APPROVED")
    
    # 2. Verify Integrity
    stored_tx = audit_trail.functions.getTransaction(tx_hash).call()
    print(f"[*] Stored Data -> Client ID: {stored_tx[1]}, Amount: {stored_tx[2]}, Status: {stored_tx[3]}")
    if stored_tx[1] == 102 and stored_tx[2] == 1000 and stored_tx[3] == "APPROVED":
        print("[+] Integrity: PASS (On-chain data exactly matches input)")
    else:
        print("[-] Integrity: FAIL")
        
    # 3. Verify Security (Attempt Overwrite/Replay)
    print("[*] Testing Security (Replay/Overwrite Prevention)...")
    success = await log_to_blockchain(tx_hash, 999, 50000, "FLAGGED")
    if not success:
        print("[+] Security: PASS (Smart contract successfully blocked duplicate transaction hash!)")
    else:
        print("[-] Security: FAIL (Contract allowed overwriting existing tx)")

async def test_scalability_and_reliability():
    print("\n" + "="*50)
    print("--- 3. SCALABILITY & RELIABILITY ---")
    num_txs = 15
    print(f"[*] Sending {num_txs} concurrent transactions...")
    
    start_time = time.time()
    
    # Using asyncio.to_thread because logTransaction.transact() in web3_integration is blocking
    # We will simulate parallel requests hitting the backend
    async def log_tx(i):
        tx_hash = hashlib.sha256(f"scale_test_{i}".encode()).hexdigest()
        return await log_to_blockchain(tx_hash, 200+i, 500, "APPROVED")
        
    tasks = [log_tx(i) for i in range(num_txs)]
    results = await asyncio.gather(*tasks)
    
    end_time = time.time()
    
    success_count = sum(1 for r in results if r is True)
    duration = end_time - start_time
    tps = num_txs / duration if duration > 0 else 0
    
    print(f"[*] Reliability: {success_count}/{num_txs} succeeded ({success_count/num_txs*100:.1f}%)")
    print(f"[*] Scalability (Throughput): {tps:.2f} Transactions Per Second (TPS)")
    print(f"[*] Total Time for {num_txs} txs: {duration:.4f} seconds")

async def main():
    print("Starting Comprehensive Blockchain Audit Layer Benchmarks...\n")
    
    await test_latency_and_energy()
    await test_integrity_and_security()
    await test_scalability_and_reliability()
    
    print("\n" + "="*50)
    print("All tests completed.")

if __name__ == "__main__":
    asyncio.run(main())
