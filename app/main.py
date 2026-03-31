from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.routers import frontend  # импортируем наш роутер
from app.config import get_settings

# Получаем настройки
settings = get_settings()

# СОЗДАЁМ ПРИЛОЖЕНИЕ
app = FastAPI(title=settings.PROJECT_NAME)

# ПОДКЛЮЧАЕМ СТАТИКУ (CSS, картинки)
# Все файлы из папки static будут доступны по URL /static/...
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# ПОДКЛЮЧАЕМ РОУТЕР (все маршруты из frontend.py)
app.include_router(frontend.router)

# Для проверки, что сервер работает
@app.get("/health")
async def health_check():
    return {"status": "ok"}