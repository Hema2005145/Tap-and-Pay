import os
import json
import hashlib

# We use the 127-bit Mersenne Prime (2^127 - 1) for fast, secure prime field arithmetic
PRIME = 170141183460469231731687303715884105727

def _eval_at(poly, x, prime):
    """Evaluates polynomial (poly) at point (x) modulo prime."""
    accum = 0
    for coeff in reversed(poly):
        accum = (accum * x + coeff) % prime
    return accum

def split_secret(secret, threshold, num_shares):
    """
    Splits a secret integer into num_shares.
    Requires 'threshold' number of shares to reconstruct.
    """
    if threshold > num_shares:
        raise ValueError("Threshold cannot be greater than number of shares")
    if secret >= PRIME:
        raise ValueError(f"Secret must be less than prime {PRIME}")
    
    # Polynomial: f(x) = secret + a_1*x + a_2*x^2 + ... + a_{t-1}*x^{t-1}
    poly = [secret] + [int.from_bytes(os.urandom(15), 'big') % PRIME for _ in range(threshold - 1)]
    
    shares = []
    for i in range(1, num_shares + 1):
        shares.append((i, _eval_at(poly, i, PRIME)))
    return shares

def reconstruct_secret(shares):
    """
    Reconstructs the secret using Lagrange interpolation over the prime field.
    Shares is a list of (x, y) tuples.
    """
    secret = 0
    for i, (x_i, y_i) in enumerate(shares):
        numerator = 1
        denominator = 1
        for j, (x_j, y_j) in enumerate(shares):
            if i == j: 
                continue
            numerator = (numerator * -x_j) % PRIME
            denominator = (denominator * (x_i - x_j)) % PRIME
        
        # pow(base, -1, mod) calculates the modular multiplicative inverse in Python 3.8+
        lagrange_poly = (numerator * pow(denominator, -1, PRIME)) % PRIME
        secret = (secret + y_i * lagrange_poly) % PRIME
        
    return secret

if __name__ == "__main__":
    cert_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "certs"))
    if not os.path.exists(cert_dir):
        os.makedirs(cert_dir)
        
    # Generate a random 120-bit Master Key
    master_secret = int.from_bytes(os.urandom(15), 'big')
    print(f"Generated Master Signing Key.")
    
    # 2-of-3 threshold signature setup
    shares = split_secret(master_secret, threshold=2, num_shares=3)
    
    # Save Share 1 (Client's Device)
    with open(os.path.join(cert_dir, "client_share.json"), "w") as f:
        json.dump({"x": shares[0][0], "y": shares[0][1]}, f)
        
    # Save Share 2 (Server's Secure Vault)
    with open(os.path.join(cert_dir, "server_share.json"), "w") as f:
        json.dump({"x": shares[1][0], "y": shares[1][1]}, f)
        
    # Save Share 3 (Cold Storage / Edge Backup)
    with open(os.path.join(cert_dir, "edge_backup_share.json"), "w") as f:
        json.dump({"x": shares[2][0], "y": shares[2][1]}, f)
        
    # Save the Hash of the Master Key to the server so it knows when reconstruction succeeds
    secret_hash = hashlib.sha256(str(master_secret).encode()).hexdigest()
    with open(os.path.join(cert_dir, "master_key_hash.txt"), "w") as f:
        f.write(secret_hash)
        
    print("Successfully split the Master Key into 3 distributed shares using Shamir's Secret Sharing (2-of-3 threshold).")
    print("Saved to certs/ directory.")
