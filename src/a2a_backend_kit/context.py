"""Server call context helpers shared by A2A backend adapters."""
# pyright: reportMissingImports=false

from __future__ import annotations

from typing import Any, Mapping, MutableMapping


DEFAULT_VERSION_WITHOUT_HEADER = "0.3"


def apply_a2a_version_header(
    headers: MutableMapping[str, str],
    default: str = DEFAULT_VERSION_WITHOUT_HEADER,
) -> MutableMapping[str, str]:
    """Ensure ``headers`` carries an ``A2A-Version`` value (both casings).

    SDK-agnostic — does not import any ``a2a`` symbol — so backends pinned
    to ``a2a-sdk==0.3.x`` can use this helper from inside their own
    context builders without pulling in v1-only modules.

    If neither ``A2A-Version`` nor ``a2a-version`` is set in ``headers``,
    ``default`` is written. The chosen value is mirrored to both casings
    so consumers using either spelling find the same string.
    """

    explicit = headers.get("A2A-Version") or headers.get("a2a-version")
    version = explicit or default
    headers["A2A-Version"] = version
    headers["a2a-version"] = version
    return headers


def headers_with_a2a_version(
    headers: Mapping[str, str] | None,
    default: str = DEFAULT_VERSION_WITHOUT_HEADER,
) -> dict[str, str]:
    """Return a new ``dict`` copy of ``headers`` with the version applied."""

    copied = dict(headers or {})
    apply_a2a_version_header(copied, default=default)
    return copied


# v1-only surface: pulling DefaultServerCallContextBuilder requires
# a2a-sdk>=1.0 because a2a.server.routes does not exist on the v0.3 line.
# The eager helpers above are SDK-agnostic; this class is loaded lazily
# from the package __init__ and resolves to None on older SDKs.
try:
    from a2a.server.agent_execution import SimpleRequestContextBuilder
    from a2a.server.context import ServerCallContext
    from a2a.server.routes.common import DefaultServerCallContextBuilder
    from starlette.requests import Request
except (ImportError, ModuleNotFoundError):  # pragma: no cover - exercised on a2a-sdk 0.3
    KitContextBuilder = None  # type: ignore[assignment]
else:

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
            apply_a2a_version_header(headers)
            context.state["headers"] = headers
            principal = getattr(request.state, "authenticated_principal", None)
            if principal is not None:
                context.state["authenticated_principal"] = principal
            return context
