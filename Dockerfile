# Используем официальный образ Python
FROM python:3.12-slim

# Устанавливаем рабочую директорию внутри контейнера
WORKDIR /app

# Копируем файл с зависимостями и устанавливаем их
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь код вашего приложения
COPY . .

RUN mkdir -p uploads/images uploads/documents

# Команда для запуска сервера (с синхронизацией файлов для разработки)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]