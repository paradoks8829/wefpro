from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.database import init_db
from app.dependencies import WebAuthRedirect
from app.files import ensure_upload_dirs
from app.routers import admin, admin_web, auth, frontend

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_upload_dirs()
    await init_db()
    yield


app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

upload_dir = Path(settings.UPLOAD_DIR)
upload_dir.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

app.include_router(frontend.router)
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(admin_web.router)


@app.exception_handler(WebAuthRedirect)
async def web_auth_redirect_handler(request, exc: WebAuthRedirect):
    from app.dependencies import clear_auth_cookie

    response = RedirectResponse(url=exc.url, status_code=303)
    clear_auth_cookie(response)
    return response


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    if (
        exc.status_code == status.HTTP_409_CONFLICT
        and request.url.path.startswith("/admin")
        and request.method == "POST"
    ):
        referer = request.headers.get("referer", "/admin")
        return RedirectResponse(url=referer, status_code=303)

    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=getattr(exc, "headers", None) or {},
    )


@app.get("/health")
async def health_check():
    return {"status": "ok"}
