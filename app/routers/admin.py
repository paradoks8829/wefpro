from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import models
from app.database import get_db
from app.dependencies import get_current_librarian
from app.schemas.news import NewsCreate, NewsRead, NewsUpdate
from app.schemas.products import ProductCreate, ProductRead, ProductUpdate

router = APIRouter(
    prefix="/api/admin",
    tags=["admin"],
    dependencies=[Depends(get_current_librarian)],
)


# --- Новости ---

@router.get("/news", response_model=list[NewsRead])
async def list_news(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(models.News).order_by(models.News.created_at.desc())
    )
    return result.scalars().all()


@router.post("/news", response_model=NewsRead, status_code=status.HTTP_201_CREATED)
async def create_news(data: NewsCreate, db: AsyncSession = Depends(get_db)):
    news = models.News(**data.model_dump())
    db.add(news)
    await db.commit()
    await db.refresh(news)
    return news


@router.get("/news/{news_id}", response_model=NewsRead)
async def get_news(news_id: int, db: AsyncSession = Depends(get_db)):
    news = await _get_news_or_404(db, news_id)
    return news


@router.patch("/news/{news_id}", response_model=NewsRead)
async def update_news(news_id: int, data: NewsUpdate, db: AsyncSession = Depends(get_db)):
    news = await _get_news_or_404(db, news_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(news, field, value)
    await db.commit()
    await db.refresh(news)
    return news


@router.delete("/news/{news_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_news(news_id: int, db: AsyncSession = Depends(get_db)):
    news = await _get_news_or_404(db, news_id)
    await db.delete(news)
    await db.commit()


async def _get_news_or_404(db: AsyncSession, news_id: int) -> models.News:
    result = await db.execute(select(models.News).where(models.News.id == news_id))
    news = result.scalar_one_or_none()
    if news is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Новость не найдена")
    return news


# --- Товары ---

@router.get("/products", response_model=list[ProductRead])
async def list_products(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(models.Product).order_by(models.Product.name)
    )
    return result.scalars().all()


@router.post("/products", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
async def create_product(data: ProductCreate, db: AsyncSession = Depends(get_db)):
    product = models.Product(**data.model_dump())
    db.add(product)
    await db.commit()
    await db.refresh(product)
    return product


@router.get("/products/{product_id}", response_model=ProductRead)
async def get_product(product_id: int, db: AsyncSession = Depends(get_db)):
    product = await _get_product_or_404(db, product_id)
    return product


@router.patch("/products/{product_id}", response_model=ProductRead)
async def update_product(
    product_id: int,
    data: ProductUpdate,
    db: AsyncSession = Depends(get_db),
):
    product = await _get_product_or_404(db, product_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(product, field, value)
    await db.commit()
    await db.refresh(product)
    return product


@router.delete("/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(product_id: int, db: AsyncSession = Depends(get_db)):
    product = await _get_product_or_404(db, product_id)
    await db.delete(product)
    await db.commit()


async def _get_product_or_404(db: AsyncSession, product_id: int) -> models.Product:
    result = await db.execute(select(models.Product).where(models.Product.id == product_id))
    product = result.scalar_one_or_none()
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Товар не найден")
    return product
