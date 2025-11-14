# api/app.py
from fastapi import FastAPI, BackgroundTasks, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
from typing import Optional, List, Dict
from datetime import datetime, timedelta
import asyncio
import os
from enum import Enum
from sqlalchemy import and_
from analysis.consensus_detector import get_consensus_detector
from analysis.message_parser import MessageParser, MessageParsingService
from core.database import Database
from core.database.models import *
from analysis.signal_matcher import SignalMatcher
from integrations.tinkoff_integration import TinkoffIntegration
from integrations.historical_data_loader import HistoricalDataLoader
from utils.datetime_utils import now_utc, utc_from_days_ago, ensure_timezone_aware, days_between_utc
from integrations.telegram_scraper import TelegramScraper
from analysis.technical_indicators import TechnicalIndicators
import re
import pandas as pd

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("trader_tracker_api")

# Глобальные переменные
db_manager: Database = None
message_parsing_service: MessageParsingService = None
signal_matcher: SignalMatcher = None
tinkoff_client: TinkoffIntegration = None
background_tasks_running = False
historical_data_loader: HistoricalDataLoader = None
consensus_detector = None
telegram_scraper: TelegramScraper = None
telegram_monitoring_task = None

# Энумы для валидации параметров
class SignalStatus(str, Enum):
    ALL = "all"
    ACTIVE = "active"
    CLOSED = "closed"
    STOPPED = "stopped"
    EXPIRED = "expired"

class SignalDirection(str, Enum):
    ALL = "all"
    LONG = "long"
    SHORT = "short"
    EXIT = "exit"

class OrderBy(str, Enum):
    TIMESTAMP = "timestamp"
    TICKER = "ticker"
    AUTHOR = "author"
    CONFIDENCE = "confidence"

class OrderDirection(str, Enum):
    ASC = "asc"
    DESC = "desc"

def get_db_manager() -> Database:
    """Получение экземпляра Database"""
    if db_manager is None:
        raise HTTPException(status_code=503, detail="Database not initialized")
    return db_manager

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения"""
    global signal_matcher, tinkoff_client, background_tasks_running, message_parsing_service, db_manager, historical_data_loader, telegram_scraper, telegram_monitoring_task
    
    try:
        logger.info("🚀 Initializing Trader Tracker API...")
        
        # Инициализируем БД
        database_url = os.getenv("DATABASE_URL", "postgresql://user:pass@localhost/trader_tracker")
        db_manager = Database(database_url)

        # Создаем таблицы если их нет
        from core.database.migrations import create_tables
        create_tables(db_manager.engine)
        logger.info("✅ Database tables checked/created")

        message_parsing_service = MessageParsingService(
            db_manager=db_manager,
            parser=MessageParser(db_manager)
        )
        logger.info("✅ Database initialized")
        
        consensus_detector = get_consensus_detector(db_manager)
        logger.info("✅ Consensus detector initialized")

        # Инициализируем Tinkoff
        tinkoff_token = os.getenv("TINKOFF_TOKEN")
        if tinkoff_token:
            try:
                tinkoff_client = TinkoffIntegration(tinkoff_token)
                await tinkoff_client.initialize()
                logger.info("✅ Tinkoff client initialized")
            except Exception as e:
                logger.warning(f"⚠️ Tinkoff integration failed: {e}")
                tinkoff_client = None
        
        # Инициализируем signal matcher
        signal_matcher = SignalMatcher(db_manager, tinkoff_client)
        
        # Инициализируем historical data loader
        if tinkoff_client:
            historical_data_loader = HistoricalDataLoader(db_manager, tinkoff_client)
        
        # Инициализация Telegram Scraper
        telegram_api_id = os.getenv("tg_api_id")
        telegram_api_hash = os.getenv("tg_api_hash")

        if telegram_api_id and telegram_api_hash:
            try:
                telegram_scraper = TelegramScraper(
                    api_id=int(telegram_api_id),
                    api_hash=telegram_api_hash,
                    db_manager=db_manager
                )

                if await telegram_scraper.initialize():
                    # Загружаем каналы из БД
                    channels_from_db = db_manager.get_channels(enabled_only=False)

                    if channels_from_db:
                        for channel in channels_from_db:
                            await telegram_scraper.add_channel(
                                channel_id=channel['channel_id'],
                                name=channel['name'],
                                enabled=channel['is_enabled']
                            )
                        logger.info(f"✅ Telegram scraper initialized with {len(channels_from_db)} channels from DB")
                    else:
                        logger.info("✅ Telegram scraper initialized (no channels in DB yet)")
                else:
                    telegram_scraper = None
                    logger.warning("⚠️ Telegram scraper failed to initialize")
            except Exception as e:
                logger.error(f"❌ Telegram scraper error: {e}")
                telegram_scraper = None
        else:
            logger.warning("⚠️ Telegram credentials not found, scraper disabled")

        # Сейчас нет смысла в background tasks, это на будущее
        background_tasks_running = False
        asyncio.create_task(background_signal_processing())
        
        logger.info("🎉 Application initialized successfully")
        yield
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize application: {e}")
        raise
    finally:
        # Очистка при завершении
        background_tasks_running = False
        if tinkoff_client:
            await tinkoff_client.close()
        if telegram_scraper:
            await telegram_scraper.close()
        logger.info("👋 Application shutdown completed")

# Создание приложения
app = FastAPI(
    title="Trader Tracker API",
    description="Универсальный API для анализа торговых сигналов",
    version="2.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebSocket connections
websocket_connections: Dict[str, WebSocket] = {}

# ===== BACKGROUND TASKS =====

async def background_signal_processing():
    """Фоновая обработка сигналов"""
    global background_tasks_running, signal_matcher
    
    while background_tasks_running:
        try:
            if signal_matcher:
                # Обрабатываем новые сигналы
                new_tracked = await signal_matcher.process_untracked_signals(limit=20)
                if new_tracked > 0:
                    logger.info(f"📈 Started tracking {new_tracked} new signals")
                
                # Обновляем активные позиции
                updated = await signal_matcher.update_active_positions()
                if updated > 0:
                    logger.info(f"🔄 Updated {updated} active positions")
            
            await asyncio.sleep(60)  # Каждую минуту
            
        except Exception as e:
            logger.error(f"❌ Error in background processing: {e}")
            await asyncio.sleep(300)  # При ошибке ждем 5 минут

async def broadcast_update(data: dict):
    """Рассылка обновлений через WebSocket"""
    if websocket_connections:
        for connection_id, websocket in list(websocket_connections.items()):
            try:
                await websocket.send_json(data)
            except:
                del websocket_connections[connection_id]

# ===== UTILITY FUNCTIONS =====

def parse_time_range(hours_back: Optional[int] = None, days_back: Optional[int] = None) -> Optional[datetime]:
    """Парсинг временного диапазона с правильными timezone"""
    if hours_back:
        return ensure_timezone_aware(datetime.utcnow() - timedelta(hours=hours_back))
    elif days_back:
        return ensure_timezone_aware(datetime.utcnow() - timedelta(days=days_back))
    return None

# ===== SYSTEM ENDPOINTS =====

@app.get("/")
async def root():
    """Корневой endpoint"""
    return {
        "service": "Trader Tracker API",
        "version": "2.0.0",
        "status": "running",
        "timestamp": datetime.utcnow().isoformat(),
        "endpoints": {
            "signals": "/api/signals",
            "traders": "/api/traders", 
            "tickers": "/api/tickers",
            "consensus": "/api/consensus",
            "health": "/api/health",
            "docs": "/docs"
        }
    }

@app.get("/api/health")
async def health_check():
    """Проверка здоровья сервиса"""
    try:
        db = get_db_manager()
        health = db.health_check()
        
        return {
            "status": "healthy",
            "database": health.get('status', 'unknown'),
            "tinkoff": "connected" if tinkoff_client else "not_configured",
            "background_tasks": "running" if background_tasks_running else "stopped",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unavailable")

@app.get("/api/statistics")
async def get_system_statistics():
    """Общая статистика системы"""
    try:
        db = get_db_manager()
        stats = db.get_system_statistics()
        return stats
    except Exception as e:
        logger.error(f"Failed to get statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ===== SIGNALS ENDPOINTS =====

@app.get("/api/signals/stats")
async def get_signal_stats():
    """Статистика по сигналам"""
    try:
        db = get_db_manager()
        
        with db.session() as session:
            total_signals = session.query(ParsedSignal).count()
            total_messages = session.query(RawMessage).count()
            processed_messages = session.query(RawMessage).filter(
                RawMessage.is_processed == True
            ).count()
            failed_messages = session.query(RawMessage).filter(
                RawMessage.is_processed == True,
                RawMessage.parse_success == False
            ).count()
            successfully_parsed = session.query(RawMessage).filter(
                RawMessage.is_processed == True,
                RawMessage.parse_success == True
            ).count()
            
            unique_tickers = session.query(ParsedSignal.ticker).distinct().count()
            
            last_24h = datetime.utcnow() - timedelta(hours=24)
            recent_signals = session.query(ParsedSignal).filter(
                ParsedSignal.timestamp >= last_24h
            ).count()
            
            return {
                "total_signals": total_signals,
                "total_messages": total_messages,
                "processed_messages": processed_messages,
                "successfully_parsed": successfully_parsed,
                "failed_messages": failed_messages,
                "unparsed_messages": total_messages - processed_messages,
                "unique_tickers": unique_tickers,
                "recent_signals_24h": recent_signals
            }
            
    except Exception as e:
        logger.error(f"Failed to get signal stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/signals")
async def get_signals(
    # Фильтры
    ticker: Optional[str] = Query(None, description="Фильтр по тикеру"),
    author: Optional[str] = Query(None, description="Фильтр по автору"),
    trader_id: Optional[int] = Query(None, description="Фильтр по ID трейдера"),
    direction: SignalDirection = Query(SignalDirection.ALL, description="Направление сигнала"),
    status: SignalStatus = Query(SignalStatus.ALL, description="Статус сигнала"),
    
    # Временные фильтры
    hours_back: Optional[int] = Query(None, description="Сигналы за последние N часов"),
    days_back: Optional[int] = Query(None, description="Сигналы за последние N дней"),
    
    # Пагинация и сортировка
    limit: int = Query(50, ge=1, le=1000, description="Количество сигналов"),
    offset: int = Query(0, ge=0, description="Смещение для пагинации"),
    order_by: OrderBy = Query(OrderBy.TIMESTAMP, description="Поле для сортировки"),
    order_dir: OrderDirection = Query(OrderDirection.DESC, description="Направление сортировки"),
    
    # Дополнительные параметры
    include_stats: bool = Query(False, description="Включить статистику в ответ")
):
    """
    🎯 Универсальный эндпоинт для получения сигналов
    
    Поддерживает все виды фильтрации и сортировки.
    Заменяет все старые эндпоинты сигналов.
    """
    try:
        db = get_db_manager()
        
        # Парсим временной диапазон
        from_date = parse_time_range(hours_back, days_back)
        
        # Получаем сигналы с фильтрами
        signals = db.get_signals_universal(
            ticker=ticker,
            author=author,
            trader_id=trader_id,
            direction=direction if direction != SignalDirection.ALL else None,
            status=status if status != SignalStatus.ALL else None,
            from_date=from_date,
            limit=limit,
            offset=offset,
            order_by=order_by.value,
            order_desc=(order_dir == OrderDirection.DESC)
        )
        
        response = {
            "count": len(signals),
            "signals": signals,
            "filters": {
                "ticker": ticker,
                "author": author,
                "trader_id": trader_id,
                "direction": direction,
                "status": status,
                "from_date": from_date.isoformat() if from_date else None
            },
            "pagination": {
                "limit": limit,
                "offset": offset,
                "has_more": len(signals) == limit  # Простая эвристика
            }
        }
        
        # Добавляем статистику если запрошена
        if include_stats:
            stats = db.get_signals_stats(
                ticker=ticker,
                author=author,
                trader_id=trader_id,
                direction=direction if direction != SignalDirection.ALL else None,
                from_date=from_date
            )
            response["stats"] = stats
        
        return response
        
    except Exception as e:
        logger.error(f"Failed to get signals: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/signals/{signal_id}")
async def get_signal_details(signal_id: str):
    """Получение детальной информации о сигнале"""
    try:
        db = get_db_manager()
        signal = db.get_signal_by_id(signal_id)
        
        if not signal:
            raise HTTPException(status_code=404, detail="Signal not found")
        
        return signal
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get signal {signal_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))



# ===== TRADERS ENDPOINTS =====

@app.get("/api/traders")
async def get_traders(
    include_stats: bool = Query(False, description="Включить статистику по каждому трейдеру"),
    active_only: bool = Query(True, description="Только активные трейдеры")
):
    """Получение списка трейдеров"""
    try:
        db = get_db_manager()
        traders = db.get_traders(include_stats=include_stats, active_only=active_only)
        return {
            "count": len(traders),
            "traders": traders
        }
    except Exception as e:
        logger.error(f"Failed to get traders: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/traders/{trader_id}")
async def get_trader_details(trader_id: int):
    """Получение детальной информации о трейдере"""
    try:
        db = get_db_manager()
        trader = db.get_trader_by_id(trader_id)
        
        if not trader:
            raise HTTPException(status_code=404, detail="Trader not found")
        
        return trader
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get trader {trader_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/traders/{trader_id}/stats")
async def get_trader_statistics(
    trader_id: int,
    days_back: int = Query(30, ge=1, le=365, description="Период для статистики")
):
    """Получение статистики трейдера"""
    try:
        db = get_db_manager()
        from_date = ensure_timezone_aware(datetime.utcnow() - timedelta(days=days_back))
        
        stats = db.get_trader_stats(trader_id, from_date=from_date)
        
        if not stats:
            raise HTTPException(status_code=404, detail="Trader not found")
        
        return stats
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get trader {trader_id} stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ===== MARKET DATA ENDPOINTS =====

@app.get("/api/tickers")
async def get_available_tickers(
    with_stats: bool = Query(True, description="Включить статистику по тикерам"),
    include_candles_stats: bool = Query(False, description="Включить статистику по свечам")
):
    """Получение списка доступных тикеров"""
    try:
        db = get_db_manager()
        tickers = db.get_available_tickers(
            with_stats=with_stats, 
            include_candles_stats=include_candles_stats
        )
        return {
            "count": len(tickers),
            "tickers": tickers
        }
    except Exception as e:
        logger.error(f"Failed to get tickers: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/api/candles/{ticker}")
async def get_candles_data(
    ticker: str,
    days: int = Query(30, ge=1, le=365, description="Количество дней"),
    interval: str = Query('5min', description="Интервал свечей (1min, 5min, hour, day)")
):
    """Получение свечных данных для тикера"""
    try:
        db = get_db_manager()
        
        # Валидация интервала
        valid_intervals = ['1min', '5min', 'hour', 'day']
        if interval not in valid_intervals:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid interval. Supported: {', '.join(valid_intervals)}"
            )
        
        instrument = db.get_instrument_by_ticker(ticker.upper())
        
        if not instrument and tinkoff_client:
            logger.info(f"Instrument {ticker} not in DB, searching via Tinkoff API...")
            try:
                api_instrument = await tinkoff_client.find_instrument_by_ticker(ticker)
                if api_instrument:
                    db.save_instrument(
                        figi=api_instrument["figi"],
                        ticker=ticker,
                        name=api_instrument["name"],
                        instrument_type=api_instrument.get("type", "share")
                    )
                    instrument = db.get_instrument_by_ticker(ticker.upper())
                    logger.info(f"✅ Added instrument {ticker} to database")
            except Exception as e:
                logger.warning(f"⚠️ Failed to find instrument via API: {e}")
        
        if not instrument:
            raise HTTPException(
                status_code=404, 
                detail=f"Instrument {ticker} not found"
            )
        
        figi = instrument['figi']
        from_date = ensure_timezone_aware(datetime.utcnow() - timedelta(days=days))
        
        candles = db.get_candles(
            figi=figi,
            interval=interval,
            from_time=from_date
        )
        
        # Если свечей нет в БД - загружаем через API
        if not candles and tinkoff_client:
            logger.info(f"No candles for {ticker} ({interval}) in DB, loading from Tinkoff API...")
            try:
                to_date = ensure_timezone_aware(datetime.utcnow())
                api_candles = await tinkoff_client.get_candles(
                    figi=figi,
                    interval=interval,
                    from_time=from_date,
                    to_time=to_date
                )
                
                if api_candles:
                    save_result = db.save_candles(api_candles, figi=figi, interval=interval)
                    if save_result.get('saved', 0) > 0:
                        candles = api_candles
                        logger.info(f"✅ Loaded and saved {len(candles)} candles for {ticker}")
                    else:
                        logger.warning(f"⚠️ Failed to save {len(api_candles)} candles to DB")
            except Exception as e:
                logger.error(f"⚠️ Failed to load candles from API: {e}")
        
        if not candles:
            raise HTTPException(
                status_code=404,
                detail=f"No candle data available for {ticker}"
            )
        
        return {
            "ticker": ticker,
            "figi": figi,
            "interval": interval,
            "count": len(candles),
            "period_days": days,
            "candles": candles
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get candles for {ticker}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/candles/{ticker}/indicators")
async def get_candles_with_indicators(
    ticker: str,
    days: int = Query(30, ge=1, le=365, description="Количество дней"),
    interval: str = Query('5min', description="Интервал свечей (1min, 5min, hour, day)"),
    rsi_period: int = Query(14, ge=2, le=100, description="Период RSI"),
    macd_fast: int = Query(12, ge=2, le=100, description="Быстрый период MACD"),
    macd_slow: int = Query(26, ge=2, le=100, description="Медленный период MACD"),
    macd_signal: int = Query(9, ge=2, le=100, description="Период сигнальной линии MACD"),
    bb_period: int = Query(20, ge=2, le=100, description="Период Bollinger Bands"),
    bb_std: float = Query(2.0, ge=0.1, le=5.0, description="Стандартное отклонение BB")
):
    """
    Получение свечных данных для тикера с вычисленными техническими индикаторами.

    Возвращает свечи с индикаторами:
    - OBV (On-Balance Volume)
    - MACD (Moving Average Convergence Divergence)
    - RSI (Relative Strength Index)
    - Bollinger Bands

    Также возвращает текущие торговые сигналы на основе индикаторов.
    """
    try:
        db = get_db_manager()

        # Валидация интервала
        valid_intervals = ['1min', '5min', 'hour', 'day']
        if interval not in valid_intervals:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid interval. Supported: {', '.join(valid_intervals)}"
            )

        # Валидация параметров MACD
        if macd_fast >= macd_slow:
            raise HTTPException(
                status_code=400,
                detail="MACD fast period must be less than slow period"
            )

        instrument = db.get_instrument_by_ticker(ticker.upper())

        if not instrument and tinkoff_client:
            logger.info(f"Instrument {ticker} not in DB, searching via Tinkoff API...")
            try:
                api_instrument = await tinkoff_client.find_instrument_by_ticker(ticker)
                if api_instrument:
                    db.save_instrument(
                        figi=api_instrument["figi"],
                        ticker=ticker,
                        name=api_instrument["name"],
                        instrument_type=api_instrument.get("type", "share")
                    )
                    instrument = db.get_instrument_by_ticker(ticker.upper())
                    logger.info(f"✅ Added instrument {ticker} to database")
            except Exception as e:
                logger.warning(f"⚠️ Failed to find instrument via API: {e}")

        if not instrument:
            raise HTTPException(
                status_code=404,
                detail=f"Instrument {ticker} not found"
            )

        figi = instrument['figi']
        from_date = ensure_timezone_aware(datetime.utcnow() - timedelta(days=days))

        candles = db.get_candles(
            figi=figi,
            interval=interval,
            from_time=from_date
        )

        # Если свечей нет в БД - загружаем через API
        if not candles and tinkoff_client:
            logger.info(f"No candles for {ticker} ({interval}) in DB, loading from Tinkoff API...")
            try:
                to_date = ensure_timezone_aware(datetime.utcnow())
                api_candles = await tinkoff_client.get_candles(
                    figi=figi,
                    interval=interval,
                    from_time=from_date,
                    to_time=to_date
                )

                if api_candles:
                    save_result = db.save_candles(api_candles, figi=figi, interval=interval)
                    if save_result.get('saved', 0) > 0:
                        candles = api_candles
                        logger.info(f"✅ Loaded and saved {len(candles)} candles for {ticker}")
                    else:
                        logger.warning(f"⚠️ Failed to save {len(api_candles)} candles to DB")
            except Exception as e:
                logger.error(f"⚠️ Failed to load candles from API: {e}")

        if not candles:
            raise HTTPException(
                status_code=404,
                detail=f"No candle data available for {ticker}"
            )

        # Преобразуем в DataFrame для расчета индикаторов
        df = pd.DataFrame(candles)

        # Вычисляем все индикаторы
        df_with_indicators = TechnicalIndicators.calculate_all_indicators(
            df,
            price_col='close',
            volume_col='volume',
            rsi_period=rsi_period,
            macd_fast=macd_fast,
            macd_slow=macd_slow,
            macd_signal=macd_signal,
            bb_period=bb_period,
            bb_std=bb_std
        )

        # Получаем торговые сигналы
        signals = TechnicalIndicators.get_indicator_signals(df_with_indicators)

        # Конвертируем DataFrame обратно в список словарей
        # Заменяем NaN на None для корректной JSON сериализации
        result_candles = df_with_indicators.replace({pd.NA: None, float('nan'): None}).to_dict('records')

        return {
            "ticker": ticker,
            "figi": figi,
            "interval": interval,
            "count": len(result_candles),
            "period_days": days,
            "candles": result_candles,
            "indicators": {
                "rsi_period": rsi_period,
                "macd_fast": macd_fast,
                "macd_slow": macd_slow,
                "macd_signal": macd_signal,
                "bb_period": bb_period,
                "bb_std": bb_std
            },
            "signals": signals
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get candles with indicators for {ticker}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===== DATA MANAGEMENT ENDPOINTS =====

@app.post("/api/data/load")
async def load_historical_data(
    ticker: str = Query(..., description="Тикер для загрузки"),
    days_back: int = Query(30, ge=1, le=365, description="Количество дней"),
    force_reload: bool = Query(False, description="Принудительная перезагрузка"),
    background_tasks: BackgroundTasks = None
):
    """Загрузка исторических данных"""
    try:
        if not historical_data_loader:
            raise HTTPException(status_code=503, detail="Historical data loader not available")
        
        # Запускаем загрузку в фоне
        background_tasks.add_task(
            historical_data_loader.load_historical_candles,
            ticker=ticker.upper(),
            interval="5min",
            days_back=days_back,
            force_reload=force_reload
        )
        
        return {
            "status": "loading_started",
            "ticker": ticker.upper(),
            "days_back": days_back,
            "force_reload": force_reload,
            "message": "Data loading started in background"
        }
    except Exception as e:
        logger.error(f"Failed to start data loading: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/data/status")
async def get_data_status():
    """Получение статуса исторических данных"""
    try:
        if not historical_data_loader:
            raise HTTPException(status_code=503, detail="Historical data loader not available")
        
        status = await historical_data_loader.get_data_status()
        return status
    except Exception as e:
        logger.error(f"Failed to get data status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ===== SIGNAL PROCESSING ENDPOINTS =====

@app.post("/api/signals/process")
async def trigger_signal_processing(background_tasks: BackgroundTasks):
    """Ручной запуск обработки сигналов"""
    try:
        if not signal_matcher:
            raise HTTPException(status_code=503, detail="Signal matcher not initialized")
        
        background_tasks.add_task(manual_signal_processing)
        
        return {
            "status": "processing_started",
            "message": "Signal processing started in background",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to trigger signal processing: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def manual_signal_processing():
    """Ручная обработка сигналов"""
    global signal_matcher
    try:
        # Обрабатываем новые сигналы
        new_tracked = await signal_matcher.process_untracked_signals(limit=50)
        
        # Обновляем активные позиции
        updated = await signal_matcher.update_active_positions()
        
        logger.info(f"Manual processing completed: {new_tracked} new, {updated} updated")
        
        # Отправляем обновления через WebSocket
        await broadcast_update({
            'type': 'processing_complete',
            'new_tracked': new_tracked,
            'updated': updated,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Manual signal processing failed: {e}")

# ===== MESSAGE PROCESSING ENDPOINTS =====
@app.post("/api/messages/parse-all")
async def parse_all_messages(
    background_tasks: BackgroundTasks,
    limit: Optional[int] = Query(None, ge=1, le=1000, description="Максимальное количество сообщений для парсинга")
):
    """Массовый парсинг неразобранных сообщений"""
    try:
        if not message_parsing_service:
            raise HTTPException(status_code=503, detail="Message parsing service not initialized")
        
        db = get_db_manager()
        unparsed_count = len(db.get_unparsed_messages(limit=1))
        
        if unparsed_count == 0:
            return {
                "status": "no_messages",
                "message": "No unparsed messages found",
                "timestamp": datetime.utcnow().isoformat()
            }
        
        background_tasks.add_task(parse_messages_task, limit)
        
        return {
            "status": "parsing_started",
            "message": f"Parsing started for up to {limit or 'all'} messages",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to start parsing: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/patterns/{pattern_id}/test-on-messages")
async def test_pattern_on_real_messages(
    pattern_id: int,
    limit: int = Query(1000, ge=1, le=5000, description="Количество сообщений для теста")
):
    """Тестирование паттерна на реальных сырых сообщениях"""
    try:
        db = get_db_manager()
        
        # Получаем паттерн
        pattern = db.get_pattern_by_id(pattern_id)
        if not pattern:
            raise HTTPException(status_code=404, detail="Pattern not found")
        
        # Получаем последние N сырых сообщений
        messages = db.get_raw_messages_sample(limit=limit)
        
        if not messages:
            return {
                "success": True,
                "pattern": pattern,
                "messages_tested": 0,
                "matches": []
            }
        
        # Тестируем паттерн на каждом сообщении
        matches = []
        pattern_regex = pattern['pattern']
        
        for msg in messages:
            text = msg.get('text', '')
            if not text:
                continue
            
            try:
                # Ищем совпадения
                found = re.findall(pattern_regex, text, re.IGNORECASE)
                if found:
                    # Получаем детали совпадений
                    match_objects = list(re.finditer(pattern_regex, text, re.IGNORECASE))
                    
                    match_details = []
                    for match_obj in match_objects:
                        match_details.append({
                            'matched_text': match_obj.group(),
                            'start': match_obj.start(),
                            'end': match_obj.end(),
                            'groups': match_obj.groups()
                        })
                    
                    matches.append({
                        'message_id': msg.get('id'),
                        'timestamp': msg.get('timestamp'),
                        'author': msg.get('author', 'Unknown'),
                        'text': text,
                        'matches': match_details,
                        'match_count': len(match_details)
                    })
            except re.error as e:
                logger.error(f"Regex error on message {msg.get('id')}: {e}")
                continue
        
        return {
            "success": True,
            "pattern": {
                "id": pattern['id'],
                "name": pattern['name'],
                "pattern": pattern['pattern'],
                "category": pattern['category']
            },
            "messages_tested": len(messages),
            "matches_found": len(matches),
            "matches": matches[:100]  # Ограничиваем вывод 100 первыми
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to test pattern {pattern_id} on messages: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/messages/reparse-all")
async def reparse_all_messages(
    background_tasks: BackgroundTasks,
    force: bool = Query(False, description="Пересоздать все сигналы (удалит старые)")
):
    """Полный репарсинг всех сырых сообщений"""
    try:
        db = get_db_manager()
        
        # Получаем статистику перед репарсингом
        total_messages = db.get_total_messages_count()
        
        if total_messages == 0:
            raise HTTPException(status_code=400, detail="No messages to reparse")
        
        # Запускаем репарсинг в фоне
        background_tasks.add_task(
            reparse_all_messages_task,
            db,
            force
        )
        
        return {
            "status": "started",
            "message": f"Reparsing {total_messages} messages started in background",
            "total_messages": total_messages,
            "force_mode": force,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start reparse: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def reparse_all_messages_task(db, force: bool = False):
    try:
        logger.info(f"🔄 Starting full reparse (force={force})")
        
        if force:
            logger.warning("⚠️ Force mode: deleting all existing signals")
            with db.session() as session:
                results_deleted = session.query(SignalResult).delete()
                logger.info(f"🗑️ Deleted {results_deleted} signal results")
                
                signals_deleted = session.query(ParsedSignal).delete()
                logger.info(f"🗑️ Deleted {signals_deleted} parsed signals")
                
                session.commit()
        
        with db.session() as session:
            updated = session.query(RawMessage).update(
                {
                    RawMessage.is_processed: False,
                    RawMessage.parse_success: None
                }
            )
            session.commit()
            logger.info(f"🔄 Marked {updated} messages as unparsed")
        
        from analysis.message_parser import MessageParser
        parser = MessageParser(db)
        parser.reload_patterns()
        
        batch_size = 100
        offset = 0
        total_parsed = 0
        total_failed = 0
        
        while True:
            messages = db.get_unparsed_messages(limit=batch_size)
            if not messages:
                break
            
            logger.info(f"📦 Processing batch: offset={offset}, size={len(messages)}")
            
            for msg in messages:
                try:
                    result = parser.parse_raw_message(msg)
                    
                    if result.success:
                        signal_data = result.signal_data
                        signal_data['raw_message_id'] = msg['id']
                        
                        db.save_signal(signal_data)
                        total_parsed += 1
                        
                        with db.session() as session:
                            message = session.query(RawMessage).filter(
                                RawMessage.id == msg['id']
                            ).first()
                            if message:
                                message.is_processed = True
                                message.parse_success = True
                                session.commit()
                    else:
                        total_failed += 1
                        
                        with db.session() as session:
                            message = session.query(RawMessage).filter(
                                RawMessage.id == msg['id']
                            ).first()
                            if message:
                                message.is_processed = True
                                message.parse_success = False
                                session.commit()
                        
                except Exception as e:
                    logger.error(f"Error parsing message {msg.get('id')}: {e}")
                    total_failed += 1
                    
                    with db.session() as session:
                        message = session.query(RawMessage).filter(
                            RawMessage.id == msg.get('id')
                        ).first()
                        if message:
                            message.is_processed = True
                            message.parse_success = False
                            session.commit()
                    continue
            
            offset += batch_size
            
            if total_parsed % 500 == 0:
                logger.info(f"⏳ Progress: {total_parsed} parsed, {total_failed} failed")
        
        logger.info(f"✅ Reparse completed: {total_parsed} parsed, {total_failed} failed")
        
    except Exception as e:
        logger.error(f"❌ Reparse task failed: {e}")

async def parse_messages_task(limit: Optional[int]):
    """Фоновая задача парсинга сообщений"""
    global message_parsing_service
    try:
        logger.info(f"Starting batch parsing with limit={limit}")
        
        stats = message_parsing_service.parse_all_unprocessed_messages(limit=limit)
        
        logger.info(f"Parsing completed: {stats}")
        
        await broadcast_update({
            'type': 'parsing_complete',
            'stats': stats,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Batch parsing failed: {e}")
        await broadcast_update({
            'type': 'parsing_error',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        })

@app.post("/api/messages/parse")
async def parse_single_message(message_data: dict):
    """Парсинг одного сообщения"""
    try:
        if not message_parsing_service:
            raise HTTPException(status_code=503, detail="Message parsing service not initialized")
        
        result = message_parsing_service.parse_message(message_data)
        
        response = {
            "success": result.success,
            "confidence": result.confidence,
            "error": result.error,
            "signal_created": bool(result.signal_data)
        }
        
        if result.signal_data:
            response['signal_data'] = {
                'ticker': result.signal_data.get('ticker'),
                'direction': result.signal_data.get('direction'),
                'author': result.signal_data.get('author'),
                'confidence_score': result.signal_data.get('confidence_score')
            }
        
        return response
        
    except Exception as e:
        logger.error(f"Failed to parse message: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/messages/failed")
async def get_failed_messages(
    limit: int = Query(50, ge=1, le=100, description="Количество сообщений"),
    offset: int = Query(0, ge=0, description="Смещение для пагинации")
):
    """Получение списка failed сообщений (is_processed=True, parse_success=False)"""
    try:
        db = get_db_manager()
        
        with db.session() as session:
            query = session.query(RawMessage).filter(
                RawMessage.is_processed == True,
                RawMessage.parse_success == False
            ).order_by(RawMessage.timestamp.desc())
            
            total_count = query.count()
            
            messages = query.offset(offset).limit(limit).all()
            
            result = [
                {
                    'id': msg.id,
                    'channel_id': msg.channel_id,
                    'message_id': msg.message_id,
                    'timestamp': msg.timestamp.isoformat() if msg.timestamp else None,
                    'text': msg.text,
                    'text_length': len(msg.text),
                    'author': msg.author_username,
                    'collected_at': msg.collected_at.isoformat() if msg.collected_at else None
                }
                for msg in messages
            ]
            
            return {
                "count": total_count,
                "messages": result,
                "showing": len(result),
                "offset": offset,
                "limit": limit
            }
            
    except Exception as e:
        logger.error(f"Failed to get failed messages: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/messages/unparsed")
async def get_unparsed_messages(
    limit: int = Query(20, ge=1, le=100, description="Количество сообщений")
):
    """Получение списка неразобранных сообщений"""
    try:
        db = get_db_manager()
        messages = db.get_unparsed_messages(limit=limit)
        
        # Получаем общее количество неразобранных
        total_count = db.get_unparsed_messages_count()
        
        return {
            "count": total_count,
            "messages": messages,
            "showing": len(messages)
        }
    except Exception as e:
        logger.error(f"Failed to get unparsed messages: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ===== DEBUG ENDPOINTS =====

@app.get("/api/debug/signals")
async def debug_signals_data():
    """🔍 DEBUG: Детальная проверка данных сигналов"""
    try:
        db = get_db_manager()
        debug_info = db.get_debug_signals_info()
        return debug_info
    except Exception as e:
        logger.error(f"Failed to get debug info: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/debug/messages")
async def get_raw_messages_sample(
    limit: int = Query(10, ge=1, le=50, description="Количество сообщений")
):
    """DEBUG: Образец сырых сообщений"""
    try:
        db = get_db_manager()
        messages = db.get_raw_messages_sample(limit=limit)
        return {
            "count": len(messages),
            "messages": messages
        }
    except Exception as e:
        logger.error(f"Failed to get raw messages: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ===== WEBSOCKET ENDPOINTS =====

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """WebSocket для реального времени"""
    await websocket.accept()
    websocket_connections[client_id] = websocket
    
    try:
        while True:
            # Ждем сообщения от клиента
            data = await websocket.receive_text()
            logger.info(f"WebSocket message from {client_id}: {data}")
            
    except WebSocketDisconnect:
        if client_id in websocket_connections:
            del websocket_connections[client_id]
        logger.info(f"WebSocket client {client_id} disconnected")

# ===== DEPRECATED ENDPOINTS (для обратной совместимости) =====

@app.get("/api/signals/ticker/{ticker}")
async def get_signals_by_ticker_deprecated(ticker: str, days: int = Query(30)):
    """⚠️ DEPRECATED: Используйте /api/signals?ticker={ticker}"""
    return await get_signals(ticker=ticker, days_back=days)

@app.get("/api/signals/recent")
async def get_recent_signals_deprecated(hours: int = Query(24), limit: int = Query(50)):
    """⚠️ DEPRECATED: Используйте /api/signals?hours_back={hours}"""
    return await get_signals(hours_back=hours, limit=limit)

@app.get("/api/signals/active")
async def get_active_signals_deprecated():
    """⚠️ DEPRECATED: Используйте /api/signals?status=active"""
    return await get_signals(status=SignalStatus.ACTIVE)

# ===== PATTERN MANAGEMENT ENDPOINTS =====

@app.get("/api/patterns")
async def get_patterns(
    category: Optional[str] = Query(None, description="Фильтр по категории"),
    active_only: bool = Query(False, description="Только активные паттерны")
):
    """Получение списка всех паттернов"""
    try:
        db = get_db_manager()
        patterns = db.get_all_patterns(category=category, active_only=active_only)
        
        return {
            "count": len(patterns),
            "patterns": patterns
        }
    except Exception as e:
        logger.error(f"Failed to get patterns: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/patterns/{pattern_id}")
async def get_pattern(pattern_id: int):
    """Получение конкретного паттерна по ID"""
    try:
        db = get_db_manager()
        pattern = db.get_pattern_by_id(pattern_id)
        
        if not pattern:
            raise HTTPException(status_code=404, detail="Pattern not found")
        
        return pattern
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get pattern {pattern_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/patterns")
async def create_pattern(pattern_data: dict):
    """Создание нового паттерна"""
    try:
        required_fields = ['name', 'category', 'pattern']
        for field in required_fields:
            if field not in pattern_data:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Missing required field: {field}"
                )
        
        db = get_db_manager()
        pattern_id = db.create_pattern(pattern_data)
        
        return {
            "success": True,
            "pattern_id": pattern_id,
            "message": "Pattern created successfully"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create pattern: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/patterns/{pattern_id}")
async def update_pattern(pattern_id: int, update_data: dict):
    """Обновление паттерна"""
    try:
        db = get_db_manager()
        success = db.update_pattern(pattern_id, update_data)
        
        if not success:
            raise HTTPException(status_code=404, detail="Pattern not found")
        
        return {
            "success": True,
            "message": "Pattern updated successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update pattern {pattern_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/patterns/{pattern_id}")
async def delete_pattern(pattern_id: int):
    """Удаление паттерна"""
    try:
        db = get_db_manager()
        success = db.delete_pattern(pattern_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Pattern not found")
        
        return {
            "success": True,
            "message": "Pattern deleted successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete pattern {pattern_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.patch("/api/patterns/{pattern_id}/toggle")
async def toggle_pattern(pattern_id: int):
    """Включение/выключение паттерна"""
    try:
        db = get_db_manager()
        new_state = db.toggle_pattern(pattern_id)
        
        if new_state is None:
            raise HTTPException(status_code=404, detail="Pattern not found")
        
        return {
            "success": True,
            "is_active": new_state,
            "message": f"Pattern {'activated' if new_state else 'deactivated'}"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to toggle pattern {pattern_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/patterns/test")
async def test_pattern(test_data: dict):
    """Тестирование паттерна на тексте"""
    try:
        if 'pattern' not in test_data or 'text' not in test_data:
            raise HTTPException(
                status_code=400,
                detail="Required fields: pattern, text"
            )
        
        import re
        pattern = test_data['pattern']
        text = test_data['text']
        
        try:
            matches = re.findall(pattern, text, re.IGNORECASE)
            match_objects = list(re.finditer(pattern, text, re.IGNORECASE))
            
            results = []
            for match_obj in match_objects:
                results.append({
                    'match': match_obj.group(),
                    'start': match_obj.start(),
                    'end': match_obj.end(),
                    'groups': match_obj.groups()
                })
            
            return {
                "success": True,
                "matches_count": len(matches),
                "matches": results,
                "pattern": pattern,
                "text_length": len(text)
            }
        except re.error as regex_error:
            return {
                "success": False,
                "error": f"Invalid regex pattern: {str(regex_error)}"
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to test pattern: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ===== CONSENSUS ENDPOINTS =====

@app.get("/api/consensus/stats")
async def get_consensus_statistics(
    ticker: Optional[str] = Query(None),
    days_back: int = Query(30, ge=1, le=365)
):
    """Статистика по консенсусам"""
    try:
        global consensus_detector
        if not consensus_detector:
            consensus_detector = get_consensus_detector(get_db_manager())
            logger.info("Consensus detector initialized in endpoint")
        
        stats = consensus_detector.get_consensus_stats(ticker=ticker, days_back=days_back)
        return stats
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get consensus stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/consensus/detect")
async def trigger_consensus_detection(
    background_tasks: BackgroundTasks,
    ticker: Optional[str] = Query(None, description="Проверить только этот тикер"),
    hours_back: int = Query(24, ge=1, le=168, description="Проверить сигналы за N часов")
):
    """Ручной запуск детекции консенсусов (для MVP)"""
    try:
        global consensus_detector
        if not consensus_detector:
            consensus_detector = get_consensus_detector(get_db_manager())
            logger.info("Consensus detector initialized in endpoint")
        
        background_tasks.add_task(
            manual_consensus_detection,
            ticker=ticker,
            hours_back=hours_back
        )
        
        return {
            'status': 'detection_started',
            'message': 'Consensus detection started in background',
            'ticker': ticker,
            'hours_back': hours_back,
            'timestamp': datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to trigger consensus detection: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ===== CONSENSUS RULES ENDPOINTS =====

@app.get("/api/consensus/rules")
async def get_consensus_rules(
    active_only: bool = Query(False, description="Только активные правила")
):
    """Получить список правил консенсуса"""
    try:
        from core.database.models import ConsensusRule

        db = get_db_manager()

        with db.session() as session:
            query = session.query(ConsensusRule)

            if active_only:
                query = query.filter(ConsensusRule.is_active == True)

            rules = query.order_by(ConsensusRule.priority.desc(), ConsensusRule.created_at.desc()).all()

            result = []
            for rule in rules:
                result.append({
                    'id': rule.id,
                    'name': rule.name,
                    'description': rule.description,
                    'is_active': rule.is_active,
                    'priority': rule.priority,
                    'min_traders': rule.min_traders,
                    'window_minutes': rule.window_minutes,
                    'strict_consensus': rule.strict_consensus,
                    'ticker_filter': rule.ticker_filter,
                    'direction_filter': rule.direction_filter,
                    'min_confidence': rule.min_confidence,
                    'min_strength': rule.min_strength,
                    'notification_settings': rule.notification_settings,
                    'config': rule.config,
                    'created_at': rule.created_at.isoformat() if rule.created_at else None,
                    'updated_at': rule.updated_at.isoformat() if rule.updated_at else None,
                    'created_by': rule.created_by
                })

            return {
                'count': len(result),
                'rules': result
            }

    except Exception as e:
        logger.error(f"Failed to get consensus rules: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/consensus/rules")
async def create_consensus_rule(rule_data: Dict):
    """Создать новое правило консенсуса"""
    try:
        from core.database.models import ConsensusRule

        db = get_db_manager()

        with db.session() as session:
            # Проверка на уникальность имени
            existing = session.query(ConsensusRule).filter(
                ConsensusRule.name == rule_data['name']
            ).first()

            if existing:
                raise HTTPException(status_code=400, detail=f"Rule with name '{rule_data['name']}' already exists")

            rule = ConsensusRule(
                name=rule_data['name'],
                description=rule_data.get('description'),
                is_active=rule_data.get('is_active', True),
                priority=rule_data.get('priority', 0),
                min_traders=rule_data.get('min_traders', 2),
                window_minutes=rule_data.get('window_minutes', 10),
                strict_consensus=rule_data.get('strict_consensus', True),
                ticker_filter=rule_data.get('ticker_filter'),
                direction_filter=rule_data.get('direction_filter'),
                min_confidence=rule_data.get('min_confidence'),
                min_strength=rule_data.get('min_strength'),
                notification_settings=rule_data.get('notification_settings'),
                config=rule_data.get('config'),
                created_by=rule_data.get('created_by', 'web_ui')
            )

            session.add(rule)
            session.commit()

            logger.info(f"✅ Consensus rule created: {rule.name} (id={rule.id})")

            return {
                'id': rule.id,
                'name': rule.name,
                'message': 'Rule created successfully'
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create consensus rule: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/consensus/rules/{rule_id}")
async def get_consensus_rule(rule_id: int):
    """Получить детали правила консенсуса"""
    try:
        from core.database.models import ConsensusRule

        db = get_db_manager()

        with db.session() as session:
            rule = session.query(ConsensusRule).filter(ConsensusRule.id == rule_id).first()

            if not rule:
                raise HTTPException(status_code=404, detail=f"Rule {rule_id} not found")

            return {
                'id': rule.id,
                'name': rule.name,
                'description': rule.description,
                'is_active': rule.is_active,
                'priority': rule.priority,
                'min_traders': rule.min_traders,
                'window_minutes': rule.window_minutes,
                'strict_consensus': rule.strict_consensus,
                'ticker_filter': rule.ticker_filter,
                'direction_filter': rule.direction_filter,
                'min_confidence': rule.min_confidence,
                'min_strength': rule.min_strength,
                'notification_settings': rule.notification_settings,
                'config': rule.config,
                'created_at': rule.created_at.isoformat() if rule.created_at else None,
                'updated_at': rule.updated_at.isoformat() if rule.updated_at else None,
                'created_by': rule.created_by
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get consensus rule: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/consensus/rules/{rule_id}")
async def update_consensus_rule(rule_id: int, rule_data: Dict):
    """Обновить правило консенсуса"""
    try:
        from core.database.models import ConsensusRule

        db = get_db_manager()

        with db.session() as session:
            rule = session.query(ConsensusRule).filter(ConsensusRule.id == rule_id).first()

            if not rule:
                raise HTTPException(status_code=404, detail=f"Rule {rule_id} not found")

            # Обновляем только переданные поля
            if 'name' in rule_data and rule_data['name'] != rule.name:
                # Проверяем уникальность нового имени
                existing = session.query(ConsensusRule).filter(
                    ConsensusRule.name == rule_data['name'],
                    ConsensusRule.id != rule_id
                ).first()
                if existing:
                    raise HTTPException(status_code=400, detail=f"Rule with name '{rule_data['name']}' already exists")
                rule.name = rule_data['name']

            if 'description' in rule_data:
                rule.description = rule_data['description']
            if 'is_active' in rule_data:
                rule.is_active = rule_data['is_active']
            if 'priority' in rule_data:
                rule.priority = rule_data['priority']
            if 'min_traders' in rule_data:
                rule.min_traders = rule_data['min_traders']
            if 'window_minutes' in rule_data:
                rule.window_minutes = rule_data['window_minutes']
            if 'strict_consensus' in rule_data:
                rule.strict_consensus = rule_data['strict_consensus']
            if 'ticker_filter' in rule_data:
                rule.ticker_filter = rule_data['ticker_filter']
            if 'direction_filter' in rule_data:
                rule.direction_filter = rule_data['direction_filter']
            if 'min_confidence' in rule_data:
                rule.min_confidence = rule_data['min_confidence']
            if 'min_strength' in rule_data:
                rule.min_strength = rule_data['min_strength']
            if 'notification_settings' in rule_data:
                rule.notification_settings = rule_data['notification_settings']
            if 'config' in rule_data:
                rule.config = rule_data['config']

            session.commit()

            logger.info(f"✅ Consensus rule updated: {rule.name} (id={rule.id})")

            return {
                'id': rule.id,
                'name': rule.name,
                'message': 'Rule updated successfully'
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update consensus rule: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/consensus/rules/{rule_id}")
async def delete_consensus_rule(rule_id: int):
    """Удалить правило консенсуса"""
    try:
        from core.database.models import ConsensusRule

        db = get_db_manager()

        with db.session() as session:
            rule = session.query(ConsensusRule).filter(ConsensusRule.id == rule_id).first()

            if not rule:
                raise HTTPException(status_code=404, detail=f"Rule {rule_id} not found")

            rule_name = rule.name
            session.delete(rule)
            session.commit()

            logger.info(f"✅ Consensus rule deleted: {rule_name} (id={rule_id})")

            return {
                'message': f'Rule "{rule_name}" deleted successfully'
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete consensus rule: {e}")
        raise HTTPException(status_code=500, detail=str(e))
@app.get("/api/consensus/{consensus_id}")
async def get_consensus_details(consensus_id: str):
    """Получение детальной информации о консенсусе"""
    try:
        db = get_db_manager()
        
        with db.session() as session:
            from core.database.models import ConsensusEvent, ConsensusSignal
            
            event = session.query(ConsensusEvent).filter(
                ConsensusEvent.id == consensus_id
            ).first()
            
            if not event:
                raise HTTPException(status_code=404, detail="Consensus not found")
            
            consensus_signals = session.query(ConsensusSignal).filter(
                ConsensusSignal.consensus_id == event.id
            ).all()
            
            signals_data = []
            for cs in consensus_signals:
                signal = cs.signal
                signals_data.append({
                    'id': str(signal.id),
                    'author': signal.author,
                    'timestamp': signal.timestamp.isoformat(),
                    'direction': signal.direction,
                    'target_price': float(signal.target_price) if signal.target_price else None,
                    'stop_loss': float(signal.stop_loss) if signal.stop_loss else None,
                    'take_profit': float(signal.take_profit) if signal.take_profit else None,
                    'original_text': signal.original_text,
                    'is_initiator': cs.is_initiator
                })
            
            return {
                'id': str(event.id),
                'ticker': event.ticker,
                'direction': event.direction,
                'traders_count': event.traders_count,
                'window_minutes': event.window_minutes,
                'consensus_strength': event.consensus_strength,
                'rule_id': event.rule_id,
                'first_signal_at': event.first_signal_at.isoformat(),
                'last_signal_at': event.last_signal_at.isoformat(),
                'detected_at': event.detected_at.isoformat(),
                'avg_entry_price': float(event.avg_entry_price) if event.avg_entry_price else None,
                'min_entry_price': float(event.min_entry_price) if event.min_entry_price else None,
                'max_entry_price': float(event.max_entry_price) if event.max_entry_price else None,
                'price_spread_pct': float(event.price_spread_pct) if event.price_spread_pct else None,
                'status': event.status,
                'consensus_metadata': event.consensus_metadata,
                'signals': signals_data
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get consensus {consensus_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/instruments/{ticker}")
async def delete_instrument(ticker: str):
    """Удаление инструмента из базы по тикеру"""
    try:
        db = get_db_manager()
        
        ticker = ticker.upper()
        
        instrument = db.get_instrument_by_ticker(ticker)
        if not instrument:
            raise HTTPException(
                status_code=404,
                detail=f"Instrument {ticker} not found in database"
            )
        
        figi = instrument['figi']
        
        with db.session() as session:
            from core.database.models import Instrument, Candle
            
            candles_deleted = session.query(Candle).filter(
                Candle.instrument_id == figi
            ).delete()
            
            session.flush()
            
            instrument_record = session.query(Instrument).filter(
                Instrument.ticker == ticker
            ).first()
            
            if instrument_record:
                session.delete(instrument_record)
                session.flush()
            
            logger.info(f"✅ Deleted instrument {ticker} (figi={figi}) and {candles_deleted} candles")
            
            return {
                "success": True,
                "ticker": ticker,
                "figi": figi,
                "candles_deleted": candles_deleted,
                "message": f"Instrument {ticker} and its candles deleted successfully"
            }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to delete instrument {ticker}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/instruments")
async def delete_instruments_batch(tickers: List[str] = Query(..., description="Список тикеров для удаления")):
    """Удаление нескольких инструментов сразу"""
    try:
        db = get_db_manager()
        
        results = {
            "total": len(tickers),
            "deleted": [],
            "not_found": [],
            "errors": []
        }
        
        for ticker in tickers:
            try:
                ticker = ticker.upper()
                
                instrument = db.get_instrument_by_ticker(ticker)
                if not instrument:
                    results["not_found"].append(ticker)
                    continue
                
                figi = instrument['figi']
                
                with db.session() as session:
                    from core.database.models import Instrument, Candle
                    
                    candles_deleted = session.query(Candle).filter(
                        Candle.instrument_id == figi
                    ).delete()
                    
                    session.flush()
                    
                    instrument_record = session.query(Instrument).filter(
                        Instrument.ticker == ticker
                    ).first()
                    
                    if instrument_record:
                        session.delete(instrument_record)
                        session.flush()
                    
                    results["deleted"].append({
                        "ticker": ticker,
                        "figi": figi,
                        "candles_deleted": candles_deleted
                    })
                    logger.info(f"✅ Deleted {ticker} (figi={figi}), {candles_deleted} candles")
                    
            except Exception as e:
                error_msg = f"Failed to delete {ticker}: {str(e)}"
                results["errors"].append({"ticker": ticker, "error": error_msg})
                logger.error(f"❌ {error_msg}")
        
        return {
            "success": len(results["errors"]) == 0,
            "results": results,
            "summary": f"Deleted: {len(results['deleted'])}, Not found: {len(results['not_found'])}, Errors: {len(results['errors'])}"
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to process batch delete: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/consensus")
async def get_consensus_events(
    ticker: Optional[str] = Query(None, description="Фильтр по тикеру"),
    direction: Optional[str] = Query(None, description="Фильтр по направлению (long/short)"),
    status: str = Query('all', description="Фильтр по статусу (all/active/closed/expired)"),
    min_strength: Optional[int] = Query(None, ge=0, le=100, description="Минимальная сила"),
    days_back: int = Query(30, ge=1, le=365, description="Дней назад"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0)
):
    """Получение списка консенсусов с фильтрами"""
    try:
        db = get_db_manager()
        
        with db.session() as session:
            from core.database.models import ConsensusEvent, ConsensusSignal
            
            query = session.query(ConsensusEvent)
            
            if ticker:
                query = query.filter(ConsensusEvent.ticker == ticker.upper())
            
            if direction:
                query = query.filter(ConsensusEvent.direction == direction.lower())
            
            if status != 'all':
                query = query.filter(ConsensusEvent.status == status)
            
            if min_strength is not None:
                query = query.filter(ConsensusEvent.consensus_strength >= min_strength)
            
            if days_back:
                cutoff = datetime.utcnow() - timedelta(days=days_back)
                query = query.filter(ConsensusEvent.detected_at >= cutoff)
            
            total = query.count()
            
            consensus_events = query.order_by(
                ConsensusEvent.detected_at.desc()
            ).limit(limit).offset(offset).all()
            
            results = []
            for event in consensus_events:
                signals_count = session.query(ConsensusSignal).filter(
                    ConsensusSignal.consensus_id == event.id
                ).count()
                
                results.append({
                    'id': str(event.id),
                    'ticker': event.ticker,
                    'direction': event.direction,
                    'traders_count': event.traders_count,
                    'signals_count': signals_count,
                    'window_minutes': event.window_minutes,
                    'consensus_strength': event.consensus_strength,
                    'rule_id': event.rule_id,
                    'first_signal_at': event.first_signal_at.isoformat(),
                    'last_signal_at': event.last_signal_at.isoformat(),
                    'detected_at': event.detected_at.isoformat(),
                    'avg_entry_price': float(event.avg_entry_price) if event.avg_entry_price else None,
                    'price_spread_pct': float(event.price_spread_pct) if event.price_spread_pct else None,
                    'status': event.status,
                    'authors': event.consensus_metadata.get('authors', []) if event.consensus_metadata else []
                })
            
            return {
                'count': total,
                'consensus_events': results,
                'filters': {
                    'ticker': ticker,
                    'direction': direction,
                    'status': status,
                    'min_strength': min_strength,
                    'days_back': days_back
                },
                'pagination': {
                    'limit': limit,
                    'offset': offset,
                    'has_more': total > (offset + limit)
                }
            }
            
    except Exception as e:
        logger.error(f"Failed to get consensus events: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def manual_consensus_detection(ticker: Optional[str] = None, hours_back: int = 24):
    """Ручная детекция консенсусов для существующих сигналов"""
    try:
        from core.database.models import ParsedSignal
        
        db = get_db_manager()
        cutoff = datetime.utcnow() - timedelta(hours=hours_back)
        
        with db.session() as session:
            query = session.query(ParsedSignal).filter(
                and_(
                    ParsedSignal.signal_type == 'entry',
                    ParsedSignal.timestamp >= cutoff,
                    ParsedSignal.direction.isnot(None)
                )
            )
            
            if ticker:
                query = query.filter(ParsedSignal.ticker == ticker.upper())
            
            signals = query.order_by(ParsedSignal.timestamp.desc()).all()
            
            logger.info(f"Manual consensus detection: checking {len(signals)} signals")
            
            detected = 0
            for signal in signals:
                result = await consensus_detector.check_new_signal(signal.id)
                if result:
                    detected += 1
            
            logger.info(f"Manual consensus detection complete: {detected} consensuses detected")
            
            await broadcast_update({
                'type': 'consensus_detection_complete',
                'detected': detected,
                'checked_signals': len(signals),
                'timestamp': datetime.utcnow().isoformat()
            })
            
    except Exception as e:
        logger.error(f"Manual consensus detection failed: {e}", exc_info=True)


# ===== TELEGRAM SCRAPER ENDPOINTS =====

@app.post("/api/telegram/start")
async def start_telegram_monitoring(
    interval_seconds: int = Query(60, ge=10, le=600, description="Интервал проверки (секунды)")
):
    """Запустить мониторинг Telegram каналов"""
    global telegram_scraper, telegram_monitoring_task
    
    if not telegram_scraper:
        raise HTTPException(status_code=503, detail="Telegram scraper not initialized")
    
    if telegram_scraper.is_running:
        return {"status": "already_running", "message": "Monitoring already active"}
    
    try:
        telegram_monitoring_task = asyncio.create_task(
            telegram_scraper.start_monitoring(interval_seconds=interval_seconds)
        )
        
        return {
            "status": "started",
            "interval_seconds": interval_seconds,
            "message": "Telegram monitoring started"
        }
    except Exception as e:
        logger.error(f"Failed to start Telegram monitoring: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/telegram/stop")
async def stop_telegram_monitoring():
    """Остановить мониторинг Telegram каналов"""
    global telegram_scraper
    
    if not telegram_scraper:
        raise HTTPException(status_code=503, detail="Telegram scraper not initialized")
    
    telegram_scraper.stop_monitoring()
    
    return {
        "status": "stopped",
        "message": "Telegram monitoring stopped"
    }

@app.get("/api/telegram/status")
async def get_telegram_status():
    """Получить статус Telegram scraper"""
    if not telegram_scraper:
        return {
            "initialized": False,
            "message": "Telegram scraper not initialized"
        }
    
    return telegram_scraper.get_status()

@app.post("/api/telegram/fetch-history")
async def fetch_telegram_history(
    channel_id: int = Query(..., description="ID канала"),
    limit: int = Query(100, ge=1, le=1000, description="Количество сообщений")
):
    """Загрузить историю сообщений из канала"""
    if not telegram_scraper:
        raise HTTPException(status_code=503, detail="Telegram scraper not initialized")
    
    try:
        collected = await telegram_scraper.fetch_history(channel_id, limit)
        
        return {
            "status": "success",
            "channel_id": channel_id,
            "messages_collected": collected
        }
    except Exception as e:
        logger.error(f"Failed to fetch history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/telegram/channel/{channel_id}/enable")
async def enable_telegram_channel(channel_id: int):
    """Включить канал"""
    if not telegram_scraper:
        raise HTTPException(status_code=503, detail="Telegram scraper not initialized")
    
    if channel_id in telegram_scraper.channels:
        telegram_scraper.channels[channel_id]['enabled'] = True
        return {"status": "enabled", "channel_id": channel_id}
    else:
        raise HTTPException(status_code=404, detail="Channel not found")

@app.post("/api/telegram/channel/{channel_id}/disable")
async def disable_telegram_channel(channel_id: int):
    """Выключить канал"""
    if not telegram_scraper:
        raise HTTPException(status_code=503, detail="Telegram scraper not initialized")
    
    if channel_id in telegram_scraper.channels:
        telegram_scraper.channels[channel_id]['enabled'] = False
        return {"status": "disabled", "channel_id": channel_id}
    else:
        raise HTTPException(status_code=404, detail="Channel not found")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

# ===== TELEGRAM CHANNEL MANAGEMENT (DB-BASED) =====

@app.get("/api/telegram/channels/{channel_id}/messages")
async def get_channel_messages(
    channel_id: int,
    limit: int = Query(10, ge=1, le=100, description="Количество сообщений"),
    offset: int = Query(0, ge=0, description="Смещение"),
    parsed_only: bool = Query(False, description="Только разобранные")
):
    """Получить последние сообщения из канала (robust)"""
    try:
        db = get_db_manager()

        # Приводим channel_id к строке и int — в зависимости от того, как хранится в БД.
        # Попробуй сначала использовать integer-совместимый фильтр, и если нет, используем str.
        with db.session() as session:
            # Безопасный фильтр: сравним с int и со str (OR)
            try:
                # Сначала предположим, что в БД хранится int/bigint
                query = session.query(RawMessage).filter(RawMessage.channel_id == int(channel_id))
            except Exception:
                # На случай, если поле в БД — текстовое
                query = session.query(RawMessage).filter(RawMessage.channel_id == str(channel_id))

            if parsed_only:
                query = query.filter(RawMessage.is_processed == True)

            query = query.order_by(RawMessage.timestamp.desc())
            query = query.offset(offset).limit(limit)

            messages = query.all()

            result = []
            for msg in messages:
                # безопасность: timestamp / created_at могут быть None
                timestamp_iso = msg.timestamp.isoformat() if getattr(msg, "timestamp", None) else None
                created_iso = msg.created_at.isoformat() if getattr(msg, "created_at", None) else None

                result.append({
                    'id': msg.id,
                    'message_id': msg.message_id,
                    'channel_id': msg.channel_id,
                    'timestamp': timestamp_iso,
                    'text': msg.text,
                    'author': getattr(msg, 'author_username', None) or getattr(msg, 'author', None),
                    'is_processed': msg.is_processed,
                    'created_at': created_iso
                })

            # Общее количество для пагинации
            try:
                total = session.query(RawMessage).filter(RawMessage.channel_id == channel_id).count()
            except Exception:
                # если прямое сравнение падает — пробуем по str
                total = session.query(RawMessage).filter(RawMessage.channel_id == str(channel_id)).count()

            return {
                'messages': result,
                'count': len(result),
                'total': total,
                'limit': limit,
                'offset': offset
            }

    except Exception as e:
        logger.exception(f"Failed to get channel messages for {channel_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/telegram/channels/{channel_id}/signals")
async def get_channel_signals(
    channel_id: int,
    limit: int = Query(10, ge=1, le=100, description="Количество сигналов"),
    offset: int = Query(0, ge=0, description="Смещение")
):
    """Получить сигналы из канала"""
    try:
        db = get_db_manager()
        
        with db.session() as session:
            query = session.query(ParsedSignal).filter(
                ParsedSignal.channel_id == channel_id
            )
            
            query = query.order_by(ParsedSignal.timestamp.desc())
            total = query.count()
            
            signals = query.offset(offset).limit(limit).all()
            
            result = []
            for signal in signals:
                result.append({
                    'id': str(signal.id),
                    'ticker': signal.ticker,
                    'direction': signal.direction,
                    'signal_type': signal.signal_type,
                    'target_price': float(signal.target_price) if signal.target_price else None,
                    'stop_loss': float(signal.stop_loss) if signal.stop_loss else None,
                    'take_profit': float(signal.take_profit) if signal.take_profit else None,
                    'timestamp': signal.timestamp.isoformat() if signal.timestamp else None,
                    'author': signal.author,
                    'confidence_score': float(signal.confidence_score) if signal.confidence_score else None,
                    'original_text': signal.original_text[:100] + '...' if signal.original_text and len(signal.original_text) > 100 else signal.original_text
                })
            
            return {
                'signals': result,
                'count': len(result),
                'total': total,
                'limit': limit,
                'offset': offset
            }
            
    except Exception as e:
        logger.exception(f"Failed to get channel signals for {channel_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
@app.post("/api/telegram/channels/{channel_id}/fetch-latest")
async def fetch_latest_messages(
    channel_id: int,
    limit: int = Query(100, ge=1, le=1000, description="Количество последних сообщений для загрузки")
):
    """Загрузить последние N сообщений из канала, начиная с последнего ID в БД"""
    if not telegram_scraper:
        raise HTTPException(status_code=503, detail="Telegram scraper not initialized")
    
    try:
        if channel_id not in telegram_scraper.channels:
            raise HTTPException(status_code=404, detail=f"Channel {channel_id} not found in scraper")
        
        db = get_db_manager()
        with db.session() as session:
            last_msg = session.query(RawMessage).filter(
                RawMessage.channel_id == channel_id
            ).order_by(RawMessage.message_id.desc()).first()
            
            last_message_id = last_msg.message_id if last_msg else None
        
        logger.info(f"Fetching latest {limit} messages from channel {channel_id}, last_id={last_message_id}")
        
        collected = await telegram_scraper.fetch_history(channel_id, limit)
        
        return {
            "status": "success",
            "channel_id": channel_id,
            "messages_collected": collected,
            "last_message_id_before": last_message_id,
            "limit_requested": limit
        }
    except Exception as e:
        logger.exception(f"Failed to fetch latest messages: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/api/telegram/channels")
async def get_telegram_channels():
    """Получить список всех каналов из БД"""
    try:
        db = get_db_manager()
        channels = db.get_channels(enabled_only=False)
        
        return {
            "channels": channels,
            "count": len(channels)
        }
    except Exception as e:
        logger.error(f"Failed to get channels: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/telegram/channels")
async def add_telegram_channel(
    channel_id: int = Query(..., description="ID канала"),
    name: str = Query(..., description="Название канала"),
    username: str = Query(None, description="Username канала"),
    enabled: bool = Query(True, description="Включить канал")
):
    """Добавить новый канал в БД"""
    try:
        db = get_db_manager()
        
        record_id = db.create_channel(
            channel_id=channel_id,
            name=name,
            username=username,
            is_enabled=enabled
        )
        
        return {
            "status": "success",
            "message": f"Channel {name} added successfully",
            "id": record_id,
            "channel_id": channel_id
        }
    except Exception as e:
        logger.error(f"Failed to add channel: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/telegram/channels/{channel_id}")
async def update_telegram_channel(
    channel_id: int,
    name: Optional[str] = Query(None, description="Новое название"),
    username: Optional[str] = Query(None, description="Новый username"),
    enabled: Optional[bool] = Query(None, description="Включить/выключить")
):
    """Обновить настройки канала в БД"""
    try:
        db = get_db_manager()
        
        updates = {}
        if name is not None:
            updates['name'] = name
        if username is not None:
            updates['username'] = username
        if enabled is not None:
            updates['is_enabled'] = enabled
        
        success = db.update_channel(channel_id, **updates)
        
        if not success:
            raise HTTPException(status_code=404, detail="Channel not found")
        
        return {
            "status": "success",
            "channel_id": channel_id,
            "updated_fields": updates
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update channel: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/telegram/channels/{channel_id}")
async def delete_telegram_channel(channel_id: int):
    """Удалить канал из БД"""
    try:
        db = get_db_manager()
        
        channel = db.get_channel_by_id(channel_id)
        if not channel:
            raise HTTPException(status_code=404, detail="Channel not found")
        
        channel_name = channel['name']
        
        success = db.delete_channel(channel_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Channel not found")
        
        return {
            "status": "success",
            "message": f"Channel {channel_name} deleted",
            "channel_id": channel_id
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete channel: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/telegram/channel/{channel_id}/enable")
async def enable_telegram_channel(channel_id: int):
    """Включить канал"""
    try:
        db = get_db_manager()
        success = db.update_channel(channel_id, is_enabled=True)
        
        if not success:
            raise HTTPException(status_code=404, detail="Channel not found")
        
        return {"status": "enabled", "channel_id": channel_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to enable channel: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/telegram/channel/{channel_id}/disable")
async def disable_telegram_channel(channel_id: int):
    """Выключить канал"""
    try:
        db = get_db_manager()
        success = db.update_channel(channel_id, is_enabled=False)
        
        if not success:
            raise HTTPException(status_code=404, detail="Channel not found")
        
        return {"status": "disabled", "channel_id": channel_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to disable channel: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/telegram/channels/{channel_id}/parse")
async def parse_channel_messages(channel_id: int):
    """Запустить парсинг сообщений конкретного канала"""
    try:
        db = get_db_manager()
        
        channel = db.get_channel_by_id(channel_id)
        if not channel:
            raise HTTPException(status_code=404, detail="Channel not found")
        
        with db.session() as session:
            from core.database.models import RawMessage
            unparsed = session.query(RawMessage).filter(
                RawMessage.channel_id == channel_id,
                RawMessage.is_processed == False
            ).count()
        
        if unparsed == 0:
            return {
                "status": "success",
                "message": "No unparsed messages for this channel",
                "channel_id": channel_id,
                "parsed": 0,
                "failed": 0
            }
        
        from analysis.message_parser import MessageParser
        parser = MessageParser(db)
        
        parsed_count = 0
        failed_count = 0
        
        with db.session() as session:
            messages = session.query(RawMessage).filter(
                RawMessage.channel_id == channel_id,
                RawMessage.is_processed == False
            ).limit(unparsed).all()
            
            for msg in messages:
                try:
                    msg_dict = {
                        'id': msg.id,
                        'channel_id': msg.channel_id,
                        'message_id': msg.message_id,
                        'timestamp': msg.timestamp,
                        'text': msg.text,
                        'author': msg.author_username
                    }
                    
                    result = parser.parse_raw_message(msg_dict)
                    
                    if result.success:
                        signal_data = result.signal_data
                        signal_data['raw_message_id'] = msg.id
                        db.save_signal(signal_data)
                        parsed_count += 1
                        msg.is_processed = True
                        msg.parse_success = True
                    else:
                        failed_count += 1
                        msg.is_processed = True
                        msg.parse_success = False
                        
                except Exception as e:
                    logger.error(f"Error parsing message {msg.id}: {e}")
                    failed_count += 1
                    msg.is_processed = True
                    msg.parse_success = False
            
            session.commit()
        
        return {
            "status": "success",
            "channel_id": channel_id,
            "channel_name": channel['name'],
            "parsed": parsed_count,
            "failed": failed_count
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to parse channel messages: {e}")
        raise HTTPException(status_code=500, detail=str(e))