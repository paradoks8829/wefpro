from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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
async def catalog_page(request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(models.Product)
        .where(models.Product.is_published.is_(True))
        .order_by(models.Product.category, models.Product.name)
    )
    products = result.scalars().all()
    categories = sorted({p.category for p in products if p.category})

    return templates.TemplateResponse(
        "catalog.html",
        _template_context(request, products=products, categories=categories, active_page="catalog"),
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
async def partners_page(request: Request):
    partners = [
        "ТЕХНОПРОМ",
        "ГазКомплект",
        "ЭКЗ Сервис",
        "НефтеМаш",
        "РосТехИнжиниринг",
        "СтройНефтеГаз",
    ]
    return templates.TemplateResponse(
        "partners.html",
        _template_context(request, partners=partners, active_page="partners"),
    )
