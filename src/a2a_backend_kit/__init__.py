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
from .observability import setup_otel
from .task_store import make_store

__all__ = [
    "AuthValidator",
    "BearerCredential",
    "PROTOCOL_VERSION",
    "build_text_agent_card",
    "install_auth",
    "install_bearer_auth",
    "make_store",
    "setup_otel",
]


make_app = None
KitContextBuilder = None
PeerRegistry = None
Peer = None
BearerInterceptor = None

try:
    from .bootstrap import make_app  # noqa: F811
    from .context import KitContextBuilder  # noqa: F811
    from .peers import BearerInterceptor, Peer, PeerRegistry  # noqa: F811

    __all__.extend(
        [
            "BearerInterceptor",
            "KitContextBuilder",
            "Peer",
            "PeerRegistry",
            "make_app",
        ]
    )
except (ImportError, ModuleNotFoundError):
    # a2a-sdk lacks v1.0 surface (routes / interceptors / create_client).
    # The four names above stay None so backends can detect the limitation.
    pass
