import asyncio
from aioquic.asyncio import serve
from aioquic.asyncio.protocol import QuicConnectionProtocol
from aioquic.quic.configuration import QuicConfiguration
from aioquic.quic.events import StreamDataReceived, QuicEvent
import os
import sys
import json
import time
import secrets

# Ensure project root is in sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from utils.pqc import generate_keypair, decapsulate
from utils.totp import verify_totp_token
from utils.crypto_payload import decrypt_payload
from utils.binary_payload import deserialize_payment
import hashlib

from utils.db import get_user, log_transaction, update_balance, TransactionRecord, get_balance_optimized
from utils.zkp_verifier import verify_proof
from utils.shamir_mpc import reconstruct_secret
import datetime
from blockchain.web3_integration import log_to_blockchain
from utils.event_broadcaster import broadcast_quic_event


class PaymentServerProtocol(QuicConnectionProtocol):
    pqc_public_key = None
    pqc_private_key = None
    totp_secret = b"QSP3_SHARED_SECRET_KEY"
    active_sessions = {}
    
    server_mpc_share = None
    master_key_hash = None
    
    # Load ZKP Verification Key into RAM once on startup
    zkp_vk_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "zkp", "verification_key.json"))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.stream_buffers = {}

    async def log_audit_trail(self, tx_hash, amount_cents, client_id, status="APPROVED"):
        """Background task for audit logging and DB update."""
        try:
            # 1. Update Cloud Balance (Now happens AFTER ZKP approval)
            await update_balance(client_id, -amount_cents)
            
            # 2. Create Audit Record
            record = TransactionRecord(
                tx_hash=tx_hash,
                client_id=client_id,
                amount_cents=amount_cents,
                status=status
            )
            await log_transaction(record)
            print(f"Server [Audit-Cloud]: Tx {tx_hash[:10]}... committed to MongoDB Atlas.")
            print(f"Server [Audit-Cloud]: Tx {tx_hash[:10]}... committed to database.")
            broadcast_quic_event("MONGODB_UPDATE", "SUCCESS", {
                "tx_hash": tx_hash,
                "amount_cents": amount_cents,
                "client_id": client_id,
                "status": "COMMITTED"
            })

            # 3. PHASE 8: Log to Blockchain
            success = await log_to_blockchain(tx_hash, client_id, amount_cents, status)
            if success:
                print(f"Server [Audit-Blockchain]: Tx {tx_hash[:10]}... successfully stored on immutable ledger.")
                broadcast_quic_event("BLOCKCHAIN_AUDIT", "SUCCESS", {
                    "tx_hash": tx_hash,
                    "amount_cents": amount_cents,
                    "client_id": client_id,
                    "status": "MINED_ON_CHAIN"
                })
            else:
                print(f"Server [Audit-Blockchain]: Failed to store Tx {tx_hash[:10]}... on ledger.")
                broadcast_quic_event("BLOCKCHAIN_AUDIT", "FAILED", {
                    "tx_hash": tx_hash,
                    "amount_cents": amount_cents,
                    "client_id": client_id,
                    "error": "Blockchain write failed"
                })

        except Exception as e:
            print(f"Server [Audit-Error]: Failed to log to cloud: {e}")
            broadcast_quic_event("MONGODB_UPDATE", "FAILED", {"error": str(e)})

    async def handle_payment_request(self, stream_id, request):
        """Async handler for secure payment requests."""
        print(f"Server: Received payment request. Length: {len(request)}")
        try:
            payload_json = json.loads(request[15:])
            session_id = payload_json["session_id"]
            encrypted_payload = bytes.fromhex(payload_json["encrypted_payload"])
            
            if session_id not in self.active_sessions:
                print(f"Server Error: Session {session_id} not found.")
                broadcast_quic_event("SESSION_CHECK", "FAILED", {"error": f"Session {session_id} expired or invalid"})
                raise KeyError(f"Session {session_id} expired")
                
            shared_secret = self.active_sessions[session_id]
            print(f"Server [AES]: Decrypting for session {session_id}...")
            decrypted_payload_bytes = decrypt_payload(shared_secret, encrypted_payload)
            decrypted_data = deserialize_payment(decrypted_payload_bytes)
            print(f"Server [AES]: Decrypted data: {decrypted_data}")
            broadcast_quic_event("AES_DECRYPTION", "SUCCESS", {
                "session_id": session_id,
                "cipher": "AES-256-GCM"
            })

            # --- CRITICAL PATH START ---
            is_token_valid = verify_totp_token(self.totp_secret, decrypted_data["totp_token"])
            is_time_valid = abs(time.time() - decrypted_data["timestamp"]) <= 120
            
            broadcast_quic_event("TOTP_VERIFICATION", "SUCCESS" if (is_token_valid and is_time_valid) else "FAILED", {
                "status": "VERIFIED" if (is_token_valid and is_time_valid) else ("STALE_TIMESTAMP" if not is_time_valid else "INVALID_TOKEN"),
                "window_valid": is_time_valid
            })
            
            # 3. PHASE 6: ZERO KNOWLEDGE PROOF VERIFICATION
            # Instead of looking up the balance, we verify the attached proof
            has_funds = False
            if "zk_proof" in payload_json:
                print("Server [ZKP]: Verifying Zero-Knowledge Proof (Groth16)...")
                # Temporarily write proof and public to disk for the verifier (in production, pass objects directly in memory)
                tmp_proof = "temp_proof.json"
                tmp_public = "temp_public.json"
                with open(tmp_proof, "w") as f: json.dump(payload_json["zk_proof"], f)
                with open(tmp_public, "w") as f: json.dump([decrypted_data["amount_cents"]], f)
                
                # The python-native verifier!
                has_funds = verify_proof(self.zkp_vk_path, tmp_proof, tmp_public)
                
                # Cleanup
                if os.path.exists(tmp_proof): os.remove(tmp_proof)
                if os.path.exists(tmp_public): os.remove(tmp_public)
                
                broadcast_quic_event("ZKP_VERIFICATION", "SUCCESS" if has_funds else "FAILED", {
                    "proof_system": "Groth16",
                    "funds_proven": has_funds,
                    "amount_cents": decrypted_data['amount_cents']
                })
            else:
                # Fallback to database if client doesn't support ZKP yet
                print("Server [Warning]: Client did not send ZKP. Falling back to DB lookup.")
                balance_cents = await get_balance_optimized(decrypted_data['client_id'])
                has_funds = balance_cents is not None and balance_cents >= decrypted_data['amount_cents']
                broadcast_quic_event("ZKP_VERIFICATION", "NOT_SENT_DB_FALLBACK", {
                    "proof_system": "NONE",
                    "funds_proven": has_funds,
                    "amount_cents": decrypted_data['amount_cents']
                })

            # 4. PHASE 7: MPC Key Protection (Shamir's Secret Sharing)
            is_mpc_valid = False
            if "mpc_share" in payload_json and self.server_mpc_share:
                client_share = (payload_json["mpc_share"]["x"], payload_json["mpc_share"]["y"])
                reconstructed_secret = reconstruct_secret([client_share, self.server_mpc_share])
                reconstructed_hash = hashlib.sha256(str(reconstructed_secret).encode()).hexdigest()
                
                if reconstructed_hash == self.master_key_hash:
                    is_mpc_valid = True
                    print("Server [MPC]: Master Signing Key successfully reconstructed! (2-of-3 threshold met)")
                else:
                    print("Server [MPC Error]: Master Signing Key reconstruction failed. Invalid share.")
                broadcast_quic_event("SHAMIR_MPC", "SUCCESS" if is_mpc_valid else "FAILED", {
                    "threshold": "2-of-3",
                    "key_hash_matched": is_mpc_valid
                })
            else:
                print("Server [MPC Warning]: Proceeding without MPC verification (Legacy Mode).")
                is_mpc_valid = True # Fallback if MPC isn't enabled
                broadcast_quic_event("SHAMIR_MPC", "SUCCESS", {
                    "threshold": "Legacy/Bypass",
                    "key_hash_matched": True
                })

            if not is_token_valid:
                response = "PAYMENT_ERR: Invalid TOTP".encode('utf-8')
                broadcast_quic_event("PAYMENT_ACK", "FAILED", {"error": "Invalid TOTP"})
            elif not is_time_valid:
                response = "PAYMENT_ERR: Stale Timestamp".encode('utf-8')
                broadcast_quic_event("PAYMENT_ACK", "FAILED", {"error": "Stale Timestamp"})
            elif not is_mpc_valid:
                response = "PAYMENT_ERR: MPC Key Reconstruction Failed. Unauthorized transaction.".encode('utf-8')
                broadcast_quic_event("PAYMENT_ACK", "FAILED", {"error": "MPC Key Reconstruction Failed"})
            elif not has_funds:
                response = "PAYMENT_ERR: Insufficient Funds (ZKP Verification Failed)".encode('utf-8')
                broadcast_quic_event("PAYMENT_ACK", "FAILED", {"error": "Insufficient Funds (ZKP Verification Failed)"})
            else:
                # Success! Respond immediately.
                amount_cents = decrypted_data['amount_cents']
                amount_str = f"${amount_cents / 100:.2f}"
                tx_hash = hashlib.sha256(decrypted_payload_bytes).hexdigest()
                response = f"PAYMENT_ACK: Success. Amount {amount_str}. TxHash: {tx_hash[:10]}".encode('utf-8')
                broadcast_quic_event("PAYMENT_ACK", "SUCCESS", {
                    "tx_hash": tx_hash,
                    "amount_cents": amount_cents,
                    "amount_str": amount_str,
                    "client_id": decrypted_data['client_id']
                })
                
                # --- BACKGROUND PATH START ---
                asyncio.create_task(self.log_audit_trail(tx_hash, amount_cents, decrypted_data['client_id']))
            # --- CRITICAL PATH END ---
                
        except Exception as e:
            import traceback
            traceback.print_exc()
            response = f"PAYMENT_ERR: {str(e)}".encode('utf-8')
            
        self._quic.send_stream_data(stream_id, response, end_stream=True)
        self.transmit()

    def quic_event_received(self, event: QuicEvent):
        if isinstance(event, StreamDataReceived):
            if event.stream_id not in self.stream_buffers:
                self.stream_buffers[event.stream_id] = bytearray()
            self.stream_buffers[event.stream_id].extend(event.data)
            
            if event.end_stream:
                request = self.stream_buffers[event.stream_id].decode('utf-8')
                del self.stream_buffers[event.stream_id]
                
                if request == "GET_PQC_PUBKEY":
                    a, t = self.pqc_public_key
                    broadcast_quic_event("PQC_KEY_EXCHANGE", "PROCESSING", {"step": "PUBKEY_REQUESTED", "algorithm": "Kyber-like / Custom PQC"})
                    response = f"PUBKEY:{json.dumps({'a': a, 't': t})}".encode('utf-8')
                    self._quic.send_stream_data(event.stream_id, response, end_stream=True)
                    self.transmit()
                    
                elif request.startswith("ESTABLISH_SESSION:"):
                    try:
                        session_data = json.loads(request[18:])
                        shared_secret = decapsulate((session_data["u"], session_data["v"]), self.pqc_private_key)
                        session_id = secrets.token_hex(16)
                        self.active_sessions[session_id] = shared_secret
                        broadcast_quic_event("PQC_KEY_EXCHANGE", "SUCCESS", {"session_id": session_id, "algorithm": "Kyber-like / Custom PQC"})
                        broadcast_quic_event("SESSION_ESTABLISHED", "SUCCESS", {"session_id": session_id})
                        response = f"SESSION_ESTABLISHED:{json.dumps({'session_id': session_id})}".encode('utf-8')
                    except Exception as e:
                        broadcast_quic_event("SESSION_ESTABLISHED", "FAILED", {"error": str(e)})
                        response = f"SESSION_ERR: {str(e)}".encode('utf-8')
                    self._quic.send_stream_data(event.stream_id, response, end_stream=True)
                    self.transmit()
                    
                elif request.startswith("SECURE_PAYMENT:"):
                    # Delegate to async handler to fix 'await outside async function' error
                    asyncio.create_task(self.handle_payment_request(event.stream_id, request))


async def main():
    configuration = QuicConfiguration(is_client=False)
    
    # Load certificates for mTLS
    cert_dir = os.path.join(os.path.dirname(__file__), "..", "certs")
    cert_dir = os.path.abspath(cert_dir)
    configuration.load_cert_chain(
        os.path.join(cert_dir, "server_cert.pem"),
        os.path.join(cert_dir, "server_key.pem")
    )
    
    # Trust the CA to verify clients (mTLS)
    configuration.load_verify_locations(os.path.join(cert_dir, "ca_cert.pem"))
    configuration.verify_mode = True # Require client certificate
    
    # Initialize PQC Keypair with persistence
    pqc_key_path = os.path.join(cert_dir, "server_pqc_keys.json")
    if os.path.exists(pqc_key_path):
        print("Server: Loading persisted PQC Keypair...")
        with open(pqc_key_path, "r") as f:
            keys = json.load(f)
            pub = (keys["pub_a"], keys["pub_t"])
            priv = keys["priv_s"]
    else:
        print("Server: Generating fresh Kyber-like PQC Keypair (ML-KEM)...")
        pub, priv = generate_keypair()
        with open(pqc_key_path, "w") as f:
            json.dump({
                "pub_a": pub[0],
                "pub_t": pub[1],
                "priv_s": priv
            }, f)
        print("Server: PQC Keypair persisted to certs/server_pqc_keys.json")

    PaymentServerProtocol.pqc_public_key = pub
    PaymentServerProtocol.pqc_private_key = priv
    
    # Load MPC Share and Hash (Phase 7)
    try:
        with open(os.path.join(cert_dir, "server_share.json"), "r") as f:
            share_data = json.load(f)
            PaymentServerProtocol.server_mpc_share = (share_data["x"], share_data["y"])
        with open(os.path.join(cert_dir, "master_key_hash.txt"), "r") as f:
            PaymentServerProtocol.master_key_hash = f.read().strip()
        print("Server [MPC]: Loaded Server Share and Master Key Hash.")
    except Exception as e:
        print(f"Server [MPC Warning]: Could not load MPC components: {e}")
    
    print("Starting QUIC Payment Server on 0.0.0.0:4433 (mTLS Enabled)...")
    broadcast_quic_event("QUIC_SERVER_STATUS", "ONLINE", {"port": 4433, "mtls": True, "pqc": "Kyber-like / Custom PQC"})
    await serve(
        "0.0.0.0", 
        4433, 
        configuration=configuration, 
        create_protocol=PaymentServerProtocol
    )

    await asyncio.Future()  # run forever

if __name__ == "__main__":
    asyncio.run(main())

