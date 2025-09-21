# .env (пример файла окружения)
"""
# База данных
DATABASE_URL=postgresql://postgres:password@localhost:5432/trader_tracker

# Tinkoff API
TINKOFF_TOKEN=your_tinkoff_token_here
TINKOFF_SANDBOX=false

# Telegram API
TELEGRAM_API_ID=your_api_id
TELEGRAM_API_HASH=your_api_hash

# API настройки
PORT=8000
DEBUG=true
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

# Функции
ENABLE_TELEGRAM=true
ENABLE_TINKOFF=true
ENABLE_BG_TASKS=true

# Логирование
LOG_LEVEL=INFO
LOG_FILE=logs/trader_tracker.log
"""

# docker-compose.yml
"""
version: '3.8'

services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: trader_tracker
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./sql/init.sql:/docker-entrypoint-initdb.d/init.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 30s
      timeout: 10s
      retries: 5

  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://postgres:password@postgres:5432/trader_tracker
      TINKOFF_TOKEN: ${TINKOFF_TOKEN}
      TELEGRAM_API_ID: ${TELEGRAM_API_ID}
      TELEGRAM_API_HASH: ${TELEGRAM_API_HASH}
    depends_on:
      postgres:
        condition: service_healthy
    volumes:
      - ./logs:/app/logs
      - ./.env:/app/.env
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
"""

# Dockerfile
"""
FROM python:3.11-slim

WORKDIR /app

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Копируем requirements и устанавливаем Python пакеты
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем исходный код
COPY . .

# Создаем директории
RUN mkdir -p logs

# Устанавливаем переменную окружения
ENV PYTHONPATH=/app

# Команда запуска
CMD ["python", "-m", "uvicorn", "api.app:app", "--host", "0.0.0.0", "--port", "8000"]
"""