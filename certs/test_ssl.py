import ssl
import os

cert_dir = os.path.dirname(os.path.abspath(__file__))
context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile=os.path.join(cert_dir, "ca_cert.pem"))
context.load_cert_chain(os.path.join(cert_dir, "client_cert.pem"), os.path.join(cert_dir, "client_key.pem"))

print("Testing SSL context loading...")
try:
    # This just tests if the certs are valid for SSL
    print("SSL Context created successfully.")
except Exception as e:
    print(f"SSL Context failed: {e}")
