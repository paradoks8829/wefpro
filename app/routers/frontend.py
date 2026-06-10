from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app import models
from app.config import get_settings
from app.database import get_db

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")
settings = get_settings()


def _template_context(request: Request, **extra):
    return {"request": request, "project_name": settings.PROJECT_NAME, **extra}


@router.get("/")
async def home(request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(models.News)
        .where(models.News.is_published.is_(True))
        .order_by(models.News.created_at.desc())
        .limit(3)
    )
    latest_news = result.scalars().all()

    return templates.TemplateResponse(
        "index.html",
        _template_context(request, news=latest_news, active_page="home"),
    )


@router.get("/news")
async def news_page(request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(models.News)
        .where(models.News.is_published.is_(True))
        .order_by(models.News.created_at.desc())
    )
    all_news = result.scalars().all()

    return templates.TemplateResponse(
        "news.html",
        _template_context(request, news=all_news, active_page="news"),
    )


@router.get("/catalog")
async def catalog_page(
    request: Request,
    category: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    categories_result = await db.execute(
        select(models.Category)
        .where(models.Category.is_published.is_(True))
        .order_by(models.Category.sort_order, models.Category.name)
    )
    categories = categories_result.scalars().all()

    active_category = None
    if category:
        active_category = next((c for c in categories if c.slug == category), None)
    if active_category is None and categories:
        active_category = categories[0]

    products: list[models.Product] = []
    if active_category:
        products_result = await db.execute(
            select(models.Product)
            .options(selectinload(models.Product.category))
            .where(
                models.Product.is_published.is_(True),
                models.Product.category_id == active_category.id,
            )
            .order_by(models.Product.name)
        )
        products = list(products_result.scalars().all())

    return templates.TemplateResponse(
        "catalog.html",
        _template_context(
            request,
            products=products,
            categories=categories,
            active_category=active_category,
            active_page="catalog",
        ),
    )


@router.get("/products")
async def products_redirect():
    return RedirectResponse(url="/catalog", status_code=301)


@router.get("/contacts")
async def contacts_page(request: Request):
    return templates.TemplateResponse(
        "contacts.html",
        _template_context(request, active_page="contacts"),
    )


@router.get("/about")
async def about_page(request: Request):
    return templates.TemplateResponse(
        "about.html",
        _template_context(request, active_page="about"),
    )


@router.get("/partners")
async def partners_page(request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(models.Partner)
        .where(models.Partner.is_published.is_(True))
        .order_by(models.Partner.sort_order, models.Partner.name)
    )
    partners = result.scalars().all()

    return templates.TemplateResponse(
        "partners.html",
        _template_context(request, partners=partners, active_page="partners"),
    )
