"""Shared helpers for Threads A2A backend adapters.

Some submodules require ``a2a-sdk>=1.0`` because they import APIs that did
not exist in the v0.3 line (``a2a.server.routes``, ``a2a.client.create_client``,
``a2a.client.interceptors``). Backends pinned to ``a2a-sdk==0.3.x`` can still
use the SDK-version-agnostic helpers (auth, observability, task_store memory
factory, agent_card builder) — those are imported eagerly. The v1-only
surface is loaded lazily; if the SDK lacks the required modules, the
corresponding names resolve to ``None``.
"""

from .agent_card import PROTOCOL_VERSION, build_text_agent_card
from .auth import AuthValidator, BearerCredential, install_auth, install_bearer_auth
from .context import (
    DEFAULT_VERSION_WITHOUT_HEADER,
    apply_a2a_version_header,
    headers_with_a2a_version,
)
from .observability import setup_otel
from .task_store import make_store

__all__ = [
    "AuthValidator",
    "BearerCredential",
    "DEFAULT_VERSION_WITHOUT_HEADER",
    "PROTOCOL_VERSION",
    "apply_a2a_version_header",
    "build_text_agent_card",
    "headers_with_a2a_version",
    "install_auth",
    "install_bearer_auth",
    "make_store",
    "setup_otel",
]


make_app = None
PeerRegistry = None
Peer = None
BearerInterceptor = None

# KitContextBuilder is exported eagerly because the symbol always exists,
# but it resolves to None on a2a-sdk 0.3 where DefaultServerCallContextBuilder
# is unavailable.
from .context import KitContextBuilder  # noqa: E402

__all__.append("KitContextBuilder")

try:
    from .bootstrap import make_app  # noqa: F811
    from .peers import BearerInterceptor, Peer, PeerRegistry  # noqa: F811

    __all__.extend(
        [
            "BearerInterceptor",
            "Peer",
            "PeerRegistry",
            "make_app",
        ]
    )
except (ImportError, ModuleNotFoundError):
    # a2a-sdk lacks v1.0 surface (routes / interceptors / create_client).
    # The names above stay None so backends can detect the limitation.
    pass
