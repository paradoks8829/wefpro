from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import models
from app.database import get_db
from app.dependencies import get_current_librarian
from app.schemas.categories import CategoryCreate, CategoryRead, CategoryUpdate
from app.schemas.news import NewsCreate, NewsRead, NewsUpdate
from app.schemas.partners import PartnerCreate, PartnerRead, PartnerUpdate
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


# --- Категории ---

@router.get("/categories", response_model=list[CategoryRead])
async def list_categories(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(models.Category).order_by(models.Category.sort_order, models.Category.name)
    )
    return result.scalars().all()


@router.post("/categories", response_model=CategoryRead, status_code=status.HTTP_201_CREATED)
async def create_category(data: CategoryCreate, db: AsyncSession = Depends(get_db)):
    category = models.Category(**data.model_dump())
    db.add(category)
    await db.commit()
    await db.refresh(category)
    return category


@router.get("/categories/{category_id}", response_model=CategoryRead)
async def get_category(category_id: int, db: AsyncSession = Depends(get_db)):
    category = await _get_category_or_404(db, category_id)
    return category


@router.patch("/categories/{category_id}", response_model=CategoryRead)
async def update_category(
    category_id: int,
    data: CategoryUpdate,
    db: AsyncSession = Depends(get_db),
):
    category = await _get_category_or_404(db, category_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(category, field, value)
    await db.commit()
    await db.refresh(category)
    return category


@router.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(category_id: int, db: AsyncSession = Depends(get_db)):
    category = await _get_category_or_404(db, category_id)
    await db.delete(category)
    await db.commit()


async def _get_category_or_404(db: AsyncSession, category_id: int) -> models.Category:
    result = await db.execute(select(models.Category).where(models.Category.id == category_id))
    category = result.scalar_one_or_none()
    if category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Категория не найдена")
    return category


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


# --- Партнёры ---

@router.get("/partners", response_model=list[PartnerRead])
async def list_partners(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(models.Partner).order_by(models.Partner.sort_order, models.Partner.name)
    )
    return result.scalars().all()


@router.post("/partners", response_model=PartnerRead, status_code=status.HTTP_201_CREATED)
async def create_partner(data: PartnerCreate, db: AsyncSession = Depends(get_db)):
    partner = models.Partner(**data.model_dump())
    db.add(partner)
    await db.commit()
    await db.refresh(partner)
    return partner


@router.get("/partners/{partner_id}", response_model=PartnerRead)
async def get_partner(partner_id: int, db: AsyncSession = Depends(get_db)):
    partner = await _get_partner_or_404(db, partner_id)
    return partner


@router.patch("/partners/{partner_id}", response_model=PartnerRead)
async def update_partner(
    partner_id: int,
    data: PartnerUpdate,
    db: AsyncSession = Depends(get_db),
):
    partner = await _get_partner_or_404(db, partner_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(partner, field, value)
    await db.commit()
    await db.refresh(partner)
    return partner


@router.delete("/partners/{partner_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_partner(partner_id: int, db: AsyncSession = Depends(get_db)):
    partner = await _get_partner_or_404(db, partner_id)
    await db.delete(partner)
    await db.commit()


async def _get_partner_or_404(db: AsyncSession, partner_id: int) -> models.Partner:
    result = await db.execute(select(models.Partner).where(models.Partner.id == partner_id))
    partner = result.scalar_one_or_none()
    if partner is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Партнёр не найден")
    return partner
