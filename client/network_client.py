"""Small TCP client used by the PixelHub command-line interface."""

import json
import socket
from typing import Any

from shared.config import BUFFER_SIZE, SERVER_HOST, SERVER_PORT, SOCKET_TIMEOUT


def _error_response(message: str) -> dict[str, Any]:
    """Create the standard response returned when the request cannot be completed."""
    return {"status": "error", "message": message, "data": None}


def _read_response(client_socket: socket.socket) -> bytes:
    """Read all response chunks until the server closes its sending side."""
    response_data = bytearray()

    while True:
        chunk = client_socket.recv(BUFFER_SIZE)
        if not chunk:
            break
        response_data.extend(chunk)

    return bytes(response_data)


def _close_socket(client_socket) -> None:
    """Close the socket after the request has finished."""
    close = getattr(client_socket, "close", None)
    if close is not None:
        close()


def send_request(action: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Send an action to the server and return its JSON response."""
    request = {"accion": action, "datos": payload or {}}
    client_socket = None

    try:
        client_socket = socket.create_connection(
            (SERVER_HOST, SERVER_PORT), timeout=SOCKET_TIMEOUT
        )
        client_socket.settimeout(SOCKET_TIMEOUT)
        client_socket.sendall(json.dumps(request).encode("utf-8"))

        # Tell the server that the complete request has been sent.
        client_socket.shutdown(socket.SHUT_WR)
        response_data = _read_response(client_socket)

        if not response_data:
            return _error_response("The server returned an empty response.")

        response = json.loads(response_data.decode("utf-8"))
        if not isinstance(response, dict):
            return _error_response("The server returned an invalid response.")

        return response
    except (OSError, json.JSONDecodeError) as error:
        return _error_response(str(error))
    finally:
        if client_socket is not None:
            _close_socket(client_socket)


if __name__ == "__main__":
    print(send_request("ping"))
