# api/app.py
from fastapi import FastAPI, BackgroundTasks, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
from typing import Optional, List, Dict
from datetime import datetime, timedelta
import asyncio
import os
from analysis.message_parser import MessageParser, MessageParsingService
from core.database import Database
from core.database.models import *
from analysis.signal_matcher import SignalMatcher
from integrations.tinkoff_integration import TinkoffIntegration
from integrations.historical_data_loader import HistoricalDataLoader
from utils.datetime_utils import now_utc, utc_from_days_ago, ensure_timezone_aware, days_between_utc
from sqlalchemy import func

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

def get_db_manager() -> Database:
    """Получение экземпляра Database"""
    if db_manager is None:
        raise HTTPException(status_code=503, detail="Database not initialized")
    return db_manager

@asynccontextmanager
async def lifespan(app: FastAPI):
    global signal_matcher, tinkoff_client, background_tasks_running, message_parsing_service, db_manager, historical_data_loader
    
    try:
        # Инициализируем БД
        database_url = os.getenv("DATABASE_URL", "postgresql://user:pass@localhost/trader_tracker")
        db_manager = Database(database_url)
        message_parsing_service = MessageParsingService(db_manager)
        logger.info("Database initialized successfully")
        
        # Инициализируем Tinkoff (не критично)
        tinkoff_token = os.getenv("TINKOFF_TOKEN")
        if tinkoff_token:
            try:
                tinkoff_client = TinkoffIntegration(tinkoff_token)
                await tinkoff_client.initialize()
                logger.info("Tinkoff client initialized")
            except Exception as e:
                logger.warning(f"Tinkoff integration failed (will work in mock mode): {e}")
                tinkoff_client = None
        
        # Инициализация matcher'а
        signal_matcher = SignalMatcher(db_manager, tinkoff_client)
        
        # Инициализация historical data loader
        if tinkoff_client:
            historical_data_loader = HistoricalDataLoader(db_manager, tinkoff_client)
        
        # Запуск фоновых задач
        background_tasks_running = True
        asyncio.create_task(background_signal_processing())
        
        logger.info("Application initialized successfully")
        yield
        
    except Exception as e:
        logger.error(f"Failed to initialize application: {e}")
        raise
    finally:
        # Очистка при завершении
        background_tasks_running = False
        if tinkoff_client:
            await tinkoff_client.close()
        logger.info("Application shutdown completed")
        
# Создание приложения
app = FastAPI(
    title="Trader Tracker Demo",
    description="API for tracking telegram trading signals performance",
    version="1.0.0",
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
                    logger.info(f"Started tracking {new_tracked} new signals")
                
                # Обновляем активные позиции
                updated = await signal_matcher.update_active_positions()
                if updated > 0:
                    logger.info(f"Updated {updated} active positions")
            
            # Пауза между обработками
            await asyncio.sleep(60)  # Каждую минуту
            
        except Exception as e:
            logger.error(f"Error in background processing: {e}")
            await asyncio.sleep(300)  # При ошибке ждем 5 минут

# ===== API ENDPOINTS =====

@app.get("/")
async def root():
    """Корневой endpoint"""
    return {
        "service": "Trader Tracker Demo",
        "version": "1.0.0",
        "status": "running",
        "timestamp": datetime.now().isoformat()
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
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unavailable")

@app.get("/api/statistics")
async def get_system_statistics():
    """Общая статистика системы"""
    try:
        db = get_db_manager()
        stats = db.get_statistics()
        return stats
    except Exception as e:
        logger.error(f"Failed to get statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ===== TRADER ENDPOINTS =====

@app.get("/api/traders")
async def get_all_traders():
    """Получение списка всех трейдеров"""
    try:
        db = get_db_manager()
        traders = db.get_all_traders()
        return traders
    except Exception as e:
        logger.error(f"Failed to get traders: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/traders/{trader_id}")
async def get_trader_stats(trader_id: int):
    """Получение статистики трейдера"""
    try:
        db = get_db_manager()
        stats = db.get_trader_stats(trader_id)
        
        if not stats:
            raise HTTPException(status_code=404, detail="Trader not found")
        
        return stats
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get trader stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/traders/{trader_id}/signals")
async def get_trader_signals(
    trader_id: int,
    ticker: Optional[str] = Query(None, description="Filter by ticker"),
    limit: int = Query(100, description="Maximum number of signals")
):
    """Получение сигналов трейдера"""
    try:
        db = get_db_manager()
        signals = db.get_signals(trader_id=trader_id, ticker=ticker, limit=limit)
        return signals
    except Exception as e:
        logger.error(f"Failed to get trader signals: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/tickers")
async def get_available_tickers():
    """Получение списка доступных тикеров"""
    try:
        db = get_db_manager()
        
        with db.session() as session:
            tickers = session.query(ParsedSignal.ticker).distinct().all()
            
            # Подсчитываем количество сигналов по каждому тикеру
            ticker_stats = []
            for (ticker,) in tickers:
                signal_count = session.query(ParsedSignal).filter(
                    ParsedSignal.ticker == ticker
                ).count()
                
                ticker_stats.append({
                    'ticker': ticker,
                    'signal_count': signal_count
                })
            
            # Сортируем по количеству сигналов
            ticker_stats.sort(key=lambda x: x['signal_count'], reverse=True)
            
            return ticker_stats
    except Exception as e:
        logger.error(f"Failed to get tickers: {e}")
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
            "timestamp": datetime.now().isoformat()
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
        await broadcast_processing_update({
            'type': 'processing_complete',
            'new_tracked': new_tracked,
            'updated': updated,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Manual signal processing failed: {e}")

@app.get("/api/signals/active")
async def get_active_signals():
    """Получение активных сигналов"""
    try:
        db = get_db_manager()
        active_signals = db.get_active_signals()
        
        return {
            'count': len(active_signals),
            'signals': active_signals
        }
            
    except Exception as e:
        logger.error(f"Failed to get active signals: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/signals/recent")
async def get_recent_signals(
    hours: int = Query(24, description="Hours to look back"),
    limit: int = Query(50, description="Maximum number of signals")
):
    """Получение недавних сигналов"""
    try:
        db = get_db_manager()
        
        since_time = datetime.now() - timedelta(hours=hours)
        signals = db.get_signals(from_date=since_time, limit=limit)
        
        return {
            'period_hours': hours,
            'count': len(signals),
            'signals': signals
        }
            
    except Exception as e:
        logger.error(f"Failed to get recent signals: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ===== WEBSOCKET ENDPOINTS =====

@app.websocket("/ws/updates")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket для получения обновлений в реальном времени"""
    await websocket.accept()
    
    client_id = f"client_{len(websocket_connections)}"
    websocket_connections[client_id] = websocket
    
    try:
        # Отправляем приветствие
        await websocket.send_json({
            'type': 'connection_established',
            'client_id': client_id,
            'timestamp': datetime.now().isoformat()
        })
        
        # Отправляем текущую статистику
        db = get_db_manager()
        stats = db.get_statistics()
        await websocket.send_json({
            'type': 'statistics_update',
            'data': stats,
            'timestamp': datetime.now().isoformat()
        })
        
        # Ожидаем сообщения от клиента
        while True:
            data = await websocket.receive_text()
            # Эхо для поддержания соединения
            await websocket.send_json({
                'type': 'echo',
                'message': data,
                'timestamp': datetime.now().isoformat()
            })
            
    except WebSocketDisconnect:
        logger.info(f"WebSocket client {client_id} disconnected")
    except Exception as e:
        logger.error(f"WebSocket error for {client_id}: {e}")
    finally:
        if client_id in websocket_connections:
            del websocket_connections[client_id]

async def broadcast_processing_update(data: Dict):
    """Рассылка обновлений всем подключенным WebSocket клиентам"""
    if not websocket_connections:
        return
    
    disconnected = []
    for client_id, websocket in websocket_connections.items():
        try:
            await websocket.send_json(data)
        except Exception as e:
            logger.error(f"Failed to send update to {client_id}: {e}")
            disconnected.append(client_id)
    
    # Удаляем отключенных клиентов
    for client_id in disconnected:
        del websocket_connections[client_id]

# ===== MARKET DATA ENDPOINTS =====

@app.get("/api/market/{ticker}/price")
async def get_current_price(ticker: str):
    """Получение текущей цены инструмента"""
    try:
        if not tinkoff_client:
            raise HTTPException(status_code=503, detail="Tinkoff client not configured")
        
        price_data = await tinkoff_client.get_current_price(ticker)
        
        if not price_data:
            raise HTTPException(status_code=404, detail=f"Price not found for {ticker}")
        
        return price_data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get current price: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/market/{ticker}/candles")
async def get_candles(
    ticker: str,
    interval: str = Query("hour", description="Candle interval"),
    days: int = Query(7, description="Number of days")
):
    """Получение свечных данных"""
    try:
        db = get_db_manager()
        
        # Получаем инструмент
        instrument = db.get_instrument_by_ticker(ticker)
        if not instrument:
            raise HTTPException(status_code=404, detail=f"Instrument not found: {ticker}")
        
        # Получаем свечи
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days)
        
        candles = db.get_candles(
            figi=instrument['figi'],
            interval=interval,
            from_time=start_time,
            to_time=end_time,
            limit=days * 24 if interval == 'hour' else days * 1440
        )
        
        return {
            'ticker': ticker,
            'interval': interval,
            'period_days': days,
            'count': len(candles),
            'candles': candles
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get candles: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ===== MESSAGE PARSING ENDPOINTS =====

@app.post("/api/messages/parse")
async def parse_raw_messages(
    background_tasks: BackgroundTasks,
    limit: Optional[int] = Query(None, description="Limit number of messages to process")
):
    """Запуск парсинга raw сообщений в parsed_signals"""
    try:
        if not message_parsing_service:
            raise HTTPException(status_code=503, detail="Message parsing service not initialized")
        
        # Запускаем парсинг в фоне
        background_tasks.add_task(run_message_parsing, limit)
        
        return {
            "status": "parsing_started",
            "message": f"Message parsing started in background{f' (limit: {limit})' if limit else ''}",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to start message parsing: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def run_message_parsing(limit: Optional[int] = None):
    """Фоновая задача для парсинга сообщений"""
    global message_parsing_service
    try:
        logger.info(f"Starting message parsing with limit: {limit}")
        stats = message_parsing_service.parse_all_unprocessed_messages(limit)
        
        logger.info(f"Message parsing completed: {stats}")
        
        # Отправляем обновление через WebSocket
        await broadcast_processing_update({
            'type': 'message_parsing_complete',
            'stats': stats,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Message parsing failed: {e}")

@app.get("/api/messages/parsing-status")
async def get_parsing_status():
    """Получение статуса парсинга сообщений"""
    try:
        db = get_db_manager()
        
        with db.session() as session:
            # Статистика raw сообщений
            total_raw = session.query(RawMessage).count()
            processed_raw = session.query(RawMessage).filter(
                RawMessage.is_processed == True
            ).count()
            unprocessed_raw = total_raw - processed_raw
            
            # Статистика parsed сигналов
            total_parsed = session.query(ParsedSignal).count()
            
            # Последние парсинги
            recent_parsed = session.query(ParsedSignal).order_by(
                ParsedSignal.created_at.desc()
            ).limit(5).all()
            
            recent_signals = [
                {
                    'id': str(signal.id),
                    'ticker': signal.ticker,
                    'direction': signal.direction,
                    'author': signal.author,
                    'confidence': float(signal.confidence_score) if signal.confidence_score else 0.0,
                    'created_at': signal.created_at.isoformat()
                }
                for signal in recent_parsed
            ]
            
            return {
                'raw_messages': {
                    'total': total_raw,
                    'processed': processed_raw,
                    'unprocessed': unprocessed_raw,
                    'processing_rate': round((processed_raw / total_raw * 100), 2) if total_raw > 0 else 0
                },
                'parsed_signals': {
                    'total': total_parsed,
                    'recent': recent_signals
                },
                'timestamp': datetime.now().isoformat()
            }
            
    except Exception as e:
        logger.error(f"Failed to get parsing status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/messages/sample/{message_id}")
async def parse_single_message(message_id: int):
    """Тестовый парсинг одного сообщения"""
    try:
        db = get_db_manager()
        
        with db.session() as session:
            raw_message = session.query(RawMessage).filter(
                RawMessage.id == message_id
            ).first()
            
            if not raw_message:
                raise HTTPException(status_code=404, detail="Message not found")
            
            # Конвертируем в нужный формат
            message_dict = {
                'id': raw_message.id,
                'text': raw_message.text,
                'timestamp': raw_message.timestamp,
                'channel_id': raw_message.channel_id,
                'author': raw_message.author,
                'message_id': raw_message.message_id
            }
            
            # Парсим сообщение
            parser = MessageParser()
            result = parser.parse_raw_message(message_dict)
            
            response = {
                'message_id': message_id,
                'original_text': raw_message.text,
                'parsing_result': {
                    'success': result.success,
                    'confidence': result.confidence,
                    'error': result.error
                }
            }
            
            if result.success and result.signal_data:
                response['extracted_data'] = {
                    'ticker': result.signal_data.get('ticker'),
                    'direction': result.signal_data.get('direction'),
                    'author': result.signal_data.get('author'),
                    'target_price': result.signal_data.get('target_price'),
                    'signal_type': result.signal_data.get('signal_type'),
                    'extracted_details': result.signal_data.get('extracted_data')
                }
            
            return response
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to parse single message: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/messages/unparsed")
async def get_unparsed_messages(
    limit: int = Query(20, description="Maximum number of messages"),
    sample_text_length: int = Query(200, description="Max length of text sample")
):
    """Получение списка неразобранных сообщений"""
    try:
        db = get_db_manager()
        
        messages = db.get_messages(is_processed=False, limit=limit)
        
        # Обрезаем текст для превью
        for msg in messages:
            if len(msg['text']) > sample_text_length:
                msg['text_sample'] = msg['text'][:sample_text_length] + '...'
            else:
                msg['text_sample'] = msg['text']
            msg['text_length'] = len(msg['text'])
        
        return {
            'count': len(messages),
            'messages': messages
        }
            
    except Exception as e:
        logger.error(f"Failed to get unparsed messages: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ===== TINKOFF ENDPOINTS =====

@app.get("/api/tinkoff/test-connection")
async def test_tinkoff_connection():
    """Тестирование подключения к Tinkoff API"""
    try:
        if not tinkoff_client:
            raise HTTPException(status_code=503, detail="Tinkoff client not initialized")
        
        result = await tinkoff_client.test_connection()
        
        if result["success"]:
            return {
                **result,
                "message": "Tinkoff API connection successful"
            }
        else:
            raise HTTPException(status_code=503, detail=f"Tinkoff API connection failed: {result['error']}")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Tinkoff connection test failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/tinkoff/search/{ticker}")
async def search_instrument(ticker: str):
    """Поиск инструмента по тикеру"""
    try:
        if not tinkoff_client:
            raise HTTPException(status_code=503, detail="Tinkoff client not initialized")
        
        instrument = await tinkoff_client.find_instrument_by_ticker(ticker)
        
        if instrument:
            return {
                "found": True,
                "instrument": instrument,
                "timestamp": now_utc().isoformat()  # ✅ ИСПРАВЛЕНО
            }
        else:
            raise HTTPException(status_code=404, detail=f"Instrument {ticker} not found")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Instrument search failed for {ticker}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
# ===== HISTORICAL DATA ENDPOINTS =====

@app.post("/api/data/sync-instruments")
async def sync_instruments_to_database():
    """Синхронизация инструментов в базу данных"""
    try:
        if not historical_data_loader:
            raise HTTPException(status_code=503, detail="Historical data loader not initialized")
        
        synced_count = await historical_data_loader.sync_instruments_to_database()
        
        return {
            "success": True,
            "synced_instruments": synced_count,
            "message": f"Synced {synced_count} instruments to database",
            "timestamp": now_utc().isoformat()  # ✅ ИСПРАВЛЕНО
        }
        
    except Exception as e:
        logger.error(f"Instruments sync failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/data/load-historical/{ticker}")
async def load_historical_candles(
    ticker: str,
    interval: str = Query("5min", description="Candle interval"),
    days_back: int = Query(30, description="Days back to load"),
    force_reload: bool = Query(False, description="Force reload existing data")
):
    """Загрузка исторических свечей для тикера"""
    try:
        if not historical_data_loader:
            raise HTTPException(status_code=503, detail="Historical data loader not initialized")
        
        if interval not in ["1min", "5min", "hour", "day"]:
            raise HTTPException(status_code=400, detail="Invalid interval. Use: 1min, 5min, hour, day")
        
        if days_back < 1 or days_back > 365:
            raise HTTPException(status_code=400, detail="days_back must be between 1 and 365")
        
        result = await historical_data_loader.load_historical_candles(
            ticker=ticker,
            interval=interval,
            days_back=days_back,
            force_reload=force_reload
        )
        
        if result["success"]:
            return result
        else:
            raise HTTPException(status_code=400, detail=result["error"])
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Historical data loading failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/data/status")
async def get_data_status():
    """Получение статуса исторических данных"""
    try:
        if not historical_data_loader:
            raise HTTPException(status_code=503, detail="Historical data loader not initialized")
        
        status = await historical_data_loader.get_data_status()
        
        if "error" in status:
            raise HTTPException(status_code=500, detail=status["error"])
        
        return status
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Data status request failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ===== UTILITY ENDPOINTS =====

@app.get("/api/debug/raw_messages")
async def get_raw_messages_sample(limit: int = Query(10, description="Number of messages")):
    """Debug endpoint для просмотра сырых сообщений"""
    try:
        db = get_db_manager()
        messages = db.get_messages(limit=limit)
        
        return [
            {
                'id': msg['id'],
                'timestamp': msg['timestamp'].isoformat() if isinstance(msg['timestamp'], datetime) else msg['timestamp'],
                'channel_id': msg['channel_id'],
                'author': msg['author'],
                'text': msg['text'][:200] + '...' if len(msg['text']) > 200 else msg['text'],
                'is_processed': msg['is_processed']
            }
            for msg in messages
        ]
            
    except Exception as e:
        logger.error(f"Failed to get raw messages: {e}")
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

@app.get("/api/candles/{ticker}")
async def get_candles_data(
    ticker: str,
    days: int = Query(30, description="Number of days back (1-365)"),
    # ✅ УБРАЛИ limit параметр полностью! Возвращаем ВСЕ свечи
):
    """Получение 5-минутных свечных данных для тикера - БЕЗ ЛИМИТОВ!"""
    try:
        # Валидация параметров
        if days < 1 or days > 365:
            raise HTTPException(
                status_code=400, 
                detail="Days must be between 1 and 365"
            )
        
        # 🔍 ДИАГНОСТИКА: Получаем инструмент
        db = get_db_manager()
        instrument = db.get_instrument_by_ticker(ticker.upper())
        
        if not instrument:
            raise HTTPException(
                status_code=404,
                detail=f"Instrument {ticker} not found. Available instruments: {[t['ticker'] for t in db.get_available_tickers()]}"
            )
        
        logger.info(f"📊 Found instrument: {instrument['figi']} for {ticker}")
        
        # Получаем свечи - БЕЗ ЛИМИТА!
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days)
        
        # ✅ УБРАЛИ limit параметр - получаем ВСЕ доступные свечи!
        candles = db.get_candles(
            figi=instrument['figi'],
            interval='5min',
            from_time=start_time,
            to_time=end_time
            # limit=НЕТ! Убрали лимит
        )
        
        logger.info(f"📈 Found {len(candles)} candles in database for {ticker}")
        
        return {
            'ticker': ticker,
            'interval': '5min',
            'period_days': days,
            'count': len(candles),
            'candles': candles,
            'instrument': {
                'figi': instrument['figi'],
                'name': instrument['name'],
                'currency': instrument['currency']
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get candles: {e}")
        raise HTTPException(status_code=500, detail=str(e))
# ===== ЭНДПОИНТЫ ДЛЯ СИГНАЛОВ =====

@app.get("/api/signals/trader/{trader}")
async def get_signals_by_trader(
    trader: str,
    days: int = Query(30, description="Days back to search"),
    limit: int = Query(100, description="Maximum signals to return")
):
    """Получение сигналов конкретного трейдера"""
    try:
        if days < 1 or days > 365:
            raise HTTPException(status_code=400, detail="Days must be between 1 and 365")
        
        db = get_db_manager()
        from_date = datetime.now() - timedelta(days=days)
        
        # Получаем сигналы по автору (trader name)
        signals = db.get_signals(
            trader_id=None,  # По ID не фильтруем
            from_date=from_date,
            limit=limit * 2  # Берем больше для фильтрации
        )
        
        # Фильтруем по имени трейдера
        trader_signals = [
            s for s in signals 
            if s.get('author', '').lower() == trader.lower()
        ][:limit]
        
        return {
            "trader": trader,
            "period_days": days,
            "count": len(trader_signals),
            "signals": [
                {
                    "id": signal["id"],
                    "timestamp": signal["timestamp"].isoformat() if hasattr(signal["timestamp"], 'isoformat') else signal["timestamp"],
                    "ticker": signal["ticker"],
                    "direction": signal["direction"],  # long/short (покупка/продажа)
                    "signal_type": signal.get("signal_type"),
                    "target_price": signal.get("target_price"),
                    "confidence_score": signal.get("confidence_score"),
                    "original_text": signal.get("original_text", "")[:200] + "..." if len(signal.get("original_text", "")) > 200 else signal.get("original_text", "")
                }
                for signal in trader_signals
            ]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting signals for trader {trader}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/signals/ticker/{ticker}")
async def get_signals_by_ticker(
    ticker: str,
    days: int = Query(30, description="Days back"),
    limit: int = Query(50, description="Max signals")
):
    """Получение всех сигналов для конкретного тикера"""
    try:
        if days < 1 or days > 365:
            raise HTTPException(status_code=400, detail="Days must be between 1 and 365")
            
        db = get_db_manager()
        from_date = datetime.now() - timedelta(days=days)
        
        signals = db.get_signals(
            ticker=ticker.upper(),
            from_date=from_date,
            limit=limit
        )
        
        return {
            "ticker": ticker.upper(),
            "period_days": days,
            "count": len(signals),
            "signals": [
                {
                    "id": signal["id"],
                    "timestamp": signal["timestamp"].isoformat() if hasattr(signal["timestamp"], 'isoformat') else signal["timestamp"],
                    "trader": signal.get("author"),
                    "direction": signal["direction"],  # long/short (покупка/продажа)
                    "signal_type": signal.get("signal_type"),
                    "target_price": signal.get("target_price"),
                    "confidence_score": signal.get("confidence_score"),
                    "original_text": signal.get("original_text", "")[:200] + "..." if len(signal.get("original_text", "")) > 200 else signal.get("original_text", "")
                }
                for signal in signals
            ]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting signals for ticker {ticker}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/signals/trader-ticker")
async def get_signals_by_trader_and_ticker(
    trader: str = Query(..., description="Trader name"),
    ticker: str = Query(..., description="Ticker symbol"),
    days: int = Query(30, description="Days back"),
    limit: int = Query(50, description="Max signals")
):
    """Получение сигналов конкретного трейдера по конкретному тикеру"""
    try:
        if days < 1 or days > 365:
            raise HTTPException(status_code=400, detail="Days must be between 1 and 365")
            
        db = get_db_manager()
        from_date = datetime.now() - timedelta(days=days)
        
        # Получаем сигналы по тикеру
        signals = db.get_signals(
            ticker=ticker.upper(),
            from_date=from_date,
            limit=limit * 3  # Берем больше для фильтрации по трейдеру
        )
        
        # Фильтруем по трейдеру
        filtered_signals = [
            s for s in signals 
            if s.get('author', '').lower() == trader.lower()
        ][:limit]
        
        return {
            "trader": trader,
            "ticker": ticker.upper(),
            "period_days": days,
            "count": len(filtered_signals),
            "signals": [
                {
                    "id": signal["id"],
                    "timestamp": signal["timestamp"].isoformat() if hasattr(signal["timestamp"], 'isoformat') else signal["timestamp"],
                    "direction": signal["direction"],  # long/short (покупка/продажа)
                    "signal_type": signal.get("signal_type"),
                    "target_price": signal.get("target_price"),
                    "confidence_score": signal.get("confidence_score"),
                    "original_text": signal.get("original_text", "")[:200] + "..." if len(signal.get("original_text", "")) > 200 else signal.get("original_text", "")
                }
                for signal in filtered_signals
            ]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting signals for trader {trader} and ticker {ticker}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/debug/database-content")
async def debug_database_content():
    """Диагностика содержимого базы данных"""
    try:
        db = get_db_manager()
        
        with db.session() as session:
            from core.database.models import Instrument, Candle
            from sqlalchemy import func, desc
            
            # 1. Проверяем инструменты
            instruments = session.query(Instrument).all()
            instruments_info = [
                {
                    "figi": inst.figi,
                    "ticker": inst.ticker, 
                    "name": inst.name,
                    "type": inst.type
                }
                for inst in instruments[:10]  # Первые 10
            ]
            
            # 2. Проверяем свечи - общая статистика
            candles_stats = session.query(
                Candle.instrument_id,
                Candle.interval,
                func.count(Candle.id).label('count'),
                func.min(Candle.time).label('first_time'),
                func.max(Candle.time).label('last_time')
            ).group_by(
                Candle.instrument_id, Candle.interval
            ).all()
            
            candles_info = [
                {
                    "instrument_id": stat.instrument_id,
                    "interval": stat.interval,
                    "count": stat.count,
                    "first_time": stat.first_time.isoformat() if stat.first_time else None,
                    "last_time": stat.last_time.isoformat() if stat.last_time else None
                }
                for stat in candles_stats
            ]
            
            # 3. Специально для SBER
            sber_instrument = session.query(Instrument).filter(
                Instrument.ticker == 'SBER'
            ).first()
            
            sber_info = None
            sber_candles_sample = []
            
            if sber_instrument:
                sber_info = {
                    "figi": sber_instrument.figi,
                    "ticker": sber_instrument.ticker,
                    "name": sber_instrument.name
                }
                
                # Получаем образцы свечей для SBER
                sber_candles = session.query(Candle).filter(
                    Candle.instrument_id == sber_instrument.figi
                ).order_by(desc(Candle.time)).limit(5).all()
                
                sber_candles_sample = [
                    {
                        "time": candle.time.isoformat(),
                        "interval": candle.interval,
                        "open": float(candle.open),
                        "close": float(candle.close),
                        "volume": candle.volume
                    }
                    for candle in sber_candles
                ]
            
            # 4. Проверяем все доступные интервалы
            intervals = session.query(Candle.interval).distinct().all()
            available_intervals = [interval[0] for interval in intervals]
            
            return {
                "total_instruments": len(instruments),
                "sample_instruments": instruments_info,
                "candles_by_instrument": candles_info,
                "available_intervals": available_intervals,
                "sber_instrument": sber_info,
                "sber_candles_sample": sber_candles_sample,
                "total_candles": session.query(Candle).count()
            }
            
    except Exception as e:
        logger.error(f"❌ Error in debug endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/data/coverage/{ticker}")
async def check_data_coverage(
    ticker: str,
    days: int = Query(365, description="Days to check coverage for"),
    interval: str = Query("5min", description="Candle interval")
):
    """Проверка покрытия данных для тикера"""
    try:
        if not historical_data_loader:
            raise HTTPException(status_code=503, detail="Historical data loader not initialized")
        
        db = get_db_manager()
        
        # Получаем инструмент
        instrument = db.get_instrument_by_ticker(ticker)
        if not instrument:
            return {
                "ticker": ticker,
                "has_instrument": False,
                "coverage": {
                    "start_date": None,
                    "end_date": None,
                    "total_days": 0,
                    "missing_days": days,
                    "coverage_percentage": 0.0
                },
                "recommendations": ["Load instrument data first"]
            }
        
        # ✅ КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: Преобразуем interval в строку
        interval_str = str(interval)
        logger.info(f"🔍 Checking coverage for {ticker}, interval: {interval_str}")
        
        # Используем timezone-aware даты
        end_date = now_utc()
        start_date = utc_from_days_ago(days)
        
        existing_candles = db.get_candles(
            figi=instrument['figi'],
            interval=interval_str,  # ✅ ИСПРАВЛЕНО: передаем строку, а не Query объект
            from_time=start_date,
            to_time=end_date,
            limit=10000
        )
        
        # Остальная логика остается без изменений...
        if not existing_candles:
            coverage_info = {
                "start_date": None,
                "end_date": None,
                "total_days": 0,
                "missing_days": days,
                "coverage_percentage": 0.0
            }
            recommendations = [f"Load {days} days of historical data for {ticker}"]
        else:
            candle_dates = [candle['time'].date() for candle in existing_candles]
            actual_start = min(candle_dates)
            actual_end = max(candle_dates)
            
            total_possible_days = (end_date.date() - start_date.date()).days
            actual_days = len(set(candle_dates))
            missing_days = total_possible_days - actual_days
            coverage_percentage = (actual_days / total_possible_days) * 100
            
            coverage_info = {
                "start_date": actual_start.isoformat(),
                "end_date": actual_end.isoformat(),
                "total_days": actual_days,
                "missing_days": missing_days,
                "coverage_percentage": round(coverage_percentage, 2)
            }
            
            recommendations = []
            if coverage_percentage < 80:
                recommendations.append(f"Load missing data - only {coverage_percentage:.1f}% coverage")
            if missing_days > 7:
                recommendations.append(f"Missing {missing_days} days of data")
        
        return {
            "ticker": ticker,
            "has_instrument": True,
            "figi": instrument['figi'],
            "coverage": coverage_info,
            "recommendations": recommendations,
            "can_auto_load": True
        }
        
    except Exception as e:
        logger.error(f"Error checking data coverage for {ticker}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/data/smart-load/{ticker}")
async def smart_load_data(
    ticker: str,
    interval: str = Query("5min", description="Interval for candles"),
    max_days: int = Query(365, description="Maximum days to load"),
    ensure_signals_coverage: bool = Query(True, description="Ensure coverage for all signals period")
):
    """Умная загрузка данных с учетом периода сигналов"""
    try:
        if not historical_data_loader:
            raise HTTPException(status_code=503, detail="Historical data loader not initialized")
        
        db = get_db_manager()
        
        # Определяем нужный период
        required_days = max_days
        
        if ensure_signals_coverage:
            # Находим самый старый сигнал для этого тикера
            oldest_signal = db.get_signals(
                ticker=ticker,
                limit=1,
                from_date=utc_from_days_ago(max_days * 2)
            )
            
            if oldest_signal:
                oldest_date = oldest_signal[0]['timestamp']
                oldest_date = ensure_timezone_aware(oldest_date)
                
                days_to_cover = days_between_utc(oldest_date, now_utc()) + 7
                required_days = min(max(days_to_cover, 30), max_days)
                
                logger.info(f"📊 Oldest signal for {ticker}: {oldest_date.date()}, will load {required_days} days")
        
        interval_str = str(interval)
        
        # Загружаем данные
        result = await historical_data_loader.load_historical_candles(
            ticker=ticker,
            interval=interval_str,
            days_back=required_days,
            force_reload=False
        )
        
        # ✅ ИСПРАВЛЕНО: Передаем правильные параметры в coverage проверку
        coverage_response = await check_data_coverage(ticker, required_days, interval_str)
        
        return {
            "ticker": ticker,
            "load_result": result,
            "coverage_after_load": coverage_response.get("coverage"),
            "days_loaded": required_days,
            "recommendations": coverage_response.get("recommendations")
        }
        
    except Exception as e:
        logger.error(f"Error in smart load for {ticker}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ===== ИСПРАВЛЕНИЯ В ДРУГИХ МЕСТАХ =====

# В функции get_candles тоже нужно исправить:
@app.get("/api/candles/{ticker}")
async def get_candles(
    ticker: str,
    days: int = Query(30, description="Days of data to fetch"),
):
    """Получение свечей для тикера - ТОЛЬКО ЧТЕНИЕ, без авто-загрузки"""
    try:
        db = get_db_manager()
        
        # Получаем инструмент
        instrument = db.get_instrument_by_ticker(ticker)
        if not instrument:
            raise HTTPException(
                status_code=404,
                detail=f"Instrument {ticker} not found in database"
            )
        
        # Используем timezone-aware даты
        end_time = now_utc()
        start_time = utc_from_days_ago(days)
        
        # ТОЛЬКО читаем из базы данных, БЕЗ авто-загрузки
        candles = db.get_candles(
            figi=instrument['figi'],
            interval="5min",
            from_time=start_time,
            to_time=end_time,
        )
        
        logger.info(f"📈 Found {len(candles)} candles in database for {ticker}")
        
        if not candles:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": f"No candle data available for {ticker}",
                    "suggestion": "Use POST /api/data/smart-load/{ticker} to load historical data first",
                    "ticker": ticker,
                    "period_requested": {
                        "start": start_time.isoformat(),
                        "end": end_time.isoformat(),
                        "days": days
                    }
                }
            )
        
        return {
            "ticker": ticker,
            "candles": candles,
            "count": len(candles),
            "period": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat(),
                "days": days
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching candles for {ticker}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
@app.post("/api/data/bulk-smart-load")
async def bulk_smart_load():
    """Массовая умная загрузка для всех тикеров с сигналами"""
    try:
        if not historical_data_loader:
            raise HTTPException(status_code=503, detail="Historical data loader not initialized")
        
        db = get_db_manager()
        
        # Получаем все тикеры с сигналами
        tickers_response = await get_available_tickers()
        tickers_with_signals = [t['ticker'] for t in tickers_response if t.get('signal_count', 0) > 0]
        
        logger.info(f"🚀 Starting bulk smart load for {len(tickers_with_signals)} tickers")
        
        results = {
            "processed": [],
            "failed": [],
            "total_tickers": len(tickers_with_signals)
        }
        
        # Ограничиваем concurrent загрузки
        semaphore = asyncio.Semaphore(2)
        
        async def load_single_ticker(ticker):
            async with semaphore:
                try:
                    result = await smart_load_data(ticker, max_days=365)
                    results["processed"].append(result)
                    logger.info(f"✅ Completed smart load for {ticker}")
                except Exception as e:
                    error_info = {"ticker": ticker, "error": str(e)}
                    results["failed"].append(error_info)
                    logger.error(f"❌ Failed smart load for {ticker}: {e}")
                
                # Пауза между загрузками
                await asyncio.sleep(1)
        
        # Запускаем параллельную загрузку
        tasks = [load_single_ticker(ticker) for ticker in tickers_with_signals]
        await asyncio.gather(*tasks, return_exceptions=True)
        
        logger.info(f"📊 Bulk smart load completed: {len(results['processed'])}/{results['total_tickers']} successful")
        
        return results
        
    except Exception as e:
        logger.error(f"Error in bulk smart load: {e}")
        raise HTTPException(status_code=500, detail=str(e))