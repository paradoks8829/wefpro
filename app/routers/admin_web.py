from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app import auth, models
from app.config import get_settings
from app.csrf import apply_csrf_cookie, clear_csrf_cookie, get_csrf_token, verify_csrf
from app.database import get_db
from app.files import resolve_document_url, resolve_image_url, save_image
from app.form_nonce import consume_form_nonce, generate_form_nonce
from app.rate_limit import check_rate_limit
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


def _render(
    request: Request,
    template: str,
    *,
    status_code: int = 200,
    librarian: models.Librarian | None = None,
    form_nonce: str | None = None,
    **extra,
):
    csrf_token = get_csrf_token(request)
    response = templates.TemplateResponse(
        template,
        _ctx(request, librarian, csrf_token=csrf_token, form_nonce=form_nonce, **extra),
        status_code=status_code,
    )
    apply_csrf_cookie(response, request, csrf_token)
    return response


def _verify_csrf(request: Request, csrf_token: str) -> None:
    verify_csrf(request, csrf_token)


def _verify_csrf_and_nonce(request: Request, csrf_token: str, form_nonce: str) -> None:
    verify_csrf(request, csrf_token)
    if not consume_form_nonce(form_nonce):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Форма уже была отправлена",
        )


@router.get("/login")
async def login_page(request: Request, db: AsyncSession = Depends(get_db)):
    token = request.cookies.get(ACCESS_TOKEN_COOKIE)
    librarian = await _get_librarian_by_token(token, db)
    if librarian:
        return RedirectResponse(url="/admin", status_code=status.HTTP_303_SEE_OTHER)

    response = _render(request, "admin/login.html")
    if token:
        clear_auth_cookie(response)
    return response


@router.post("/login")
async def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    csrf_token: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    try:
        check_rate_limit(request, "admin_login")
        verify_csrf(request, csrf_token)
    except HTTPException as exc:
        return _render(
            request,
            "admin/login.html",
            status_code=exc.status_code,
            error=exc.detail if isinstance(exc.detail, str) else "Ошибка запроса",
        )

    result = await db.execute(
        select(models.Librarian).where(models.Librarian.username == username)
    )
    librarian = result.scalar_one_or_none()

    if (
        librarian is None
        or not librarian.is_active
        or not auth.verify_password(password, librarian.hashed_password)
    ):
        return _render(
            request,
            "admin/login.html",
            status_code=status.HTTP_401_UNAUTHORIZED,
            error="Неверный логин или пароль",
        )

    response = RedirectResponse(url="/admin", status_code=status.HTTP_303_SEE_OTHER)
    set_auth_cookie(
        response,
        auth.create_access_token(librarian.username),
        settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    return response


@router.post("/logout")
async def logout(request: Request, csrf_token: str = Form(...)):
    verify_csrf(request, csrf_token)
    response = RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)
    clear_auth_cookie(response)
    clear_csrf_cookie(response)
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

    return _render(
        request,
        "admin/dashboard.html",
        librarian=librarian,
        active_page="dashboard",
        news_count=news_count or 0,
        products_count=products_count or 0,
        partners_count=partners_count or 0,
        categories_count=categories_count or 0,
        published_news=published_news or 0,
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
    return _render(
        request,
        "admin/news_list.html",
        librarian=librarian,
        active_page="news",
        news_items=result.scalars().all(),
    )


@router.get("/news/new")
async def news_create_form(
    request: Request,
    librarian: models.Librarian = Depends(get_current_librarian_web),
):
    return _render(
        request,
        "admin/news_form.html",
        librarian=librarian,
        active_page="news",
        news_item=None,
        form_nonce=generate_form_nonce(),
    )


@router.post("/news/new")
async def news_create_submit(
    request: Request,
    title: str = Form(...),
    content: str = Form(...),
    is_published: bool = Form(False),
    csrf_token: str = Form(...),
    form_nonce: str = Form(...),
    db: AsyncSession = Depends(get_db),
    librarian: models.Librarian = Depends(get_current_librarian_web),
):
    _verify_csrf_and_nonce(request, csrf_token, form_nonce)
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
    return _render(
        request,
        "admin/news_form.html",
        librarian=librarian,
        active_page="news",
        news_item=news_item,
        form_nonce=generate_form_nonce(),
    )


@router.post("/news/{news_id}/edit")
async def news_edit_submit(
    request: Request,
    news_id: int,
    title: str = Form(...),
    content: str = Form(...),
    is_published: bool = Form(False),
    csrf_token: str = Form(...),
    form_nonce: str = Form(...),
    db: AsyncSession = Depends(get_db),
    librarian: models.Librarian = Depends(get_current_librarian_web),
):
    _verify_csrf_and_nonce(request, csrf_token, form_nonce)
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
    request: Request,
    news_id: int,
    csrf_token: str = Form(...),
    db: AsyncSession = Depends(get_db),
    librarian: models.Librarian = Depends(get_current_librarian_web),
):
    _verify_csrf(request, csrf_token)
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
    return _render(
        request,
        "admin/categories_list.html",
        librarian=librarian,
        active_page="categories",
        categories=result.scalars().all(),
    )


@router.get("/categories/new")
async def category_create_form(
    request: Request,
    librarian: models.Librarian = Depends(get_current_librarian_web),
):
    return _render(
        request,
        "admin/category_form.html",
        librarian=librarian,
        active_page="categories",
        category=None,
        form_nonce=generate_form_nonce(),
    )


@router.post("/categories/new")
async def category_create_submit(
    request: Request,
    name: str = Form(...),
    slug: str = Form(...),
    sort_order: int = Form(0),
    is_published: bool = Form(False),
    csrf_token: str = Form(...),
    form_nonce: str = Form(...),
    db: AsyncSession = Depends(get_db),
    librarian: models.Librarian = Depends(get_current_librarian_web),
):
    _verify_csrf_and_nonce(request, csrf_token, form_nonce)
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
    return _render(
        request,
        "admin/category_form.html",
        librarian=librarian,
        active_page="categories",
        category=category,
        form_nonce=generate_form_nonce(),
    )


@router.post("/categories/{category_id}/edit")
async def category_edit_submit(
    request: Request,
    category_id: int,
    name: str = Form(...),
    slug: str = Form(...),
    sort_order: int = Form(0),
    is_published: bool = Form(False),
    csrf_token: str = Form(...),
    form_nonce: str = Form(...),
    db: AsyncSession = Depends(get_db),
    librarian: models.Librarian = Depends(get_current_librarian_web),
):
    _verify_csrf_and_nonce(request, csrf_token, form_nonce)
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
    request: Request,
    category_id: int,
    csrf_token: str = Form(...),
    db: AsyncSession = Depends(get_db),
    librarian: models.Librarian = Depends(get_current_librarian_web),
):
    _verify_csrf(request, csrf_token)
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
    return _render(
        request,
        "admin/products_list.html",
        librarian=librarian,
        active_page="products",
        products=result.scalars().all(),
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
    return _render(
        request,
        "admin/product_form.html",
        librarian=librarian,
        active_page="products",
        product=None,
        categories=categories,
        preset_category_id=preset_category_id,
        form_nonce=generate_form_nonce(),
    )


@router.post("/products/new")
async def product_create_submit(
    request: Request,
    name: str = Form(...),
    producer: str = Form(""),
    category_id: str = Form(""),
    image_url: str = Form(""),
    pdf_url: str = Form(""),
    description: str = Form(""),
    is_published: bool = Form(False),
    csrf_token: str = Form(...),
    form_nonce: str = Form(...),
    image_file: UploadFile | None = File(None),
    pdf_file: UploadFile | None = File(None),
    db: AsyncSession = Depends(get_db),
    librarian: models.Librarian = Depends(get_current_librarian_web),
):
    _verify_csrf_and_nonce(request, csrf_token, form_nonce)
    product = models.Product(
        name=name.strip(),
        producer=producer.strip() or None,
        category_id=int(category_id) if category_id else None,
        image_url=await resolve_image_url(image_file, image_url),
        pdf_url=await resolve_document_url(pdf_file, pdf_url),
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
    return _render(
        request,
        "admin/product_form.html",
        librarian=librarian,
        active_page="products",
        product=product,
        categories=categories,
        form_nonce=generate_form_nonce(),
    )


@router.post("/products/{product_id}/edit")
async def product_edit_submit(
    request: Request,
    product_id: int,
    name: str = Form(...),
    producer: str = Form(""),
    category_id: str = Form(""),
    image_url: str = Form(""),
    pdf_url: str = Form(""),
    description: str = Form(""),
    is_published: bool = Form(False),
    csrf_token: str = Form(...),
    form_nonce: str = Form(...),
    image_file: UploadFile | None = File(None),
    pdf_file: UploadFile | None = File(None),
    db: AsyncSession = Depends(get_db),
    librarian: models.Librarian = Depends(get_current_librarian_web),
):
    _verify_csrf_and_nonce(request, csrf_token, form_nonce)
    product = await _get_product(db, product_id)
    if product is None:
        return RedirectResponse(url="/admin/products", status_code=status.HTTP_303_SEE_OTHER)
    product.name = name.strip()
    product.producer = producer.strip() or None
    product.category_id = int(category_id) if category_id else None
    if image_file and image_file.filename:
        product.image_url = await resolve_image_url(image_file, "")
    elif image_url.strip():
        product.image_url = image_url.strip()
    if pdf_file and pdf_file.filename:
        product.pdf_url = await resolve_document_url(pdf_file, "")
    elif pdf_url.strip():
        product.pdf_url = pdf_url.strip()
    product.description = description.strip() or None
    product.is_published = is_published
    await db.commit()
    return RedirectResponse(url="/admin/products", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/products/{product_id}/delete")
async def product_delete(
    request: Request,
    product_id: int,
    csrf_token: str = Form(...),
    db: AsyncSession = Depends(get_db),
    librarian: models.Librarian = Depends(get_current_librarian_web),
):
    _verify_csrf(request, csrf_token)
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
    return _render(
        request,
        "admin/partners_list.html",
        librarian=librarian,
        active_page="partners",
        partners=result.scalars().all(),
    )


@router.get("/partners/new")
async def partner_create_form(
    request: Request,
    librarian: models.Librarian = Depends(get_current_librarian_web),
):
    return _render(
        request,
        "admin/partner_form.html",
        librarian=librarian,
        active_page="partners",
        partner=None,
        form_nonce=generate_form_nonce(),
    )


@router.post("/partners/new")
async def partner_create_submit(
    request: Request,
    name: str = Form(...),
    logo_url: str = Form(""),
    website_url: str = Form(""),
    description: str = Form(""),
    sort_order: int = Form(0),
    is_published: bool = Form(False),
    csrf_token: str = Form(...),
    form_nonce: str = Form(...),
    logo_file: UploadFile | None = File(None),
    db: AsyncSession = Depends(get_db),
    librarian: models.Librarian = Depends(get_current_librarian_web),
):
    _verify_csrf_and_nonce(request, csrf_token, form_nonce)
    partner = models.Partner(
        name=name.strip(),
        logo_url=await resolve_image_url(logo_file, logo_url),
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
    return _render(
        request,
        "admin/partner_form.html",
        librarian=librarian,
        active_page="partners",
        partner=partner,
        form_nonce=generate_form_nonce(),
    )


@router.post("/partners/{partner_id}/edit")
async def partner_edit_submit(
    request: Request,
    partner_id: int,
    name: str = Form(...),
    logo_url: str = Form(""),
    website_url: str = Form(""),
    description: str = Form(""),
    sort_order: int = Form(0),
    is_published: bool = Form(False),
    csrf_token: str = Form(...),
    form_nonce: str = Form(...),
    logo_file: UploadFile | None = File(None),
    db: AsyncSession = Depends(get_db),
    librarian: models.Librarian = Depends(get_current_librarian_web),
):
    _verify_csrf_and_nonce(request, csrf_token, form_nonce)
    partner = await _get_partner(db, partner_id)
    if partner is None:
        return RedirectResponse(url="/admin/partners", status_code=status.HTTP_303_SEE_OTHER)
    partner.name = name.strip()
    if logo_file and logo_file.filename:
        partner.logo_url = await save_image(logo_file)
    elif logo_url.strip():
        partner.logo_url = logo_url.strip()
    partner.website_url = website_url.strip() or None
    partner.description = description.strip() or None
    partner.sort_order = sort_order
    partner.is_published = is_published
    await db.commit()
    return RedirectResponse(url="/admin/partners", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/partners/{partner_id}/delete")
async def partner_delete(
    request: Request,
    partner_id: int,
    csrf_token: str = Form(...),
    db: AsyncSession = Depends(get_db),
    librarian: models.Librarian = Depends(get_current_librarian_web),
):
    _verify_csrf(request, csrf_token)
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
