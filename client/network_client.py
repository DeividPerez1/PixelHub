"""Asynchronous TCP client used by the PixelHub command-line interface."""

import asyncio
import json
from typing import Any
from rich.console import Console

console = Console()

SERVER_HOST = "127.0.0.1"
SERVER_PORT = 5000
SOCKET_TIMEOUT = 10


def _error_response(message: str) -> dict[str, Any]:
    """Create the standard response returned for a failed request."""
    return {"status": "error", "message": message, "data": None}


async def send_request(
    action: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Send one request asynchronously and return its JSON response."""
    request = {"accion": action, "datos": payload or {}}

    try:
        # Open a non-blocking TCP connection managed by the event loop.
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(SERVER_HOST, SERVER_PORT),
            timeout=SOCKET_TIMEOUT,
        )
    except (OSError, asyncio.TimeoutError) as error:
        return _error_response(str(error))

    try:
        writer.write(json.dumps(request).encode("utf-8"))
        # Wait until the request bytes are accepted by the transport.
        await writer.drain()
        try:
            writer.write_eof()
        except (OSError, NotImplementedError):
            pass

        response_data = await asyncio.wait_for(
            reader.read(),
            timeout=SOCKET_TIMEOUT,
        )
        if not response_data:
            return _error_response("The server returned an empty response.")

        response = json.loads(response_data.decode("utf-8"))
        if not isinstance(response, dict):
            return _error_response("The server returned an invalid response.")
        return response
    except (
        OSError,
        asyncio.TimeoutError,
        UnicodeDecodeError,
        json.JSONDecodeError,
    ) as error:
        return _error_response(str(error))
    finally:
        # Close the stream even when the server or network raises an error.
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
        f"[bold cyan]Processing '{action}' in the server...",
        spinner="bouncingBar",
    ):
        return asyncio.run(send_request(action, payload))


if __name__ == "__main__":
    print(send_request_sync("ping"))

