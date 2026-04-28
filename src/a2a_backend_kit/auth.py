"""Bearer auth middleware shared by A2A backend adapters."""
# pyright: reportMissingImports=false

from __future__ import annotations

from collections.abc import Awaitable, Callable, Iterable
from dataclasses import dataclass
import secrets

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response


@dataclass(frozen=True)
class BearerCredential:
    token: str
    principal: str


def install_bearer_auth(
    app: FastAPI,
    credentials: Iterable[BearerCredential],
    public_paths: Iterable[str] = (),
) -> None:
    credential_tuple = tuple(credentials)
    public_path_set = set(public_paths)

    @app.middleware("http")
    async def bearer_auth(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request.state.a2a_headers = dict(request.headers)
        if (
            request.method == "OPTIONS"
            or request.url.path in public_path_set
            or not credential_tuple
        ):
            return await call_next(request)

        credential = _match_bearer(
            request.headers.get("authorization", ""),
            credential_tuple,
        )
        if credential is None:
            return JSONResponse(
                {"error": "Unauthorized"},
                status_code=401,
                headers={"WWW-Authenticate": "Bearer"},
            )
        request.state.authenticated_principal = credential.principal
        return await call_next(request)


def _match_bearer(
    authorization: str,
    credentials: tuple[BearerCredential, ...],
) -> BearerCredential | None:
    try:
        scheme, token = authorization.split(" ", 1)
    except ValueError:
        return None
    if scheme.lower() != "bearer":
        return None
    stripped = token.strip()
    for credential in credentials:
        if secrets.compare_digest(stripped, credential.token):
            return credential
    return None
