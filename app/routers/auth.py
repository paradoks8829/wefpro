from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import auth, models
from app.database import get_db
from app.dependencies import get_current_librarian
from app.schemas.auth import LibrarianRead, Token

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(models.Librarian).where(models.Librarian.username == form_data.username)
    )
    librarian = result.scalar_one_or_none()

    if librarian is None or not auth.verify_password(form_data.password, librarian.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный логин или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not librarian.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Аккаунт деактивирован")

    access_token = auth.create_access_token(librarian.username)
    return Token(access_token=access_token)


@router.get("/me", response_model=LibrarianRead)
async def me(current_librarian: models.Librarian = Depends(get_current_librarian)):
    return current_librarian
