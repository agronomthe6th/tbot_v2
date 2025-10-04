# api/app.py - ИСПРАВЛЕННАЯ ВЕРСИЯ с фиксами ошибок
from fastapi import FastAPI, BackgroundTasks, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
from typing import Optional, List, Dict
from datetime import datetime, timedelta
import asyncio
import os
from enum import Enum

from analysis.message_parser import MessageParser, MessageParsingService
from core.database import Database
from core.database.models import *
from analysis.signal_matcher import SignalMatcher
from integrations.tinkoff_integration import TinkoffIntegration
from integrations.historical_data_loader import HistoricalDataLoader
from utils.datetime_utils import now_utc, utc_from_days_ago, ensure_timezone_aware, days_between_utc

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
    global signal_matcher, tinkoff_client, background_tasks_running, message_parsing_service, db_manager, historical_data_loader
    
    try:
        logger.info("🚀 Initializing Trader Tracker API...")
        
        # Инициализируем БД
        database_url = os.getenv("DATABASE_URL", "postgresql://user:pass@localhost/trader_tracker")
        db_manager = Database(database_url)
        message_parsing_service = MessageParsingService(
            db_manager=db_manager,
            parser=MessageParser(db_manager)
        )
        logger.info("✅ Database initialized")
        
        # Инициализируем Tinkoff (не критично)
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
        
        # Запуск фоновых задач
        background_tasks_running = True
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
async def get_signals_statistics(
    # Те же фильтры что и в /api/signals
    ticker: Optional[str] = Query(None),
    author: Optional[str] = Query(None),
    trader_id: Optional[int] = Query(None),
    direction: SignalDirection = Query(SignalDirection.ALL),
    status: SignalStatus = Query(SignalStatus.ALL),
    hours_back: Optional[int] = Query(None),
    days_back: Optional[int] = Query(None)
):
    """Статистика по сигналам с фильтрами"""
    try:
        db = get_db_manager()
        from_date = parse_time_range(hours_back, days_back)
        
        stats = db.get_signals_stats(
            ticker=ticker,
            author=author,
            trader_id=trader_id,
            direction=direction if direction != SignalDirection.ALL else None,
            status=status if status != SignalStatus.ALL else None,
            from_date=from_date
        )
        
        return stats
    except Exception as e:
        logger.error(f"Failed to get signals statistics: {e}")
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
    with_stats: bool = Query(True, description="Включить статистику по тикерам")
):
    """Получение списка доступных тикеров"""
    try:
        db = get_db_manager()
        tickers = db.get_available_tickers(with_stats=with_stats)
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
    days: int = Query(30, ge=1, le=365, description="Количество дней")
):
    """Получение свечных данных для тикера"""
    try:
        db = get_db_manager()
        
        # ИСПРАВЛЕНИЕ: используем database для получения свечей, а не historical_data_loader
        # Сначала получаем FIGI инструмента
        instrument = db.get_instrument_by_ticker(ticker.upper())
        if not instrument:
            raise HTTPException(status_code=404, detail=f"Instrument {ticker} not found")
        
        # Вычисляем временной диапазон
        from_time = ensure_timezone_aware(datetime.utcnow() - timedelta(days=days))
        
        # Получаем свечи из базы данных
        candles = db.get_candles(
            figi=instrument['figi'],
            interval='5min',  # По умолчанию 5-минутные свечи
            from_time=from_time
        )
        
        return {
            "ticker": ticker.upper(),
            "period_days": days,
            "count": len(candles),
            "candles": candles
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get candles for {ticker}: {e}")
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

@app.get("/api/messages/unparsed")
async def get_unparsed_messages(
    limit: int = Query(20, ge=1, le=100, description="Количество сообщений")
):
    """Получение списка неразобранных сообщений"""
    try:
        db = get_db_manager()
        messages = db.get_unparsed_messages(limit=limit)
        
        return {
            "count": len(messages),
            "messages": messages
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

