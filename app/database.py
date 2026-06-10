from collections.abc import AsyncGenerator

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings

settings = get_settings()


def _to_async_url(url: str) -> str:
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if url.startswith("sqlite:///"):
        return url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
    return url


engine = create_async_engine(
    _to_async_url(settings.DATABASE_URL),
    echo=False,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


DEFAULT_PARTNERS = [
    "ТЕХНОПРОМ",
    "ГазКомплект",
    "ЭКЗ Сервис",
    "НефтеМаш",
    "РосТехИнжиниринг",
    "СтройНефтеГаз",
]

DEFAULT_CATEGORIES = [
    ("mennekes", "Mennekes"),
    ("hensel", "Hensel"),
    ("electro-motors", "Электродвигатели"),
    ("electro-chem-protection", "Электрохимзащита"),
    ("cables", "Кабели"),
    ("insulation", "Изоляция"),
]


def _migrate_products_schema(connection) -> None:
    """Добавляет category_id в старую таблицу products при необходимости."""
    from sqlalchemy import inspect

    inspector = inspect(connection)
    if "products" not in inspector.get_table_names():
        return

    columns = {col["name"] for col in inspector.get_columns("products")}
    if "category_id" not in columns:
        connection.execute(text("ALTER TABLE products ADD COLUMN category_id INTEGER"))


def _migrate_legacy_category_values(connection) -> None:
    """Переносит текстовое поле category -> category_id."""
    from sqlalchemy import inspect

    inspector = inspect(connection)
    if "products" not in inspector.get_table_names():
        return
    if "categories" not in inspector.get_table_names():
        return

    columns = {col["name"] for col in inspector.get_columns("products")}
    if "category" not in columns or "category_id" not in columns:
        return

    categories = connection.execute(text("SELECT id, name FROM categories")).fetchall()
    name_to_id = {name: cat_id for cat_id, name in categories}

    rows = connection.execute(
        text("SELECT id, category FROM products WHERE category IS NOT NULL AND category != ''")
    ).fetchall()

    for product_id, category_name in rows:
        category_id = name_to_id.get(category_name)
        if category_id is None:
            category_id = name_to_id.get(category_name.strip())
        if category_id is not None:
            connection.execute(
                text(
                    "UPDATE products SET category_id = :category_id "
                    "WHERE id = :product_id AND category_id IS NULL"
                ),
                {"category_id": category_id, "product_id": product_id},
            )


async def init_db() -> None:
    from app import models  # noqa: F401 — регистрация всех моделей в metadata

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_migrate_products_schema)

    async with AsyncSessionLocal() as session:
        try:
            partners_count = await session.scalar(select(func.count()).select_from(models.Partner))
            if not partners_count:
                for i, name in enumerate(DEFAULT_PARTNERS):
                    session.add(models.Partner(name=name, sort_order=i, is_published=True))

            categories_count = await session.scalar(select(func.count()).select_from(models.Category))
            if not categories_count:
                for i, (slug, name) in enumerate(DEFAULT_CATEGORIES):
                    session.add(
                        models.Category(name=name, slug=slug, sort_order=i, is_published=True)
                    )

            await session.commit()
        except Exception:
            await session.rollback()
            raise

    async with engine.begin() as conn:
        await conn.run_sync(_migrate_legacy_category_values)
