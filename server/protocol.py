"""Validation helpers for requests received by the server."""

from typing import Any

from domain.dtos import Request


def error_response(message: str) -> dict[str, Any]:
    """Return the standard format used for an error response."""
    return {"status": "error", "message": message, "data": None}


def _require_fields(data: dict[str, Any], fields: tuple[str, ...]) -> str | None:
    for field in fields:
        value = data.get(field)
        if value is None or value == "":
            return f"The field '{field}' is required."
    return None


def _validate_integer(data: dict[str, Any], field: str) -> str | None:
    value = data.get(field)
    try:
        int(value)
    except (TypeError, ValueError):
        return f"The field '{field}' must be an integer."
    return None


def validate_request(
    request: Any, supported_actions: set[str]
) -> tuple[Request | None, dict[str, Any] | None]:
    """Validate the JSON object before it reaches a service."""
    if not isinstance(request, dict):
        return None, error_response("The request must be a JSON object.")

    action = request.get("accion")
    if not isinstance(action, str) or not action:
        return None, error_response("The field 'accion' is required.")

    if action != "ping" and action not in supported_actions:
        return None, error_response(f"Unknown action: {action}")

    data = request.get("datos", {})
    if data is None:
        data = {}
    if not isinstance(data, dict):
        return None, error_response("Request data must be a JSON object.")

    required_fields = {
        "add_user": ("username", "email", "password", "role_id"),
        "add_role": ("name",),
        "add_profile": ("user_id", "first_name", "last_name", "birth_date"),
        "add_post": ("title", "category_id", "user_id", "content"),
        "add_category": ("name",),
        "add_tag": ("name",),
        "get_user_by_username": ("username",),
        "get_user_by_email": ("email",),
        "get_posts_by_category": ("category_id",),
        "get_posts_by_user": ("user_id",),
    }
    missing_field = _require_fields(data, required_fields.get(action, ()))
    if missing_field:
        return None, error_response(missing_field)

    integer_fields = {
        "delete_user": ("id",),
        "get_user": ("id",),
        "delete_role": ("id",),
        "get_role": ("id",),
        "delete_profile": ("id",),
        "get_profile": ("id",),
        "delete_post": ("id",),
        "get_post": ("id",),
        "delete_category": ("id",),
        "get_category": ("id",),
        "delete_tag": ("id",),
        "get_tag": ("id",),
        "get_posts_by_category": ("category_id",),
        "get_posts_by_user": ("user_id",),
        "add_user": ("role_id",),
        "add_profile": ("user_id",),
        "add_post": ("category_id", "user_id"),
    }
    for field in integer_fields.get(action, ()):
        invalid_field = _validate_integer(data, field)
        if invalid_field:
            return None, error_response(invalid_field)

    if action.startswith("update_"):
        for field in ("id", "attribute", "new_value"):
            missing_field = _require_fields(data, (field,))
            if missing_field:
                return None, error_response(missing_field)
        invalid_id = _validate_integer(data, "id")
        if invalid_id:
            return None, error_response(invalid_id)
        if action == "update_user" and data.get("attribute") == "role_id":
            invalid_role_id = _validate_integer(data, "new_value")
            if invalid_role_id:
                return None, error_response(invalid_role_id)

    return {"action": action, "data": data}, None
