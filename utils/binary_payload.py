import struct
from typing import Dict, Any

def serialize_payment(amount_cents: int, sender_id: int, totp_token: int, timestamp: int, receiver_id: int = 2) -> bytes:
    """
    Serializes payment details into a compact 16-byte binary format.
    Structure:
      - amount_cents: 4 bytes (unsigned int 'I')
      - sender_id: 2 bytes (unsigned short 'H')
      - receiver_id: 2 bytes (unsigned short 'H')
      - totp_token: 4 bytes (unsigned int 'I')
      - timestamp: 4 bytes (unsigned int 'I')
    """
    return struct.pack(">IHHII", amount_cents, sender_id, receiver_id, totp_token, timestamp)

def deserialize_payment(data: bytes) -> Dict[str, Any]:
    """
    Deserializes the binary payment data.
    Supports both 16-byte multi-user format and legacy 14-byte single-party format.
    """
    if len(data) == 16:
        amount_cents, sender_id, receiver_id, totp_token, timestamp = struct.unpack(">IHHII", data)
        return {
            "amount_cents": amount_cents,
            "sender_id": sender_id,
            "receiver_id": receiver_id,
            "client_id": sender_id,  # Backwards compatibility
            "totp_token": f"{totp_token:06d}",
            "timestamp": timestamp
        }
    elif len(data) == 14:
        amount_cents, client_id, totp_token, timestamp = struct.unpack(">IHII", data)
        return {
            "amount_cents": amount_cents,
            "sender_id": client_id,
            "receiver_id": 2,  # Default merchant receiver
            "client_id": client_id,
            "totp_token": f"{totp_token:06d}",
            "timestamp": timestamp
        }
    else:
        raise ValueError(f"Invalid binary payment payload length: {len(data)} bytes (expected 16 or 14)")
