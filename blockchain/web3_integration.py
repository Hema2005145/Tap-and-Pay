import json
import os
from web3 import Web3, EthereumTesterProvider
from solcx import compile_standard, install_solc

# Install specific solidity compiler version
install_solc('0.8.0')

def compile_contract():
    contract_path = os.path.join(os.path.dirname(__file__), "AuditTrail.sol")
    with open(contract_path, "r") as f:
        contract_source = f.read()

    compiled_sol = compile_standard(
        {
            "language": "Solidity",
            "sources": {"AuditTrail.sol": {"content": contract_source}},
            "settings": {
                "outputSelection": {
                    "*": {"*": ["abi", "metadata", "evm.bytecode", "evm.sourceMap"]}
                }
            },
        },
        solc_version="0.8.0",
    )

    bytecode = compiled_sol["contracts"]["AuditTrail.sol"]["AuditTrail"]["evm"]["bytecode"]["object"]
    abi = compiled_sol["contracts"]["AuditTrail.sol"]["AuditTrail"]["abi"]
    return abi, bytecode

# Initialize the Lightweight Local Blockchain
# Instead of Ganache GUI, we use eth-tester for blazing fast in-memory execution during the prototype
w3 = Web3(EthereumTesterProvider())

# Set a default account to act as the "Server Node" paying for gas
w3.eth.default_account = w3.eth.accounts[0]

# Compile and Deploy the Contract
print("Blockchain [Web3]: Compiling and deploying AuditTrail.sol to local blockchain...")
abi, bytecode = compile_contract()
AuditContract = w3.eth.contract(abi=abi, bytecode=bytecode)
tx_hash = AuditContract.constructor().transact()
tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

# Create the contract instance to interact with
audit_trail = w3.eth.contract(
    address=tx_receipt.contractAddress,
    abi=abi
)
print(f"Blockchain [Web3]: Contract deployed at {tx_receipt.contractAddress}")

async def log_to_blockchain(tx_hash_str, client_id, amount_cents, status="APPROVED"):
    """Writes the transaction hash to the immutable ledger."""
    try:
        # Build the transaction
        tx = audit_trail.functions.logTransaction(
            tx_hash_str, 
            client_id, 
            amount_cents, 
            status
        ).transact()
        
        # Wait for the block to be mined
        receipt = w3.eth.wait_for_transaction_receipt(tx)
        print(f"Blockchain [Web3]: Mined Tx {tx_hash_str[:10]}... into Block {receipt.blockNumber} (Gas Used: {receipt.gasUsed})")
        return True
    except Exception as e:
        print(f"Blockchain [Web3 Error]: {e}")
        return False
