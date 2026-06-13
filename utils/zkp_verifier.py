import json
from py_ecc.bn128 import FQ, FQ2, G1, G2, pairing, add, multiply, neg, is_inf, Z1, Z2
import sys
import time

def parse_g1(obj):
    """Parses a G1 point from SnarkJS JSON format."""
    x = int(obj[0])
    y = int(obj[1])
    z = int(obj[2])
    if z == 0:
        return Z1
    return (FQ(x), FQ(y))

def parse_g2(obj):
    """Parses a G2 point from SnarkJS JSON format."""
    x = (FQ(int(obj[0][0])), FQ(int(obj[0][1])))
    y = (FQ(int(obj[1][0])), FQ(int(obj[1][1])))
    z_real = int(obj[2][1])
    if z_real == 0:
        return Z2
    x_fq2 = FQ2([int(obj[0][0]), int(obj[0][1])])
    y_fq2 = FQ2([int(obj[1][0]), int(obj[1][1])])
    return (x_fq2, y_fq2)

def verify_proof(vk_path, proof_path, public_path):
    """
    Verifies a Groth16 proof purely in Python using py_ecc.
    This runs entirely in the Python memory space, eliminating Node.js overhead.
    """
    try:
        with open(vk_path, 'r') as f:
            vk = json.load(f)
        with open(proof_path, 'r') as f:
            proof = json.load(f)
        with open(public_path, 'r') as f:
            public_inputs = json.load(f)

        alpha = parse_g1(vk['vk_alpha_1'])
        beta = parse_g2(vk['vk_beta_2'])
        gamma = parse_g2(vk['vk_gamma_2'])
        delta = parse_g2(vk['vk_delta_2'])
        ic = [parse_g1(p) for p in vk['IC']]

        A = parse_g1(proof['pi_a'])
        B = parse_g2(proof['pi_b'])
        C = parse_g1(proof['pi_c'])

        vk_x = ic[0]
        for i, pub_in in enumerate(public_inputs):
            scalar = int(pub_in)
            if scalar != 0:
                p = multiply(ic[i + 1], scalar)
                vk_x = add(vk_x, p)

        # Groth16 Verification Equation: e(A, B) == e(alpha, beta) * e(vk_x, gamma) * e(C, delta)
        pair_AB = pairing(B, A)
        pair_alpha_beta = pairing(beta, alpha)
        pair_vk_x_gamma = pairing(gamma, vk_x)
        pair_C_delta = pairing(delta, C)
        
        rhs = pair_alpha_beta * pair_vk_x_gamma * pair_C_delta

        return pair_AB == rhs
    except Exception as e:
        print(f"ZKP Verification Error: {e}")
        return False

if __name__ == "__main__":
    import os
    zkp_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "zkp"))
    vk = os.path.join(zkp_dir, "verification_key.json")
    proof = os.path.join(zkp_dir, "proof.json")
    public = os.path.join(zkp_dir, "public.json")
    
    print("Testing Native Python ZKP Verifier (No Subprocess)...")
    start_time = time.perf_counter()
    is_valid = verify_proof(vk, proof, public)
    end_time = time.perf_counter()
    
    print(f"Proof Valid? {is_valid}")
    print(f"Verification Time: {(end_time - start_time) * 1000:.2f} ms")

