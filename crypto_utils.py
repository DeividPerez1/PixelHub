"""Cryptographic utilities for secure client-server communication (Practice 3).

This module implements hybrid cryptography as taught in Python Cryptography:
1. X.509 Certificate Generation & Verification:
   - Validates client public certificates against a trusted Certification Authority (CA).
2. Asymmetric Key Exchange (RSA-OAEP with SHA-256):
   - Securely wraps/unwraps a temporary symmetric AES session key.
3. Authenticated Symmetric Encryption (AES-GCM with 256-bit key & 12-byte nonce):
   - Protects application request and response payloads with confidentiality and integrity.
"""

from __future__ import annotations

import datetime
import ipaddress
import json
import os
from pathlib import Path
from typing import Any

from cryptography import x509
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.x509.oid import NameOID

# Default directory where certificates and keys are stored
CERTS_DIR = Path(__file__).resolve().parent / "certs"


# ============================================================================
# 1. Certificate and Key Generation (CA, Server, and Clients)
# ============================================================================

def generate_rsa_private_key(key_size: int = 2048) -> rsa.RSAPrivateKey:
    """Generate an RSA private key with the standard public exponent 65537."""
    return rsa.generate_private_key(
        public_exponent=65537,
        key_size=key_size,
    )


def serialize_private_key(key: rsa.RSAPrivateKey) -> bytes:
    """Serialize an RSA private key to PEM format without passphrase encryption."""
    return key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )


def serialize_certificate(cert: x509.Certificate) -> bytes:
    """Serialize an X.509 certificate to PEM format."""
    return cert.public_bytes(encoding=serialization.Encoding.PEM)


def load_certificate_from_pem(pem_bytes: bytes) -> x509.Certificate:
    """Parse a PEM-encoded X.509 certificate."""
    return x509.load_pem_x509_certificate(pem_bytes)


def load_private_key_from_pem(pem_bytes: bytes) -> rsa.RSAPrivateKey:
    """Parse a PEM-encoded RSA private key."""
    key = serialization.load_pem_private_key(pem_bytes, password=None)
    if not isinstance(key, rsa.RSAPrivateKey):
        raise ValueError("Key is not an RSA private key.")
    return key


def create_ca(common_name: str = "PixelHub Root CA") -> tuple[x509.Certificate, rsa.RSAPrivateKey]:
    """Create a self-signed root Certification Authority (CA).

    The CA acts as the trusted anchor for validating all server and client certificates.
    """
    private_key = generate_rsa_private_key()
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "ES"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "PixelHub Security"),
        x509.NameAttribute(NameOID.COMMON_NAME, common_name),
    ])

    now = datetime.datetime.now(datetime.timezone.utc)
    certificate = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(days=1))
        .not_valid_after(now + datetime.timedelta(days=365))
        .add_extension(
            x509.BasicConstraints(ca=True, path_length=None),
            critical=True,
        )
        .sign(private_key, hashes.SHA256())
    )
    return certificate, private_key


def issue_certificate(
    common_name: str,
    ca_cert: x509.Certificate,
    ca_key: rsa.RSAPrivateKey,
    is_server: bool = False,
) -> tuple[x509.Certificate, rsa.RSAPrivateKey]:
    """Issue a leaf certificate signed by the trusted CA (for server or client)."""
    private_key = generate_rsa_private_key()
    subject = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "ES"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "PixelHub"),
        x509.NameAttribute(NameOID.COMMON_NAME, common_name),
    ])

    now = datetime.datetime.now(datetime.timezone.utc)
    builder = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(ca_cert.subject)
        .public_key(private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(days=1))
        .not_valid_after(now + datetime.timedelta(days=365))
        .add_extension(
            x509.BasicConstraints(ca=False, path_length=None),
            critical=True,
        )
    )

    if is_server:
        builder = builder.add_extension(
            x509.SubjectAlternativeName([
                x509.DNSName("localhost"),
                x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
            ]),
            critical=False,
        )

    certificate = builder.sign(ca_key, hashes.SHA256())
    return certificate, private_key


def ensure_certificates_exist(target_dir: Path | None = None) -> None:
    """Generate CA, server, and client certificates if they do not already exist."""
    certs_path = target_dir or CERTS_DIR
    certs_path.mkdir(parents=True, exist_ok=True)

    ca_cert_file = certs_path / "ca_cert.pem"
    ca_key_file = certs_path / "ca_key.pem"

    if not (ca_cert_file.exists() and ca_key_file.exists()):
        ca_cert, ca_key = create_ca()
        ca_cert_file.write_bytes(serialize_certificate(ca_cert))
        ca_key_file.write_bytes(serialize_private_key(ca_key))
    else:
        ca_cert = load_certificate_from_pem(ca_cert_file.read_bytes())
        ca_key = load_private_key_from_pem(ca_key_file.read_bytes())

    # Generate server certificate
    server_cert_file = certs_path / "server_cert.pem"
    server_key_file = certs_path / "server_key.pem"
    if not (server_cert_file.exists() and server_key_file.exists()):
        s_cert, s_key = issue_certificate("PixelHub Server", ca_cert, ca_key, is_server=True)
        server_cert_file.write_bytes(serialize_certificate(s_cert))
        server_key_file.write_bytes(serialize_private_key(s_key))

    # Generate at least two client certificates (client1 and client2)
    for client_name in ("client1", "client2"):
        c_cert_file = certs_path / f"{client_name}_cert.pem"
        c_key_file = certs_path / f"{client_name}_key.pem"
        if not (c_cert_file.exists() and c_key_file.exists()):
            c_cert, c_key = issue_certificate(client_name, ca_cert, ca_key, is_server=False)
            c_cert_file.write_bytes(serialize_certificate(c_cert))
            c_key_file.write_bytes(serialize_private_key(c_key))


# ============================================================================
# 2. Certificate Validation
# ============================================================================

def verify_certificate_against_ca(
    cert: x509.Certificate,
    ca_cert: x509.Certificate,
) -> tuple[bool, str]:
    """Verify that a certificate is currently valid and was signed by the trusted CA.

    Returns:
        (True, "OK") if the certificate is authentic and valid.
        (False, error_reason) if validation fails.
    """
    now = datetime.datetime.now(datetime.timezone.utc)

    # 1. Check validity dates
    if now < cert.not_valid_before_utc:
        return False, "Certificate is not yet valid."
    if now > cert.not_valid_after_utc:
        return False, "Certificate has expired."

    # 2. Check issuer matches CA subject
    if cert.issuer != ca_cert.subject:
        return False, "Certificate was not issued by the trusted CA."

    # 3. Cryptographically verify the digital signature using the CA public key
    try:
        ca_public_key = ca_cert.public_key()
        if not isinstance(ca_public_key, rsa.RSAPublicKey):
            return False, "CA public key is not an RSA key."

        ca_public_key.verify(
            cert.signature,
            cert.tbs_certificate_bytes,
            padding.PKCS1v15(),
            cert.signature_hash_algorithm,
        )
        return True, "Certificate verified successfully."
    except InvalidSignature:
        return False, "Invalid certificate signature."
    except Exception as error:
        return False, f"Certificate verification error: {error}"


# ============================================================================
# 3. Asymmetric Encryption: RSA-OAEP (Slides 18-19)
# ============================================================================

def encrypt_session_key(public_key: rsa.RSAPublicKey, aes_key: bytes) -> bytes:
    """Encrypt a symmetric AES session key using the recipient's RSA public key (RSA-OAEP)."""
    return public_key.encrypt(
        aes_key,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )


def decrypt_session_key(private_key: rsa.RSAPrivateKey, encrypted_key: bytes) -> bytes:
    """Decrypt a symmetric AES session key using the recipient's RSA private key (RSA-OAEP)."""
    return private_key.decrypt(
        encrypted_key,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )


# ============================================================================
# 4. Symmetric Encryption: AES-GCM (Slides 11-13)
# ============================================================================

def generate_aes_key() -> bytes:
    """Generate a random 256-bit symmetric session key for AES-GCM."""
    return AESGCM.generate_key(bit_length=256)


def encrypt_payload(aes_key: bytes, plaintext_data: dict[str, Any] | str) -> dict[str, str]:
    """Encrypt JSON or string payload with AES-GCM using a fresh 12-byte nonce.

    Returns a dictionary with 'nonce' and 'ciphertext' encoded as hex strings.
    """
    if isinstance(plaintext_data, dict):
        raw_bytes = json.dumps(plaintext_data).encode("utf-8")
    else:
        raw_bytes = plaintext_data.encode("utf-8")

    aes = AESGCM(aes_key)
    nonce = os.urandom(12)  # Standard 96-bit nonce for AES-GCM
    ciphertext = aes.encrypt(nonce, raw_bytes, None)

    return {
        "nonce": nonce.hex(),
        "ciphertext": ciphertext.hex(),
    }


def decrypt_payload(aes_key: bytes, nonce_hex: str, ciphertext_hex: str) -> dict[str, Any]:
    """Decrypt an AES-GCM payload and decode it as a JSON object."""
    aes = AESGCM(aes_key)
    nonce = bytes.fromhex(nonce_hex)
    ciphertext = bytes.fromhex(ciphertext_hex)

    decrypted_bytes = aes.decrypt(nonce, ciphertext, None)
    return json.loads(decrypted_bytes.decode("utf-8"))
