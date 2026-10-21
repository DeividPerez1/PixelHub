import json

import server as router
from protocol import validate_request


class FakeConnection:
    def __init__(self, request_data):
        self.request_data = request_data
        self.response_data = bytearray()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def recv(self, size):
        request_data, self.request_data = self.request_data, b""
        return request_data

    def sendall(self, data):
        self.response_data.extend(data)


class FakeListener:
    def __init__(self, request_data):
        self.connection = FakeConnection(request_data)
        self.accepted = False

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def setsockopt(self, *args):
        pass

    def bind(self, address):
        pass

    def listen(self):
        pass

    def accept(self):
        if self.accepted:
            raise KeyboardInterrupt
        self.accepted = True
        return self.connection, ("127.0.0.1", 12345)


def run_server_request(monkeypatch, request_data):
    listener = FakeListener(request_data)
    monkeypatch.setattr(router.socket, "socket", lambda *args: listener)

    try:
        router.start_server()
    except KeyboardInterrupt:
        pass

    return json.loads(listener.connection.response_data.decode("utf-8"))


def test_server_rejects_malformed_json(monkeypatch):
    response = run_server_request(monkeypatch, b'{"accion":')

    assert response["status"] == "error"
    assert response["message"].startswith("Internal server error:")
    assert response["data"] is None


def test_server_rejects_non_object_request_data(monkeypatch):
    request = json.dumps({"accion": "get_all_roles", "datos": ["invalid"]}).encode("utf-8")

    response = run_server_request(monkeypatch, request)

    assert response == {
        "status": "error",
        "message": "Request data must be a JSON object.",
        "data": None,
    }


def test_server_defaults_missing_request_data_to_empty_object(monkeypatch):
    request = json.dumps({"accion": "ping"}).encode("utf-8")

    response = run_server_request(monkeypatch, request)

    assert response == {
        "status": "ok",
        "message": "Connection successful.",
        "data": None,
    }


def test_protocol_rejects_missing_identifier():
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
