# core/models.py - ИСПРАВЛЕННАЯ ВЕРСИЯ
from sqlalchemy import (
    Column, String, BigInteger, Integer, Numeric, Text, 
    Boolean, DateTime, UniqueConstraint, Index, ForeignKey
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum

Base = declarative_base()

class SignalDirection(str, Enum):
    LONG = "long"
    SHORT = "short"
    EXIT = "exit"

class SignalStatus(str, Enum):
    ACTIVE = "active"
    CLOSED = "closed"
    STOPPED = "stopped"
    EXPIRED = "expired"

# ===== TELEGRAM DATA MODELS =====

class RawMessage(Base):
    """Сырые сообщения из Telegram"""
    __tablename__ = 'raw_messages'
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    channel_id = Column(BigInteger, nullable=False)  # Без foreign key - просто ID
    message_id = Column(BigInteger, nullable=False)
    
    # Автор сообщения
    author_id = Column(BigInteger)
    author_username = Column(String(100))
    author_first_name = Column(String(100))
    
    # Содержимое сообщения
    text = Column(Text)
    views = Column(Integer, default=0)
    forwards = Column(Integer, default=0)
    
    # Метаданные
    edit_date = Column(DateTime(timezone=True))
    media_type = Column(String(50))
    reply_to_message_id = Column(BigInteger)
    raw_data = Column(JSONB)
    collected_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Статус обработки
    is_processed = Column(Boolean, default=False)
    processing_attempts = Column(Integer, default=0)
    
    # Relationships - ТОЛЬКО с parsed_signals
    parsed_signals = relationship("ParsedSignal", back_populates="raw_message")
    
    __table_args__ = (
        UniqueConstraint('channel_id', 'message_id', name='unique_channel_message'),
        Index('idx_raw_messages_channel_timestamp', 'channel_id', 'timestamp'),
        Index('idx_raw_messages_unprocessed', 'is_processed', 'timestamp'),
    )

class ParsedSignal(Base):
    """Распознанные торговые сигналы"""
    __tablename__ = 'parsed_signals'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    raw_message_id = Column(BigInteger, ForeignKey('raw_messages.id'), nullable=True)
    
    # Временные метки
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Метаданные парсинга
    parser_version = Column(String(20), nullable=False)
    confidence_score = Column(Numeric(3, 2))  # 0.00 - 1.00
    
    # Канал и автор
    channel_id = Column(BigInteger, nullable=False)  # Без foreign key - просто ID
    trader_id = Column(Integer, ForeignKey('traders.id'), nullable=True)
    author = Column(String(100))  # Имя автора из сообщения
    
    # Исходный текст
    original_text = Column(Text, nullable=False)
    
    # Основные торговые данные
    ticker = Column(String(10), nullable=False, index=True)
    figi = Column(String(12), nullable=True)  # FIGI для Tinkoff API
    direction = Column(String(10))  # long, short, exit
    signal_type = Column(String(10))  # entry, exit, update
    
    # Цены
    target_price = Column(Numeric(12, 4))
    stop_loss = Column(Numeric(12, 4))
    take_profit = Column(Numeric(12, 4))
    entry_condition = Column(String(20))  # market, limit, not_above, not_below
    
    # Дополнительные данные
    confidence_level = Column(String(10))  # high, medium, low
    timeframe = Column(String(10))  # 1h, 1d, 1w
    views = Column(Integer, default=0)
    
    # Результаты парсинга
    extracted_data = Column(JSONB)
    
    # Relationships
    raw_message = relationship("RawMessage", back_populates="parsed_signals")
    trader = relationship("Trader", back_populates="signals")
    signal_result = relationship("SignalResult", back_populates="signal", uselist=False)
    
    __table_args__ = (
        Index('idx_parsed_signals_ticker_timestamp', 'ticker', 'timestamp'),
        Index('idx_parsed_signals_author', 'author'),
        Index('idx_parsed_signals_direction', 'direction'),
        Index('idx_parsed_signals_channel_timestamp', 'channel_id', 'timestamp'),
    )

# ===== TRADER TRACKING MODELS =====

class Trader(Base):
    """Профили трейдеров для отслеживания статистики"""
    __tablename__ = 'traders'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    telegram_username = Column(String(100))
    channel_id = Column(BigInteger, nullable=False)  # Без foreign key - просто ID
    
    # Метаданные
    is_active = Column(Boolean, default=True)
    first_signal_at = Column(DateTime(timezone=True))
    last_signal_at = Column(DateTime(timezone=True))
    total_signals = Column(Integer, default=0)
    
    # Кешированная статистика (обновляется периодически)
    win_rate = Column(Numeric(5, 2))  # Процент прибыльных сделок
    avg_profit_pct = Column(Numeric(8, 4))  # Средняя прибыль в %
    max_drawdown_pct = Column(Numeric(8, 4))  # Максимальная просадка в %
    sharpe_ratio = Column(Numeric(6, 3))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships - БЕЗ channel
    signals = relationship("ParsedSignal", back_populates="trader")
    
    __table_args__ = (
        Index('idx_traders_name', 'name'),
        Index('idx_traders_active', 'is_active'),
    )

class SignalResult(Base):
    """Результаты отслеживания сигналов"""
    __tablename__ = 'signal_results'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    signal_id = Column(UUID(as_uuid=True), ForeignKey('parsed_signals.id'), nullable=False)
    
    # Цены исполнения (факт vs план)
    planned_entry_price = Column(Numeric(12, 4))  # Запланированная цена входа
    actual_entry_price = Column(Numeric(12, 4))   # Фактическая цена входа
    exit_price = Column(Numeric(12, 4))           # Цена выхода
    
    # Результаты
    profit_loss_pct = Column(Numeric(8, 4))       # P&L в процентах
    profit_loss_abs = Column(Numeric(12, 4))      # P&L в абсолютных значениях
    
    # Временные метки
    entry_time = Column(DateTime(timezone=True))   # Время входа
    exit_time = Column(DateTime(timezone=True))    # Время выхода
    duration_minutes = Column(Integer)             # Время в позиции
    
    # Статус позиции
    status = Column(String(20), default='active') # active, closed, stopped, expired
    exit_reason = Column(String(50))               # take_profit, stop_loss, manual, timeout
    
    # Метаданные отслеживания
    tracking_started_at = Column(DateTime(timezone=True), server_default=func.now())
    last_updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    signal = relationship("ParsedSignal", back_populates="signal_result")
    
    __table_args__ = (
        Index('idx_signal_results_status', 'status'),
        Index('idx_signal_results_profit', 'profit_loss_pct'),
        Index('idx_signal_results_duration', 'duration_minutes'),
    )

# ===== MARKET DATA MODELS =====

class Instrument(Base):
    """Инструменты для торговли"""
    __tablename__ = 'instruments'
    
    figi = Column(String(12), primary_key=True)
    ticker = Column(String(10), unique=True, nullable=False)
    name = Column(String(200))
    type = Column(String(20))  # share, etf, bond, future, currency
    currency = Column(String(3))
    lot = Column(Integer, default=1)
    
    # Метаданные
    is_active = Column(Boolean, default=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    __table_args__ = (
        Index('idx_instruments_ticker', 'ticker'),
        Index('idx_instruments_type', 'type'),
    )

class ParsingPattern(Base):
    """Паттерны для парсинга сообщений (регулярные выражения)"""
    __tablename__ = 'parsing_patterns'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    category = Column(String(50), nullable=False)
    pattern = Column(Text, nullable=False)
    priority = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    description = Column(Text)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    __table_args__ = (
        Index('idx_patterns_category_priority', 'category', 'priority', 'is_active'),
        Index('idx_patterns_active', 'is_active'),
    )

class Candle(Base):
    """Свечные данные"""
    __tablename__ = 'candles'
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    instrument_id = Column(String(12), ForeignKey('instruments.figi'), nullable=False)
    interval = Column(String(10), nullable=False)  # 1min, 5min, hour, day
    time = Column(DateTime(timezone=True), nullable=False)
    
    open = Column(Numeric(12, 4), nullable=False)
    high = Column(Numeric(12, 4), nullable=False)
    low = Column(Numeric(12, 4), nullable=False)
    close = Column(Numeric(12, 4), nullable=False)
    volume = Column(BigInteger, default=0)
    
    __table_args__ = (
        UniqueConstraint('instrument_id', 'interval', 'time', name='unique_candle'),
        Index('idx_candles_instrument_time', 'instrument_id', 'time'),
        Index('idx_candles_interval_time', 'interval', 'time'),
    )

# ===== DATACLASSES FOR API RESPONSES =====

@dataclass
class TraderStatsResponse:
    """Статистика трейдера для API"""
    trader_name: str
    total_signals: int
    active_signals: int
    closed_signals: int
    win_rate: float
    avg_profit_pct: float
    max_drawdown_pct: float
    sharpe_ratio: Optional[float]
    first_signal: Optional[datetime]
    last_signal: Optional[datetime]

@dataclass
class SignalWithResult:
    """Сигнал с результатом для API"""
    signal_id: str
    timestamp: datetime
    trader: str
    ticker: str
    direction: str
    target_price: Optional[float]
    stop_loss: Optional[float]
    take_profit: Optional[float]
    
    # Результаты (если есть)
    actual_entry_price: Optional[float] = None
    exit_price: Optional[float] = None
    profit_loss_pct: Optional[float] = None
    duration_minutes: Optional[int] = None
    status: str = 'active'
    exit_reason: Optional[str] = None

@dataclass
class ChartDataPoint:
    """Точка данных для графика"""
    timestamp: datetime
    price: float
    signal_type: Optional[str] = None  # 'entry_long', 'entry_short', 'exit'
    signal_id: Optional[str] = None
    trader: Optional[str] = None