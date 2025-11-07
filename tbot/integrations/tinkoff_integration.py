# integrations/tinkoff_integration.py
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple
import pytz
import os

logger = logging.getLogger(__name__)

class TinkoffIntegration:
    """ПОЛНАЯ интеграция с Tinkoff API с правильным target + все оригинальные методы"""
    
    def __init__(self, token: str, sandbox: bool = True):
        self.token = token
        self.sandbox = sandbox
        self.client = None
        self.instruments_cache = {}
        
        # Проверяем наличие библиотеки
        try:
            global AsyncClient, CandleInterval, InstrumentIdType
            from tinkoff.invest import AsyncClient, CandleInterval, InstrumentIdType
            
            # 🔥 КЛЮЧЕВОЕ ИСПРАВЛЕНИЕ: импортируем константы для target
            from tinkoff.invest.constants import INVEST_GRPC_API, INVEST_GRPC_API_SANDBOX
            self.target = INVEST_GRPC_API_SANDBOX if sandbox else INVEST_GRPC_API
            
            logger.info(f"🎯 Target set to: {'SANDBOX' if sandbox else 'PRODUCTION'}")
            
        except ImportError:
            logger.error("❌ Tinkoff Invest library not found. Install: pip install tinkoff-invest")
            raise ImportError("tinkoff-invest library required")
        
    async def initialize(self) -> bool:
        """Инициализация клиента с правильным target"""
        try:
            if not self.token or self.token == "your_tinkoff_token_here":
                logger.error("❌ Tinkoff token not configured")
                return False
                
            logger.info(f"🔗 Initializing Tinkoff API (sandbox={self.sandbox})")
            
            # 🔥 ИСПРАВЛЕНИЕ: используем target для выбора контура
            async with AsyncClient(self.token, target=self.target) as client:
                # Простой тест - получаем аккаунты
                accounts = await client.users.get_accounts()
                logger.info(f"✅ Tinkoff client initialized successfully")
                logger.info(f"📊 Found {len(accounts.accounts)} accounts")
                logger.info(f"🎯 Using {'SANDBOX' if self.sandbox else 'PRODUCTION'} environment")
                
                # Дополнительная проверка - поиск простого инструмента
                try:
                    test_response = await client.instruments.shares()
                    logger.info(f"🔍 Found {len(test_response.instruments)} shares available")
                except Exception as e:
                    logger.warning(f"⚠️ Could not fetch shares list: {e}")
                
                return True
                
        except Exception as e:
            logger.error(f"❌ Failed to initialize Tinkoff client: {e}")
            logger.error(f"🔧 Debug info: token length={len(self.token)}, sandbox={self.sandbox}, target={getattr(self, 'target', 'NOT_SET')}")
            return False
    
    async def close(self):
        """Закрытие соединения"""
        logger.info("🔄 Tinkoff client closed")
    
    async def find_instrument_by_ticker(self, ticker: str) -> Optional[Dict]:
        """Поиск инструмента по тикеру с правильным target"""
        async with AsyncClient(self.token, target=self.target) as client:
            try:
                logger.info(f"🔍 Searching for instrument: {ticker}")
                
                ticker_upper = ticker.upper()
                found_instruments = []
                
                instrument_types = [
                    ("shares", client.instruments.shares),
                    ("etfs", client.instruments.etfs),
                    ("bonds", client.instruments.bonds),
                    ("futures", client.instruments.futures),
                    ("currencies", client.instruments.currencies)
                ]
                
                for type_name, instrument_method in instrument_types:
                    try:
                        response = await instrument_method()
                        
                        for instrument in response.instruments:
                            instrument_ticker_upper = instrument.ticker.upper()
                            
                            if instrument_ticker_upper == ticker_upper:
                                result = {
                                    "figi": instrument.figi,
                                    "ticker": instrument.ticker,
                                    "name": instrument.name,
                                    "type": type_name,
                                    "currency": instrument.currency,
                                    "lot": instrument.lot,
                                    "trading_status": str(instrument.trading_status) if hasattr(instrument, 'trading_status') else 'unknown'
                                }
                                logger.info(f"✅ Found exact match {ticker}: {result['name']} ({result['figi']})")
                                return result
                            
                            elif instrument_ticker_upper.startswith(ticker_upper):
                                found_instruments.append({
                                    "figi": instrument.figi,
                                    "ticker": instrument.ticker,
                                    "name": instrument.name,
                                    "type": type_name,
                                    "currency": instrument.currency,
                                    "lot": instrument.lot,
                                    "trading_status": str(instrument.trading_status) if hasattr(instrument, 'trading_status') else 'unknown'
                                })
                                
                    except Exception as e:
                        logger.warning(f"⚠️ Error searching in {type_name}: {e}")
                        continue
                
                if found_instruments:
                    logger.info(f"🔎 Found {len(found_instruments)} partial matches for '{ticker}':")
                    for idx, inst in enumerate(found_instruments[:5]):
                        logger.info(f"  {idx+1}. {inst['ticker']} - {inst['name']} ({inst['type']})")
                    
                    logger.info(f"✅ Returning first match: {found_instruments[0]['ticker']}")
                    return found_instruments[0]
                
                logger.warning(f"❌ Instrument {ticker} not found")
                return None
                
            except Exception as e:
                logger.error(f"❌ Error searching for {ticker}: {e}")
                return None

    async def get_current_price(self, ticker: str) -> Optional[Dict]:
        """Получение текущей цены инструмента с правильным target"""
        try:
            # Сначала находим инструмент
            instrument = await self.find_instrument_by_ticker(ticker)
            if not instrument:
                return None
            
            async with AsyncClient(self.token, target=self.target) as client:
                # Получаем последнюю цену
                response = await client.market_data.get_last_prices(
                    figi=[instrument['figi']]
                )
                
                if response.last_prices:
                    last_price = response.last_prices[0]
                    price_value = float(last_price.price.units) + float(last_price.price.nano) / 1e9
                    
                    return {
                        "ticker": ticker,
                        "figi": instrument['figi'],
                        "price": price_value,
                        "currency": instrument['currency'],
                        "timestamp": datetime.now().isoformat(),
                        "source": f"tinkoff_api_{'sandbox' if self.sandbox else 'production'}"
                    }
                
                return None
                
        except Exception as e:
            logger.error(f"❌ Error getting price for {ticker}: {e}")
            return None

    async def get_candles(self, figi: str, interval: str, from_time: datetime, to_time: Optional[datetime] = None) -> List[Dict]:
        """Получение свечей для инструмента с валидацией и дедупликацией"""
        try:
            if to_time is None:
                to_time = datetime.now(pytz.UTC)
            
            # Конвертируем интервал
            interval_map = {
                "1min": CandleInterval.CANDLE_INTERVAL_1_MIN,
                "5min": CandleInterval.CANDLE_INTERVAL_5_MIN,
                "hour": CandleInterval.CANDLE_INTERVAL_HOUR,
                "day": CandleInterval.CANDLE_INTERVAL_DAY
            }
            
            if interval not in interval_map:
                logger.error(f"❌ Unsupported interval: {interval}")
                return []
            
            candles = []
            async with AsyncClient(self.token, target=self.target) as client:
                async for candle in client.get_all_candles(
                    figi=figi,
                    from_=from_time,
                    to=to_time,
                    interval=interval_map[interval]
                ):
                    candles.append({
                        "time": candle.time,
                        "open": float(candle.open.units) + float(candle.open.nano) / 1e9,
                        "high": float(candle.high.units) + float(candle.high.nano) / 1e9,
                        "low": float(candle.low.units) + float(candle.low.nano) / 1e9,
                        "close": float(candle.close.units) + float(candle.close.nano) / 1e9,
                        "volume": candle.volume
                    })
            
            logger.info(f"📊 Received {len(candles)} raw candles from Tinkoff API")
            
            # 🆕 ВАЛИДИРУЕМ И ОЧИЩАЕМ ДАННЫЕ
            validated_candles = self._validate_candles_data(candles)
            
            # Сортируем по времени для надежности
            validated_candles.sort(key=lambda x: x['time'])
            
            logger.info(f"✅ Returning {len(validated_candles)} validated candles")
            return validated_candles
            
        except Exception as e:
            logger.error(f"❌ Error getting candles for {figi}: {e}")
            return []


    async def test_connection(self) -> Dict:
        """Тестирование подключения к API с правильным target"""
        try:
            async with AsyncClient(self.token, target=self.target) as client:
                # Получаем информацию об аккаунте
                accounts = await client.users.get_accounts()
                
                # Пробуем найти популярный инструмент
                test_instrument = await self.find_instrument_by_ticker("SBER")
                
                return {
                    "success": True,
                    "sandbox": self.sandbox,
                    "target": "SANDBOX" if self.sandbox else "PRODUCTION",
                    "accounts_count": len(accounts.accounts),
                    "test_instrument": test_instrument is not None,
                    "test_ticker": "SBER",
                    "timestamp": datetime.now().isoformat()
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "sandbox": self.sandbox,
                "target": "SANDBOX" if self.sandbox else "PRODUCTION",
                "timestamp": datetime.now().isoformat()
            }

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

    async def get_popular_instruments(self, limit: int = 50) -> List[Dict]:
        """Получение популярных инструментов с правильным target"""
        try:
            async with AsyncClient(self.token, target=self.target) as client:
                shares_response = await client.instruments.shares()
                
                # Берем первые limit инструментов
                instruments = []
                for instrument in shares_response.instruments[:limit]:
                    instruments.append({
                        "figi": instrument.figi,
                        "ticker": instrument.ticker,
                        "name": instrument.name,
                        "currency": instrument.currency,
                        "lot": instrument.lot,
                        "type": "share"
                    })
                
                logger.info(f"📊 Loaded {len(instruments)} popular instruments")
                return instruments
                
        except Exception as e:
            logger.error(f"❌ Error loading popular instruments: {e}")
            return []

    async def bulk_load_instruments(self, tickers: List[str]) -> Dict:
        """🔄 ВОССТАНОВЛЕННЫЙ МЕТОД: Массовая загрузка инструментов с прогрессом"""
        results = {
            "loaded": [],
            "failed": [],
            "total_requested": len(tickers),
            "total_loaded": 0
        }
        
        for i, ticker in enumerate(tickers):
            try:
                logger.info(f"🔍 Loading {i+1}/{len(tickers)}: {ticker}")
                instrument = await self.find_instrument_by_ticker(ticker)
                
                if instrument:
                    results["loaded"].append(instrument)
                    results["total_loaded"] += 1
                else:
                    results["failed"].append({"ticker": ticker, "error": "Not found"})
                    
                # Пауза между запросами
                await asyncio.sleep(0.1)
                
            except Exception as e:
                results["failed"].append({"ticker": ticker, "error": str(e)})
                logger.error(f"❌ Error loading {ticker}: {e}")
        
        logger.info(f"📊 Bulk load completed: {results['total_loaded']}/{results['total_requested']}")
        return results

    async def get_account_info(self) -> Dict:
        """Получение информации об аккаунте"""
        try:
            async with AsyncClient(self.token, target=self.target) as client:
                accounts = await client.users.get_accounts()
                
                account_info = []
                for account in accounts.accounts:
                    account_info.append({
                        "id": account.id,
                        "name": account.name,
                        "type": str(account.type),
                        "status": str(account.status),
                        "access_level": str(account.access_level)
                    })
                
                return {
                    "success": True,
                    "accounts": account_info,
                    "total_accounts": len(account_info)
                }
                
        except Exception as e:
            logger.error(f"❌ Error getting account info: {e}")
            return {
                "success": False,
                "error": str(e),
                "accounts": []
            }

    async def get_instrument_by_figi(self, figi: str) -> Optional[Dict]:
        """Получение инструмента по FIGI"""
        try:
            async with AsyncClient(self.token, target=self.target) as client:
                response = await client.instruments.get_instrument_by(
                    id_type=InstrumentIdType.INSTRUMENT_ID_TYPE_FIGI,
                    id=figi
                )
                
                if response.instrument:
                    instrument = response.instrument
                    return {
                        "figi": instrument.figi,
                        "ticker": instrument.ticker,
                        "name": instrument.name,
                        "currency": instrument.currency,
                        "lot": instrument.lot,
                        "type": "unknown"  # Нужно определить тип отдельно
                    }
                return None
                
        except Exception as e:
            logger.error(f"❌ Error getting instrument by FIGI {figi}: {e}")
            return None

    async def search_instruments(self, query: str, limit: int = 20) -> List[Dict]:
        """Поиск инструментов по запросу"""
        try:
            # Простой поиск - пробуем найти как тикер
            if len(query) <= 6 and query.isupper():
                instrument = await self.find_instrument_by_ticker(query)
                if instrument:
                    return [instrument]
            
            # Расширенный поиск по всем инструментам
            results = []
            async with AsyncClient(self.token, target=self.target) as client:
                instrument_types = [
                    ("shares", client.instruments.shares),
                    ("etfs", client.instruments.etfs),
                    ("bonds", client.instruments.bonds),
                ]
                
                for type_name, instrument_method in instrument_types:
                    try:
                        response = await instrument_method()
                        for instrument in response.instruments:
                            if (query.upper() in instrument.ticker.upper() or 
                                query.upper() in instrument.name.upper()):
                                results.append({
                                    "figi": instrument.figi,
                                    "ticker": instrument.ticker,
                                    "name": instrument.name,
                                    "type": type_name,
                                    "currency": instrument.currency,
                                    "lot": instrument.lot
                                })
                                
                                if len(results) >= limit:
                                    break
                    except Exception as e:
                        logger.warning(f"⚠️ Error searching in {type_name}: {e}")
                        continue
                        
                    if len(results) >= limit:
                        break
            
            logger.info(f"🔍 Found {len(results)} instruments for query '{query}'")
            return results
            
        except Exception as e:
            logger.error(f"❌ Error searching instruments: {e}")

            return []

# Обновляем глобальную инициализацию
async def create_tinkoff_client() -> TinkoffIntegration:
    """Создание и инициализация Tinkoff клиента с правильным target"""
    token = os.getenv("TINKOFF_TOKEN")
    sandbox = os.getenv("TINKOFF_SANDBOX", "false").lower() == "true"
    
    if not token:
        raise ValueError("TINKOFF_TOKEN environment variable not set")
    
    client = TinkoffIntegration(token, sandbox)
    success = await client.initialize()
    
    if not success:
        raise Exception("Failed to initialize Tinkoff client")
    
    return client


# 🔄 ВОССТАНОВЛЕННЫЕ ФУНКЦИИ СОВМЕСТИМОСТИ из старого кода
async def sync_instruments_from_tinkoff(tinkoff_client, instrument_type="shares"):
    """Синхронизация инструментов (обновленная версия)"""
    if instrument_type == "shares":
        instruments = await tinkoff_client.get_popular_instruments()
        return len(instruments)
    return 0

async def get_missing_candles_for_signals(tinkoff_client):
    """Загрузка недостающих свечей для сигналов"""
    # Эта функция будет реализована позже при интеграции с SignalMatcher
    logger.info("🕯️ Getting missing candles for signals...")
    return 0

