"""Peer registry helpers shared by A2A backend adapters."""
# pyright: reportMissingImports=false

from __future__ import annotations

from dataclasses import dataclass
import importlib
import os
from pathlib import Path
from typing import Any

import httpx
from a2a.client import ClientConfig, create_client
from a2a.client.client import ClientCallContext
from a2a.client.interceptors import AfterArgs, BeforeArgs, ClientCallInterceptor

from .agent_card import PROTOCOL_VERSION


@dataclass(frozen=True)
class Peer:
    name: str
    url: str
    bearer_token: str | None = None


class BearerInterceptor(ClientCallInterceptor):
    def __init__(self, token: str) -> None:
        self._token = token

    async def before(self, args: BeforeArgs) -> None:
        if args.context is None:
            args.context = ClientCallContext()
        if args.context.service_parameters is None:
            args.context.service_parameters = {}
        args.context.service_parameters["Authorization"] = f"Bearer {self._token}"

    async def after(self, args: AfterArgs) -> None:
        return None


class PeerRegistry:
    def __init__(self, peers: dict[str, Peer]) -> None:
        self._peers = dict(peers)

    @classmethod
    def from_yaml(cls, path: str | Path) -> "PeerRegistry":
        data = _load_yaml(Path(path))
        peers: dict[str, Peer] = {}
        for name, config in (data.get("agents") or {}).items():
            auth = config.get("auth") or {}
            token = None
            if str(auth.get("scheme", "")).lower() == "bearer":
                token_env = auth.get("token_env")
                token = (os.getenv(str(token_env)) if token_env else None) or auth.get(
                    "token_default"
                )
            peer_name = str(name)
            peers[peer_name] = Peer(
                name=peer_name,
                url=str(config["url"]),
                bearer_token=token,
            )
        return cls(peers)

    def peer(self, name: str) -> Peer:
        return self._peers[name]

    async def client(self, name: str) -> Any:
        peer = self.peer(name)
        httpx_client = httpx.AsyncClient(headers={"A2A-Version": PROTOCOL_VERSION})
        interceptors: list[ClientCallInterceptor] = []
        if peer.bearer_token:
            interceptors.append(BearerInterceptor(peer.bearer_token))
        return await create_client(
            peer.url,
            client_config=ClientConfig(streaming=False, httpx_client=httpx_client),
            interceptors=interceptors,
        )


def _load_yaml(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    try:
        yaml = importlib.import_module("yaml")
    except ModuleNotFoundError:
        return _load_simple_agents_yaml(text)
    return yaml.safe_load(text) or {}


def _load_simple_agents_yaml(text: str) -> dict[str, Any]:
    result: dict[str, Any] = {"agents": {}}
    current_agent: str | None = None
    in_auth = False
    for raw_line in text.splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        if raw_line == "agents:":
            continue
        if raw_line.startswith("  ") and not raw_line.startswith("    ") and raw_line.strip().endswith(":"):
            current_agent = raw_line.strip()[:-1]
            result["agents"][current_agent] = {}
            in_auth = False
            continue
        if current_agent and raw_line.startswith("    ") and not raw_line.startswith("      "):
            key, value = raw_line.strip().split(":", 1)
            if key == "auth":
                result["agents"][current_agent]["auth"] = {}
                in_auth = True
            else:
                result["agents"][current_agent][key] = value.strip()
                in_auth = False
            continue
        if current_agent and in_auth and raw_line.startswith("      "):
            key, value = raw_line.strip().split(":", 1)
            result["agents"][current_agent]["auth"][key] = value.strip()
    return result
