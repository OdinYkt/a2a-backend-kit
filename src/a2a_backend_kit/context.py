"""Server call context helpers shared by A2A backend adapters."""
# pyright: reportMissingImports=false

from __future__ import annotations

from typing import Any

from a2a.server.agent_execution import SimpleRequestContextBuilder
from a2a.server.context import ServerCallContext
from a2a.server.routes.common import DefaultServerCallContextBuilder
from starlette.requests import Request


DEFAULT_VERSION_WITHOUT_HEADER = "0.3"


class KitContextBuilder(DefaultServerCallContextBuilder):
    def __init__(self) -> None:
        self._request_context_builder = SimpleRequestContextBuilder(
            should_populate_referred_tasks=False
        )

    def build(self, *args: Any, **kwargs: Any) -> Any:
        if args and isinstance(args[0], Request):
            return self._build_server_call_context(args[0])
        if "request" in kwargs and isinstance(kwargs["request"], Request):
            return self._build_server_call_context(kwargs["request"])
        return self._request_context_builder.build(*args, **kwargs)

    def _build_server_call_context(self, request: Request) -> ServerCallContext:
        context = super().build(request)
        headers = dict(getattr(request.state, "a2a_headers", dict(request.headers)))
        explicit_version = headers.get("A2A-Version") or headers.get("a2a-version")
        version = explicit_version or DEFAULT_VERSION_WITHOUT_HEADER
        headers["A2A-Version"] = version
        headers["a2a-version"] = version
        context.state["headers"] = headers
        principal = getattr(request.state, "authenticated_principal", None)
        if principal is not None:
            context.state["authenticated_principal"] = principal
        return context
