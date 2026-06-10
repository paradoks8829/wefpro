from fastapi import APIRouter, Depends, Form, Query, Request, status
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app import auth, models
from app.config import get_settings
from app.database import get_db
from app.dependencies import (
    ACCESS_TOKEN_COOKIE,
    _get_librarian_by_token,
    clear_auth_cookie,
    get_current_librarian_web,
    set_auth_cookie,
)

router = APIRouter(prefix="/admin", tags=["admin-web"])
templates = Jinja2Templates(directory="app/templates")
settings = get_settings()


def _ctx(request: Request, librarian: models.Librarian | None = None, **extra):
    return {
        "request": request,
        "project_name": settings.PROJECT_NAME,
        "librarian": librarian,
        **extra,
    }


@router.get("/login")
async def login_page(request: Request, db: AsyncSession = Depends(get_db)):
    token = request.cookies.get(ACCESS_TOKEN_COOKIE)
    librarian = await _get_librarian_by_token(token, db)
    if librarian:
        return RedirectResponse(url="/admin", status_code=status.HTTP_303_SEE_OTHER)

    response = templates.TemplateResponse("admin/login.html", _ctx(request))
    if token:
        clear_auth_cookie(response)
    return response


@router.post("/login")
async def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(models.Librarian).where(models.Librarian.username == username)
    )
    librarian = result.scalar_one_or_none()

    if (
        librarian is None
        or not librarian.is_active
        or not auth.verify_password(password, librarian.hashed_password)
    ):
        return templates.TemplateResponse(
            "admin/login.html",
            _ctx(request, error="Неверный логин или пароль"),
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    response = RedirectResponse(url="/admin", status_code=status.HTTP_303_SEE_OTHER)
    set_auth_cookie(
        response,
        auth.create_access_token(librarian.username),
        settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    return response


@router.post("/logout")
async def logout():
    response = RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)
    clear_auth_cookie(response)
    return response


@router.get("")
@router.get("/")
async def dashboard(
    request: Request,
    db: AsyncSession = Depends(get_db),
    librarian: models.Librarian = Depends(get_current_librarian_web),
):
    news_count = await db.scalar(select(func.count()).select_from(models.News))
    products_count = await db.scalar(select(func.count()).select_from(models.Product))
    partners_count = await db.scalar(select(func.count()).select_from(models.Partner))
    categories_count = await db.scalar(select(func.count()).select_from(models.Category))
    published_news = await db.scalar(
        select(func.count()).select_from(models.News).where(models.News.is_published.is_(True))
    )

    return templates.TemplateResponse(
        "admin/dashboard.html",
        _ctx(
            request,
            librarian,
            active_page="dashboard",
            news_count=news_count or 0,
            products_count=products_count or 0,
            partners_count=partners_count or 0,
            categories_count=categories_count or 0,
            published_news=published_news or 0,
        ),
    )


# --- Новости ---

@router.get("/news")
async def news_list(
    request: Request,
    db: AsyncSession = Depends(get_db),
    librarian: models.Librarian = Depends(get_current_librarian_web),
):
    result = await db.execute(
        select(models.News).order_by(models.News.created_at.desc())
    )
    return templates.TemplateResponse(
        "admin/news_list.html",
        _ctx(request, librarian, active_page="news", news_items=result.scalars().all()),
    )


@router.get("/news/new")
async def news_create_form(
    request: Request,
    librarian: models.Librarian = Depends(get_current_librarian_web),
):
    return templates.TemplateResponse(
        "admin/news_form.html",
        _ctx(request, librarian, active_page="news", news_item=None),
    )


@router.post("/news/new")
async def news_create_submit(
    request: Request,
    title: str = Form(...),
    content: str = Form(...),
    is_published: bool = Form(False),
    db: AsyncSession = Depends(get_db),
    librarian: models.Librarian = Depends(get_current_librarian_web),
):
    news = models.News(title=title.strip(), content=content.strip(), is_published=is_published)
    db.add(news)
    await db.commit()
    return RedirectResponse(url="/admin/news", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/news/{news_id}/edit")
async def news_edit_form(
    request: Request,
    news_id: int,
    db: AsyncSession = Depends(get_db),
    librarian: models.Librarian = Depends(get_current_librarian_web),
):
    news_item = await _get_news(db, news_id)
    if news_item is None:
        return RedirectResponse(url="/admin/news", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse(
        "admin/news_form.html",
        _ctx(request, librarian, active_page="news", news_item=news_item),
    )


@router.post("/news/{news_id}/edit")
async def news_edit_submit(
    news_id: int,
    title: str = Form(...),
    content: str = Form(...),
    is_published: bool = Form(False),
    db: AsyncSession = Depends(get_db),
    librarian: models.Librarian = Depends(get_current_librarian_web),
):
    news_item = await _get_news(db, news_id)
    if news_item is None:
        return RedirectResponse(url="/admin/news", status_code=status.HTTP_303_SEE_OTHER)
    news_item.title = title.strip()
    news_item.content = content.strip()
    news_item.is_published = is_published
    await db.commit()
    return RedirectResponse(url="/admin/news", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/news/{news_id}/delete")
async def news_delete(
    news_id: int,
    db: AsyncSession = Depends(get_db),
    librarian: models.Librarian = Depends(get_current_librarian_web),
):
    news_item = await _get_news(db, news_id)
    if news_item is None:
        return RedirectResponse(url="/admin/news", status_code=status.HTTP_303_SEE_OTHER)
    await db.delete(news_item)
    await db.commit()
    return RedirectResponse(url="/admin/news", status_code=status.HTTP_303_SEE_OTHER)


# --- Категории ---

@router.get("/categories")
async def categories_list(
    request: Request,
    db: AsyncSession = Depends(get_db),
    librarian: models.Librarian = Depends(get_current_librarian_web),
):
    result = await db.execute(
        select(models.Category).order_by(models.Category.sort_order, models.Category.name)
    )
    return templates.TemplateResponse(
        "admin/categories_list.html",
        _ctx(request, librarian, active_page="categories", categories=result.scalars().all()),
    )


@router.get("/categories/new")
async def category_create_form(
    request: Request,
    librarian: models.Librarian = Depends(get_current_librarian_web),
):
    return templates.TemplateResponse(
        "admin/category_form.html",
        _ctx(request, librarian, active_page="categories", category=None),
    )


@router.post("/categories/new")
async def category_create_submit(
    name: str = Form(...),
    slug: str = Form(...),
    sort_order: int = Form(0),
    is_published: bool = Form(False),
    db: AsyncSession = Depends(get_db),
    librarian: models.Librarian = Depends(get_current_librarian_web),
):
    category = models.Category(
        name=name.strip(),
        slug=slug.strip().lower(),
        sort_order=sort_order,
        is_published=is_published,
    )
    db.add(category)
    await db.commit()
    return RedirectResponse(url="/admin/categories", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/categories/{category_id}/edit")
async def category_edit_form(
    request: Request,
    category_id: int,
    db: AsyncSession = Depends(get_db),
    librarian: models.Librarian = Depends(get_current_librarian_web),
):
    category = await _get_category(db, category_id)
    if category is None:
        return RedirectResponse(url="/admin/categories", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse(
        "admin/category_form.html",
        _ctx(request, librarian, active_page="categories", category=category),
    )


@router.post("/categories/{category_id}/edit")
async def category_edit_submit(
    category_id: int,
    name: str = Form(...),
    slug: str = Form(...),
    sort_order: int = Form(0),
    is_published: bool = Form(False),
    db: AsyncSession = Depends(get_db),
    librarian: models.Librarian = Depends(get_current_librarian_web),
):
    category = await _get_category(db, category_id)
    if category is None:
        return RedirectResponse(url="/admin/categories", status_code=status.HTTP_303_SEE_OTHER)
    category.name = name.strip()
    category.slug = slug.strip().lower()
    category.sort_order = sort_order
    category.is_published = is_published
    await db.commit()
    return RedirectResponse(url="/admin/categories", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/categories/{category_id}/delete")
async def category_delete(
    category_id: int,
    db: AsyncSession = Depends(get_db),
    librarian: models.Librarian = Depends(get_current_librarian_web),
):
    category = await _get_category(db, category_id)
    if category is None:
        return RedirectResponse(url="/admin/categories", status_code=status.HTTP_303_SEE_OTHER)
    await db.delete(category)
    await db.commit()
    return RedirectResponse(url="/admin/categories", status_code=status.HTTP_303_SEE_OTHER)


# --- Товары ---

@router.get("/products")
async def products_list(
    request: Request,
    db: AsyncSession = Depends(get_db),
    librarian: models.Librarian = Depends(get_current_librarian_web),
):
    result = await db.execute(
        select(models.Product)
        .options(selectinload(models.Product.category))
        .order_by(models.Product.name)
    )
    return templates.TemplateResponse(
        "admin/products_list.html",
        _ctx(request, librarian, active_page="products", products=result.scalars().all()),
    )


@router.get("/products/new")
async def product_create_form(
    request: Request,
    category_id: int | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    librarian: models.Librarian = Depends(get_current_librarian_web),
):
    categories = await _load_categories(db)
    preset_category_id = category_id
    if preset_category_id and not any(c.id == preset_category_id for c in categories):
        preset_category_id = None
    return templates.TemplateResponse(
        "admin/product_form.html",
        _ctx(
            request,
            librarian,
            active_page="products",
            product=None,
            categories=categories,
            preset_category_id=preset_category_id,
        ),
    )


@router.post("/products/new")
async def product_create_submit(
    name: str = Form(...),
    producer: str = Form(""),
    category_id: str = Form(""),
    image_url: str = Form(""),
    pdf_url: str = Form(""),
    description: str = Form(""),
    is_published: bool = Form(False),
    db: AsyncSession = Depends(get_db),
    librarian: models.Librarian = Depends(get_current_librarian_web),
):
    product = models.Product(
        name=name.strip(),
        producer=producer.strip() or None,
        category_id=int(category_id) if category_id else None,
        image_url=image_url.strip() or None,
        pdf_url=pdf_url.strip() or None,
        description=description.strip() or None,
        is_published=is_published,
    )
    db.add(product)
    await db.commit()
    return RedirectResponse(url="/admin/products", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/products/{product_id}/edit")
async def product_edit_form(
    request: Request,
    product_id: int,
    db: AsyncSession = Depends(get_db),
    librarian: models.Librarian = Depends(get_current_librarian_web),
):
    product = await _get_product(db, product_id)
    if product is None:
        return RedirectResponse(url="/admin/products", status_code=status.HTTP_303_SEE_OTHER)
    categories = await _load_categories(db)
    return templates.TemplateResponse(
        "admin/product_form.html",
        _ctx(request, librarian, active_page="products", product=product, categories=categories),
    )


@router.post("/products/{product_id}/edit")
async def product_edit_submit(
    product_id: int,
    name: str = Form(...),
    producer: str = Form(""),
    category_id: str = Form(""),
    image_url: str = Form(""),
    pdf_url: str = Form(""),
    description: str = Form(""),
    is_published: bool = Form(False),
    db: AsyncSession = Depends(get_db),
    librarian: models.Librarian = Depends(get_current_librarian_web),
):
    product = await _get_product(db, product_id)
    if product is None:
        return RedirectResponse(url="/admin/products", status_code=status.HTTP_303_SEE_OTHER)
    product.name = name.strip()
    product.producer = producer.strip() or None
    product.category_id = int(category_id) if category_id else None
    product.image_url = image_url.strip() or None
    product.pdf_url = pdf_url.strip() or None
    product.description = description.strip() or None
    product.is_published = is_published
    await db.commit()
    return RedirectResponse(url="/admin/products", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/products/{product_id}/delete")
async def product_delete(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    librarian: models.Librarian = Depends(get_current_librarian_web),
):
    product = await _get_product(db, product_id)
    if product is None:
        return RedirectResponse(url="/admin/products", status_code=status.HTTP_303_SEE_OTHER)
    await db.delete(product)
    await db.commit()
    return RedirectResponse(url="/admin/products", status_code=status.HTTP_303_SEE_OTHER)


# --- Партнёры ---

@router.get("/partners")
async def partners_list(
    request: Request,
    db: AsyncSession = Depends(get_db),
    librarian: models.Librarian = Depends(get_current_librarian_web),
):
    result = await db.execute(
        select(models.Partner).order_by(models.Partner.sort_order, models.Partner.name)
    )
    return templates.TemplateResponse(
        "admin/partners_list.html",
        _ctx(request, librarian, active_page="partners", partners=result.scalars().all()),
    )


@router.get("/partners/new")
async def partner_create_form(
    request: Request,
    librarian: models.Librarian = Depends(get_current_librarian_web),
):
    return templates.TemplateResponse(
        "admin/partner_form.html",
        _ctx(request, librarian, active_page="partners", partner=None),
    )


@router.post("/partners/new")
async def partner_create_submit(
    name: str = Form(...),
    logo_url: str = Form(""),
    website_url: str = Form(""),
    description: str = Form(""),
    sort_order: int = Form(0),
    is_published: bool = Form(False),
    db: AsyncSession = Depends(get_db),
    librarian: models.Librarian = Depends(get_current_librarian_web),
):
    partner = models.Partner(
        name=name.strip(),
        logo_url=logo_url.strip() or None,
        website_url=website_url.strip() or None,
        description=description.strip() or None,
        sort_order=sort_order,
        is_published=is_published,
    )
    db.add(partner)
    await db.commit()
    return RedirectResponse(url="/admin/partners", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/partners/{partner_id}/edit")
async def partner_edit_form(
    request: Request,
    partner_id: int,
    db: AsyncSession = Depends(get_db),
    librarian: models.Librarian = Depends(get_current_librarian_web),
):
    partner = await _get_partner(db, partner_id)
    if partner is None:
        return RedirectResponse(url="/admin/partners", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse(
        "admin/partner_form.html",
        _ctx(request, librarian, active_page="partners", partner=partner),
    )


@router.post("/partners/{partner_id}/edit")
async def partner_edit_submit(
    partner_id: int,
    name: str = Form(...),
    logo_url: str = Form(""),
    website_url: str = Form(""),
    description: str = Form(""),
    sort_order: int = Form(0),
    is_published: bool = Form(False),
    db: AsyncSession = Depends(get_db),
    librarian: models.Librarian = Depends(get_current_librarian_web),
):
    partner = await _get_partner(db, partner_id)
    if partner is None:
        return RedirectResponse(url="/admin/partners", status_code=status.HTTP_303_SEE_OTHER)
    partner.name = name.strip()
    partner.logo_url = logo_url.strip() or None
    partner.website_url = website_url.strip() or None
    partner.description = description.strip() or None
    partner.sort_order = sort_order
    partner.is_published = is_published
    await db.commit()
    return RedirectResponse(url="/admin/partners", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/partners/{partner_id}/delete")
async def partner_delete(
    partner_id: int,
    db: AsyncSession = Depends(get_db),
    librarian: models.Librarian = Depends(get_current_librarian_web),
):
    partner = await _get_partner(db, partner_id)
    if partner is None:
        return RedirectResponse(url="/admin/partners", status_code=status.HTTP_303_SEE_OTHER)
    await db.delete(partner)
    await db.commit()
    return RedirectResponse(url="/admin/partners", status_code=status.HTTP_303_SEE_OTHER)


async def _load_categories(db: AsyncSession) -> list[models.Category]:
    result = await db.execute(
        select(models.Category).order_by(models.Category.sort_order, models.Category.name)
    )
    return list(result.scalars().all())


async def _get_category(db: AsyncSession, category_id: int) -> models.Category | None:
    result = await db.execute(select(models.Category).where(models.Category.id == category_id))
    return result.scalar_one_or_none()


async def _get_news(db: AsyncSession, news_id: int) -> models.News | None:
    result = await db.execute(select(models.News).where(models.News.id == news_id))
    return result.scalar_one_or_none()


async def _get_product(db: AsyncSession, product_id: int) -> models.Product | None:
    result = await db.execute(select(models.Product).where(models.Product.id == product_id))
    return result.scalar_one_or_none()


async def _get_partner(db: AsyncSession, partner_id: int) -> models.Partner | None:
    result = await db.execute(select(models.Partner).where(models.Partner.id == partner_id))
    return result.scalar_one_or_none()
