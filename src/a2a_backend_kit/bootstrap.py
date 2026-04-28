"""Composable building blocks for A2A backend FastAPI apps.

This module is intentionally a *toolbox*, not a framework. Each public
helper does one thing:

- :func:`build_default_handler` wraps the SDK ``DefaultRequestHandler``
  with a sensible default :class:`~a2a_backend_kit.context.KitContextBuilder`.
- :func:`mount_a2a_routes` mounts the canonical SDK routes
  (``create_jsonrpc_routes``, ``create_rest_routes``,
  ``create_agent_card_routes``) on an existing FastAPI app.
- :func:`mount_health_endpoints` adds ``/healthz``, ``/health`` and
  ``/readyz`` with a pluggable readiness probe.
- :func:`make_app` composes the above for the *simple* backend case.
  Backends that need lifespan, custom RequestHandler subclasses, custom
  middlewares, or extra routes should compose the helpers above
  themselves rather than asking ``make_app`` to grow another keyword.

The mount/handler helpers require ``a2a-sdk>=1.0`` (they import
``a2a.server.routes`` which does not exist on ``a2a-sdk==0.3.x``).
``mount_health_endpoints`` is SDK-agnostic.
"""
# pyright: reportMissingImports=false

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any

from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import (
    create_agent_card_routes,
    create_jsonrpc_routes,
    create_rest_routes,
)
from fastapi import FastAPI

from .auth import BearerCredential, install_bearer_auth
from .bootstrap_health import mount_health_endpoints
from .context import KitContextBuilder
from .observability import setup_otel
from .task_store import make_store

__all__ = [
    "build_default_handler",
    "make_app",
    "mount_a2a_routes",
    "mount_health_endpoints",
]


def build_default_handler(
    executor: Any,
    *,
    agent_card: Any,
    task_store: Any | None = None,
    request_context_builder: Any | None = None,
) -> DefaultRequestHandler:
    """Construct a SDK ``DefaultRequestHandler`` with kit defaults.

    ``task_store`` defaults to an in-memory store; ``request_context_builder``
    defaults to a fresh :class:`KitContextBuilder` so the
    ``A2A-Version`` header is propagated automatically.
    """

    return DefaultRequestHandler(
        agent_executor=executor,
        task_store=task_store or make_store("memory"),
        agent_card=agent_card,
        request_context_builder=request_context_builder or KitContextBuilder(),
    )


def mount_a2a_routes(
    app: FastAPI,
    handler: Any,
    agent_card: Any,
    *,
    rpc_url: str = "/",
    include_rest: bool = True,
    rest_path_prefix: str = "",
    context_builder: Any | None = None,
    enable_v0_3_compat: bool = False,
) -> None:
    """Mount canonical A2A routes (JSON-RPC, REST, AgentCard) on ``app``.

    REST routes are skipped when ``include_rest`` is ``False`` or when
    the supplied ``agent_card`` does not advertise a REST interface.
    AgentCard routes (``/.well-known/agent-card`` and
    ``/.well-known/agent-card.json``) are always mounted.

    ``enable_v0_3_compat`` is forwarded to the SDK route factories so
    backends can accept legacy v0.3 method names (``message/send``,
    ``tasks/get``, ...) alongside the v1.0 surface — useful when serving
    a population of clients that has not migrated to v1.0 yet.
    """

    cb = context_builder or KitContextBuilder()

    # AgentCard routes go first so they take precedence over the v0.3
    # compat wildcard ``/{tenant}`` and ``/{tenant:path}`` routes that
    # ``create_jsonrpc_routes`` / ``create_rest_routes`` register under
    # the same prefix when ``enable_v0_3_compat=True``.
    for route in create_agent_card_routes(agent_card):
        app.router.routes.append(route)

    for route in create_jsonrpc_routes(
        handler,
        rpc_url=rpc_url,
        context_builder=cb,
        enable_v0_3_compat=enable_v0_3_compat,
    ):
        app.router.routes.append(route)

    if include_rest and _card_advertises_rest(agent_card):
        for route in create_rest_routes(
            handler,
            context_builder=cb,
            path_prefix=rest_path_prefix,
            enable_v0_3_compat=enable_v0_3_compat,
        ):
            app.router.routes.append(route)


def make_app(
    *,
    executor: Any,
    agent_card: Any,
    task_store: Any | None = None,
    bearer_credentials: Iterable[BearerCredential] = (),
    service_name: str,
    service_version: str = "dev",
    enable_otel: bool = True,
    rpc_url: str = "/",
    include_rest: bool = True,
    ready: Callable[[], bool] | None = None,
) -> FastAPI:
    """Compose a minimal FastAPI app for *simple* backends.

    ``make_app`` is a convenience for backends that only need the kit's
    canonical building blocks (auth + headers + routes + health + OTel).
    Backends that need a custom ``FastAPI`` subclass, lifespan, extra
    middlewares, or custom routes should call
    :func:`build_default_handler`, :func:`mount_a2a_routes`,
    :func:`mount_health_endpoints`, :func:`install_bearer_auth` and
    :func:`setup_otel` themselves rather than expecting ``make_app`` to
    grow more keyword arguments.
    """

    if enable_otel:
        setup_otel(service_name=service_name, service_version=service_version)

    handler = build_default_handler(
        executor,
        agent_card=agent_card,
        task_store=task_store,
    )

    app = FastAPI(title=service_name, version=service_version)
    mount_health_endpoints(app, ready_check=ready)
    mount_a2a_routes(app, handler, agent_card, rpc_url=rpc_url, include_rest=include_rest)
    install_bearer_auth(
        app,
        credentials=bearer_credentials,
        public_paths={
            "/health",
            "/healthz",
            "/readyz",
            "/.well-known/agent-card",
            "/.well-known/agent-card.json",
        },
    )
    return app


def _card_advertises_rest(agent_card: Any) -> bool:
    return any(
        getattr(interface, "protocol_binding", "") == "REST"
        for interface in getattr(agent_card, "supported_interfaces", [])
    )
