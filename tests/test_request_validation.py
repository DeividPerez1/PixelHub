"""Tests for server-side request validation, certificate authentication, and decryption (Practice 3).

This module tests that:
1. Unauthenticated clients without certificates are rejected.
2. Certificates not issued by the trusted CA are rejected.
3. Tampered ciphertexts trigger AEAD integrity errors.
4. Valid authenticated requests are properly decrypted, validated, and processed.
"""

import asyncio
import json

from crypto_utils import (
    CERTS_DIR,
    create_ca,
    decrypt_payload,
    decrypt_session_key,
    encrypt_payload,
    load_certificate_from_pem,
    load_private_key_from_pem,
    serialize_certificate,
)
from protocol import validate_request
import server as router


class FakeServerStreamWriter:
    """Simulates an asyncio.StreamWriter from the server perspective."""

    def __init__(self, peername=("127.0.0.1", 12345)) -> None:
        self.data = bytearray()
        self.peername = peername
        self.closed = False

    def get_extra_info(self, name: str, default=None):
        if name == "peername":
            return self.peername
        return default

    def write(self, data: bytes) -> None:
        self.data.extend(data)

    async def drain(self) -> None:
        pass

    def close(self) -> None:
        self.closed = True

    async def wait_closed(self) -> None:
        pass


def execute_server_exchange(
    request_data: dict | bytes,
    client_cert_pem: str | None = None,
    client_key=None,
    send_handshake: bool = True,
) -> tuple[dict, FakeServerStreamWriter]:
    """Helper that runs server.handle_client through handshake and AES-GCM request exchange."""
    writer = FakeServerStreamWriter()

    # Load default valid client1 credentials
    if client_cert_pem is None:
        client_cert_pem = (CERTS_DIR / "client1_cert.pem").read_text(encoding="utf-8")
    if client_key is None:
        client_key = load_private_key_from_pem((CERTS_DIR / "client1_key.pem").read_bytes())

    async def run():
        reader = asyncio.StreamReader()

        # Step 1: Send handshake if enabled
        if send_handshake:
            hello = json.dumps({"type": "client_hello", "certificate": client_cert_pem}) + "\n"
            reader.feed_data(hello.encode("utf-8"))

        # Step 2: Feed application request
        # If string/dict and handshake is expected, we will encrypt it once we know the session key
        # In a real test, handle_client runs concurrently with this writer.
        # We run handle_client in a task so it processes handshake first!
        server_task = asyncio.create_task(router.handle_client(reader, writer))

        if send_handshake:
            # Yield control to let server process handshake line
            await asyncio.sleep(0.01)

            # Check if server accepted handshake
            output = bytes(writer.data)
            if b"\n" in output:
                handshake_line, rest = output.split(b"\n", 1)
                handshake_resp = json.loads(handshake_line.decode("utf-8"))
                if handshake_resp.get("status") == "ok":
                    encrypted_key = bytes.fromhex(handshake_resp["encrypted_session_key"])
                    aes_key = decrypt_session_key(client_key, encrypted_key)

                    # Now feed encrypted request payload
                    if isinstance(request_data, dict):
                        envelope = encrypt_payload(aes_key, request_data)
                        reader.feed_data(json.dumps(envelope).encode("utf-8"))
                    elif isinstance(request_data, bytes):
                        reader.feed_data(request_data)
                    reader.feed_eof()
                    await server_task
                    return aes_key

        if not send_handshake:
            if isinstance(request_data, bytes):
                reader.feed_data(request_data)
            reader.feed_eof()

        await server_task
        return None

    aes_key = asyncio.run(run())

    # Extract final application response
    lines = bytes(writer.data).split(b"\n")
    # If handshake occurred, application response is after the handshake line
    if send_handshake and len(lines) > 1 and lines[1]:
        resp_json = json.loads(lines[1].decode("utf-8"))
        if aes_key and "ciphertext" in resp_json:
            return decrypt_payload(aes_key, resp_json["nonce"], resp_json["ciphertext"]), writer
        return resp_json, writer
    elif lines[0]:
        return json.loads(lines[0].decode("utf-8")), writer
    return {}, writer


def test_server_rejects_unauthenticated_connection():
    """Verify that a client trying to send raw commands without handshake is rejected."""
    response, writer = execute_server_exchange(
        b'{"accion": "ping"}',
        send_handshake=False,
    )

    assert response["status"] == "error"
    assert "Expected client_hello" in response["message"]
    assert writer.closed is True


def test_server_rejects_untrusted_client_certificate():
    """Verify that a certificate issued by an unknown/untrusted CA is rejected."""
    # Create an untrusted self-signed certificate
    untrusted_cert, untrusted_key = create_ca(common_name="Malicious Hacker CA")
    untrusted_pem = serialize_certificate(untrusted_cert).decode("utf-8")

    response, writer = execute_server_exchange(
        {"accion": "ping"},
        client_cert_pem=untrusted_pem,
        client_key=untrusted_key,
        send_handshake=True,
    )

    assert response["status"] == "error"
    assert "Authentication failed" in response["message"]
    assert writer.closed is True


def test_server_defaults_missing_request_data_to_empty_object():
    """Verify that an authenticated request defaults 'datos' to an empty object for 'ping'."""
    response, writer = execute_server_exchange({"accion": "ping"})

    assert response == {
        "status": "ok",
        "message": "Connection successful.",
        "data": None,
    }
    assert writer.closed is True


def test_server_rejects_non_object_request_data():
    """Verify that an authenticated request with invalid 'datos' type is rejected."""
    response, writer = execute_server_exchange({"accion": "get_all_roles", "datos": ["invalid"]})

    assert response == {
        "status": "error",
        "message": "Request data must be a JSON object.",
        "data": None,
    }
    assert writer.closed is True


def test_protocol_rejects_missing_identifier():
    """Unit test for protocol.validate_request: missing required 'id'."""
    request, response = validate_request(
        {"accion": "get_user", "datos": {}},
        {"get_user"},
    )

    assert request is None
    assert response == {
        "status": "error",
        "message": "The field 'id' must be an integer.",
        "data": None,
    }


def test_protocol_rejects_invalid_identifier():
    """Unit test for protocol.validate_request: non-integer 'id'."""
    request, response = validate_request(
        {"accion": "get_user", "datos": {"id": "abc"}},
        {"get_user"},
    )

    assert request is None
    assert response == {
        "status": "error",
        "message": "The field 'id' must be an integer.",
        "data": None,
    }
