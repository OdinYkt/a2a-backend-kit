"""SDK-agnostic health/readiness endpoint helpers.

Lives in its own module so backends pinned to ``a2a-sdk==0.3.x`` can
import :func:`mount_health_endpoints` without pulling in the v1-only
route helpers exposed from :mod:`a2a_backend_kit.bootstrap`.
"""
# pyright: reportMissingImports=false

from __future__ import annotations

from collections.abc import Callable

from fastapi import FastAPI
from fastapi.responses import JSONResponse


def mount_health_endpoints(
    app: FastAPI,
    *,
    ready_check: Callable[[], bool] | None = None,
) -> None:
    """Add ``/healthz``, ``/health`` (liveness) and ``/readyz`` (readiness).

    ``ready_check`` is invoked on every ``/readyz`` call. Returning
    ``False`` makes ``/readyz`` respond with HTTP 503; otherwise the
    endpoint reports HTTP 200.
    """

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/readyz")
    async def readyz() -> JSONResponse:
        if ready_check is not None and not ready_check():
            return JSONResponse({"status": "not_ready"}, status_code=503)
        return JSONResponse({"status": "ready"})
