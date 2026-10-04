#!/usr/bin/env python3
"""Generate a self-signed cert for the phone-voice HTTPS listener.

SANs cover the laptop LAN IP (crew phone reaches it over Wi-Fi) plus
localhost/127.0.0.1 (USB adb underscore). The browser will still show a
self-signed warning on first visit; proceeding treats the page as a secure
context so the Web Speech mic is authorizable.
"""
import os
import datetime

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

IP = "10.203.252.92"
BASE = os.path.dirname(os.path.abspath(__file__))
CERT = os.path.join(BASE, "certs", "cert.pem")
KEY = os.path.join(BASE, "certs", "key.pem")

os.makedirs(os.path.join(BASE, "certs"), exist_ok=True)

key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, IP)])
now = datetime.datetime.now(datetime.timezone.utc)
san = x509.SubjectAlternativeName(
    [x509.IPAddress(__import__("ipaddress").ip_address(IP)),
     x509.DNSName("localhost"),
     x509.IPAddress(__import__("ipaddress").ip_address("127.0.0.1"))]
)
cert = (
    x509.CertificateBuilder()
    .subject_name(name)
    .issuer_name(name)
    .public_key(key.public_key())
    .serial_number(x509.random_serial_number())
    .not_valid_before(now - datetime.timedelta(minutes=1))
    .not_valid_after(now + datetime.timedelta(days=365))
    .add_extension(san, critical=False)
    .add_extension(
        x509.BasicConstraints(ca=True, path_length=None), critical=True
    )
    .sign(key, hashes.SHA256())
)

with open(KEY, "wb") as f:
    f.write(key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.TraditionalOpenSSL,
        serialization.NoEncryption(),
    ))
with open(CERT, "wb") as f:
    f.write(cert.public_bytes(serialization.Encoding.PEM))

print("wrote:", CERT)
print("wrote:", KEY)