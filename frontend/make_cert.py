from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
import datetime
import ipaddress

key = rsa.generate_private_key(65537, 2048)

name = x509.Name([
    x509.NameAttribute(NameOID.COMMON_NAME, "192.168.31.88")
])

cert = (
    x509.CertificateBuilder()
    .subject_name(name)
    .issuer_name(name)
    .public_key(key.public_key())
    .serial_number(x509.random_serial_number())
    .not_valid_before(
        datetime.datetime.now(datetime.timezone.utc)
        - datetime.timedelta(minutes=1)
    )
    .not_valid_after(
        datetime.datetime.now(datetime.timezone.utc)
        + datetime.timedelta(days=365)
    )
    .add_extension(
        x509.SubjectAlternativeName([
            x509.IPAddress(
                ipaddress.ip_address("192.168.31.88")
            )
        ]),
        critical=False
    )
    .sign(key, hashes.SHA256())
)

with open("localhost-key.pem", "wb") as f:
    f.write(key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.TraditionalOpenSSL,
        serialization.NoEncryption()
    ))

with open("localhost-cert.pem", "wb") as f:
    f.write(cert.public_bytes(serialization.Encoding.PEM))

print("CERTIFICATE CREATED")