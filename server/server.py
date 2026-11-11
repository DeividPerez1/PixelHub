"""Asynchronous TCP server with certificate authentication and AES-GCM encryption."""

import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Callable

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from crypto_utils import (
    CERTS_DIR,
    decrypt_payload,
    encrypt_payload,
    encrypt_session_key,
    ensure_certificates_exist,
    generate_aes_key,
    load_certificate_from_pem,
    verify_certificate_against_ca,
)
from domain.db import Session, engine
from domain.dtos import Response
from domain.repository import (
    CategoryRepository,
    PostRepository,
    ProfileRepository,
    RoleRepository,
    TagRepository,
    UserRepository,
)
from protocol import error_response, validate_request
from services.category_service import process_category_actions
from services.post_service import process_post_actions
from services.profile_service import process_profile_actions
from services.role_service import process_role_actions
from services.tag_service import process_tag_actions
from services.user_service import process_user_actions

SERVER_HOST = "127.0.0.1"
SERVER_PORT = 5000
SOCKET_TIMEOUT = 10

HOST = SERVER_HOST
PORT = SERVER_PORT

# Path to the trusted Certification Authority (CA) certificate
CA_CERT_PATH = CERTS_DIR / "ca_cert.pem"

ActionProcessor = Callable[
    [str, dict[str, Any], Any, Session],
    dict[str, Any],
]

ACTION_HANDLERS: dict[str, tuple[str, ActionProcessor]] = {
    "add_user": ("user", process_user_actions),
    "delete_user": ("user", process_user_actions),
    "update_user": ("user", process_user_actions),
    "get_all_users": ("user", process_user_actions),
    "get_user": ("user", process_user_actions),
    "get_user_by_username": ("user", process_user_actions),
    "get_user_by_email": ("user", process_user_actions),
    "add_role": ("role", process_role_actions),
    "delete_role": ("role", process_role_actions),
    "update_role": ("role", process_role_actions),
    "get_all_roles": ("role", process_role_actions),
    "get_role": ("role", process_role_actions),
    "add_profile": ("profile", process_profile_actions),
    "delete_profile": ("profile", process_profile_actions),
    "update_profile": ("profile", process_profile_actions),
    "get_all_profiles": ("profile", process_profile_actions),
    "get_profile": ("profile", process_profile_actions),
    "add_post": ("post", process_post_actions),
    "delete_post": ("post", process_post_actions),
    "update_post": ("post", process_post_actions),
    "get_all_posts": ("post", process_post_actions),
    "get_post": ("post", process_post_actions),
    "get_posts_by_category": ("post", process_post_actions),
    "get_posts_by_user": ("post", process_post_actions),
    "get_last_posts": ("post", process_post_actions),
    "add_category": ("category", process_category_actions),
    "delete_category": ("category", process_category_actions),
    "update_category": ("category", process_category_actions),
    "get_all_categories": ("category", process_category_actions),
    "get_category": ("category", process_category_actions),
    "add_tag": ("tag", process_tag_actions),
    "delete_tag": ("tag", process_tag_actions),
    "update_tag": ("tag", process_tag_actions),
    "get_all_tags": ("tag", process_tag_actions),
    "get_tag": ("tag", process_tag_actions),
}

REPOSITORIES = {
    "user": UserRepository,
    "role": RoleRepository,
    "profile": ProfileRepository,
    "post": PostRepository,
    "category": CategoryRepository,
    "tag": TagRepository,
}


def _get_ca_certificate():
    """Load the trusted root CA certificate from disk (generates certs if missing)."""
    ensure_certificates_exist()
    return load_certificate_from_pem(CA_CERT_PATH.read_bytes())


def _process_database_action(
    action: str,
    data: dict[str, Any],
) -> dict[str, Any]:
    """Run the existing synchronous service and database workflow in a worker thread."""
    entity, processor = ACTION_HANDLERS[action]
    session = Session(bind=engine)

    try:
        repository = REPOSITORIES[entity](session)
        return processor(action, data, repository, session)
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


async def _create_response(request: dict[str, Any]) -> dict[str, Any]:
    """Validate a request and execute its action without blocking the loop."""
    validated_request, validation_error = validate_request(
        request,
        set(ACTION_HANDLERS),
    )
    if validation_error:
        return validation_error

    action = validated_request["action"]
    data = validated_request["data"]
    if action == "ping":
        return {
            "status": "ok",
            "message": "Connection successful.",
            "data": None,
        }

    # Run synchronous SQLAlchemy and service code in a worker thread.
    return await asyncio.to_thread(_process_database_action, action, data)


async def _handle_handshake(
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
) -> bytes | None:
    """Authenticate client certificate against trusted CA and establish AES session key.

    Returns the shared AES session key (bytes) on success, or None on failure.
    """
    handshake_line = await asyncio.wait_for(reader.readline(), timeout=SOCKET_TIMEOUT)
    if not handshake_line:
        return None

    try:
        hello_msg = json.loads(handshake_line.decode("utf-8"))
    except Exception as error:
        error_resp = json.dumps({"status": "error", "message": f"Malformed handshake: {error}"}) + "\n"
        writer.write(error_resp.encode("utf-8"))
        await writer.drain()
        return None

    # Verify message structure and certificate presence
    if hello_msg.get("type") != "client_hello" or "certificate" not in hello_msg:
        error_resp = json.dumps({"status": "error", "message": "Expected client_hello with certificate."}) + "\n"
        writer.write(error_resp.encode("utf-8"))
        await writer.drain()
        return None

    # Load and validate client certificate against the trusted CA
    try:
        client_cert = load_certificate_from_pem(hello_msg["certificate"].encode("utf-8"))
        ca_cert = _get_ca_certificate()
        is_valid, reason = verify_certificate_against_ca(client_cert, ca_cert)
        if not is_valid:
            error_resp = json.dumps({"status": "error", "message": f"Authentication failed: {reason}"}) + "\n"
            writer.write(error_resp.encode("utf-8"))
            await writer.drain()
            return None
    except Exception as error:
        error_resp = json.dumps({"status": "error", "message": f"Invalid certificate format: {error}"}) + "\n"
        writer.write(error_resp.encode("utf-8"))
        await writer.drain()
        return None

    # Generate AES session key and wrap it using client public key (RSA-OAEP)
    aes_key = generate_aes_key()
    encrypted_key = encrypt_session_key(client_cert.public_key(), aes_key)

    accept_msg = json.dumps({
        "status": "ok",
        "encrypted_session_key": encrypted_key.hex(),
    }) + "\n"
    writer.write(accept_msg.encode("utf-8"))
    await writer.drain()

    return aes_key


async def handle_client(
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
) -> None:
    """Process one secure client connection with authentication, AES encryption, and safe cleanup."""
    address = writer.get_extra_info("peername")

    try:
        # Phase 1: Authenticate client and establish AES session key
        aes_key = await _handle_handshake(reader, writer)
        if aes_key is None:
            return

        # Phase 2: Read encrypted application request until EOF
        encrypted_data = await asyncio.wait_for(
            reader.read(),
            timeout=SOCKET_TIMEOUT,
        )
        if not encrypted_data:
            return

        # Decrypt payload using the established AES-GCM session key
        try:
            envelope = json.loads(encrypted_data.decode("utf-8"))
            request = decrypt_payload(aes_key, envelope["nonce"], envelope["ciphertext"])
        except Exception as error:
            error_envelope = encrypt_payload(aes_key, error_response(f"Decryption error: {error}"))
            writer.write(json.dumps(error_envelope).encode("utf-8"))
            await writer.drain()
            return

        # Execute application logic and routing
        response = await _create_response(request)

        # Encrypt response with AES-GCM and send back to client
        encrypted_response = encrypt_payload(aes_key, response)
        writer.write(json.dumps(encrypted_response).encode("utf-8"))
        await writer.drain()

    except (asyncio.TimeoutError, ConnectionResetError, BrokenPipeError):
        print(f"Client disconnected or timed out: {address}")
    except Exception as error:
        print(f"Server error from {address}: {error}")
    finally:
        writer.close()
        try:
            await writer.wait_closed()
        except (ConnectionResetError, BrokenPipeError):
            pass


async def start_server() -> None:
    """Start the secure asynchronous server."""
    _get_ca_certificate()  # Ensure certificates are generated before listening
    server = await asyncio.start_server(handle_client, HOST, PORT)
    addresses = ", ".join(
        str(socket.getsockname()) for socket in server.sockets or []
    )
    print(f"PixelHub secure async server listening on {addresses}")

    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(start_server())
