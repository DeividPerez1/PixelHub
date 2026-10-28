"""TCP server that receives actions from the PixelHub client."""

SERVER_HOST = "127.0.0.1"
SERVER_PORT = 5000
SOCKET_TIMEOUT = 10
BUFFER_SIZE = 4096

import json
import socket
from typing import Any

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
from services.category_service import process_category_actions
from services.post_service import process_post_actions
from services.profile_service import process_profile_actions
from services.role_service import process_role_actions
from services.tag_service import process_tag_actions
from services.user_service import process_user_actions
from protocol import error_response, validate_request


HOST = SERVER_HOST
PORT = SERVER_PORT

ACTION_HANDLERS = {
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


def _send_json(connection, response: Response | dict[str, Any]):
    connection.sendall(json.dumps(response).encode("utf-8"))


def _read_request(connection) -> bytes:
    """Read request chunks until the client closes its sending side."""
    request_data = bytearray()

    while True:
        chunk = connection.recv(BUFFER_SIZE)
        if not chunk:
            break
        request_data.extend(chunk)

    return bytes(request_data)


def _process_database_action(action, data):
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


def _create_response(request: dict[str, Any]) -> dict[str, Any]:
    validated_request, validation_error = validate_request(
        request, set(ACTION_HANDLERS)
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

    return _process_database_action(action, data)


def _close_socket(connection):
    """Close a real socket while keeping the helper easy to test."""
    close = getattr(connection, "close", None)
    if close is not None:
        close()


def start_server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((HOST, PORT))
        server_socket.listen()
        print(f"PixelHub server listening on {HOST}:{PORT}...")

        while True:
            connection, address = server_socket.accept()

            try:
                request_data = _read_request(connection)
                if not request_data:
                    continue

                request = json.loads(request_data.decode("utf-8"))
                response = _create_response(request)
                _send_json(connection, response)
            except Exception as error:
                print(f"Server request error from {address}: {error}")
                _send_json(
                    connection,
                    error_response(f"Internal server error: {error}"),
                )
            finally:
                _close_socket(connection)
    finally:
        _close_socket(server_socket)


if __name__ == "__main__":
    start_server()
