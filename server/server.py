"""Asynchronous TCP server for the PixelHub client."""

import asyncio
import json
from typing import Any, Callable

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


def _encode_response(response: Response | dict[str, Any]) -> bytes:
    """Encode a response as UTF-8 JSON."""
    return json.dumps(response).encode("utf-8")


def _decode_request(request_data: bytes) -> dict[str, Any]:
    """Decode a UTF-8 JSON request."""
    request = json.loads(request_data.decode("utf-8"))
    if not isinstance(request, dict):
        raise ValueError("The request must be a JSON object.")
    return request


def _process_database_action(
    action: str,
    data: dict[str, Any],
) -> dict[str, Any]:
    """Run the existing synchronous service and database workflow."""
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


async def _send_response(
    writer: asyncio.StreamWriter,
    response: Response | dict[str, Any],
) -> None:
    """Write a JSON response and wait until it is handed to the OS."""
    writer.write(_encode_response(response))
    # Drain prevents an unbounded write buffer when a client is slow.
    await writer.drain()


async def handle_client(
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
) -> None:
    """Process one client connection and close it safely."""
    address = writer.get_extra_info("peername")

    try:
        # Read until the client sends EOF, preserving the existing protocol.
        request_data = await asyncio.wait_for(
            reader.read(),
            timeout=SOCKET_TIMEOUT,
        )
        if not request_data:
            return

        request = _decode_request(request_data)
        response = await _create_response(request)
        await _send_response(writer, response)
    except (asyncio.TimeoutError, ConnectionResetError, BrokenPipeError):
        print(f"Client disconnected or timed out: {address}")
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        try:
            await _send_response(writer, error_response(str(error)))
        except (ConnectionResetError, BrokenPipeError):
            print(f"Client disconnected before receiving an error: {address}")
    except Exception as error:
        print(f"Server request error from {address}: {error}")
        try:
            await _send_response(
                writer,
                error_response(f"Internal server error: {error}"),
            )
        except (ConnectionResetError, BrokenPipeError):
            print(f"Client disconnected before receiving an error: {address}")
    finally:
        # Always release the connection, including after client failures.
        writer.close()
        try:
            await writer.wait_closed()
        except (ConnectionResetError, BrokenPipeError):
            pass


async def start_server() -> None:
    """Start the asynchronous server and serve clients indefinitely."""
    server = await asyncio.start_server(handle_client, HOST, PORT)
    addresses = ", ".join(
        str(socket.getsockname()) for socket in server.sockets or []
    )
    print(f"PixelHub async server listening on {addresses}")

    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(start_server())
