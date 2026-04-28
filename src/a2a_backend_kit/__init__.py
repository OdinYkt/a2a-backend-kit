"""Shared helpers for Threads A2A backend adapters."""

from .agent_card import PROTOCOL_VERSION, build_text_agent_card
from .auth import BearerCredential, install_bearer_auth
from .bootstrap import make_app
from .context import KitContextBuilder
from .observability import setup_otel
from .peers import BearerInterceptor, Peer, PeerRegistry
from .task_store import make_store

__all__ = [
    "BearerCredential",
    "BearerInterceptor",
    "KitContextBuilder",
    "PROTOCOL_VERSION",
    "Peer",
    "PeerRegistry",
    "build_text_agent_card",
    "install_bearer_auth",
    "make_app",
    "make_store",
    "setup_otel",
]
