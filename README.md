# a2a-backend-kit

Shared scaffold for [A2A v1.0](https://github.com/google/A2A) backend adapters used by [Threads](https://github.com/OdinYkt/Threads) agents.

Removes boilerplate from each backend by providing canonical building blocks:

- `make_app(executor, agent_card, ...)` — FastAPI app with SDK request handler, JSON-RPC + REST routes, AgentCard, health/ready, Bearer auth, OpenTelemetry — all pre-wired.
- `install_bearer_auth(app, credentials)` — middleware that copies request headers to `request.state.a2a_headers` so the SDK validator finds `A2A-Version`.
- `KitContextBuilder` — `DefaultServerCallContextBuilder` subclass that propagates the `A2A-Version` header to `ServerCallContext.state['headers']`.
- `setup_otel(service_name)` — Langfuse-ready OTLP HTTP exporter, idempotent, gracefully no-op without env.
- `PeerRegistry.from_yaml(path)` + `BearerInterceptor` — outbound A2A peer client backed by the canonical `a2a.client.create_client` with bearer auth.
- `make_store(kind="memory")` — task-store factory wrapping the SDK `InMemoryTaskStore`.
- `build_text_agent_card(...)` — text-only AgentCard helper declaring `protocol_version="1.0"` for JSON-RPC and REST interfaces.

## Install

```bash
pip install "a2a-backend-kit @ git+https://github.com/OdinYkt/a2a-backend-kit.git@v0.1.0"
```

## Usage

```python
from a2a_backend_kit import (
    BearerCredential,
    build_text_agent_card,
    make_app,
)

card = build_text_agent_card(
    name="my-agent",
    description="...",
    version="0.1.0",
    public_url="http://my-agent:8000",
    skill_id="default",
    skill_name="Default skill",
    skill_description="...",
    streaming=False,
)

app = make_app(
    executor=MyAgentExecutor(),
    agent_card=card,
    bearer_credentials=[BearerCredential(token="secret", principal="default")],
    service_name="my-agent",
)
```

The reference backend at [`fake-agent-a2a`](https://github.com/OdinYkt/Threads/tree/master/src/fake-agent-a2a) shows the minimal integration.

## Modules

| Module | Public surface |
| --- | --- |
| `a2a_backend_kit.bootstrap` | `make_app` |
| `a2a_backend_kit.auth` | `install_bearer_auth`, `BearerCredential` |
| `a2a_backend_kit.context` | `KitContextBuilder` |
| `a2a_backend_kit.observability` | `setup_otel` |
| `a2a_backend_kit.peers` | `PeerRegistry`, `Peer`, `BearerInterceptor` |
| `a2a_backend_kit.task_store` | `make_store` |
| `a2a_backend_kit.agent_card` | `build_text_agent_card`, `PROTOCOL_VERSION` |

## License

Apache-2.0
