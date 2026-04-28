from __future__ import annotations
# pyright: reportMissingImports=false

import inspect
import os
from pathlib import Path
from typing import Any

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient


def test_build_text_agent_card_declares_v1_jsonrpc_and_rest_interfaces() -> None:
    from a2a_backend_kit.agent_card import build_text_agent_card

    card = build_text_agent_card(
        name="Harness Agent",
        description="Harness backend",
        version="0.1.0",
        public_url="http://example.test/a2a/",
        skill_id="harness-message",
        skill_name="Harness message",
        skill_description="Accepts harness text messages.",
        streaming=True,
    )

    assert card.name == "Harness Agent"
    assert card.description == "Harness backend"
    assert card.version == "0.1.0"
    assert card.capabilities.streaming is True
    assert list(card.default_input_modes) == ["text/plain"]
    assert list(card.default_output_modes) == ["text/plain"]
    assert [(skill.id, skill.name) for skill in card.skills] == [
        ("harness-message", "Harness message")
    ]
    assert [
        (interface.protocol_binding, interface.protocol_version, interface.url)
        for interface in card.supported_interfaces
    ] == [
        ("JSONRPC", "1.0", "http://example.test/a2a"),
        ("REST", "1.0", "http://example.test/a2a"),
    ]


def test_build_text_agent_card_can_disable_streaming() -> None:
    from a2a_backend_kit.agent_card import build_text_agent_card

    card = build_text_agent_card(
        name="No Stream Agent",
        description="Sync backend",
        version="0.1.0",
        public_url="http://example.test/sync",
        skill_id="sync-message",
        skill_name="Sync message",
        skill_description="Accepts sync text messages.",
        streaming=False,
    )

    assert card.capabilities.streaming is False


def test_build_text_agent_card_can_declare_jsonrpc_only_route() -> None:
    from a2a_backend_kit.agent_card import build_text_agent_card

    card = build_text_agent_card(
        name="JSONRPC Agent",
        description="JSONRPC backend",
        version="0.1.0",
        public_url="http://example.test",
        jsonrpc_url="http://example.test/a2a/jsonrpc",
        include_rest=False,
        skill_id="jsonrpc-message",
        skill_name="JSONRPC message",
        skill_description="Accepts JSONRPC text messages.",
        streaming=False,
    )

    assert [
        (interface.protocol_binding, interface.protocol_version, interface.url)
        for interface in card.supported_interfaces
    ] == [("JSONRPC", "1.0", "http://example.test/a2a/jsonrpc")]


def test_build_text_agent_card_accepts_additional_skill_tags() -> None:
    from a2a_backend_kit.agent_card import build_text_agent_card

    card = build_text_agent_card(
        name="Tagged Agent",
        description="Backend with tags",
        version="0.1.0",
        public_url="http://example.test",
        skill_id="tagged-message",
        skill_name="Tagged message",
        skill_description="Accepts tagged text messages.",
        streaming=False,
        skill_tags=("threads", "kit"),
    )

    assert list(card.skills[0].tags) == ["threads", "kit"]


def test_install_bearer_auth_accepts_valid_token_and_copies_headers() -> None:
    from a2a_backend_kit.auth import BearerCredential, install_bearer_auth

    app = FastAPI()
    install_bearer_auth(
        app,
        credentials=(BearerCredential(token="good-token", principal="alice"),),
        public_paths={"/public"},
    )

    @app.get("/private")
    async def private(request: Request) -> dict[str, Any]:
        return {
            "principal": request.state.authenticated_principal,
            "headers": request.state.a2a_headers,
        }

    response = TestClient(app).get(
        "/private",
        headers={"Authorization": "Bearer good-token", "A2A-Version": "1.0"},
    )

    assert response.status_code == 200
    assert response.json()["principal"] == "alice"
    assert response.json()["headers"]["authorization"] == "Bearer good-token"
    assert response.json()["headers"]["a2a-version"] == "1.0"


def test_install_bearer_auth_rejects_missing_or_bad_token() -> None:
    from a2a_backend_kit.auth import BearerCredential, install_bearer_auth

    app = FastAPI()
    install_bearer_auth(
        app,
        credentials=(BearerCredential(token="good-token", principal="alice"),),
        public_paths={"/public"},
    )

    @app.get("/private")
    async def private() -> dict[str, str]:
        return {"ok": "true"}

    client = TestClient(app)

    missing = client.get("/private")
    bad = client.get("/private", headers={"Authorization": "Bearer bad-token"})
    public = client.get("/public")

    assert missing.status_code == 401
    assert missing.headers["WWW-Authenticate"] == "Bearer"
    assert bad.status_code == 401
    assert public.status_code == 404


def test_install_bearer_auth_allows_requests_when_no_credentials_configured() -> None:
    from a2a_backend_kit.auth import install_bearer_auth

    app = FastAPI()
    install_bearer_auth(app, credentials=(), public_paths=set())

    @app.get("/private")
    async def private(request: Request) -> dict[str, Any]:
        return {"headers": request.state.a2a_headers}

    response = TestClient(app).get("/private", headers={"A2A-Version": "1.0"})

    assert response.status_code == 200
    assert response.json()["headers"]["a2a-version"] == "1.0"


def test_kit_context_builder_preserves_explicit_v1_header() -> None:
    from a2a_backend_kit.context import KitContextBuilder

    app = FastAPI()

    @app.get("/ctx")
    async def ctx(request: Request) -> dict[str, Any]:
        request.state.authenticated_principal = "alice"
        context = KitContextBuilder().build(request)
        return {
            "headers": context.state["headers"],
            "principal": context.state["authenticated_principal"],
        }

    response = TestClient(app).get("/ctx", headers={"A2A-Version": "1.0"})

    assert response.status_code == 200
    assert response.json()["headers"]["A2A-Version"] == "1.0"
    assert response.json()["headers"]["a2a-version"] == "1.0"
    assert response.json()["principal"] == "alice"


def test_kit_context_builder_defaults_to_legacy_when_version_header_absent() -> None:
    from a2a_backend_kit.context import KitContextBuilder

    app = FastAPI()

    @app.get("/ctx")
    async def ctx(request: Request) -> dict[str, Any]:
        context = KitContextBuilder().build(request)
        return {"headers": context.state["headers"]}

    response = TestClient(app).get("/ctx")

    assert response.status_code == 200
    assert response.json()["headers"]["A2A-Version"] == "0.3"
    assert response.json()["headers"]["a2a-version"] == "0.3"


def test_make_store_returns_sdk_in_memory_task_store() -> None:
    from a2a.server.tasks.inmemory_task_store import InMemoryTaskStore
    from a2a_backend_kit.task_store import make_store

    store = make_store("memory")

    assert isinstance(store, InMemoryTaskStore)


def test_make_store_rejects_unsupported_persistent_kinds() -> None:
    from a2a_backend_kit.task_store import make_store

    with pytest.raises(ValueError, match="Unsupported task store kind"):
        make_store("sqlite", database_url="sqlite:///tasks.db")


def test_bearer_interceptor_injects_authorization_into_service_parameters() -> None:
    from a2a.client.client import ClientCallContext
    from a2a.client.interceptors import BeforeArgs
    from a2a.types import AgentCard
    from a2a_backend_kit.peers import BearerInterceptor

    args = BeforeArgs(
        input=None,
        method="message/send",
        agent_card=AgentCard(name="Peer", description="Peer", version="1"),
        context=ClientCallContext(),
    )

    import anyio

    anyio.run(BearerInterceptor("peer-token").before, args)

    assert args.context is not None
    assert args.context.service_parameters == {"Authorization": "Bearer peer-token"}


def test_peer_registry_from_agents_yaml_resolves_env_token_and_returns_peer(
    tmp_path: Path,
    monkeypatch,
) -> None:
    from a2a_backend_kit.peers import PeerRegistry

    config = tmp_path / "peers.yaml"
    config.write_text(
        "agents:\n"
        "  mock:\n"
        "    url: http://peer.test/a2a\n"
        "    auth:\n"
        "      scheme: bearer\n"
        "      token_env: PEER_TOKEN\n"
        "      token_default: default-token\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("PEER_TOKEN", "env-token")

    peer = PeerRegistry.from_yaml(config).peer("mock")

    assert peer.name == "mock"
    assert peer.url == "http://peer.test/a2a"
    assert peer.bearer_token == "env-token"


def test_peer_registry_client_uses_sdk_create_client_with_v1_header_and_interceptor(
    monkeypatch,
) -> None:
    from a2a_backend_kit.peers import BearerInterceptor, Peer, PeerRegistry

    captured: dict[str, Any] = {}

    async def fake_create_client(agent_url, *, client_config, interceptors):
        captured["agent_url"] = agent_url
        captured["client_config"] = client_config
        captured["interceptors"] = interceptors
        return "sdk-client"

    monkeypatch.setattr("a2a_backend_kit.peers.create_client", fake_create_client)
    registry = PeerRegistry(
        {"mock": Peer(name="mock", url="http://peer.test/a2a", bearer_token="peer-token")}
    )

    import anyio

    client = anyio.run(registry.client, "mock")

    assert client == "sdk-client"
    assert captured["agent_url"] == "http://peer.test/a2a"
    assert captured["client_config"].streaming is False
    assert captured["client_config"].httpx_client.headers["A2A-Version"] == "1.0"
    assert isinstance(captured["interceptors"][0], BearerInterceptor)


def test_setup_otel_returns_false_without_langfuse_env(monkeypatch) -> None:
    from a2a_backend_kit.observability import setup_otel

    monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
    monkeypatch.delenv("LANGFUSE_SECRET_KEY", raising=False)
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)

    assert setup_otel(service_name="kit-test") is False


def test_setup_otel_configures_langfuse_otlp_http_exporter(monkeypatch) -> None:
    from a2a_backend_kit import observability

    captured: dict[str, Any] = {}

    class FakeExporter:
        def __init__(self, *, endpoint, headers):
            captured["endpoint"] = endpoint
            captured["headers"] = headers

    class FakeSpanProcessor:
        def __init__(self, exporter):
            captured["exporter"] = exporter

    class FakeResource:
        @staticmethod
        def create(attrs):
            captured["resource"] = attrs
            return attrs

    class FakeProvider:
        def __init__(self, *, resource):
            captured["provider_resource"] = resource

        def add_span_processor(self, processor):
            captured["processor"] = processor

    class FakeTrace:
        @staticmethod
        def set_tracer_provider(provider):
            captured["provider"] = provider

    monkeypatch.setenv("LANGFUSE_HOST", "https://cloud.langfuse.com/")
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "public")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "secret")
    monkeypatch.setattr(observability, "_otel_configured", False)
    monkeypatch.setattr(observability, "OTLPSpanExporter", FakeExporter, raising=False)
    monkeypatch.setattr(observability, "BatchSpanProcessor", FakeSpanProcessor, raising=False)
    monkeypatch.setattr(observability, "Resource", FakeResource, raising=False)
    monkeypatch.setattr(observability, "TracerProvider", FakeProvider, raising=False)
    monkeypatch.setattr(observability, "trace", FakeTrace, raising=False)

    assert observability.setup_otel(service_name="kit-test", service_version="1.2.3") is True
    assert captured["endpoint"] == "https://cloud.langfuse.com/api/public/otel/v1/traces"
    assert captured["headers"]["Authorization"] == "Basic cHVibGljOnNlY3JldA=="
    assert captured["resource"]["service.name"] == "kit-test"
    assert captured["resource"]["service.version"] == "1.2.3"


def test_bootstrap_make_app_uses_sdk_handler_and_routes(monkeypatch) -> None:
    from a2a_backend_kit.agent_card import build_text_agent_card
    from a2a_backend_kit import bootstrap
    from a2a_backend_kit.auth import BearerCredential

    card = build_text_agent_card(
        name="Bootstrap Agent",
        description="Bootstrap backend",
        version="0.1.0",
        public_url="http://example.test/a2a",
        skill_id="bootstrap-message",
        skill_name="Bootstrap message",
        skill_description="Accepts bootstrap text messages.",
        streaming=False,
    )

    captured: dict[str, Any] = {"jsonrpc": [], "rest": [], "cards": []}

    class FakeHandler:
        def __init__(self, **kwargs):
            captured["handler_kwargs"] = kwargs

    def fake_jsonrpc_routes(handler, *, rpc_url, context_builder=None, **kwargs):
        captured["jsonrpc"].append((handler, rpc_url, context_builder, kwargs))
        return []

    def fake_rest_routes(handler, *, context_builder=None, path_prefix="", **kwargs):
        captured["rest"].append((handler, context_builder, path_prefix, kwargs))
        return []

    def fake_card_routes(agent_card):
        captured["cards"].append(agent_card)
        return []

    monkeypatch.setattr(bootstrap, "DefaultRequestHandler", FakeHandler)
    monkeypatch.setattr(bootstrap, "create_jsonrpc_routes", fake_jsonrpc_routes)
    monkeypatch.setattr(bootstrap, "create_rest_routes", fake_rest_routes)
    monkeypatch.setattr(bootstrap, "create_agent_card_routes", fake_card_routes)
    monkeypatch.setattr(bootstrap, "setup_otel", lambda **kwargs: captured.setdefault("otel", kwargs) or True)

    app = bootstrap.make_app(
        executor=object(),
        agent_card=card,
        bearer_credentials=(BearerCredential(token="t", principal="p"),),
        service_name="bootstrap-test",
        service_version="1.2.3",
        rpc_url="/a2a/jsonrpc",
        include_rest=True,
        ready=lambda: True,
    )
    client = TestClient(app)

    card_response = client.get("/.well-known/agent-card.json")
    health_response = client.get("/healthz")
    ready_response = client.get("/readyz")

    assert health_response.json() == {"status": "ok"}
    assert ready_response.json() == {"status": "ready"}
    assert card_response.status_code == 404
    assert captured["handler_kwargs"]["agent_executor"] is not None
    assert captured["handler_kwargs"]["agent_card"] is card
    assert captured["handler_kwargs"]["request_context_builder"].__class__.__name__ == "KitContextBuilder"
    assert captured["jsonrpc"][0][1] == "/a2a/jsonrpc"
    assert captured["jsonrpc"][0][2].__class__.__name__ == "KitContextBuilder"
    assert captured["rest"][0][1].__class__.__name__ == "KitContextBuilder"
    assert captured["cards"] == [card]
    assert captured["otel"] == {"service_name": "bootstrap-test", "service_version": "1.2.3"}


def test_bootstrap_make_app_makes_both_agent_card_paths_public(monkeypatch) -> None:
    from a2a_backend_kit.agent_card import build_text_agent_card
    from a2a_backend_kit import bootstrap
    from a2a_backend_kit.auth import BearerCredential

    captured: dict[str, Any] = {}

    class FakeHandler:
        def __init__(self, **kwargs):
            pass

    monkeypatch.setattr(bootstrap, "DefaultRequestHandler", FakeHandler)
    monkeypatch.setattr(bootstrap, "create_jsonrpc_routes", lambda *args, **kwargs: [])
    monkeypatch.setattr(bootstrap, "create_rest_routes", lambda *args, **kwargs: [])
    monkeypatch.setattr(bootstrap, "create_agent_card_routes", lambda *args, **kwargs: [])
    monkeypatch.setattr(bootstrap, "setup_otel", lambda **kwargs: False)

    def fake_install_bearer_auth(app, *, credentials, public_paths):
        captured["credentials"] = tuple(credentials)
        captured["public_paths"] = set(public_paths)

    monkeypatch.setattr(bootstrap, "install_bearer_auth", fake_install_bearer_auth)

    card = build_text_agent_card(
        name="Bootstrap Agent",
        description="Bootstrap backend",
        version="0.1.0",
        public_url="http://example.test/a2a",
        skill_id="bootstrap-message",
        skill_name="Bootstrap message",
        skill_description="Accepts bootstrap text messages.",
        streaming=False,
    )

    bootstrap.make_app(
        executor=object(),
        agent_card=card,
        bearer_credentials=(BearerCredential(token="t", principal="p"),),
        service_name="bootstrap-test",
        enable_otel=False,
    )

    assert "/.well-known/agent-card.json" in captured["public_paths"]
    assert "/.well-known/agent-card" in captured["public_paths"]


def test_bootstrap_make_app_signature_has_reviewed_contract() -> None:
    from a2a_backend_kit.bootstrap import make_app

    parameters = inspect.signature(make_app).parameters

    assert "executor" in parameters
    assert "jsonrpc_handler" not in parameters
    assert "rest_send_handler" not in parameters
    assert parameters["service_version"].default == "dev"
    assert parameters["rpc_url"].default == "/"
    assert parameters["include_rest"].default is True


def test_package_exports_reviewed_contracts() -> None:
    import a2a_backend_kit

    for name in (
        "make_app",
        "make_store",
        "setup_otel",
        "Peer",
        "PeerRegistry",
        "BearerInterceptor",
        "BearerCredential",
        "KitContextBuilder",
        "build_text_agent_card",
        "PROTOCOL_VERSION",
    ):
        assert hasattr(a2a_backend_kit, name)


def test_pyproject_declares_reviewed_dependencies() -> None:
    pyproject = (Path(__file__).resolve().parents[1] / "pyproject.toml").read_text(encoding="utf-8")

    for dependency in (
        "a2a-sdk>=0.3.26,<2.0",
        "fastapi>=0.115",
        "httpx>=0.27",
        "sse-starlette>=3.0",
        "pyyaml>=6.0",
        "opentelemetry-sdk>=1.27",
        "opentelemetry-exporter-otlp-proto-http>=1.27",
    ):
        assert dependency in pyproject
