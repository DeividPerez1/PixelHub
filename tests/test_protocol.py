import json
from unittest.mock import Mock

import pytest

import network_client


class FakeClientSocket:
    def __init__(self, response_chunks):
        self.response_chunks = list(response_chunks)
        self.sent_data = bytearray()
        self.timeout = None
        self.shutdown_direction = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def settimeout(self, timeout):
        self.timeout = timeout

    def sendall(self, data):
        self.sent_data.extend(data)

    def shutdown(self, direction):
        self.shutdown_direction = direction

    def recv(self, size):
        if self.response_chunks:
            return self.response_chunks.pop(0)
        return b""


def run_client_request(monkeypatch, response_chunks, action="ping", payload=None):
    client_socket = FakeClientSocket(response_chunks)
    connection = {}

    def create_connection(address, timeout):
        connection["address"] = address
        connection["timeout"] = timeout
        return client_socket

    monkeypatch.setattr(network_client.socket, "create_connection", create_connection)
    response = network_client.send_request(action, payload)
    return response, client_socket, connection


def test_client_serializes_request_and_reads_chunked_response(monkeypatch):
    response, client_socket, connection = run_client_request(
        monkeypatch,
        [b'{"status":"ok",', b'"message":"done","data":1}'],
        action="get_role",
        payload={"id": 6},
    )

    assert json.loads(client_socket.sent_data.decode("utf-8")) == {
        "accion": "get_role",
        "datos": {"id": 6},
    }
    assert connection == {"address": ("127.0.0.1", 5000), "timeout": 10}
    assert client_socket.timeout == 10
    assert client_socket.shutdown_direction == network_client.socket.SHUT_WR
    assert response == {"status": "ok", "message": "done", "data": 1}


def test_client_replaces_empty_payload_with_empty_object(monkeypatch):
    _, client_socket, _ = run_client_request(monkeypatch, [b'{"status":"ok"}'], payload=None)

    assert json.loads(client_socket.sent_data.decode("utf-8"))["datos"] == {}


def test_client_reports_empty_server_response(monkeypatch):
    response, _, _ = run_client_request(monkeypatch, [])

    assert response == {
        "status": "error",
        "message": "The server returned an empty response.",
        "data": None,
    }


def test_client_returns_error_when_connection_fails(monkeypatch):
    monkeypatch.setattr(
        network_client.socket,
        "create_connection",
        Mock(side_effect=OSError("connection refused")),
    )

    response = network_client.send_request("ping")

    assert response == {
        "status": "error",
        "message": "connection refused",
        "data": None,
    }


@pytest.mark.parametrize("response_body", [b"not-json", b"[]"])
def test_client_reports_invalid_server_response(monkeypatch, response_body):
    response, _, _ = run_client_request(monkeypatch, [response_body])

    assert response["status"] == "error"
    assert response["data"] is None
    if response_body == b"[]":
        assert response["message"] == "The server returned an invalid response."
