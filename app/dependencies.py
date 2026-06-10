from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import auth, models
from app.database import get_db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

ACCESS_TOKEN_COOKIE = "access_token"
COOKIE_PATH = "/"


def set_auth_cookie(response, token: str, max_age: int) -> None:
    response.set_cookie(
        key=ACCESS_TOKEN_COOKIE,
        value=token,
        max_age=max_age,
        path=COOKIE_PATH,
        httponly=True,
        samesite="lax",
    )


def clear_auth_cookie(response) -> None:
    response.delete_cookie(key=ACCESS_TOKEN_COOKIE, path=COOKIE_PATH)


async def _get_librarian_by_token(token: str | None, db: AsyncSession) -> models.Librarian | None:
    if not token:
        return None

    username = auth.decode_access_token(token)
    if username is None:
        return None

    result = await db.execute(
        select(models.Librarian).where(models.Librarian.username == username)
    )
    librarian = result.scalar_one_or_none()

    if librarian is None or not librarian.is_active:
        return None

    return librarian


async def get_current_librarian(
    token: str | None = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> models.Librarian:
    librarian = await _get_librarian_by_token(token, db)
    if librarian is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный токен авторизации",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return librarian


class WebAuthRedirect(Exception):
    def __init__(self, url: str = "/admin/login"):
        self.url = url


async def get_current_librarian_web(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> models.Librarian:
    token = request.cookies.get(ACCESS_TOKEN_COOKIE)
    librarian = await _get_librarian_by_token(token, db)
    if librarian is None:
        raise WebAuthRedirect()
    return librarian
