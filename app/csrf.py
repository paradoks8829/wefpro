import secrets

from fastapi import HTTPException, Request, Response, status

CSRF_COOKIE = "csrf_token"


def generate_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def get_csrf_token(request: Request) -> str:
    return request.cookies.get(CSRF_COOKIE) or generate_csrf_token()


def apply_csrf_cookie(response: Response, request: Request, token: str) -> None:
    if not request.cookies.get(CSRF_COOKIE):
        response.set_cookie(
            key=CSRF_COOKIE,
            value=token,
            httponly=True,
            samesite="lax",
            path="/",
            max_age=60 * 60 * 24,
        )


def verify_csrf(request: Request, form_token: str) -> None:
    cookie_token = request.cookies.get(CSRF_COOKIE)
    if (
        not cookie_token
        or not form_token
        or not secrets.compare_digest(cookie_token, form_token)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недействительный CSRF-токен",
        )


def clear_csrf_cookie(response: Response) -> None:
    response.delete_cookie(CSRF_COOKIE, path="/")
