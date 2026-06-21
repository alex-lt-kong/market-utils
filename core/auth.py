"""Host-level token->cookie auth gate, shared by every module.

Disabled when no auth_tokens are configured. When enabled:
  - `?token=<uuid>` matching a configured token records its hash in the signed
    session cookie and redirects to the same URL without the token;
  - a request is authorised only if the session's token hash is STILL in the
    configured set, so removing a token immediately invalidates its sessions;
  - everything else gets 401.
"""

import hashlib
from typing import Awaitable, Callable, Iterable

from starlette.requests import Request
from starlette.responses import PlainTextResponse, RedirectResponse, Response

_Next = Callable[[Request], Awaitable[Response]]


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def make_auth_gate(tokens: Iterable[str]) -> Callable[[Request, _Next], Awaitable[Response]]:
    valid = {_hash(t) for t in tokens if t}

    async def gate(request: Request, call_next: _Next) -> Response:
        if not valid:
            return await call_next(request)
        supplied = request.query_params.get("token")
        if supplied and _hash(supplied) in valid:
            request.session["th"] = _hash(supplied)
            return RedirectResponse(str(request.url.remove_query_params("token")), status_code=303)
        if request.session.get("th") in valid:
            return await call_next(request)
        return PlainTextResponse("Unauthorized", status_code=401)

    return gate
