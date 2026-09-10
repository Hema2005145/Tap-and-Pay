import asyncio
from aioquic.asyncio import connect
from aioquic.asyncio.protocol import QuicConnectionProtocol
from aioquic.quic.configuration import QuicConfiguration
from aioquic.quic.events import StreamDataReceived, QuicEvent
import os
import sys
import ssl
import json
import time
import numpy as np
import pickle
import tensorflow.lite as tflite
import subprocess

# Ensure project root is in sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from utils.pqc import encapsulate
from utils.totp import get_totp_token
from utils.crypto_payload import encrypt_payload
from utils.binary_payload import serialize_payment
from utils.event_broadcaster import broadcast_quic_event


class PaymentClientProtocol(QuicConnectionProtocol):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.response_received = asyncio.Event()
        self.server_pubkey = None
        self.payment_ack = None
        self.session_id = None
        self.stream_buffers = {}

    def quic_event_received(self, event: QuicEvent):
        if isinstance(event, StreamDataReceived):
            if event.stream_id not in self.stream_buffers:
                self.stream_buffers[event.stream_id] = bytearray()
            self.stream_buffers[event.stream_id].extend(event.data)
            
            if event.end_stream:
                data = self.stream_buffers[event.stream_id].decode('utf-8')
                del self.stream_buffers[event.stream_id]
                
                if data.startswith("PUBKEY:"):
                    pubkey_data = json.loads(data[7:])
                    self.server_pubkey = (pubkey_data["a"], pubkey_data["t"])
                    self.response_received.set()
                elif data.startswith("SESSION_ESTABLISHED:"):
                    session_info = json.loads(data[20:])
                    self.session_id = session_info["session_id"]
                    self.response_received.set()
                elif data.startswith("PAYMENT_ACK:") or data.startswith("PAYMENT_ERR:"):
                    self.payment_ack = data
                    self.response_received.set()

class BehavioralAI:
    def __init__(self, model_dir):
        # Load Scaler
        with open(os.path.join(model_dir, "scaler.pkl"), "rb") as f:
            self.scaler = pickle.load(f)
            
        # Load Threshold
        with open(os.path.join(model_dir, "threshold.txt"), "r") as f:
            self.threshold = float(f.read())
            
        # Load TFLite Model (INT8 Quantized)
        self.interpreter = tflite.Interpreter(model_path=os.path.join(model_dir, "behavioral_ai_quantized.tflite"))
        self.interpreter.allocate_tensors()
        self.input_details = self.interpreter.get_input_details()
        self.output_details = self.interpreter.get_output_details()

    def check_anomaly(self, amount, lat, lon, tilt_x, tilt_y, tilt_z, hour):
        """Returns True if behavior is anomalous, False if normal."""
        # 1. Prepare Data
        raw_data = np.array([[amount, lat, lon, tilt_x, tilt_y, tilt_z, hour]])
        scaled_data = self.scaler.transform(raw_data)
        
        # TFLite expects INT8 input because we quantized it heavily.
        # We need to manually quantize the float32 scaled data into the INT8 range of the model's input.
        input_scale, input_zero_point = self.input_details[0]['quantization']
        if input_scale > 0:
            quantized_input = (scaled_data / input_scale) + input_zero_point
            quantized_input = np.clip(quantized_input, -128, 127).astype(np.int8)
        else:
             # Fallback if converter left it as float32
            quantized_input = scaled_data.astype(np.float32)

        # 2. Run Inference
        self.interpreter.set_tensor(self.input_details[0]['index'], quantized_input)
        self.interpreter.invoke()
        output_data = self.interpreter.get_tensor(self.output_details[0]['index'])
        
        # De-quantize output to calculate error
        output_scale, output_zero_point = self.output_details[0]['quantization']
        if output_scale > 0:
            reconstructed = (output_data.astype(np.float32) - output_zero_point) * output_scale
        else:
            reconstructed = output_data
            
        # 3. Calculate Error
        mae_error = np.mean(np.abs(reconstructed - scaled_data))
        print(f"Client [AI]: Context Error Score = {mae_error:.4f} (Threshold: {self.threshold:.4f})")
        
        return mae_error > self.threshold
        is_anomaly = bool(mae_error > self.threshold)
        broadcast_quic_event("BEHAVIORAL_AI", "ANOMALY" if is_anomaly else "SUCCESS", {
            "mae_error": round(float(mae_error), 4),
            "threshold": round(float(self.threshold), 4),
            "is_anomaly": is_anomaly
        })
        return is_anomaly

class PaymentClient:
    def __init__(self, configuration, totp_secret, cert_dir, ai_model=None):
        self.configuration = configuration
        self.totp_secret = totp_secret
        self.cert_dir = cert_dir
        self.ai_model = ai_model
        self.session = {}
        self.connection = None
        self.protocol = None
        self.zkp_dir = os.path.abspath(os.path.join(cert_dir, "..", "zkp"))
        
        # Load MPC Share (Phase 7)
        mpc_path = os.path.join(cert_dir, "client_share.json")
        if os.path.exists(mpc_path):
            with open(mpc_path, "r") as f:
                self.mpc_share = json.load(f)
        else:
            self.mpc_share = None

    async def __aenter__(self):
        self.connection = connect(
            "127.0.0.1",
            4433,
            configuration=self.configuration,
            create_protocol=PaymentClientProtocol
        )
        self.protocol = await self.connection.__aenter__()
        return self
        try:
            self.connection = connect(
                "127.0.0.1",
                4433,
                configuration=self.configuration,
                create_protocol=PaymentClientProtocol
            )
            self.protocol = await self.connection.__aenter__()
            broadcast_quic_event("QUIC_CONNECTION", "SUCCESS", {"endpoint": "127.0.0.1:4433"})
            broadcast_quic_event("MTLS_VERIFICATION", "SUCCESS", {"cert": "client_cert.pem", "status": "VERIFIED"})
            return self
        except Exception as e:
            broadcast_quic_event("QUIC_CONNECTION", "FAILED", {"endpoint": "127.0.0.1:4433", "error": str(e)})
            raise e


    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.connection:
            await self.connection.__aexit__(exc_type, exc_val, exc_tb)

    async def _ensure_session(self, force_refetch=False):
        cache_path = os.path.join(self.cert_dir, "cached_server_pubkey.json")
        pubkey = None

        if force_refetch or not self.session.get("session_id") or not self.session.get("shared_secret"):
            if force_refetch:
                self.session.clear()
                if os.path.exists(cache_path):
                    try: os.remove(cache_path)
                    except Exception: pass

            if not force_refetch and os.path.exists(cache_path):
                try:
                    with open(cache_path, "r") as f:
                        cached_data = json.load(f)
                        pubkey = (cached_data["a"], cached_data["t"])
                        print("Client [PQC]: Loaded public key from cache.")
                except Exception:
                    pubkey = None

            if pubkey is None:
                print("Client [PQC]: Cache miss. Requesting PQC Public Key from server...")
                stream_id = self.protocol._quic.get_next_available_stream_id()
                self.protocol._quic.send_stream_data(stream_id, b"GET_PQC_PUBKEY", end_stream=True)
                self.protocol.transmit()
                await self.protocol.response_received.wait()
                self.protocol.response_received.clear()
                pubkey = self.protocol.server_pubkey
                try:
                    with open(cache_path, "w") as f:
                        json.dump({"a": pubkey[0], "t": pubkey[1]}, f)
                    print("Client [PQC]: PQC public key cached locally.")
                except Exception as e:
                    print(f"Client: Failed to write cache: {e}")

            print("Client [PQC]: Encapsulating session key...")
            ciphertext, shared_secret = encapsulate(pubkey)
            u, v = ciphertext
            session_msg = f"ESTABLISH_SESSION:{json.dumps({'u': u, 'v': v})}".encode('utf-8')
            
            stream_id = self.protocol._quic.get_next_available_stream_id()
            self.protocol._quic.send_stream_data(stream_id, session_msg, end_stream=True)
            self.protocol.transmit()
            await self.protocol.response_received.wait()
            self.protocol.response_received.clear()
            
            self.session["session_id"] = self.protocol.session_id
            self.session["shared_secret"] = shared_secret
            print(f"Client [Session]: Session established with ID: {self.session['session_id']}")
            broadcast_quic_event("PQC_KEY_EXCHANGE", "SUCCESS", {"session_id": self.session["session_id"], "algorithm": "Kyber-like / Custom PQC"})
            broadcast_quic_event("SESSION_ESTABLISHED", "SUCCESS", {"session_id": self.session["session_id"]})

    def generate_zkp(self, amount_cents, private_balance_cents):
        """Generates a Zero-Knowledge Proof that balance >= amount using SnarkJS."""
        try:
            print("Client [ZKP]: Generating cryptographic proof of funds...")
            broadcast_quic_event("ZKP_GENERATION", "PROCESSING", {"amount_cents": amount_cents})
            input_file = os.path.join(self.zkp_dir, "temp_input.json")
            with open(input_file, "w") as f:
                json.dump({"amount": amount_cents, "balance": private_balance_cents}, f)
            
            # 1. Generate Witness
            if sys.platform == "linux" or sys.platform == "linux2":
                print("Client [ZKP]: Using ultra-low latency C++ native witness generator...")
                subprocess.run(
                    ["./balance_check_cpp/balance_check", "temp_input.json", "temp_witness.wtns"],
                    cwd=self.zkp_dir, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
            else:
                print("Client [ZKP]: Using Node.js WebAssembly witness generator...")
                subprocess.run(
                    ["node", "balance_check_js/generate_witness.js", "balance_check_js/balance_check.wasm", "temp_input.json", "temp_witness.wtns"],
                    cwd=self.zkp_dir, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
            
            # 2. Generate Proof
            cmd_args = ["snarkjs", "groth16", "prove", "balance_check_final.zkey", "temp_witness.wtns", "temp_proof.json", "temp_public.json"]
            subprocess.run(
                " ".join(cmd_args) if sys.platform != "win32" else cmd_args,
                cwd=self.zkp_dir, shell=True, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            
            # Read proof
            with open(os.path.join(self.zkp_dir, "temp_proof.json"), "r") as f:
                proof = json.load(f)
                
            # Cleanup
            for f in ["temp_input.json", "temp_witness.wtns", "temp_proof.json", "temp_public.json"]:
                path = os.path.join(self.zkp_dir, f)
                if os.path.exists(path): os.remove(path)
                
            broadcast_quic_event("ZKP_GENERATION", "SUCCESS", {"proof_system": "Groth16", "curve": "bn128"})
            return proof
        except Exception as e:
            print(f"Client [ZKP Error]: Failed to generate proof: {e}")
            broadcast_quic_event("ZKP_GENERATION", "FAILED", {"error": str(e)})
            return None

    async def pay(self, amount_cents, client_id, behavior_data=None, force_refetch=False, private_balance=None):
        """
        behavior_data: dict containing lat, lon, tilt_x, tilt_y, tilt_z, hour
        """
        # --- PHASE 3: BEHAVIORAL AI SHIELD ---
        # Run local edge inference before hitting the network
        if self.ai_model and behavior_data:
            is_anomaly = self.ai_model.check_anomaly(
                amount_cents, 
                behavior_data['lat'], behavior_data['lon'],
                behavior_data['tilt_x'], behavior_data['tilt_y'], behavior_data['tilt_z'],
                behavior_data['hour']
            )
            
            if is_anomaly:
                print("Client [Security]: BEHAVIORAL ANOMALY DETECTED. Blocking Transaction.")
                return b"AI_BLOCKED: Suspicious context. Requesting PIN/Biometric override."
            
        # --- PHASE 6: ZERO KNOWLEDGE PROOF ---
        zk_proof = None
        if private_balance is not None:
            if private_balance < amount_cents:
                print("Client [ZKP]: Insufficient local balance. Proof generation mathematically impossible. Blocking Tap.")
                broadcast_quic_event("ZKP_GENERATION", "DECLINED_LOCALLY", {"error": "Insufficient local funds for proof"})
                return b"DECLINED_LOCALLY: Insufficient funds."
            zk_proof = self.generate_zkp(amount_cents, private_balance)

        # If normal, proceed to network phase
        await self._ensure_session(force_refetch=force_refetch)
        
        token = int(get_totp_token(self.totp_secret))
        binary_payload = serialize_payment(amount_cents, client_id, token, int(time.time()))
        encrypted = encrypt_payload(self.session["shared_secret"], binary_payload)
        broadcast_quic_event("AES_ENCRYPTION", "SUCCESS", {"cipher": "AES-256-GCM"})
        
        payload_dict = {
            "session_id": self.session["session_id"],
            "encrypted_payload": encrypted.hex()
        }
        if zk_proof:
            payload_dict["zk_proof"] = zk_proof
        if self.mpc_share:
            payload_dict["mpc_share"] = self.mpc_share
            
        payload_json = json.dumps(payload_dict)
        request_msg = f"SECURE_PAYMENT:{payload_json}".encode('utf-8')
        
        broadcast_quic_event("PAYMENT_TRANSMISSION", "PROCESSING", {"session_id": self.session["session_id"]})
        stream_id = self.protocol._quic.get_next_available_stream_id()
        self.protocol._quic.send_stream_data(stream_id, request_msg, end_stream=True)
        self.protocol.transmit()
        
        await self.protocol.response_received.wait()
        self.protocol.response_received.clear()
        
        ack_str = self.protocol.payment_ack if isinstance(self.protocol.payment_ack, str) else (self.protocol.payment_ack.decode('utf-8') if self.protocol.payment_ack else "UNKNOWN")
        broadcast_quic_event("PAYMENT_ACK_RECEIVED", "SUCCESS" if ("PAYMENT_ACK" in ack_str) else "FAILED", {
            "raw_ack": ack_str
        })
        return self.protocol.payment_ack

async def main():
    configuration = QuicConfiguration(is_client=True, server_name="localhost")
    configuration.verify_mode = ssl.CERT_NONE 
    
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    cert_dir = os.path.join(project_root, "certs")
    model_dir = os.path.join(project_root, "models")
    
    configuration.load_cert_chain(
        os.path.join(cert_dir, "client_cert.pem"),
        os.path.join(cert_dir, "client_key.pem")
    )
    
    totp_secret = b"QSP3_SHARED_SECRET_KEY"
    
    print("Initializing Edge AI Shield (TFLite INT8)...")
    try:
        ai_shield = BehavioralAI(model_dir)
    except Exception as e:
        print(f"Failed to load AI model: {e}")
        ai_shield = None
    
    async with PaymentClient(configuration, totp_secret, cert_dir, ai_shield) as client:
        # Transaction 1: NORMAL BEHAVIOR + ZKP
        print("\n--- Initiating Transaction 1 ($25.00) [NORMAL BEHAVIOR + ZKP] ---")
        normal_context = {
            'lat': 12.9716, 'lon': 77.5946,
            'tilt_x': 0.7, 'tilt_y': 0.2, 'tilt_z': 0.9,
            'hour': 14
        }
        # Assume the phone knows locally the user has $500.00
        private_local_balance = 50000 
        
        start = time.perf_counter()
        response = await client.pay(2500, 109, normal_context, private_balance=private_local_balance)
        print(f"Client: Tx 1 ({time.perf_counter()-start:.4f}s): {response}\n")
        
        if response and isinstance(response, bytes) and b"Verification failed" in response:
            print("Client: Session invalid. Retrying with new session...")
            await client.pay(2500, 109, normal_context, force_refetch=True, private_balance=private_local_balance)

        # Transaction 2: INSUFFICIENT FUNDS (ZKP blocks locally)
        print("\n--- Initiating Transaction 2 ($600.00) [INSUFFICIENT FUNDS] ---")
        # User tries to buy something for $600 but only has $475 left
        private_local_balance = 47500 
        start = time.perf_counter()
        response2 = await client.pay(60000, 109, normal_context, private_balance=private_local_balance)
        print(f"Client: Tx 2 ({time.perf_counter()-start:.4f}s): {response2}")

if __name__ == "__main__":
    asyncio.run(main())
