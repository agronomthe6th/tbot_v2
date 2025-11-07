# Trader Tracker Bot v2

Система для отслеживания и анализа торговых сигналов из Telegram каналов.

## Конфигурация

### .env файл (пример)

```env
# База данных
DATABASE_URL=postgresql://postgres:password@localhost:5432/trader_tracker

# Tinkoff API
TINKOFF_TOKEN="t.your_tinkoff_token_here"
TINKOFF_SANDBOX=true

# Telegram API credentials
tg_api_id=21638473
tg_api_hash=9f62f3896d254cf6bb5d39614709e7c3

# API настройки
PORT=8000
DEBUG=true
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

# Функции
ENABLE_TELEGRAM=true
ENABLE_TINKOFF=true
ENABLE_BG_TASKS=false

# Логирование
LOG_LEVEL=INFO
LOG_FILE=logs/trader_tracker.log

VITE_API_URL=http://localhost:8000/api
```

## Управление Telegram каналами

**Каналы управляются через БД и веб-интерфейс** (DataManagement.vue).

### Способы добавления каналов:

#### 1. Через веб-интерфейс
Откройте: `http://localhost:3000/data-management`

Нажмите "➕ Добавить канал" и введите:
- Channel ID (например: `-2198949181` или `-2907147155`)
- Название канала
- Включить мониторинг

#### 2. Через API

```bash
# Добавить канал
curl -X POST "http://localhost:8000/api/telegram/channels?channel_id=-2198949181&name=Main Trading Channel&enabled=true"

# Получить список каналов
curl "http://localhost:8000/api/telegram/channels"

# Включить/выключить канал
curl -X POST "http://localhost:8000/api/telegram/channel/-2198949181/enable"
curl -X POST "http://localhost:8000/api/telegram/channel/-2198949181/disable"

# Удалить канал
curl -X DELETE "http://localhost:8000/api/telegram/channels/-2198949181"
```

### Важно о Channel ID:

- Channel ID может быть **отрицательным числом** (для супергрупп/каналов)
- Узнать channel_id можно через бота @userinfobot или @getidsbot
- Примеры: `-2198949181`, `-2907147155`

## docker-compose.yml

```yaml
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
```

## Dockerfile

```dockerfile
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
```

## Запуск

### Локально

```bash
# 1. Установить зависимости
pip install -r requirements.txt

# 2. Запустить PostgreSQL (через Docker)
docker-compose up -d postgres

# 3. Запустить API
python -m uvicorn tbot.api.app:app --reload --host 0.0.0.0 --port 8000

# 4. Запустить frontend (в отдельном терминале)
cd frontend
npm install
npm run dev
```

### Docker

```bash
docker-compose up -d
```

## API Endpoints

### Channels Management
- `GET /api/telegram/channels` - список каналов
- `POST /api/telegram/channels` - добавить канал
- `PUT /api/telegram/channels/{channel_id}` - обновить канал
- `DELETE /api/telegram/channels/{channel_id}` - удалить канал
- `POST /api/telegram/channel/{channel_id}/enable` - включить
- `POST /api/telegram/channel/{channel_id}/disable` - выключить

### Monitoring
- `POST /api/telegram/start` - запустить мониторинг
- `POST /api/telegram/stop` - остановить мониторинг
- `GET /api/telegram/status` - статус мониторинга

### Messages & Signals
- `GET /api/signals` - получить сигналы
- `POST /api/messages/parse-all` - распарсить сообщения
- `GET /api/messages/unparsed` - непарсированные сообщения

## Структура проекта

```
tbot_v2/
├── tbot/
│   ├── api/
│   │   └── app.py                    # FastAPI приложение
│   ├── core/
│   │   └── database/
│   │       ├── models.py             # SQLAlchemy модели
│   │       └── database.py           # Database класс
│   ├── integrations/
│   │   ├── telegram_scraper.py       # Telegram клиент
│   │   └── tinkoff_integration.py    # Tinkoff API
│   ├── analysis/
│   │   ├── message_parser.py         # Парсинг сообщений
│   │   └── signal_matcher.py         # Анализ сигналов
│   └── config.py                     # Конфигурация
├── frontend/
│   └── src/
│       ├── views/
│       │   └── DataManagement.vue    # UI управления
│       └── services/
│           └── api.js                # API клиент
└── README.md
```

## Особенности

- ✅ Управление каналами через БД (без хардкода в .env)
- ✅ Веб-интерфейс для управления
- ✅ Автоматический парсинг сообщений
- ✅ Real-time мониторинг каналов
- ✅ Анализ торговых сигналов
- ✅ Интеграция с Tinkoff API
