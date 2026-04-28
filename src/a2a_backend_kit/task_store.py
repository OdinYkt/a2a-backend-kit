"""SDK task store factory helpers."""
# pyright: reportMissingImports=false

from __future__ import annotations

from typing import Any

from a2a.server.tasks.inmemory_task_store import InMemoryTaskStore


def make_store(kind: str = "memory", *, database_url: str | None = None) -> Any:
    normalized = kind.strip().lower()
    if normalized in {"", "memory", "inmemory", "in-memory"}:
        return InMemoryTaskStore()
    raise ValueError(
        f"Unsupported task store kind {kind!r}; only 'memory' is available in a2a_backend_kit."
    )
