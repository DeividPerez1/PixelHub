import json
from unittest.mock import Mock

import server as router

from test_request_validation import FakeListener, run_server_request


def test_router_returns_error_for_unknown_action(monkeypatch):
    request = json.dumps({"accion": "not_registered", "datos": {}}).encode("utf-8")

    response = run_server_request(monkeypatch, request)

    assert response == {
        "status": "error",
        "message": "Unknown action: not_registered",
        "data": None,
    }


def test_router_dispatches_action_to_service_and_repository(monkeypatch):
    listener = FakeListener(
        json.dumps({"accion": "get_role", "datos": {"id": 6}}).encode("utf-8")
    )
    monkeypatch.setattr(router.socket, "socket", lambda *args: listener)
    repository = Mock()
    session = Mock()
    session.__enter__ = Mock(return_value=session)
    session.__exit__ = Mock(return_value=False)
    processor = Mock(return_value={"status": "ok", "message": "routed", "data": {"id": 6}})
    repository_factory = Mock(return_value=repository)
    monkeypatch.setattr(router, "Session", Mock(return_value=session))
    monkeypatch.setitem(router.REPOSITORIES, "role", repository_factory)
    monkeypatch.setitem(router.ACTION_HANDLERS, "get_role", ("role", processor))

    try:
        router.start_server()
    except KeyboardInterrupt:
        pass

    processor.assert_called_once_with("get_role", {"id": 6}, repository, session)
    repository_factory.assert_called_once_with(session)
    response = json.loads(listener.connection.response_data.decode("utf-8"))
    assert response == {"status": "ok", "message": "routed", "data": {"id": 6}}
