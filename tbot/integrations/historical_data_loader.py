# integrations/historical_data_loader.py
import logging
import json
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from pathlib import Path
from core.database.database import Instrument,Candle
from utils.datetime_utils import now_utc, utc_from_days_ago, utc_from_minutes_ago, ensure_timezone_aware, days_between_utc
from .tinkoff_integration import TinkoffIntegration
from core.database import Database
from sqlalchemy import func

logger = logging.getLogger(__name__)

class HistoricalDataLoader:
    """Загрузчик исторических данных из Tinkoff API в базу"""
    
    def __init__(self, db: Database, tinkoff_client: TinkoffIntegration):
        self.db = db
        self.tinkoff = tinkoff_client
        self.mapping_file = Path("instruments_mapping.json")
        
    async def load_instruments_mapping(self) -> Dict:
        """Загрузка маппинга инструментов"""
        try:
            if self.mapping_file.exists():
                with open(self.mapping_file, 'r', encoding='utf-8') as f:
                    mapping = json.load(f)
                    logger.info(f"📋 Loaded {len(mapping['instruments'])} instruments from mapping")
                    return mapping
            else:
                logger.warning("⚠️ Instruments mapping file not found, creating from API...")
                return await self.create_instruments_mapping()
                
        except Exception as e:
            logger.error(f"❌ Error loading instruments mapping: {e}")
            return {"instruments": {}}
    
    async def create_instruments_mapping(self) -> Dict:
        """Создание маппинга инструментов через API"""
        popular_instruments = await self.tinkoff.get_popular_instruments()
        
        mapping = {
            "description": "Auto-generated mapping from Tinkoff API",
            "last_updated": datetime.now().isoformat(),
            "instruments": {}
        }
        
        for instrument in popular_instruments:
            mapping["instruments"][instrument["ticker"]] = {
                "figi": instrument["figi"],
                "name": instrument["name"],
                "type": instrument["type"],
                "currency": instrument["currency"]
            }
        
        # Сохраняем маппинг
        try:
            with open(self.mapping_file, 'w', encoding='utf-8') as f:
                json.dump(mapping, f, indent=2, ensure_ascii=False)
            logger.info(f"💾 Saved instruments mapping to {self.mapping_file}")
        except Exception as e:
            logger.error(f"❌ Error saving mapping: {e}")
        
        return mapping
    
    async def sync_instruments_to_database(self) -> int:
        """Синхронизация инструментов в базу данных"""
        try:
            mapping = await self.load_instruments_mapping()
            synced_count = 0
            
            for ticker, info in mapping.get("instruments", {}).items():
                try:
                    # Используем готовый метод Database
                    figi = self.db.save_instrument(
                        figi=info["figi"],
                        ticker=ticker,
                        name=info["name"],
                        instrument_type=info.get("type", "share")
                    )
                    
                    if figi:
                        synced_count += 1
                        logger.info(f"✅ Synced instrument: {ticker} ({info['name']})")
                    else:
                        logger.warning(f"⚠️ Failed to sync instrument: {ticker}")
                        
                except Exception as e:
                    logger.error(f"❌ Error syncing {ticker}: {e}")
            
            logger.info(f"📊 Synced {synced_count} instruments to database")
            return synced_count
            
        except Exception as e:
            logger.error(f"❌ Error syncing instruments: {e}")
            return 0

    async def load_historical_candles(
        self,
        ticker: str,
        interval: str = "5min", 
        days_back: int = 30,
        force_reload: bool = False
    ) -> Dict:
        """
        Загрузка исторических свечей для конкретного тикера
        
        Args:
            ticker: Тикер инструмента (например, "SBER")
            interval: Интервал свечей ("1min", "5min", "hour", "day")  
            days_back: Количество дней назад для загрузки
            force_reload: Принудительная перезагрузка (очистить существующие)
            
        Returns:
            Dict с результатами загрузки
        """
        try:
            # Получаем информацию об инструменте через готовый метод
            instrument = self.db.get_instrument_by_ticker(ticker)
            if not instrument:
                # Пытаемся найти через API и добавить в базу
                api_instrument = await self.tinkoff.find_instrument_by_ticker(ticker)
                if not api_instrument:
                    return {
                        "success": False,
                        "error": f"Instrument {ticker} not found",
                        "loaded_candles": 0
                    }
                
                # Добавляем инструмент в базу
                self.db.save_instrument(
                    figi=api_instrument["figi"],
                    ticker=ticker,
                    name=api_instrument["name"],
                    instrument_type=api_instrument.get("type", "share")
                )
                
                instrument = {"figi": api_instrument["figi"]}
            
            figi = instrument["figi"]
            
            # Проверяем существующие данные через готовый метод
            if not force_reload:
                existing_candles = self.db.get_candles(
                    figi=figi,
                    interval=interval,
                    limit=10
                )
                
                if existing_candles:
                    logger.info(f"📊 Found {len(existing_candles)} existing candles for {ticker}")
                    
                    # ✅ ИСПРАВЛЕНО: Определяем с какого времени загружать
                    # Все даты из БД уже timezone-aware (UTC)
                    last_candle_time = max(candle['time'] for candle in existing_candles)
                    last_candle_time = ensure_timezone_aware(last_candle_time)  # На всякий случай
                    
                    from_time = last_candle_time + timedelta(minutes=1)
                    to_time = now_utc()  # ✅ ИСПРАВЛЕНО: timezone-aware
                    
                    # ✅ ИСПРАВЛЕНО: Безопасное сравнение timezone-aware дат
                    if from_time >= to_time:
                        return {
                            "success": True,
                            "message": "Data is up to date",
                            "loaded_candles": 0,
                            "existing_candles": len(existing_candles)
                        }
                else:
                    # Загружаем полный период
                    from_time = utc_from_days_ago(days_back)  # ✅ ИСПРАВЛЕНО
                    to_time = now_utc()  # ✅ ИСПРАВЛЕНО
            else:
                # Принудительная загрузка - загружаем весь период
                from_time = utc_from_days_ago(days_back)  # ✅ ИСПРАВЛЕНО
                to_time = now_utc()  # ✅ ИСПРАВЛЕНО
            
            # Загружаем свечи через API
            logger.info(f"📈 Loading {interval} candles for {ticker} from {from_time.date()} to {to_time.date()}")
            
            candles_data = await self.tinkoff.get_candles(
                figi=figi,
                interval=interval,
                from_time=from_time,
                to_time=to_time
            )
            
            if not candles_data:
                return {
                    "success": False,
                    "error": "No candles received from API",
                    "loaded_candles": 0
                }
            
            # Сохраняем свечи в базу через готовый метод
            result = self.db.save_candles(candles_data, figi=figi, interval=interval)
            
            if result.get('saved', 0) > 0:
                logger.info(f"✅ Successfully loaded {len(candles_data)} candles for {ticker}")
                return {
                    "success": True,
                    "ticker": ticker,
                    "interval": interval,
                    "loaded_candles": len(candles_data),
                    "period": f"{from_time.date()} - {to_time.date()}"
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to save candles to database",
                    "loaded_candles": 0
                }
                
        except Exception as e:
            logger.error(f"❌ Error loading historical candles for {ticker}: {e}")
            return {
                "success": False,
                "error": str(e),
                "loaded_candles": 0
            }

    async def bulk_load_popular_instruments(
        self,
        interval: str = "5min",
        days_back: int = 30,
        max_concurrent: int = 3
    ) -> Dict:
        """
        Массовая загрузка популярных инструментов
        
        Args:
            interval: Интервал свечей
            days_back: Дней назад
            max_concurrent: Максимум одновременных загрузок
        """
        try:
            mapping = await self.load_instruments_mapping()
            popular_tickers = list(mapping.get("demo_signals", {}).get("most_traded", []))
            
            if not popular_tickers:
                popular_tickers = ["SBER", "GAZP", "LKOH", "YNDX", "VTBR"]
            
            logger.info(f"🚀 Starting bulk load for {len(popular_tickers)} instruments")
            
            results = {
                "completed": [],
                "failed": [],
                "total_candles": 0,
                "total_requested": len(popular_tickers),
                "start_time": now_utc().isoformat(),  # ✅ ИСПРАВЛЕНО
            }
            
            # Создаем семафор для ограничения concurrent запросов
            semaphore = asyncio.Semaphore(max_concurrent)
            
            async def load_single_ticker(ticker):
                async with semaphore:
                    result = await self.load_historical_candles(
                        ticker=ticker,
                        interval=interval,
                        days_back=days_back
                    )
                    
                    if result["success"]:
                        results["completed"].append(result)
                        results["total_candles"] += result["loaded_candles"]
                    else:
                        results["failed"].append({
                            "ticker": ticker,
                            "error": result["error"]
                        })
                    
                    # Пауза между загрузками
                    await asyncio.sleep(1)
            
            # Запускаем параллельную загрузку
            tasks = [load_single_ticker(ticker) for ticker in popular_tickers]
            await asyncio.gather(*tasks, return_exceptions=True)
            
            results["end_time"] = now_utc().isoformat()  # ✅ ИСПРАВЛЕНО
            results["duration_minutes"] = (
                datetime.fromisoformat(results["end_time"].replace('Z', '+00:00')) - 
                datetime.fromisoformat(results["start_time"].replace('Z', '+00:00'))
            ).total_seconds() / 60
            
            logger.info(f"📊 Bulk load completed: {len(results['completed'])}/{len(popular_tickers)} successful")
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Error in bulk load: {e}")
            return {
                "error": str(e),
                "completed": [],
                "failed": [],
                "total_candles": 0,
                "end_time": now_utc().isoformat()  # ✅ ИСПРАВЛЕНО
            }
    
    async def get_data_status(self) -> Dict:
        """
        Получение статуса исторических данных
        
        Returns:
            Dict с информацией о состоянии данных
        """
        try:
            with self.db.get_session() as session:
                # Основная статистика
                total_instruments = session.query(Instrument).count()
                total_candles = session.query(Candle).count()
                
                # Информация по инструментам
                instruments = session.query(Instrument).limit(10).all()
                instruments_info = []
                
                for instrument in instruments:
                    candles_count = session.query(Candle).filter(
                        Candle.figi == instrument.figi
                    ).count()
                    
                    # ✅ ИСПРАВЛЕНО: Получаем последнюю свечу с timezone-aware сравнением
                    latest_candle = session.query(Candle).filter(
                        Candle.figi == instrument.figi
                    ).order_by(Candle.time.desc()).first()
                    
                    latest_time = None
                    if latest_candle:
                        latest_time = ensure_timezone_aware(latest_candle.time).isoformat()
                    
                    instruments_info.append({
                        "ticker": instrument.ticker,
                        "figi": instrument.figi,
                        "name": instrument.name,
                        "candles_count": candles_count,
                        "latest_candle": latest_time
                    })
                
                # Информация по свечам
                candles_info = []
                candles_by_figi = session.query(
                    Candle.figi, 
                    func.count(Candle.id).label('count')
                ).group_by(Candle.figi).limit(10).all()
                
                for figi, count in candles_by_figi:
                    instrument = session.query(Instrument).filter(
                        Instrument.figi == figi
                    ).first()
                    
                    candles_info.append({
                        "figi": figi,
                        "ticker": instrument.ticker if instrument else "Unknown",
                        "candles_count": count
                    })
                
                # Проверяем все доступные интервалы
                intervals = session.query(Candle.interval).distinct().all()
                available_intervals = [interval[0] for interval in intervals]
                
                return {
                    "total_instruments": total_instruments,
                    "total_candles": total_candles,
                    "sample_instruments": instruments_info,
                    "candles_by_instrument": candles_info,
                    "available_intervals": available_intervals,
                    "status_timestamp": now_utc().isoformat(),  # ✅ ИСПРАВЛЕНО
                    "status": "operational"
                }
                
        except Exception as e:
            logger.error(f"❌ Error getting data status: {e}")
            return {
                "error": str(e),
                "status": "error",
                "status_timestamp": now_utc().isoformat()  # ✅ ИСПРАВЛЕНО
            }
    
    def _get_instruments_detailed_stats(self) -> List[Dict]:
        """Получить детальную статистику по инструментам"""
        instruments_info = []
        
        try:
            with self.db.session() as session:
                from core.database import Instrument, Candle
                from sqlalchemy import func
                
                # Статистика по инструментам
                instruments_stats = session.query(
                    Instrument.ticker,
                    Instrument.name,
                    func.count(Candle.id).label('candles_count'),
                    func.max(Candle.time).label('last_candle'),
                    func.min(Candle.time).label('first_candle')
                ).outerjoin(
                    Candle, Instrument.figi == Candle.instrument_id
                ).group_by(
                    Instrument.ticker, Instrument.name
                ).all()
                
                for stat in instruments_stats:
                    instruments_info.append({
                        "ticker": stat.ticker,
                        "name": stat.name,
                        "candles_count": stat.candles_count,
                        "last_candle": stat.last_candle.isoformat() if stat.last_candle else None,
                        "first_candle": stat.first_candle.isoformat() if stat.first_candle else None,
                        "has_data": stat.candles_count > 0
                    })
        except Exception as e:
            logger.error(f"❌ Error getting instruments stats: {e}")
        
        return instruments_info
    
    async def cleanup_old_data(self, days_to_keep: int = 90) -> Dict:
        """Очистка старых данных"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            
            with self.db.session() as session:
                from core.database import Candle
                
                # Считаем сколько записей будет удалено
                old_records = session.query(Candle).filter(
                    Candle.time < cutoff_date
                ).count()
                
                # Удаляем старые записи
                deleted = session.query(Candle).filter(
                    Candle.time < cutoff_date
                ).delete()
                
                logger.info(f"🗑️ Cleaned up {deleted} old candle records (older than {cutoff_date.date()})")
                
                return {
                    "success": True,
                    "deleted_records": deleted,
                    "cutoff_date": cutoff_date.isoformat(),
                    "days_kept": days_to_keep
                }
                
        except Exception as e:
            logger.error(f"❌ Error cleaning up old data: {e}")
            return {
                "success": False,
                "error": str(e)
            }
        
    def _deduplicate_candles_data(self, candles_data: List[Dict], figi: str, interval: str) -> List[Dict]:
        """
        Удаляет дубликаты из данных свечей перед сохранением
        
        Args:
            candles_data: данные свечей от Tinkoff API
            figi: FIGI инструмента
            interval: интервал свечей
            
        Returns:
            List[Dict]: очищенные от дубликатов данные
        """
        if not candles_data:
            return candles_data
        
        seen_times = set()
        deduplicated = []
        duplicates_count = 0
        
        for candle in candles_data:
            candle_time = candle['time']
            
            # Создаем уникальный ключ
            time_key = (figi, interval, candle_time)
            
            if time_key not in seen_times:
                seen_times.add(time_key)
                deduplicated.append(candle)
            else:
                duplicates_count += 1
                logger.warning(f"⚠️ Removing duplicate candle for {figi} at {candle_time}")
        
        if duplicates_count > 0:
            logger.info(f"🧹 Removed {duplicates_count} duplicate candles from {len(candles_data)} total")
        
        return deduplicated

    # Добавить в integrations/tinkoff_integration.py

    def _validate_candles_data(self, candles: List[Dict]) -> List[Dict]:
        """
        Валидирует и очищает данные свечей от API
        
        Args:
            candles: сырые данные от Tinkoff API
            
        Returns:
            List[Dict]: валидированные данные
        """
        valid_candles = []
        
        for i, candle in enumerate(candles):
            try:
                # Проверяем обязательные поля
                required_fields = ['time', 'open', 'high', 'low', 'close']
                if not all(field in candle for field in required_fields):
                    logger.warning(f"⚠️ Skipping candle {i}: missing required fields")
                    continue
                
                # Проверяем логичность цен
                open_price = float(candle['open'])
                high_price = float(candle['high'])
                low_price = float(candle['low'])
                close_price = float(candle['close'])
                
                if not (low_price <= open_price <= high_price and 
                    low_price <= close_price <= high_price):
                    logger.warning(f"⚠️ Skipping candle {i}: invalid OHLC values")
                    continue
                
                # Проверяем что цены положительные
                if any(price <= 0 for price in [open_price, high_price, low_price, close_price]):
                    logger.warning(f"⚠️ Skipping candle {i}: negative or zero prices")
                    continue
                
                valid_candles.append(candle)
                
            except (ValueError, TypeError) as e:
                logger.warning(f"⚠️ Skipping candle {i}: validation error {e}")
                continue
        
        logger.info(f"✅ Validated {len(valid_candles)}/{len(candles)} candles")
        return valid_candles