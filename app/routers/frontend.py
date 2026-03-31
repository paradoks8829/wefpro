from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.database import get_db
from app import models
from app.config import get_settings

# Создаём роутер (группу маршрутов)
router = APIRouter()

# Настраиваем Jinja2 для работы с HTML-шаблонами
templates = Jinja2Templates(directory="app/templates")

# Получаем настройки (чтобы взять имя проекта)
settings = get_settings()

@router.get("/")
async def home(request: Request, db: Session = Depends(get_db)):
    """
    ГЛАВНАЯ СТРАНИЦА
    
    1. Получает из БД последние 3 новости
    2. Передаёт их в шаблон index.html
    3. Возвращает готовую HTML-страницу
    """
    
    # ЗАПРОС К БАЗЕ ДАННЫХ:
    # Берём из таблицы News только опубликованные, сортируем по дате (сначала новые),
    # ограничиваем 3 записями
    latest_news = db.query(models.News).filter(
        models.News.is_published == True
    ).order_by(
        models.News.created_at.desc()
    ).limit(3).all()
    
    # ОТДАЁМ HTML:
    # Берём шаблон index.html, подставляем в него переменные
    return templates.TemplateResponse("index.html", {
        "request": request,              # обязательно для Jinja2
        "news": latest_news,             # список новостей
        "project_name": settings.PROJECT_NAME  # имя сайта из .env
    })