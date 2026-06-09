from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app import auth, models
from app.config import get_settings
from app.database import get_db
from app.dependencies import ACCESS_TOKEN_COOKIE, get_current_librarian_web

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
async def login_page(request: Request):
    token = request.cookies.get(ACCESS_TOKEN_COOKIE)
    if token and auth.decode_access_token(token):
        return RedirectResponse(url="/admin", status_code=status.HTTP_303_SEE_OTHER)

    return templates.TemplateResponse("admin/login.html", _ctx(request))


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
    response.set_cookie(
        key=ACCESS_TOKEN_COOKIE,
        value=auth.create_access_token(librarian.username),
        httponly=True,
        samesite="lax",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    return response


@router.post("/logout")
async def logout():
    response = RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie(ACCESS_TOKEN_COOKIE)
    return response


@router.get("")
async def dashboard(
    request: Request,
    db: AsyncSession = Depends(get_db),
    librarian: models.Librarian = Depends(get_current_librarian_web),
):
    news_count = await db.scalar(select(func.count()).select_from(models.News))
    products_count = await db.scalar(select(func.count()).select_from(models.Product))
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


# --- Товары ---

@router.get("/products")
async def products_list(
    request: Request,
    db: AsyncSession = Depends(get_db),
    librarian: models.Librarian = Depends(get_current_librarian_web),
):
    result = await db.execute(
        select(models.Product).order_by(models.Product.category, models.Product.name)
    )
    return templates.TemplateResponse(
        "admin/products_list.html",
        _ctx(request, librarian, active_page="products", products=result.scalars().all()),
    )


@router.get("/products/new")
async def product_create_form(
    request: Request,
    librarian: models.Librarian = Depends(get_current_librarian_web),
):
    return templates.TemplateResponse(
        "admin/product_form.html",
        _ctx(request, librarian, active_page="products", product=None),
    )


@router.post("/products/new")
async def product_create_submit(
    name: str = Form(...),
    producer: str = Form(""),
    category: str = Form(""),
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
        category=category.strip() or None,
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
    return templates.TemplateResponse(
        "admin/product_form.html",
        _ctx(request, librarian, active_page="products", product=product),
    )


@router.post("/products/{product_id}/edit")
async def product_edit_submit(
    product_id: int,
    name: str = Form(...),
    producer: str = Form(""),
    category: str = Form(""),
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
    product.category = category.strip() or None
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


async def _get_news(db: AsyncSession, news_id: int) -> models.News | None:
    result = await db.execute(select(models.News).where(models.News.id == news_id))
    return result.scalar_one_or_none()


async def _get_product(db: AsyncSession, product_id: int) -> models.Product | None:
    result = await db.execute(select(models.Product).where(models.Product.id == product_id))
    return result.scalar_one_or_none()
