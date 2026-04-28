"""SDK-agnostic health/readiness endpoint helpers.

Lives in its own module so backends pinned to ``a2a-sdk==0.3.x`` can
import :func:`mount_health_endpoints` without pulling in the v1-only
route helpers exposed from :mod:`a2a_backend_kit.bootstrap`.
"""
# pyright: reportMissingImports=false

from __future__ import annotations

from collections.abc import Callable
from typing import Union

from fastapi import FastAPI
from fastapi.responses import JSONResponse


ReadyResult = Union[bool, tuple[bool, str | None]]
"""``ready_check`` may return either ``bool`` (terse) or
``tuple[bool, str | None]`` (richer — second element becomes the
``reason`` field of the 503 response)."""


def mount_health_endpoints(
    app: FastAPI,
    *,
    ready_check: Callable[[], ReadyResult] | None = None,
    liveness_payload: dict[str, str] | None = None,
) -> None:
    """Add ``/healthz``, ``/health`` (liveness) and ``/readyz`` (readiness).

    ``ready_check`` is invoked on every ``/readyz`` call.

    * Return ``True`` (or ``(True, ...)``) for HTTP 200.
    * Return ``False`` (or ``(False, "reason")``) for HTTP 503; if a
      reason is supplied it is exposed as ``{"status": "not_ready",
      "reason": ...}`` so downstream tooling can disambiguate why the
      backend is not ready.

    ``liveness_payload`` lets backends customise the response body of
    ``/healthz`` and ``/health`` (e.g. ``{"status": "live"}``).
    Defaults to ``{"status": "ok"}``.
    """

    payload = dict(liveness_payload) if liveness_payload else {"status": "ok"}

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return dict(payload)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return dict(payload)

    @app.get("/readyz")
    async def readyz() -> JSONResponse:
        if ready_check is None:
            return JSONResponse({"status": "ready"})
        result = ready_check()
        if isinstance(result, tuple):
            ready, reason = result
        else:
            ready, reason = bool(result), None
        if ready:
            return JSONResponse({"status": "ready"})
        body: dict[str, str] = {"status": "not_ready"}
        if reason:
            body["reason"] = reason
        return JSONResponse(body, status_code=503)
