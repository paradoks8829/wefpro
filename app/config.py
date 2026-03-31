from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    """Настройки приложения, читаются из .env"""
    DATABASE_URL: str
    PROJECT_NAME: str
    
    class Config:
        env_file = ".env"  # откуда читать

@lru_cache()
def get_settings() -> Settings:
    """Возвращает объект с настройками (кеширует результат)"""
    return Settings()