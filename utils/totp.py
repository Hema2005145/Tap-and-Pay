import time
import hmac
import hashlib
import struct

def get_hotp_token(secret: bytes, intervals_no: int) -> str:
    """Generates an HOTP token for a given secret and counter interval."""
    # Convert intervals_no to an 8-byte big-endian integer
    msg = struct.pack(">Q", intervals_no)
    
    # Generate HMAC-SHA1 signature
    h = hmac.new(secret, msg, hashlib.sha1).digest()
    
    # Dynamic truncation (extract a 4-byte dynamic binary code)
    o = h[-1] & 0x0f
    bin_code = struct.unpack(">I", h[o:o+4])[0] & 0x7fffffff
    
    # Generate a 6-digit decimal token
    token = bin_code % 1000000
    return f"{token:06d}"

def get_totp_token(secret: bytes, time_step: int = 30) -> str:
    """Generates a TOTP token (RFC 6238) based on current epoch time."""
    return get_hotp_token(secret, int(time.time() / time_step))

def verify_totp_token(secret: bytes, token: str, time_step: int = 30, window: int = 1) -> bool:
    """Verifies a given TOTP token with a configurable window for clock drift."""
    current_interval = int(time.time() / time_step)
    # Check within the validation window (current, past, and future intervals)
    for i in range(-window, window + 1):
        if get_hotp_token(secret, current_interval + i) == token:
            return True
    return False
