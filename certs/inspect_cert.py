import os
from cryptography import x509
from cryptography.hazmat.backends import default_backend

cert_dir = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(cert_dir, "server_cert.pem"), "rb") as f:
    cert_data = f.read()
    cert = x509.load_pem_x509_certificate(cert_data, default_backend())
    
    print(f"Subject: {cert.subject}")
    try:
        ext = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName)
        print(f"SAN: {ext.value}")
    except Exception as e:
        print(f"SAN Extension not found: {e}")
