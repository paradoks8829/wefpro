"""
Создание учётной записи библиотекаря (администратора контента).

Пример:
    python scripts/create_librarian.py admin secretpassword
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select

from app import auth, models
from app.database import AsyncSessionLocal, init_db


async def create_librarian(username: str, password: str) -> None:
    await init_db()

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(models.Librarian).where(models.Librarian.username == username)
        )
        if result.scalar_one_or_none():
            print(f"Пользователь '{username}' уже существует")
            return

        librarian = models.Librarian(
            username=username,
            hashed_password=auth.get_password_hash(password),
        )
        db.add(librarian)
        await db.commit()
        print(f"Библиотекарь '{username}' создан")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Использование: python scripts/create_librarian.py <username> <password>")
        sys.exit(1)

    asyncio.run(create_librarian(sys.argv[1], sys.argv[2]))
