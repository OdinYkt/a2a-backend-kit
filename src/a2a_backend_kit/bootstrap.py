"""Thin FastAPI bootstrap helpers for A2A backend adapters."""
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
from fastapi.responses import JSONResponse

from .auth import BearerCredential, install_bearer_auth
from .context import KitContextBuilder
from .observability import setup_otel
from .task_store import make_store


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
    if enable_otel:
        setup_otel(service_name=service_name, service_version=service_version)

    context_builder = KitContextBuilder()
    request_handler = DefaultRequestHandler(
        agent_executor=executor,
        task_store=task_store or make_store("memory"),
        agent_card=agent_card,
        request_context_builder=context_builder,
    )
    app = FastAPI(title=service_name, version=service_version)

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/readyz")
    async def readyz() -> JSONResponse:
        if ready is not None and not ready():
            return JSONResponse({"status": "not_ready"}, status_code=503)
        return JSONResponse({"status": "ready"})

    for route in create_jsonrpc_routes(
        request_handler,
        rpc_url=rpc_url,
        context_builder=context_builder,
    ):
        app.router.routes.append(route)

    if include_rest and _card_advertises_rest(agent_card):
        for route in create_rest_routes(
            request_handler,
            context_builder=context_builder,
            path_prefix="",
        ):
            app.router.routes.append(route)

    for route in create_agent_card_routes(agent_card):
        app.router.routes.append(route)

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
