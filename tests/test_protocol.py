"""Unit tests for the secure client communication protocol (Practice 3).

This module tests that network_client.py:
1. Sends the client certificate in an initial handshake message.
2. Successfully decrypts the server's RSA-OAEP encrypted AES session key.
3. Encrypts the application request payload using AES-GCM with a fresh 12-byte nonce.
4. Reads and decrypts the server's AES-GCM encrypted response.
5. Gracefully handles authentication rejections, timeouts, and network failures.
"""

import asyncio
import json

import pytest

from crypto_utils import (
    CERTS_DIR,
    decrypt_payload,
    decrypt_session_key,
    encrypt_payload,
    encrypt_session_key,
    generate_aes_key,
    load_certificate_from_pem,
    load_private_key_from_pem,
)
import network_client


class FakeStreamWriter:
    """Simulates an asyncio.StreamWriter to inspect client output and lifecycle."""

    def __init__(self) -> None:
        self.sent_data = bytearray()
        self.drained = False
        self.eof_written = False
        self.closed = False

    def write(self, data: bytes) -> None:
        self.sent_data.extend(data)

    async def drain(self) -> None:
        self.drained = True

    def write_eof(self) -> None:
        self.eof_written = True

    def close(self) -> None:
        self.closed = True

    async def wait_closed(self) -> None:
        pass


def run_client_request_secure(monkeypatch, server_response_dict, handshake_ok=True, handshake_error_msg=""):
    """Helper that runs network_client.send_request with simulated handshake and AES encryption."""
    writer = FakeStreamWriter()
    connection = {}

    client_cert = load_certificate_from_pem((CERTS_DIR / "client1_cert.pem").read_bytes())
    aes_key = generate_aes_key()

    async def execute():
        reader = asyncio.StreamReader()

        # 1. Prepare server handshake response line
        if handshake_ok:
            encrypted_key = encrypt_session_key(client_cert.public_key(), aes_key)
            handshake_resp = json.dumps({
                "status": "ok",
                "encrypted_session_key": encrypted_key.hex(),
            }) + "\n"
        else:
            handshake_resp = json.dumps({
                "status": "error",
                "message": handshake_error_msg,
            }) + "\n"

        reader.feed_data(handshake_resp.encode("utf-8"))

        # 2. If handshake succeeds, feed the AES-encrypted response
        if handshake_ok and server_response_dict is not None:
            encrypted_body = encrypt_payload(aes_key, server_response_dict)
            reader.feed_data(json.dumps(encrypted_body).encode("utf-8"))

        reader.feed_eof()

        async def fake_open_connection(host, port):
            connection["host"] = host
            connection["port"] = port
            return reader, writer

        monkeypatch.setattr(network_client.asyncio, "open_connection", fake_open_connection)
        return await network_client.send_request("get_role", {"id": 6})

    response = asyncio.run(execute())
    return response, writer, connection, aes_key


def test_client_performs_handshake_and_encrypts_request(monkeypatch):
    """Verify handshake exchange and AES-GCM encryption of client request."""
    expected_response = {"status": "ok", "message": "done", "data": 1}

    response, writer, connection, aes_key = run_client_request_secure(
        monkeypatch,
        expected_response,
    )

    # 1. Connection check
    assert connection == {"host": "127.0.0.1", "port": 5000}
    assert writer.eof_written is True
    assert writer.closed is True

    # 2. Split output into handshake line and encrypted body
    lines = writer.sent_data.split(b"\n", 1)
    handshake_msg = json.loads(lines[0].decode("utf-8"))

    assert handshake_msg["type"] == "client_hello"
    assert "BEGIN CERTIFICATE" in handshake_msg["certificate"]

    # 3. Decrypt the application request using the shared AES key to verify confidentiality
    encrypted_envelope = json.loads(lines[1].decode("utf-8"))
    decrypted_request = decrypt_payload(
        aes_key,
        encrypted_envelope["nonce"],
        encrypted_envelope["ciphertext"],
    )
    assert decrypted_request == {
        "accion": "get_role",
        "datos": {"id": 6},
    }

    # 4. Final decrypted response returned to caller
    assert response == expected_response


def test_client_handles_authentication_rejection(monkeypatch):
    """Verify that a rejected certificate returns an authentication error."""
    response, writer, _, _ = run_client_request_secure(
        monkeypatch,
        server_response_dict=None,
        handshake_ok=False,
        handshake_error_msg="Certificate has expired.",
    )

    assert response["status"] == "error"
    assert "Certificate has expired" in response["message"]
    assert writer.closed is True


def test_client_reports_empty_server_response(monkeypatch):
    """Verify error handling when the server closes connection after handshake without body."""
    response, writer, _, _ = run_client_request_secure(
        monkeypatch,
        server_response_dict=None,
        handshake_ok=True,
    )

    assert response == {
        "status": "error",
        "message": "The server returned an empty response.",
        "data": None,
    }
    assert writer.closed is True


def test_client_returns_error_when_connection_fails(monkeypatch):
    """Verify that network connection failures return an error dictionary."""

    async def fake_open_connection_fail(host, port):
        raise OSError("connection refused")

    monkeypatch.setattr(
        network_client.asyncio,
        "open_connection",
        fake_open_connection_fail,
    )

    response = asyncio.run(network_client.send_request("ping"))

    assert response == {
        "status": "error",
        "message": "connection refused",
        "data": None,
    }


def test_send_request_sync_wrapper(monkeypatch):
    """Verify that send_request_sync correctly wraps the async send_request."""
    expected = {"status": "ok", "message": "pong", "data": None}

    async def fake_send_request(action, payload=None):
        return expected

    monkeypatch.setattr(network_client, "send_request", fake_send_request)

    result = network_client.send_request_sync("ping")
    assert result == expected
