from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.database import init_db
from app.dependencies import WebAuthRedirect
from app.routers import admin, admin_web, auth, frontend

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

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


@app.get("/health")
async def health_check():
    return {"status": "ok"}
