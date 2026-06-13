import os
import ipaddress
from datetime import datetime, timedelta, timezone
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa

def create_cert(name, cn, ca_cert=None, ca_key=None):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, cn),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, u"QSP3"),
    ])
    issuer = ca_cert.subject if ca_cert else subject
    
    builder = x509.CertificateBuilder()
    builder = builder.subject_name(subject)
    builder = builder.issuer_name(issuer)
    builder = builder.public_key(key.public_key())
    builder = builder.serial_number(x509.random_serial_number())
    builder = builder.not_valid_before(datetime.now(timezone.utc) - timedelta(hours=1))
    builder = builder.not_valid_after(datetime.now(timezone.utc) + timedelta(days=365))
    
    if not ca_cert: # It's a CA
        builder = builder.add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
    else:
        builder = builder.add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        builder = builder.add_extension(x509.SubjectAlternativeName([
            x509.DNSName(u"localhost"), 
            x509.IPAddress(ipaddress.ip_address(u"127.0.0.1"))
        ]), critical=False)
        
    signing_key = ca_key if ca_key else key
    cert = builder.sign(signing_key, hashes.SHA256())
    
    cert_dir = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(cert_dir, f"{name}_key.pem"), "wb") as f:
        f.write(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.TraditionalOpenSSL, serialization.NoEncryption()))
    with open(os.path.join(cert_dir, f"{name}_cert.pem"), "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))
    return key, cert

print("Regenerating fixed mTLS certs...")
ca_key, ca_cert = create_cert("ca", u"QSP3 Root CA")
create_cert("server", u"localhost", ca_cert, ca_key)
create_cert("client", u"localhost", ca_cert, ca_key)
print("Done!")
