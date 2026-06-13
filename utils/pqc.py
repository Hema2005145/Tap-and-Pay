import hashlib
import os
import random
import ctypes
from typing import Tuple, List

# Kyber-like Ring-LWE parameters
N = 256
Q = 3329
HALF_Q = Q // 2

Poly = List[int]

# --- C-EXTENSION INTEGRATION (Hardware Acceleration) ---
C_LIB_AVAILABLE = False
try:
    lib_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'fast_poly.dll'))
    if os.path.exists(lib_path):
        _fast_poly = ctypes.CDLL(lib_path)
        # Define argtypes: const int32_t* a, const int32_t* b, int32_t* out
        _fast_poly.poly_mul_c.argtypes = [
            ctypes.POINTER(ctypes.c_int32),
            ctypes.POINTER(ctypes.c_int32),
            ctypes.POINTER(ctypes.c_int32)
        ]
        C_LIB_AVAILABLE = True
        print("PQC [Optimization]: Successfully hooked into C-compiled math library.")
except Exception as e:
    pass

def poly_add(a: Poly, b: Poly) -> Poly:
    """Adds two polynomials in R_q."""
    return [(x + y) % Q for x, y in zip(a, b)]

def poly_sub(a: Poly, b: Poly) -> Poly:
    """Subtracts two polynomials in R_q."""
    return [(x - y) % Q for x, y in zip(a, b)]

def poly_mul(a: Poly, b: Poly) -> Poly:
    """Multiplies two polynomials in R_q modulo (X^256 + 1)."""
    # 1. Hardware Accelerated Path (C-Extension)
    if C_LIB_AVAILABLE:
        arr_type = ctypes.c_int32 * N
        ca = arr_type(*a)
        cb = arr_type(*b)
        cout = arr_type()
        _fast_poly.poly_mul_c(ca, cb, cout)
        return list(cout)
        
    # 2. Fallback Path (Pure Python)
    c = [0] * (2 * N)
    for i in range(N):
        for j in range(N):
            c[i + j] = (c[i + j] + a[i] * b[j]) % Q
            
    out = [0] * N
    for i in range(N):
        out[i] = (c[i] - c[i + N]) % Q
    return out

def get_small_poly() -> Poly:
    """Generates a small error polynomial with coefficients in {-1, 0, 1}."""
    return [random.choice([-1, 0, 1]) % Q for _ in range(N)]

def get_random_poly() -> Poly:
    """Generates a random polynomial in R_q."""
    return [random.randint(0, Q - 1) for _ in range(N)]

def bytes_to_bits(b: bytes) -> List[int]:
    """Converts bytes to a list of bits (little-endian)."""
    bits = []
    for byte in b:
        for i in range(8):
            bits.append((byte >> i) & 1)
    return bits

def bits_to_bytes(bits: List[int]) -> bytes:
    """Converts a list of bits back to bytes."""
    b = bytearray()
    for i in range(0, len(bits), 8):
        byte = 0
        for j in range(8):
            if i + j < len(bits):
                byte |= (bits[i + j] << j)
        b.append(byte)
    return bytes(b)

def encode_key(key_bytes: bytes) -> Poly:
    """Encodes 256 bits (32 bytes) into a polynomial in R_q."""
    bits = bytes_to_bits(key_bytes)
    # Ensure it fits the polynomial length N (256)
    bits = (bits + [0] * N)[:N]
    return [bit * HALF_Q for bit in bits]

def decode_key(poly: Poly) -> bytes:
    """Decodes a polynomial in R_q back to 256 bits (32 bytes) by rounding."""
    bits = []
    for x in poly:
        # Measure distance to HALF_Q vs 0 modulo Q
        diff_to_half = min(abs(x - HALF_Q), Q - abs(x - HALF_Q))
        diff_to_zero = min(x, Q - x)
        if diff_to_half < diff_to_zero:
            bits.append(1)
        else:
            bits.append(0)
    return bits_to_bytes(bits)

def generate_keypair() -> Tuple[Tuple[Poly, Poly], Poly]:
    """
    Generates a Kyber-like public key (a, t) and a private key s.
    t = a * s + e
    """
    a = get_random_poly()
    s = get_small_poly()
    e = get_small_poly()
    t = poly_add(poly_mul(a, s), e)
    return (a, t), s

def encapsulate(public_key: Tuple[Poly, Poly]) -> Tuple[Tuple[Poly, Poly], bytes]:
    """
    Encapsulates a random 256-bit session key.
    Returns:
        ciphertext (u, v)
        shared_secret (sha256 of the session key)
    """
    a, t = public_key
    key_bytes = os.urandom(32) # Generate 256-bit message
    m = encode_key(key_bytes)
    
    r = get_small_poly()
    e1 = get_small_poly()
    e2 = get_small_poly()
    
    # u = a * r + e1
    u = poly_add(poly_mul(a, r), e1)
    # v = t * r + e2 + m
    v = poly_add(poly_add(poly_mul(t, r), e2), m)
    
    ciphertext = (u, v)
    shared_secret = hashlib.sha256(key_bytes).digest()
    return ciphertext, shared_secret

def decapsulate(ciphertext: Tuple[Poly, Poly], private_key: Poly) -> bytes:
    """
    Decapsulates the ciphertext (u, v) using private key s.
    Returns:
        shared_secret (sha256 of the recovered session key)
    """
    u, v = ciphertext
    s = private_key
    # w = v - u * s
    w = poly_sub(v, poly_mul(u, s))
    key_bytes = decode_key(w)
    return hashlib.sha256(key_bytes).digest()
