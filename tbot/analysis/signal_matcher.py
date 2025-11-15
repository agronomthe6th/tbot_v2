# analysis/signal_matcher.py - ИСПРАВЛЕННАЯ ВЕРСИЯ
import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta, timezone  # ✅ ДОБАВИЛИ timezone
from dataclasses import dataclass
from utils.datetime_utils import now_utc, utc_from_minutes_ago, ensure_timezone_aware, days_between_utc
from core.database import Database
from core.database import ParsedSignal, SignalResult, ChartDataPoint

logger = logging.getLogger(__name__)

@dataclass
class PriceMatch:
    """Результат сопоставления сигнала с ценой"""
    signal_id: str
    signal_time: datetime
    target_price: Optional[float]
    actual_price: float
    price_time: datetime
    slippage_pct: float
    delay_minutes: int

class SignalMatcher:
    """Класс для сопоставления торговых сигналов с рыночными ценами + Tinkoff API"""
    
    def __init__(self, db_manager: Database, tinkoff_client=None):
        self.db = db_manager
        self.tinkoff = tinkoff_client 
        self.tracking_timeout_hours = 24
        
    # ===== ОБНОВЛЕННЫЕ МЕТОДЫ ДЛЯ РАБОТЫ С TINKOFF API =====

    async def _find_entry_price(self, signal: Dict, figi: str) -> Optional[PriceMatch]:
        """
        🔄 ОБНОВЛЕНО: Поиск цены входа для сигнала (база данных + API)
        """
        try:
            signal_time = ensure_timezone_aware(signal['timestamp'])  # ✅ ИСПРАВЛЕНО
            search_end = signal_time + timedelta(hours=1)
            
            # ✨ СНАЧАЛА ПЫТАЕМСЯ НАЙТИ В БАЗЕ ДАННЫХ
            candles = self.db.get_candles(
                figi,  # ✅ ИСПРАВЛЕНО: убрали instrument_id=
                interval='5min',  # 🔄 ИЗМЕНЕНО: 5min для лучшего покрытия
                from_time=signal_time,
                to_time=search_end,
                limit=12  # 12 свечей по 5 мин = 1 час
            )
            
            if candles:
                # Нашли в базе - используем как раньше
                first_candle = candles[0]
                entry_price = first_candle['open']
                entry_time = ensure_timezone_aware(first_candle['time'])  # ✅ ИСПРАВЛЕНО
                
                logger.info(f"💾 Found entry price in database: {entry_price} for {signal['ticker']}")
                
            else:
                # ✨ НЕТ В БАЗЕ - ИСПОЛЬЗУЕМ API
                if not self.tinkoff:
                    logger.error("❌ No DB data and Tinkoff API not available")
                    return None
                
                logger.info(f"🌐 Getting entry price via API for {signal['ticker']}")
                price_data = await self.tinkoff.get_current_price(signal['ticker'])
                
                if not price_data:
                    return None
                
                entry_price = price_data['price']
                entry_time = now_utc()  # ✅ ИСПРАВЛЕНО: timezone-aware
                
                logger.info(f"🌐 Entry price via API: {entry_price}")
            
            # Вычисляем проскальзывание
            target_price = signal.get('target_price')
            slippage_pct = 0.0
            
            if target_price:
                slippage_pct = ((entry_price - target_price) / target_price) * 100
            
            # ✅ ИСПРАВЛЕНО: Безопасное вычисление разности времени
            delay_minutes = int((entry_time - signal_time).total_seconds() / 60)
            
            return PriceMatch(
                signal_id=signal['id'],
                signal_time=signal_time,
                target_price=target_price,
                actual_price=entry_price,
                price_time=entry_time,
                slippage_pct=slippage_pct,
                delay_minutes=delay_minutes
            )
            
        except Exception as e:
            logger.error(f"❌ Error finding entry price: {e}")
            return None

    async def _check_exit_conditions(self, position: Dict, signal: Dict, figi: str) -> Optional[Dict]:
        """
        🔄 ОБНОВЛЕНО: Проверка условий выхода (база данных + API)
        """
        try:
            current_time = now_utc()  # ✅ ИСПРАВЛЕНО: timezone-aware
            direction = signal['direction']
            
            # Получаем текущую цену
            current_price = await self._get_current_price(figi, signal['ticker'])
            if not current_price:
                return None
            
            # Проверяем stop-loss
            if signal.get('stop_loss'):
                stop_loss = float(signal['stop_loss'])
                if direction == 'long' and current_price <= stop_loss:
                    return {'price': current_price, 'time': current_time, 'reason': 'stop_loss'}
                elif direction == 'short' and current_price >= stop_loss:
                    return {'price': current_price, 'time': current_time, 'reason': 'stop_loss'}
            
            # Проверяем take-profit
            if signal.get('take_profit'):
                take_profit = float(signal['take_profit'])
                if direction == 'long' and current_price >= take_profit:
                    return {'price': current_price, 'time': current_time, 'reason': 'take_profit'}
                elif direction == 'short' and current_price <= take_profit:
                    return {'price': current_price, 'time': current_time, 'reason': 'take_profit'}
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Error checking exit conditions: {e}")
            return None

    async def _get_current_price(self, figi: str, ticker: str = None) -> Optional[float]:
        """
        🔄 ОБНОВЛЕНО: Получение текущей цены (база данных + API)
        """
        try:
            # Пытаемся получить из базы
            candles = self.db.get_candles(
                figi,  # ✅ ИСПРАВЛЕНО: убрали instrument_id=
                interval='5min',  # 🔄 ИЗМЕНЕНО: 5min
                from_time=utc_from_minutes_ago(25),  # ✅ ИСПРАВЛЕНО: timezone-aware
                limit=1
            )
            
            if candles:
                price = candles[0]['close']
                logger.debug(f"💾 Current price from DB: {price}")
                return float(price)
            
            # 🆕 НЕТ В БАЗЕ - ПЫТАЕМСЯ ЧЕРЕЗ API
            if self.tinkoff:
                logger.debug(f"🌐 Getting current price via API for {ticker or figi}")
                price_data = await self.tinkoff.get_current_price(ticker or figi)
                
                if price_data and 'price' in price_data:
                    price = float(price_data['price'])
                    logger.debug(f"🌐 Current price from API: {price}")
                    return price
            
            logger.warning(f"⚠️ No price data available for {ticker or figi}")
            return None
            
        except Exception as e:
            logger.error(f"❌ Error getting current price: {e}")
            return None
    # ===== НОВЫЕ МЕТОДЫ ДЛЯ РАБОТЫ С TINKOFF =====
    
    async def ensure_instrument_in_database(self, ticker: str) -> Optional[str]:
        """
        ✨ Убеждаемся что инструмент есть в базе данных
        """
        try:
            # Ищем в базе
            instrument = self.db.get_instrument_by_ticker(ticker)
            if instrument:
                return instrument['figi']
            
            # Нет в базе - попытаемся найти через API
            if not self.tinkoff:
                logger.error(f"❌ Instrument {ticker} not in DB and no API available")
                return None
            
            logger.info(f"🔍 Searching instrument {ticker} via API...")
            api_instrument = await self.tinkoff.find_instrument_by_ticker(ticker)
            
            if not api_instrument:
                logger.error(f"❌ Instrument {ticker} not found via API")
                return None
            
            # Сохраняем в базу
            self.db.save_instrument(
                figi=api_instrument["figi"],
                ticker=ticker,
                name=api_instrument["name"],
                instrument_type=api_instrument.get("type", "share")
            )
            
            logger.info(f"✅ Added instrument {ticker} to database")
            return api_instrument["figi"]
            
        except Exception as e:
            logger.error(f"❌ Error ensuring instrument {ticker} in database: {e}")
            return None
    
    async def process_untracked_signals(self, limit: int = 50) -> int:
        """
        🔄 ОБНОВЛЕНО: Обработка сигналов без результатов отслеживания
        """
        try:
            untracked_signals = self._get_untracked_signals(limit)
            processed = 0
            
            for signal in untracked_signals:
                try:
                    figi = await self.ensure_instrument_in_database(signal['ticker'])
                    if not figi:
                        logger.warning(f"⚠️ Cannot process signal - instrument {signal['ticker']} not available")
                        continue
                    
                    # Находим цену входа (теперь с поддержкой API)
                    entry_match = await self._find_entry_price(signal, figi)
                    if entry_match:
                        result_data = {
                            'planned_entry_price': signal.get('target_price'),
                            'actual_entry_price': entry_match.actual_price,
                            'entry_time': entry_match.price_time,
                            'status': 'active'
                        }
                        result_id = self.db.save_signal_result(signal['id'], result_data)
                        
                        if result_id:
                            processed += 1
                            logger.info(f"✅ Started tracking signal {signal['id']}: {signal['ticker']} "
                                      f"@ {entry_match.actual_price}")
                    
                except Exception as e:
                    logger.error(f"❌ Error processing signal {signal['id']}: {e}")
                    continue
            
            logger.info(f"📊 Started tracking {processed} new signals")
            return processed
            
        except Exception as e:
            logger.error(f"❌ Error in process_untracked_signals: {e}")
            return 0

    async def update_active_positions(self) -> int:
        """
        🔄 ОБНОВЛЕНО: Обновление активных позиций с проверкой выходов
        """
        try:
            active_positions = self._get_active_positions()
            updated = 0
            
            logger.info(f"📊 Checking {len(active_positions)} active positions...")
            
            for position in active_positions:
                try:
                    # Получаем информацию о сигнале
                    signal = self._get_signal_by_id(position['signal_id'])
                    if not signal:
                        continue
                    
                    # ✨ УБЕЖДАЕМСЯ ЧТО ИНСТРУМЕНТ ЕСТЬ В БАЗЕ
                    figi = await self.ensure_instrument_in_database(signal['ticker'])
                    if not figi:
                        continue
                    
                    # Проверяем условия выхода (теперь с поддержкой API)
                    exit_result = await self._check_exit_conditions(position, signal, figi)
                    
                    if exit_result:
                        # Закрываем позицию
                        self.db.update_signal_result(
                            position['id'],  # ✅ ИСПРАВЛЕНО: result_id
                            {  # ✅ ИСПРАВЛЕНО: updates как словарь
                                'exit_price': exit_result['price'],
                                'exit_time': exit_result['time'],
                                'exit_reason': exit_result['reason'],
                                'status': 'closed'
                            }
                        )
                        updated += 1
                        logger.info(f"✅ Closed position {position['signal_id']}: "
                                f"{exit_result['reason']} @ {exit_result['price']}")
                    
                    # Проверяем таймаут
                    elif self._is_position_expired(position):
                        current_price = await self._get_current_price(figi, signal['ticker'])
                        if current_price:
                            self.db.update_signal_result(
                                position['id'],  # ✅ ИСПРАВЛЕНО: result_id  
                                {  # ✅ ИСПРАВЛЕНО: updates как словарь
                                    'exit_price': current_price,
                                    'exit_time': now_utc(),  # ✅ ИСПРАВЛЕНО
                                    'exit_reason': 'timeout',
                                    'status': 'closed'
                                }
                            )
                            updated += 1
                            logger.info(f"⏰ Closed expired position {position['signal_id']} @ {current_price}")
                
                except Exception as e:
                    logger.error(f"❌ Error updating position {position['signal_id']}: {e}")
                    continue
            
            logger.info(f"📈 Updated {updated} active positions")
            return updated
            
        except Exception as e:
            logger.error(f"❌ Error in update_active_positions: {e}")
            return 0    

    # ===== ОСТАЛЬНЫЕ МЕТОДЫ ОСТАЮТСЯ БЕЗ ИЗМЕНЕНИЙ =====
    
    def _get_untracked_signals(self, limit: int) -> List[Dict]:
        """Получение сигналов без результатов отслеживания (без изменений)"""
        try:
            with self.db.session() as session:
                # ✅ ИСПРАВЛЕНО: Используем timezone-aware дату для фильтрации
                from_date = now_utc() - timedelta(days=7)
                
                signals = session.query(ParsedSignal).outerjoin(SignalResult).filter(
                    SignalResult.id.is_(None),
                    ParsedSignal.direction.in_(['long', 'short']),
                    ParsedSignal.timestamp >= from_date
                ).order_by(ParsedSignal.timestamp).limit(limit).all()
                
                return [
                    {
                        'id': str(signal.id),
                        'ticker': signal.ticker,
                        'direction': signal.direction,
                        'target_price': float(signal.target_price) if signal.target_price else None,
                        'timestamp': signal.timestamp,
                        'trader': signal.author
                    }
                    for signal in signals
                ]
        except Exception as e:
            logger.error(f"❌ Error getting untracked signals: {e}")
        return []
    
    def _get_active_positions(self) -> List[Dict]:
        """Получение активных позиций для отслеживания с блокировкой"""
        try:
            with self.db.session() as session:
                # Используем SELECT FOR UPDATE для предотвращения race conditions
                # SKIP LOCKED пропускает уже заблокированные строки
                results = session.query(SignalResult).filter(
                    SignalResult.status == 'active'
                ).with_for_update(skip_locked=True).all()

                return [
                    {
                        'id': str(result.id),
                        'signal_id': str(result.signal_id),
                        'entry_price': float(result.actual_entry_price),
                        'entry_time': result.entry_time,
                        'tracking_started_at': result.tracking_started_at
                    }
                    for result in results
                ]
        except Exception as e:
            logger.error(f"❌ Error getting active positions: {e}")
            return []
    
    def _get_signal_by_id(self, signal_id: str) -> Optional[Dict]:
        """Получение сигнала по ID (без изменений)"""
        try:
            with self.db.session() as session:
                signal = session.query(ParsedSignal).filter(
                    ParsedSignal.id == signal_id
                ).first()
                
                if not signal:
                    return None
                
                return {
                    'id': str(signal.id),
                    'ticker': signal.ticker,
                    'direction': signal.direction,
                    'target_price': float(signal.target_price) if signal.target_price else None,
                    'stop_loss': float(signal.stop_loss) if signal.stop_loss else None,
                    'take_profit': float(signal.take_profit) if signal.take_profit else None,
                    'timestamp': signal.timestamp,
                    'trader': signal.author
                }
        except Exception as e:
            logger.error(f"❌ Error getting signal {signal_id}: {e}")
            return None
    
    def _is_position_expired(self, position: Dict) -> bool:
        """
        Проверка на истечение срока позиции
        """
        try:
            tracking_started = ensure_timezone_aware(position['tracking_started_at'])  # ✅ ИСПРАВЛЕНО
            current_time = now_utc()  # ✅ ИСПРАВЛЕНО
            
            hours_tracked = (current_time - tracking_started).total_seconds() / 3600
            return hours_tracked >= self.tracking_timeout_hours
            
        except Exception as e:
            logger.error(f"❌ Error checking position expiry: {e}")
            return False