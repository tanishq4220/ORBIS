"""Host-only session cookies for HTTPS previews and local development.

HTTPS cookies are partitioned by the embedding site (CHIPS), so a preview can
authenticate without allowing unrestricted third-party cookies. No session
token is exposed to JavaScript. HTTP localhost keeps its SameSite=Lax cookie.
"""

from fastapi import Request, Response

COOKIE_NAME = "orbis_session"
SESSION_MAX_AGE = 86400 * 7


def _is_secure(request: Request) -> bool:
    # The TLS ingress may forward to uvicorn over HTTP.
    forwarded = request.headers.get("x-forwarded-proto", "").split(",")[0].strip()
    return request.url.scheme == "https" or forwarded == "https"


def _write_cookie(response: Response, request: Request, value: str, max_age: int) -> None:
    secure = _is_secure(request)
    cookie = Response()
    cookie.set_cookie(
        COOKIE_NAME,
        value,
        max_age=max_age,
        expires=0 if max_age == 0 else None,
        path="/",
        httponly=True,
        secure=secure,
        samesite="none" if secure else "lax",
    )
    # Python <3.14 SimpleCookie cannot encode Partitioned. Append only this
    # static attribute; Starlette still handles encoding the actual value.
    header = cookie.headers["set-cookie"]
    response.headers.append("set-cookie", header + ("; Partitioned" if secure else ""))
    response.headers["Cache-Control"] = "no-store"


def set_session_cookie(response: Response, request: Request, token: str) -> None:
    if _is_secure(request):
        # Prevent an older, unpartitioned login from shadowing the new session.
        response.delete_cookie(COOKIE_NAME, path="/", httponly=True, secure=True, samesite="none")
    _write_cookie(response, request, token, SESSION_MAX_AGE)


def clear_session_cookie(response: Response, request: Request) -> None:
    if _is_secure(request):
        # Clear any unpartitioned cookie from before the preview-cookie fix,
        # as well as the current partition's cookie.
        response.delete_cookie(COOKIE_NAME, path="/", httponly=True, secure=True, samesite="none")
    _write_cookie(response, request, "", 0)