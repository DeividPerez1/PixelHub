"""Unit tests for the client communication protocol (Practice 2 - AsyncIO).

This module tests that network_client.py:
1. Serializes requests using UTF-8 JSON with the required format: {"accion": ..., "datos": ...}.
2. Properly establishes asynchronous connections using asyncio.open_connection().
3. Sends the EOF signal (write_eof) after writing the request.
4. Reads and parses responses (including chunked responses).
5. Closes the StreamWriter cleanly in all execution paths (success, error, timeout).
"""

import asyncio
import json
from unittest.mock import Mock

import pytest

import network_client


class FakeStreamWriter:
    """Simulates an asyncio.StreamWriter to inspect client behavior during tests.

    Captures sent bytes, tracks write_eof() calls, and records stream closure.
    """

    def __init__(self) -> None:
        self.sent_data = bytearray()
        self.drained = False
        self.eof_written = False
        self.closed = False

    def write(self, data: bytes) -> None:
        """Accumulate bytes sent by the client."""
        self.sent_data.extend(data)

    async def drain(self) -> None:
        """Simulate waiting for the transport buffer to flush."""
        self.drained = True

    def write_eof(self) -> None:
        """Record that the client notified the server that sending is finished."""
        self.eof_written = True

    def close(self) -> None:
        """Record that the stream has been closed."""
        self.closed = True

    async def wait_closed(self) -> None:
        """Simulate waiting for socket closure."""
        pass


def run_client_request(monkeypatch, response_chunks, action="ping", payload=None):
    """Helper function to execute network_client.send_request with simulated streams.

    Instead of using real TCP sockets, this feeds predefined bytes to a standard
    asyncio.StreamReader inside an active event loop and collects outgoing bytes with FakeStreamWriter.
    """
    writer = FakeStreamWriter()
    connection = {}

    async def execute():
        # StreamReader must be created inside an active event loop
        reader = asyncio.StreamReader()
        for chunk in response_chunks:
            reader.feed_data(chunk)
        reader.feed_eof()

        async def fake_open_connection(host, port):
            connection["host"] = host
            connection["port"] = port
            return reader, writer

        monkeypatch.setattr(network_client.asyncio, "open_connection", fake_open_connection)
        return await network_client.send_request(action, payload)

    response = asyncio.run(execute())
    return response, writer, connection


def test_client_serializes_request_and_reads_chunked_response(monkeypatch):
    """Verify that the client formats JSON correctly, signals EOF, and reads chunked responses."""
    response, writer, connection = run_client_request(
        monkeypatch,
        [b'{"status":"ok",', b'"message":"done","data":1}'],
        action="get_role",
        payload={"id": 6},
    )

    # Check request payload structure sent over TCP
    sent_json = json.loads(writer.sent_data.decode("utf-8"))
    assert sent_json == {
        "accion": "get_role",
        "datos": {"id": 6},
    }

    # Verify connection parameters
    assert connection == {"host": "127.0.0.1", "port": 5000}

    # Verify lifecycle: EOF signaled and stream closed
    assert writer.eof_written is True
    assert writer.closed is True

    # Verify assembled response
    assert response == {"status": "ok", "message": "done", "data": 1}


def test_client_replaces_empty_payload_with_empty_object(monkeypatch):
    """Verify that a request with no payload sends an empty object '{}' in 'datos'."""
    _, writer, _ = run_client_request(monkeypatch, [b'{"status":"ok"}'], payload=None)

    sent_json = json.loads(writer.sent_data.decode("utf-8"))
    assert sent_json["datos"] == {}


def test_client_reports_empty_server_response(monkeypatch):
    """Verify error handling when the server closes connection without sending data."""
    response, writer, _ = run_client_request(monkeypatch, [])

    assert response == {
        "status": "error",
        "message": "The server returned an empty response.",
        "data": None,
    }
    assert writer.closed is True


def test_client_returns_error_when_connection_fails(monkeypatch):
    """Verify that network connection failures (e.g., ConnectionRefused) return an error response."""

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


@pytest.mark.parametrize("response_body", [b"not-json", b"[]"])
def test_client_reports_invalid_server_response(monkeypatch, response_body):
    """Verify that invalid JSON or non-object responses return an error dictionary."""
    response, writer, _ = run_client_request(monkeypatch, [response_body])

    assert response["status"] == "error"
    assert response["data"] is None
    if response_body == b"[]":
        assert response["message"] == "The server returned an invalid response."
    assert writer.closed is True


def test_client_reports_timeout_on_read(monkeypatch):
    """Verify that read timeouts return an error response and close the writer."""
    writer = FakeStreamWriter()

    async def execute():
        reader = asyncio.StreamReader()
        # Note: no EOF fed, so read() will block until timeout

        async def fake_open_connection(host, port):
            return reader, writer

        monkeypatch.setattr(network_client.asyncio, "open_connection", fake_open_connection)
        monkeypatch.setattr(network_client, "SOCKET_TIMEOUT", 0.05)

        return await network_client.send_request("ping")

    response = asyncio.run(execute())

    assert response["status"] == "error"
    assert writer.closed is True


def test_send_request_sync_wrapper(monkeypatch):
    """Verify that the synchronous adapter send_request_sync correctly calls asyncio.run."""
    expected = {"status": "ok", "message": "pong", "data": None}

    async def fake_send_request(action, payload=None):
        return expected

    monkeypatch.setattr(network_client, "send_request", fake_send_request)

    result = network_client.send_request_sync("ping")
    assert result == expected
