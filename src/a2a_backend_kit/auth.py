"""Bearer auth middleware shared by A2A backend adapters."""
# pyright: reportMissingImports=false

from __future__ import annotations

from collections.abc import Awaitable, Callable, Iterable
from dataclasses import dataclass
import secrets
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response


@dataclass(frozen=True)
class BearerCredential:
    """A static bearer-token credential.

    Backends that need richer auth (Basic, capabilities, credential ids,
    etc.) should use :func:`install_auth` with a custom validator that
    returns its own principal type.
    """

    token: str
    principal: str


AuthValidator = Callable[[Request, str, str], Any]
"""Callable invoked as ``validator(request, auth_scheme, auth_value)``.

Returns a principal object on success — stored at
``request.state.authenticated_principal`` — or ``None`` to reject the
request with 401. Validators may also mutate ``request.state`` to expose
auxiliary fields (identity, capabilities, credential id, ...) that
downstream context builders will read.
"""


def install_bearer_auth(
    app: FastAPI,
    credentials: Iterable[BearerCredential],
    public_paths: Iterable[str] = (),
) -> None:
    """Install simple bearer-token auth.

    Convenience wrapper over :func:`install_auth` for backends that only
    need a fixed list of bearer tokens. Each accepted token resolves to
    its principal string on ``request.state.authenticated_principal``.
    """

    credential_tuple = tuple(credentials)

    def validator(_request: Request, scheme: str, value: str) -> str | None:
        if scheme.lower() != "bearer":
            return None
        match = _match_bearer(value, credential_tuple)
        return match.principal if match is not None else None

    install_auth(
        app,
        validator=validator if credential_tuple else None,
        public_paths=public_paths,
        www_authenticate=("Bearer",) if credential_tuple else (),
    )


def install_auth(
    app: FastAPI,
    *,
    validator: AuthValidator | None,
    public_paths: Iterable[str] = (),
    www_authenticate: Iterable[str] = ("Bearer",),
) -> None:
    """Install pluggable auth middleware.

    The middleware always copies the incoming HTTP headers to
    ``request.state.a2a_headers`` so context builders (e.g.
    :class:`KitContextBuilder`) can read ``A2A-Version`` and friends.

    If ``validator`` is ``None`` the middleware is purely passive — it
    propagates headers but never rejects requests. This matches the
    behaviour of :func:`install_bearer_auth` with no credentials and is
    useful for tests.

    Otherwise the middleware:

    1. Skips ``OPTIONS`` requests and any path in ``public_paths``.
    2. Parses ``Authorization: <scheme> <value>`` from the request.
    3. Calls ``validator(scheme, value)``. On non-``None`` return the
       principal is stored on ``request.state.authenticated_principal``;
       on ``None`` the middleware responds with HTTP 401 and the
       configured ``WWW-Authenticate`` challenge list.
    """

    public_path_set = set(public_paths)
    challenge_header = ", ".join(www_authenticate) if www_authenticate else "Bearer"

    @app.middleware("http")
    async def auth_middleware(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request.state.a2a_headers = dict(request.headers)
        if (
            validator is None
            or request.method == "OPTIONS"
            or request.url.path in public_path_set
        ):
            return await call_next(request)

        scheme, value = _split_authorization(request.headers.get("authorization", ""))
        if scheme is None:
            return _unauthorized(challenge_header)
        principal = validator(request, scheme, value)
        if principal is None:
            return _unauthorized(challenge_header)
        request.state.authenticated_principal = principal
        return await call_next(request)


def _unauthorized(challenge: str) -> JSONResponse:
    return JSONResponse(
        {"error": "Unauthorized"},
        status_code=401,
        headers={"WWW-Authenticate": challenge},
    )


def _split_authorization(authorization: str) -> tuple[str | None, str]:
    try:
        scheme, value = authorization.split(" ", 1)
    except ValueError:
        return None, ""
    return scheme, value.strip()


def _match_bearer(
    value: str,
    credentials: tuple[BearerCredential, ...],
) -> BearerCredential | None:
    for credential in credentials:
        if secrets.compare_digest(value, credential.token):
            return credential
    return None
