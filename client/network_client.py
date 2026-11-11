"""Secure asynchronous TCP client for the PixelHub command-line interface."""

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any
from rich.console import Console

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from crypto_utils import (
    CERTS_DIR,
    decrypt_payload,
    decrypt_session_key,
    encrypt_payload,
    ensure_certificates_exist,
    load_certificate_from_pem,
    load_private_key_from_pem,
)

console = Console()

SERVER_HOST = "127.0.0.1"
SERVER_PORT = 5000
SOCKET_TIMEOUT = 10

# Default client identity is 'client1' (can be switched to 'client2' or custom)
CURRENT_CLIENT_NAME = os.environ.get("PIXELHUB_CLIENT", "client1")


def set_client_identity(client_name: str) -> None:
    """Switch client certificate identity (e.g., 'client1' or 'client2')."""
    global CURRENT_CLIENT_NAME
    CURRENT_CLIENT_NAME = client_name


def _get_client_credentials() -> tuple[str, Any]:
    """Load the PEM certificate string and RSA private key for the active client."""
    ensure_certificates_exist()
    cert_path = CERTS_DIR / f"{CURRENT_CLIENT_NAME}_cert.pem"
    key_path = CERTS_DIR / f"{CURRENT_CLIENT_NAME}_key.pem"

    if not cert_path.exists() or not key_path.exists():
        raise FileNotFoundError(
            f"Client credentials for '{CURRENT_CLIENT_NAME}' not found in {CERTS_DIR}"
        )

    cert_pem = cert_path.read_text(encoding="utf-8")
    private_key = load_private_key_from_pem(key_path.read_bytes())
    return cert_pem, private_key


def _error_response(message: str) -> dict[str, Any]:
    """Create the standard response returned for a failed request."""
    return {"status": "error", "message": message, "data": None}


async def _perform_handshake(
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
    cert_pem: str,
    private_key: Any,
) -> bytes:
    """Send client certificate, receive RSA-encrypted AES key, and decrypt it.

    Returns the shared AES session key (bytes).
    """
    # 1. Send client hello with public certificate
    hello_msg = json.dumps({"type": "client_hello", "certificate": cert_pem}) + "\n"
    writer.write(hello_msg.encode("utf-8"))
    await writer.drain()

    # 2. Read server response line
    resp_line = await asyncio.wait_for(reader.readline(), timeout=SOCKET_TIMEOUT)
    if not resp_line:
        raise ConnectionError("The server closed connection during handshake.")

    handshake_resp = json.loads(resp_line.decode("utf-8"))
    if handshake_resp.get("status") != "ok":
        reason = handshake_resp.get("message", "Unknown authentication error")
        raise PermissionError(f"Authentication rejected by server: {reason}")

    # 3. Decrypt the symmetric AES session key using client RSA private key
    encrypted_key = bytes.fromhex(handshake_resp["encrypted_session_key"])
    return decrypt_session_key(private_key, encrypted_key)


async def send_request(
    action: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Perform secure handshake, send encrypted request via AES-GCM, and return decrypted response."""
    request = {"accion": action, "datos": payload or {}}

    try:
        cert_pem, private_key = _get_client_credentials()
    except Exception as error:
        return _error_response(f"Certificate load error: {error}")

    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(SERVER_HOST, SERVER_PORT),
            timeout=SOCKET_TIMEOUT,
        )
    except (OSError, asyncio.TimeoutError) as error:
        return _error_response(str(error))

    try:
        # Phase 1: Authentication and AES key establishment
        aes_key = await _perform_handshake(reader, writer, cert_pem, private_key)

        # Phase 2: Encrypt request with AES-GCM and send with EOF
        encrypted_envelope = encrypt_payload(aes_key, request)
        writer.write(json.dumps(encrypted_envelope).encode("utf-8"))
        await writer.drain()
        try:
            writer.write_eof()
        except (OSError, NotImplementedError):
            pass

        # Phase 3: Read and decrypt server response
        response_data = await asyncio.wait_for(
            reader.read(),
            timeout=SOCKET_TIMEOUT,
        )
        if not response_data:
            return _error_response("The server returned an empty response.")

        encrypted_resp = json.loads(response_data.decode("utf-8"))
        response = decrypt_payload(
            aes_key,
            encrypted_resp["nonce"],
            encrypted_resp["ciphertext"],
        )
        if not isinstance(response, dict):
            return _error_response("The server returned an invalid response.")
        return response

    except (
        OSError,
        asyncio.TimeoutError,
        PermissionError,
        UnicodeDecodeError,
        json.JSONDecodeError,
    ) as error:
        return _error_response(str(error))
    finally:
        writer.close()
        try:
            await writer.wait_closed()
        except (ConnectionResetError, BrokenPipeError):
            pass


def send_request_sync(
    action: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Call the async client from the existing synchronous Rich menus."""
    with console.status(
        f"[bold cyan]Processing '{action}' securely...",
        spinner="bouncingBar",
    ):
        return asyncio.run(send_request(action, payload))


if __name__ == "__main__":
    print(send_request_sync("ping"))
