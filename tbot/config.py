# config.py
import os
from dataclasses import dataclass
from typing import List, Dict

@dataclass
class DatabaseConfig:
    """Конфигурация базы данных"""
    url: str = os.getenv(
        "DATABASE_URL", 
        "postgresql://postgres:password@localhost:5432/trader_tracker"
    )
    pool_size: int = 20
    max_overflow: int = 30
    echo: bool = False

@dataclass
class TinkoffConfig:
    """Конфигурация Tinkoff API"""
    token: str = os.getenv("TINKOFF_TOKEN", "")
    sandbox: bool = os.getenv("TINKOFF_SANDBOX", "false").lower() == "true"
    cache_ttl_seconds: int = 60

@dataclass
class TelegramConfig:
    """Конфигурация Telegram"""
    api_id: int = int(os.getenv("tg_api_id", "0"))
    api_hash: str = os.getenv("tg_api_hash", "")
    session_name: str = os.getenv("TELEGRAM_SESSION", "trader_session")

@dataclass
class TrackingConfig:
    """Конфигурация отслеживания сигналов"""
    position_timeout_hours: int = 24  # Таймаут позиций
    processing_interval_seconds: int = 60  # Интервал обработки
    max_signals_per_batch: int = 50
    lookback_days: int = 30  # Период для поиска сигналов

@dataclass 
class APIConfig:
    """Конфигурация API"""
    host: str = "0.0.0.0"
    port: int = int(os.getenv("PORT", "8000"))
    reload: bool = os.getenv("DEBUG", "false").lower() == "true"
    cors_origins: List[str] = None

    def __post_init__(self):
        if self.cors_origins is None:
            origins_str = os.getenv("CORS_ORIGINS", "*")
            self.cors_origins = [origin.strip() for origin in origins_str.split(",")]

@dataclass
class Config:
    """Главная конфигурация приложения"""
    database: DatabaseConfig
    tinkoff: TinkoffConfig
    telegram: TelegramConfig
    tracking: TrackingConfig
    api: APIConfig
    
    # Режимы работы
    enable_telegram: bool = os.getenv("ENABLE_TELEGRAM", "true").lower() == "true"
    enable_tinkoff: bool = os.getenv("ENABLE_TINKOFF", "true").lower() == "true"
    enable_background_tasks: bool = os.getenv("ENABLE_BG_TASKS", "true").lower() == "true"
    
    # Логирование
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    log_file: str = os.getenv("LOG_FILE", "logs/trader_tracker.log")

# Глобальный экземпляр конфигурации
config = Config(
    database=DatabaseConfig(),
    tinkoff=TinkoffConfig(),
    telegram=TelegramConfig(),
    tracking=TrackingConfig(),
    api=APIConfig()
)