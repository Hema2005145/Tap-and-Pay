import os
import json
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from typing import Tuple

def encrypt_payload(key: bytes, plaintext: bytes) -> bytes:
    """Encrypts plaintext bytes using AES-256-GCM."""
    # Generate a random 12-byte IV (Initialization Vector)
    iv = os.urandom(12)
    
    # Initialize AES-GCM cipher
    encryptor = Cipher(
        algorithms.AES(key),
        modes.GCM(iv)
    ).encryptor()
    
    ciphertext = encryptor.update(plaintext) + encryptor.finalize()
    
    # Pack: IV (12 bytes) + Tag (16 bytes) + Ciphertext
    return iv + encryptor.tag + ciphertext

def decrypt_payload(key: bytes, encrypted_data: bytes) -> bytes:
    """Decrypts a payload using AES-256-GCM and returns the raw plaintext bytes."""
    if len(encrypted_data) < 28:
        raise ValueError("Encrypted data too short")
        
    iv = encrypted_data[:12]
    tag = encrypted_data[12:28]
    ciphertext = encrypted_data[28:]
    
    # Initialize AES-GCM decryptor
    decryptor = Cipher(
        algorithms.AES(key),
        modes.GCM(iv, tag)
    ).decryptor()
    
    plaintext = decryptor.update(ciphertext) + decryptor.finalize()
    return plaintext
