import struct
from typing import Dict, Any

def serialize_payment(amount_cents: int, client_id: int, totp_token: int, timestamp: int) -> bytes:
    """
    Serializes payment details into a compact 14-byte binary format.
    Structure:
      - amount_cents: 4 bytes (unsigned int 'I')
      - client_id: 2 bytes (unsigned short 'H')
      - totp_token: 4 bytes (unsigned int 'I')
      - timestamp: 4 bytes (unsigned int 'I')
    """
    return struct.pack(">IHII", amount_cents, client_id, totp_token, timestamp)

def deserialize_payment(data: bytes) -> Dict[str, Any]:
    """
    Deserializes the compact 14-byte binary payment data.
    """
    amount_cents, client_id, totp_token, timestamp = struct.unpack(">IHII", data)
    
    return {
        "amount_cents": amount_cents,
        "client_id": client_id,
        "totp_token": f"{totp_token:06d}",
        "timestamp": timestamp
    }
