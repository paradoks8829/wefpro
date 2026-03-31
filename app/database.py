from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import get_settings

# 1. Получаем настройки (читаем DATABASE_URL из .env)
settings = get_settings()

# 2. Создаём "движок" — ядро для работы с БД
#    connect_args нужно только для SQLite
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}
)

# 3. Создаём "фабрику сессий" — будет выдавать подключения к БД
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 4. Создаём базовый класс для моделей (таблиц)
#    Все модели будут наследоваться от него
Base = declarative_base()

# 5. Функция для получения сессии БД (будет использоваться в роутерах)
def get_db():
    """Создаёт сессию БД и автоматически закрывает её после использования"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
