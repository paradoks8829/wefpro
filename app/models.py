from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean
from datetime import datetime
from app.database import Base  # ← импортируем Base из database.py

class News(Base):
    """
    Таблица 'news' для хранения новостей.
    
    Каждая колонка — это поле в базе данных.
    """
    __tablename__ = "news"  # имя таблицы в БД
    
    id = Column(Integer, primary_key=True, index=True)  # номер новости (сам растёт)
    title = Column(String(200), nullable=False)         # заголовок (обязательный)
    content = Column(Text, nullable=False)              # текст новости (обязательный)
    created_at = Column(DateTime, default=datetime.utcnow)  # дата создания (автоматически)
    is_published = Column(Boolean, default=True)        # опубликована? (по умолчанию да)
    
    