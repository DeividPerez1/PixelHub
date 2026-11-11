"""Tests for the server routing mechanism and action dispatching (Practice 3).

This module tests that:
1. Unknown actions sent over an authenticated channel return standard errors.
2. Valid authenticated requests are dispatched through ACTION_HANDLERS to their
   corresponding service processor and repository inside an offloaded thread.
"""

from unittest.mock import Mock

import server as router
from test_request_validation import execute_server_exchange


def test_router_returns_error_for_unknown_action():
    """Verify that an unknown action returns a standard error response."""
    response, writer = execute_server_exchange({"accion": "not_registered", "datos": {}})

    assert response == {
        "status": "error",
        "message": "Unknown action: not_registered",
        "data": None,
    }
    assert writer.closed is True


def test_router_dispatches_action_to_service_and_repository(monkeypatch):
    """Verify that an authenticated action dispatches to repository and service processor."""
    # Mock the SQLAlchemy session and repositories
    repository = Mock()
    session = Mock()
    session.rollback = Mock()
    session.close = Mock()

    # Mock processor function returning a successful DTO-like dictionary
    expected_response = {
        "status": "ok",
        "message": "Role retrieved successfully.",
        "data": {"id": 6, "name": "Admin"},
    }
    processor = Mock(return_value=expected_response)
    repository_factory = Mock(return_value=repository)

    # Patch server dependencies
    monkeypatch.setattr(router, "Session", Mock(return_value=session))
    monkeypatch.setitem(router.REPOSITORIES, "role", repository_factory)
    monkeypatch.setitem(router.ACTION_HANDLERS, "get_role", ("role", processor))

    response, writer = execute_server_exchange({"accion": "get_role", "datos": {"id": 6}})

    # 1. Verify repository was instantiated with the active database session
    repository_factory.assert_called_once_with(session)

    # 2. Verify the service processor was called with action, data, repository, and session
    processor.assert_called_once_with("get_role", {"id": 6}, repository, session)

    # 3. Verify session was closed safely in the finally block
    session.close.assert_called_once()

    # 4. Verify the client received the exact decrypted response
    assert response == expected_response
    assert writer.closed is True
