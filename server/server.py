import json
import socket

from domain.db import Session, engine
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


HOST = "127.0.0.1"
PORT = 5000

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


def _send_json(connection, response):
    connection.sendall(json.dumps(response).encode("utf-8"))


def start_server():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((HOST, PORT))
        server_socket.listen()
        print(f"PixelHub server listening on {HOST}:{PORT}...")

        while True:
            connection, address = server_socket.accept()
            with connection:
                session = None
                try:
                    request_data = bytearray()
                    while True:
                        chunk = connection.recv(4096)
                        if not chunk:
                            break
                        request_data.extend(chunk)

                    if not request_data:
                        continue

                    request = json.loads(request_data.decode("utf-8"))
                    action = request.get("accion")
                    data = request.get("datos", {})
                    if data is None:
                        data = {}

                    if action == "ping":
                        response = {
                            "status": "ok",
                            "message": "Connection successful.",
                            "data": None,
                        }
                    elif action not in ACTION_HANDLERS:
                        response = {
                            "status": "error",
                            "message": f"Unknown action: {action}",
                            "data": None,
                        }
                    elif not isinstance(data, dict):
                        response = {
                            "status": "error",
                            "message": "Request data must be a JSON object.",
                            "data": None,
                        }
                    else:
                        entity, processor = ACTION_HANDLERS[action]
                        with Session(bind=engine) as session:
                            repository = REPOSITORIES[entity](session)
                            response = processor(action, data, repository, session)

                    _send_json(connection, response)
                except Exception as error:
                    print(f"Server request error from {address}: {error}")
                    if session is not None:
                        session.rollback()
                    _send_json(
                        connection,
                        {
                            "status": "error",
                            "message": f"Internal server error: {error}",
                            "data": None,
                        },
                    )


if __name__ == "__main__":
    start_server()
