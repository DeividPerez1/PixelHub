"""Types for the JSON data exchanged through the network."""

from typing import Any, TypedDict


class Request(TypedDict):
    action: str
    data: dict[str, Any]


class Response(TypedDict):
    status: str
    message: str
    data: Any
