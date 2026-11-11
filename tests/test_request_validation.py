"""Tests for server-side request validation and protocol decoding (Practice 2).

This module tests that:
1. The server's handle_client properly decodes UTF-8 JSON requests.
2. Malformed JSON payloads return clear error responses without crashing.
3. Requests with missing or invalid fields are rejected by the validation layer.
4. Pure protocol validation rules (protocol.validate_request) function correctly.
"""

import asyncio
import json

import server as router
from protocol import validate_request


class FakeServerStreamWriter:
    """Simulates an asyncio.StreamWriter from the server perspective.

    Captures response data written by the server, simulates draining,
    records closure, and provides get_extra_info("peername").
    """

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


def run_server_request(request_bytes: bytes) -> tuple[dict, FakeServerStreamWriter]:
    """Helper that feeds request_bytes into server.handle_client() and returns the response.

    This directly invokes the server coroutine inside an event loop with simulated streams,
    making it easy for students to see exactly how requests enter handle_client and responses exit.
    """
    writer = FakeServerStreamWriter()

    async def execute():
        reader = asyncio.StreamReader()
        if request_bytes:
            reader.feed_data(request_bytes)
        reader.feed_eof()

        await router.handle_client(reader, writer)

    asyncio.run(execute())

    if not writer.data:
        return {}, writer
    return json.loads(writer.data.decode("utf-8")), writer


def test_server_rejects_malformed_json():
    """Verify that syntactically invalid JSON receives an error response without crashing."""
    response, writer = run_server_request(b'{"accion":')

    assert response["status"] == "error"
    assert response["data"] is None
    assert "Invalid" in response["message"] or "JSON" in response["message"] or "line" in response["message"]
    assert writer.closed is True


def test_server_rejects_non_object_request_data():
    """Verify that a request where 'datos' is not a JSON object is rejected."""
    request = json.dumps({"accion": "get_all_roles", "datos": ["invalid"]}).encode("utf-8")
    response, writer = run_server_request(request)

    assert response == {
        "status": "error",
        "message": "Request data must be a JSON object.",
        "data": None,
    }
    assert writer.closed is True


def test_server_defaults_missing_request_data_to_empty_object():
    """Verify that omitting 'datos' defaults to an empty object, allowing valid requests like 'ping'."""
    request = json.dumps({"accion": "ping"}).encode("utf-8")
    response, writer = run_server_request(request)

    assert response == {
        "status": "ok",
        "message": "Connection successful.",
        "data": None,
    }
    assert writer.closed is True


def test_server_handles_clean_empty_disconnect():
    """Verify that a client that opens a connection and immediately closes it (EOF) is handled cleanly."""
    response, writer = run_server_request(b"")

    # No response expected for empty EOF disconnection
    assert response == {}
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
