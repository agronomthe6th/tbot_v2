# core/database/database.py
"""
Класс для работы с PostgreSQL
"""
import logging
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta
from contextlib import contextmanager, asynccontextmanager

from sqlalchemy import create_engine, func, and_, or_, desc, asc
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError

from .models import *

logger = logging.getLogger(__name__)

class Database:
    """Класс для работы с PostgreSQL (sync + async)"""
    
    def __init__(self, database_url: str, pool_size: int = 10, echo: bool = False):
        """
        Инициализация подключения к БД
        
        Args:
            database_url: PostgreSQL URL вида postgresql://user:pass@host:port/db
            pool_size: размер пула соединений
            echo: выводить SQL запросы в лог
        """
        self.database_url = database_url
        
        # Синхронный engine
        self.engine = create_engine(
            database_url,
            pool_size=pool_size,
            max_overflow=pool_size * 2,
            pool_pre_ping=True,
            echo=echo
        )
        self.SessionLocal = sessionmaker(bind=self.engine)
        
        # Асинхронный engine
        async_url = database_url.replace('postgresql://', 'postgresql+asyncpg://')
        self.async_engine = create_async_engine(
            async_url,
            pool_size=pool_size,
            max_overflow=pool_size * 2,
            echo=echo
        )
        self.AsyncSessionLocal = async_sessionmaker(bind=self.async_engine)
        
        logger.info(f"✅ Database initialized: {self._mask_url(database_url)}")
    
    def _mask_url(self, url: str) -> str:
        """Маскировка пароля в URL для логов"""
        if '@' in url and ':' in url:
            parts = url.split('@')
            if len(parts) == 2:
                user_pass = parts[0].split('://')[-1]
                if ':' in user_pass:
                    user = user_pass.split(':')[0]
                    return url.replace(user_pass, f"{user}:***")
        return url
    
    @contextmanager
    def session(self):
        """Контекстный менеджер для синхронных операций"""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    @asynccontextmanager
    async def async_session(self):
        """Контекстный менеджер для асинхронных операций"""
        async with self.AsyncSessionLocal() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
    
    def close(self):
        """Закрыть все соединения"""
        self.engine.dispose()
        logger.info("🔌 Database connections closed")
    
    # ===== СООБЩЕНИЯ =====
    
    def save_message(self, channel_id: int, message_id: int, 
                    timestamp: datetime, text: str, author: str = None,
                    is_processed: bool = False) -> int:
        """
        Сохранить сырое сообщение из Telegram
        
        Returns:
            int: ID сохраненного сообщения
        """
        with self.session() as session:
            message = RawMessage(
                channel_id=channel_id,
                message_id=message_id,
                timestamp=timestamp,
                text=text,
                author=author,
                is_processed=is_processed
            )
            
            try:
                session.add(message)
                session.flush()
                logger.debug(f"💾 Message saved: {message.id}")
                return message.id
                
            except IntegrityError:
                session.rollback()
                # Сообщение уже существует - обновляем
                existing = session.query(RawMessage).filter(
                    RawMessage.channel_id == channel_id,
                    RawMessage.message_id == message_id
                ).first()
                
                if existing:
                    existing.text = text
                    existing.author = author
                    existing.is_processed = is_processed
                    session.flush()
                    return existing.id
                
                raise
    
    def get_messages(self, channel_id: int = None, is_processed: bool = None,
                    from_date: datetime = None, limit: int = 1000) -> List[Dict]:
        """
        Получить сообщения с фильтрацией
        
        Returns:
            List[Dict]: список сообщений в виде словарей
        """
        with self.session() as session:
            query = session.query(RawMessage)
            
            if channel_id is not None:
                query = query.filter(RawMessage.channel_id == channel_id)
            
            if is_processed is not None:
                query = query.filter(RawMessage.is_processed == is_processed)
                
            if from_date:
                query = query.filter(RawMessage.timestamp >= from_date)
            
            messages = query.order_by(desc(RawMessage.timestamp)).limit(limit).all()
            
            return [
                {
                    'id': msg.id,
                    'channel_id': msg.channel_id,
                    'message_id': msg.message_id,
                    'timestamp': msg.timestamp,
                    'text': msg.text,
                    'author': msg.author,
                    'is_processed': msg.is_processed
                }
                for msg in messages
            ]
    
    def mark_message_processed(self, message_id: int):
        """Отметить сообщение как обработанное"""
        with self.session() as session:
            session.query(RawMessage).filter(RawMessage.id == message_id).update(
                {'is_processed': True}
            )
    
    # ===== СИГНАЛЫ =====
    
    def save_signal(self, signal_data: Dict) -> str:
        """
        Сохранить торговый сигнал
        
        Args:
            signal_data: словарь с данными сигнала
            
        Returns:
            str: UUID сохраненного сигнала
        """
        with self.session() as session:
            signal = ParsedSignal(
                raw_message_id=signal_data.get('raw_message_id'),
                timestamp=signal_data['timestamp'],
                parser_version=signal_data.get('parser_version', '1.0'),
                confidence_score=signal_data.get('confidence_score'),
                channel_id=signal_data['channel_id'],
                trader_id=signal_data.get('trader_id'),
                author=signal_data.get('author'),
                original_text=signal_data['original_text'],
                ticker=signal_data['ticker'],
                figi=signal_data.get('figi'),
                direction=signal_data.get('direction'),
                signal_type=signal_data.get('signal_type'),
                target_price=signal_data.get('target_price'),
                stop_loss=signal_data.get('stop_loss'),
                take_profit=signal_data.get('take_profit'),
                entry_condition=signal_data.get('entry_condition'),
                confidence_level=signal_data.get('confidence_level'),
                timeframe=signal_data.get('timeframe'),
                extracted_data=signal_data.get('extracted_data')
            )
            
            session.add(signal)
            session.flush()
            
            logger.debug(f"📈 Signal saved: {signal.id}")
            return str(signal.id)
    
    def get_signals(self, ticker: str = None, trader_id: int = None,
                   channel_id: int = None, direction: str = None,
                   from_date: datetime = None, limit: int = 100) -> List[Dict]:
        """
        Получить сигналы с фильтрацией
        
        Returns:
            List[Dict]: список сигналов
        """
        with self.session() as session:
            query = session.query(ParsedSignal)
            
            if ticker:
                query = query.filter(ParsedSignal.ticker == ticker)
            
            if trader_id:
                query = query.filter(ParsedSignal.trader_id == trader_id)
                
            if channel_id:
                query = query.filter(ParsedSignal.channel_id == channel_id)
                
            if direction:
                query = query.filter(ParsedSignal.direction == direction)
                
            if from_date:
                query = query.filter(ParsedSignal.timestamp >= from_date)
            
            signals = query.order_by(desc(ParsedSignal.timestamp)).limit(limit).all()
            
            return [
                {
                    'id': str(signal.id),
                    'timestamp': signal.timestamp,
                    'ticker': signal.ticker,
                    'direction': signal.direction,
                    'signal_type': signal.signal_type,
                    'target_price': float(signal.target_price) if signal.target_price else None,
                    'stop_loss': float(signal.stop_loss) if signal.stop_loss else None,
                    'take_profit': float(signal.take_profit) if signal.take_profit else None,
                    'author': signal.author,
                    'trader_id': signal.trader_id,
                    'confidence_score': float(signal.confidence_score) if signal.confidence_score else None,
                    'original_text': signal.original_text
                }
                for signal in signals
            ]
    
    # ===== ТРЕЙДЕРЫ =====
    
    def create_trader(self, name: str, channel_id: int, 
                     telegram_username: str = None) -> int:
        """
        Создать профиль трейдера
        
        Returns:
            int: ID созданного трейдера
        """
        with self.session() as session:
            trader = Trader(
                name=name,
                channel_id=channel_id,
                telegram_username=telegram_username,
                is_active=True,
                total_signals=0
            )
            
            try:
                session.add(trader)
                session.flush()
                logger.info(f"👤 Trader created: {trader.name} (ID: {trader.id})")
                return trader.id
                
            except IntegrityError:
                session.rollback()
                # Трейдер уже существует
                existing = session.query(Trader).filter(Trader.name == name).first()
                if existing:
                    return existing.id
                raise
    
    def get_trader_stats(self, trader_id: int) -> Optional[Dict]:
        """
        Получить статистику трейдера
        
        Returns:
            Dict: статистика трейдера или None
        """
        with self.session() as session:
            trader = session.query(Trader).filter(Trader.id == trader_id).first()
            
            if not trader:
                return None
            
            # Считаем статистику по сигналам
            total_signals = session.query(ParsedSignal).filter(
                ParsedSignal.trader_id == trader_id
            ).count()
            
            # Статистика по результатам
            results_query = session.query(SignalResult).join(ParsedSignal).filter(
                ParsedSignal.trader_id == trader_id
            )
            
            total_results = results_query.count()
            closed_results = results_query.filter(SignalResult.status == 'closed').all()
            
            win_count = len([r for r in closed_results if r.profit_loss_pct and r.profit_loss_pct > 0])
            win_rate = (win_count / len(closed_results) * 100) if closed_results else 0
            
            avg_profit = sum(float(r.profit_loss_pct or 0) for r in closed_results) / len(closed_results) if closed_results else 0
            
            return {
                'trader_id': trader.id,
                'name': trader.name,
                'telegram_username': trader.telegram_username,
                'channel_id': trader.channel_id,
                'is_active': trader.is_active,
                'total_signals': total_signals,
                'total_results': total_results,
                'closed_results': len(closed_results),
                'win_rate': round(win_rate, 2),
                'avg_profit_pct': round(avg_profit, 2),
                'first_signal_at': trader.first_signal_at,
                'last_signal_at': trader.last_signal_at
            }
    
    def get_all_traders(self, active_only: bool = True) -> List[Dict]:
        """
        Получить список всех трейдеров
        
        Returns:
            List[Dict]: список трейдеров
        """
        with self.session() as session:
            query = session.query(Trader)
            
            if active_only:
                query = query.filter(Trader.is_active == True)
            
            traders = query.order_by(asc(Trader.name)).all()
            
            return [
                {
                    'id': trader.id,
                    'name': trader.name,
                    'telegram_username': trader.telegram_username,
                    'channel_id': trader.channel_id,
                    'is_active': trader.is_active,
                    'total_signals': trader.total_signals,
                    'win_rate': float(trader.win_rate) if trader.win_rate else None,
                    'avg_profit_pct': float(trader.avg_profit_pct) if trader.avg_profit_pct else None
                }
                for trader in traders
            ]
    
    # ===== РЕЗУЛЬТАТЫ СИГНАЛОВ =====
    
    def save_signal_result(self, signal_id: str, result_data: Dict) -> str:
        """
        Сохранить результат отслеживания сигнала
        
        Returns:
            str: UUID результата
        """
        with self.session() as session:
            result = SignalResult(
                signal_id=signal_id,
                planned_entry_price=result_data.get('planned_entry_price'),
                actual_entry_price=result_data.get('actual_entry_price'),
                exit_price=result_data.get('exit_price'),
                profit_loss_pct=result_data.get('profit_loss_pct'),
                profit_loss_abs=result_data.get('profit_loss_abs'),
                entry_time=result_data.get('entry_time'),
                exit_time=result_data.get('exit_time'),
                duration_minutes=result_data.get('duration_minutes'),
                status=result_data.get('status', 'active'),
                exit_reason=result_data.get('exit_reason')
            )
            
            session.add(result)
            session.flush()
            
            logger.debug(f"📊 Signal result saved: {result.id}")
            return str(result.id)
    
    def update_signal_result(self, result_id: str, updates: Dict):
        """Обновить результат сигнала"""
        with self.session() as session:
            session.query(SignalResult).filter(SignalResult.id == result_id).update(updates)
    
    def get_active_signals(self) -> List[Dict]:
        """
        Получить активные сигналы для отслеживания
        
        Returns:
            List[Dict]: активные сигналы с результатами
        """
        with self.session() as session:
            query = session.query(ParsedSignal, SignalResult).outerjoin(SignalResult).filter(
                or_(
                    SignalResult.status == 'active',
                    SignalResult.status.is_(None)  # Сигналы без результатов
                )
            )
            
            results = []
            for signal, result in query.all():
                signal_data = {
                    'signal_id': str(signal.id),
                    'timestamp': signal.timestamp,
                    'ticker': signal.ticker,
                    'direction': signal.direction,
                    'target_price': float(signal.target_price) if signal.target_price else None,
                    'stop_loss': float(signal.stop_loss) if signal.stop_loss else None,
                    'take_profit': float(signal.take_profit) if signal.take_profit else None,
                    'trader_id': signal.trader_id,
                    'author': signal.author
                }
                
                if result:
                    signal_data.update({
                        'result_id': str(result.id),
                        'actual_entry_price': float(result.actual_entry_price) if result.actual_entry_price else None,
                        'status': result.status,
                        'entry_time': result.entry_time,
                        'tracking_started_at': result.tracking_started_at
                    })
                
                results.append(signal_data)
            
            return results
    
    # ===== ИНСТРУМЕНТЫ И СВЕЧИ =====
    
    def save_instrument(self, figi: str, ticker: str, name: str, 
                       instrument_type: str = 'share') -> str:
        """
        Сохранить информацию об инструменте
        
        Returns:
            str: FIGI инструмента
        """
        with self.session() as session:
            instrument = Instrument(
                figi=figi,
                ticker=ticker,
                name=name,
                type=instrument_type,
                is_active=True
            )
            
            try:
                session.merge(instrument)  # Используем merge для upsert
                return figi
                
            except Exception as e:
                session.rollback()
                logger.error(f"❌ Error saving instrument {ticker}: {e}")
                raise
    
    def get_instrument_by_ticker(self, ticker: str) -> Optional[Dict]:
        """
        Получить инструмент по тикеру
        
        Returns:
            Dict: данные инструмента или None
        """
        with self.session() as session:
            instrument = session.query(Instrument).filter(
                Instrument.ticker == ticker
            ).first()
            
            if not instrument:
                return None
            
            return {
                'figi': instrument.figi,
                'ticker': instrument.ticker,
                'name': instrument.name,
                'type': instrument.type,
                'currency': instrument.currency,
                'lot': instrument.lot,
                'is_active': instrument.is_active
            }

    # Исправленный метод save_candles для core/database/database.py

    def save_candles(self, candles_data, figi: str = None, interval: str = None) -> Dict:
        """
        Массовое сохранение свечных данных с батчингом для PostgreSQL
        
        Args:
            candles_data: список кортежей (figi, interval, time, open, high, low, close, volume)
                        ИЛИ список словарей {'time': ..., 'open': ..., ...} + figi и interval отдельно
            figi: FIGI инструмента (если candles_data это список словарей)
            interval: интервал (если candles_data это список словарей)
            
        Returns:
            Dict: статистика сохранения
        """
        if not candles_data:
            logger.warning("⚠️ save_candles called with empty data")
            return {'saved': 0, 'errors': 0}
        
        logger.info(f"💾 Attempting to save {len(candles_data)} candles...")
        
        # 🔍 Определяем формат данных
        first_item = candles_data[0]
        is_dict_format = isinstance(first_item, dict)
        
        logger.info(f"📊 Data format: {'dict' if is_dict_format else 'tuple'}")
        
        if is_dict_format and (not figi or not interval):
            logger.error("❌ Dict format requires figi and interval parameters")
            return {'saved': 0, 'errors': len(candles_data)}
        
        with self.session() as session:
            try:
                candles_dicts = []
                errors = 0
                seen_times = set()  # 🆕 Отслеживаем дубликаты по времени
                
                # Обрабатываем данные в правильный формат
                for i, candle in enumerate(candles_data):
                    try:
                        if is_dict_format:
                            # Обработка формата словарей (от Tinkoff API)
                            candle_time = candle['time']
                            
                            # 🆕 ПРОВЕРЯЕМ ДУБЛИКАТЫ ПО ВРЕМЕНИ
                            time_key = (figi, interval, candle_time)
                            if time_key in seen_times:
                                logger.warning(f"⚠️ Skipping duplicate candle at {candle_time}")
                                continue
                            seen_times.add(time_key)
                            
                            candle_dict = {
                                'instrument_id': figi,
                                'interval': interval,
                                'time': candle_time,
                                'open': float(candle['open']),
                                'high': float(candle['high']),
                                'low': float(candle['low']),
                                'close': float(candle['close']),
                                'volume': int(candle.get('volume', 0))
                            }
                        else:
                            # Обработка формата кортежей (старый формат)
                            if len(candle) < 7:
                                logger.error(f"❌ Invalid tuple length at index {i}: {len(candle)}")
                                errors += 1
                                continue
                            
                            # 🆕 ПРОВЕРЯЕМ ДУБЛИКАТЫ ПО ВРЕМЕНИ
                            time_key = (candle[0], candle[1], candle[2])
                            if time_key in seen_times:
                                logger.warning(f"⚠️ Skipping duplicate candle at {candle[2]}")
                                continue
                            seen_times.add(time_key)
                            
                            candle_dict = {
                                'instrument_id': candle[0],
                                'interval': candle[1],
                                'time': candle[2],
                                'open': float(candle[3]),
                                'high': float(candle[4]),
                                'low': float(candle[5]),
                                'close': float(candle[6]),
                                'volume': int(candle[7]) if len(candle) > 7 else 0
                            }
                        
                        candles_dicts.append(candle_dict)
                        
                    except (ValueError, IndexError, TypeError, KeyError) as e:
                        logger.error(f"❌ Error processing candle at index {i}: {e}")
                        errors += 1
                        continue
                
                if not candles_dicts:
                    logger.error("❌ No valid candles to save after processing")
                    return {'saved': 0, 'errors': len(candles_data)}
                
                logger.info(f"✅ Processed {len(candles_dicts)} valid candles (removed {len(candles_data) - len(candles_dicts)} duplicates), {errors} errors")
                
                # 🔥 КЛЮЧЕВОЕ ИСПРАВЛЕНИЕ: УМЕНЬШЕННЫЙ РАЗМЕР БАТЧА
                from sqlalchemy.dialects.postgresql import insert
                
                BATCH_SIZE = 500  # 🆕 Уменьшено с 1000 до 500 для стабильности
                total_saved = 0
                
                # Разбиваем данные на батчи
                for i in range(0, len(candles_dicts), BATCH_SIZE):
                    batch = candles_dicts[i:i + BATCH_SIZE]
                    logger.info(f"📦 Processing batch {i//BATCH_SIZE + 1}/{(len(candles_dicts)-1)//BATCH_SIZE + 1}: {len(batch)} records")
                    
                    try:
                        # Создаем запрос для батча
                        stmt = insert(Candle).values(batch)
                        
                        # ON CONFLICT для избежания дубликатов
                        stmt = stmt.on_conflict_do_update(
                            index_elements=['instrument_id', 'interval', 'time'],
                            set_={
                                'open': stmt.excluded.open,
                                'high': stmt.excluded.high,
                                'low': stmt.excluded.low,
                                'close': stmt.excluded.close,
                                'volume': stmt.excluded.volume
                            }
                        )
                        
                        # Выполняем запрос для батча
                        result = session.execute(stmt)
                        session.commit()  # 🆕 Коммитим каждый батч отдельно
                        total_saved += len(batch)
                        
                        logger.info(f"✅ Saved batch {i//BATCH_SIZE + 1}: {len(batch)} records")
                        
                    except Exception as batch_error:
                        session.rollback()  # 🆕 Откатываем только текущий батч
                        logger.error(f"❌ Error saving batch {i//BATCH_SIZE + 1}: {batch_error}")
                        
                        # 🆕 Пытаемся сохранить по одной записи для диагностики
                        if len(batch) <= 10:  # Только для небольших батчей
                            single_saved = 0
                            for single_candle in batch:
                                try:
                                    single_stmt = insert(Candle).values([single_candle])
                                    single_stmt = single_stmt.on_conflict_do_update(
                                        index_elements=['instrument_id', 'interval', 'time'],
                                        set_={
                                            'open': single_stmt.excluded.open,
                                            'high': single_stmt.excluded.high,
                                            'low': single_stmt.excluded.low,
                                            'close': single_stmt.excluded.close,
                                            'volume': single_stmt.excluded.volume
                                        }
                                    )
                                    session.execute(single_stmt)
                                    session.commit()
                                    single_saved += 1
                                except Exception as single_error:
                                    session.rollback()
                                    logger.error(f"❌ Failed to save single candle: {single_error}")
                                    logger.error(f"❌ Problem candle: {single_candle}")
                            
                            total_saved += single_saved
                            logger.info(f"🔄 Saved {single_saved}/{len(batch)} records individually")
                
                logger.info(f"🎉 Successfully saved {total_saved} candles to database")
                
                # Проверяем что данные сохранились
                if is_dict_format:
                    verification_count = session.query(Candle).filter(
                        Candle.instrument_id == figi,
                        Candle.interval == interval
                    ).count()
                    logger.info(f"🔍 Verification: {verification_count} candles now in DB for {figi}/{interval}")
                
                return {'saved': total_saved, 'errors': errors}
                
            except Exception as e:
                session.rollback()
                logger.error(f"❌ Error saving candles: {e}")
                logger.error(f"❌ Error type: {type(e)}")
                
                # Показываем пример данных при ошибке
                if candles_dicts:
                    logger.error(f"❌ Sample candle_dict: {candles_dicts[0]}")
                
                return {'saved': 0, 'errors': len(candles_data)}

    
    # Исправленный метод async_save_candles для core/database/database.py

    async def async_save_candles(self, candles_data, figi: str = None, interval: str = None) -> Dict:
        """
        Массовое сохранение свечных данных (асинхронно, для вебсокетов)
        
        Args:
            candles_data: список кортежей (figi, interval, time, open, high, low, close, volume)
                        ИЛИ список словарей {'time': ..., 'open': ..., ...} + figi и interval отдельно
            figi: FIGI инструмента (если candles_data это список словарей)
            interval: интервал (если candles_data это список словарей)
            
        Returns:
            Dict: статистика сохранения
        """
        if not candles_data:
            return {'saved': 0, 'errors': 0}
        
        # 🔍 Определяем формат данных
        first_item = candles_data[0]
        is_dict_format = isinstance(first_item, dict)
        
        if is_dict_format and (not figi or not interval):
            logger.error("❌ Dict format requires figi and interval parameters")
            return {'saved': 0, 'errors': len(candles_data)}
        
        async with self.async_session() as session:
            try:
                candles_dicts = []
                errors = 0
                seen_times = set()  # 🆕 Отслеживаем дубликаты по времени
                
                for i, candle in enumerate(candles_data):
                    try:
                        if is_dict_format:
                            # 🆕 Обработка формата словарей (от Tinkoff API)
                            candle_time = candle['time']
                            
                            # 🆕 ПРОВЕРЯЕМ ДУБЛИКАТЫ ПО ВРЕМЕНИ
                            time_key = (figi, interval, candle_time)
                            if time_key in seen_times:
                                logger.warning(f"⚠️ Skipping duplicate async candle at {candle_time}")
                                continue
                            seen_times.add(time_key)
                            
                            candle_dict = {
                                'instrument_id': figi,
                                'interval': interval,
                                'time': candle_time,
                                'open': float(candle['open']),
                                'high': float(candle['high']),
                                'low': float(candle['low']),
                                'close': float(candle['close']),
                                'volume': int(candle.get('volume', 0))
                            }
                        else:
                            # 📄 Обработка формата кортежей (старый формат)
                            if len(candle) < 7:
                                errors += 1
                                continue
                            
                            # 🆕 ПРОВЕРЯЕМ ДУБЛИКАТЫ ПО ВРЕМЕНИ
                            time_key = (candle[0], candle[1], candle[2])
                            if time_key in seen_times:
                                logger.warning(f"⚠️ Skipping duplicate async candle at {candle[2]}")
                                continue
                            seen_times.add(time_key)
                            
                            candle_dict = {
                                'instrument_id': candle[0],
                                'interval': candle[1],
                                'time': candle[2],
                                'open': float(candle[3]),
                                'high': float(candle[4]),
                                'low': float(candle[5]),
                                'close': float(candle[6]),
                                'volume': int(candle[7]) if len(candle) > 7 else 0
                            }
                        
                        candles_dicts.append(candle_dict)
                        
                    except (ValueError, IndexError, TypeError, KeyError) as e:
                        logger.error(f"❌ Error processing async candle at index {i}: {e}")
                        errors += 1
                        continue
                
                if not candles_dicts:
                    return {'saved': 0, 'errors': len(candles_data)}
                
                logger.info(f"✅ Processed {len(candles_dicts)} valid async candles (removed {len(candles_data) - len(candles_dicts)} duplicates)")
                
                # 🆕 БАТЧИНГ ДЛЯ АСИНХРОННОГО МЕТОДА
                from sqlalchemy.dialects.postgresql import insert
                
                BATCH_SIZE = 250  # Меньше для асинхронных операций
                total_saved = 0
                
                for i in range(0, len(candles_dicts), BATCH_SIZE):
                    batch = candles_dicts[i:i + BATCH_SIZE]
                    
                    try:
                        stmt = insert(Candle).values(batch)
                        stmt = stmt.on_conflict_do_update(
                            index_elements=['instrument_id', 'interval', 'time'],
                            set_={
                                'open': stmt.excluded.open,
                                'high': stmt.excluded.high,
                                'low': stmt.excluded.low,
                                'close': stmt.excluded.close,
                                'volume': stmt.excluded.volume
                            }
                        )
                        
                        await session.execute(stmt)
                        await session.commit()  # 🆕 Коммитим каждый батч
                        total_saved += len(batch)
                        
                    except Exception as batch_error:
                        await session.rollback()
                        logger.error(f"❌ Error saving async batch: {batch_error}")
                        continue
                
                return {'saved': total_saved, 'errors': errors}
                
            except Exception as e:
                await session.rollback()
                logger.error(f"❌ Error saving candles async: {e}")
                return {'saved': 0, 'errors': len(candles_data)}

    def get_candles(self, figi: str, interval: str, 
                    from_time: datetime = None, to_time: datetime = None,
                    limit: int = None) -> List[Dict]:  # ✅ limit теперь опциональный
            """
            Получить свечные данные (синхронно) - БЕЗ ОБЯЗАТЕЛЬНОГО ЛИМИТА
            
            Returns:
                List[Dict]: список свечей (ВСЕ доступные по умолчанию)
            """
            with self.session() as session:
                query = session.query(Candle).filter(
                    Candle.instrument_id == figi,
                    Candle.interval == interval
                )
                
                if from_time:
                    query = query.filter(Candle.time >= from_time)
                
                if to_time:
                    query = query.filter(Candle.time <= to_time)
                
                query = query.order_by(asc(Candle.time))
                
                # ✅ Применяем лимит только если он явно указан
                if limit is not None and limit > 0:
                    query = query.limit(limit)
                
                candles = query.all()
                
                return [
                    {
                        'time': candle.time,
                        'open': float(candle.open),
                        'high': float(candle.high),
                        'low': float(candle.low),
                        'close': float(candle.close),
                        'volume': candle.volume
                    }
                    for candle in candles
                ]
    
    async def async_get_candles(self, figi: str, interval: str, 
                                from_time: datetime = None, to_time: datetime = None,
                                limit: int = None) -> List[Dict]:  # ✅ limit опциональный
            """
            Получить свечные данные (асинхронно) - БЕЗ ОБЯЗАТЕЛЬНОГО ЛИМИТА
            
            Returns:
                List[Dict]: список свечей (ВСЕ доступные по умолчанию)
            """
            async with self.async_session() as session:
                from sqlalchemy import select
                
                query = select(Candle).filter(
                    Candle.instrument_id == figi,
                    Candle.interval == interval
                )
                
                if from_time:
                    query = query.filter(Candle.time >= from_time)
                
                if to_time:
                    query = query.filter(Candle.time <= to_time)
                
                query = query.order_by(asc(Candle.time))
                
                if limit is not None and limit > 0:
                    query = query.limit(limit)
                
                result = await session.execute(query)
                candles = result.scalars().all()
                
                return [
                    {
                        'time': candle.time,
                        'open': float(candle.open),
                        'high': float(candle.high),
                        'low': float(candle.low),
                        'close': float(candle.close),
                        'volume': candle.volume
                    }
                    for candle in candles
                ]

    
    # ===== СТАТИСТИКА =====
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Получить общую статистику системы
        
        Returns:
            Dict: статистика по всем таблицам
        """
        with self.session() as session:
            stats = {
                'messages': {
                    'total': session.query(RawMessage).count(),
                    'processed': session.query(RawMessage).filter(RawMessage.is_processed == True).count(),
                    'unprocessed': session.query(RawMessage).filter(RawMessage.is_processed == False).count()
                },
                'signals': {
                    'total': session.query(ParsedSignal).count(),
                    'unique_tickers': session.query(ParsedSignal.ticker).distinct().count(),
                    'last_24h': session.query(ParsedSignal).filter(
                        ParsedSignal.timestamp >= datetime.now() - timedelta(hours=24)
                    ).count()
                },
                'traders': {
                    'total': session.query(Trader).count(),
                    'active': session.query(Trader).filter(Trader.is_active == True).count()
                },
                'results': {
                    'total': session.query(SignalResult).count(),
                    'active': session.query(SignalResult).filter(SignalResult.status == 'active').count(),
                    'closed': session.query(SignalResult).filter(SignalResult.status == 'closed').count()
                },
                'instruments': session.query(Instrument).count(),
                'candles': session.query(Candle).count()
            }
            
            return stats
    
    def health_check(self) -> Dict[str, Any]:
        """
        Проверка здоровья БД
        
        Returns:
            Dict: статус подключения и основные метрики
        """
        try:
            with self.session() as session:
                session.execute("SELECT 1")
                
                return {
                    'status': 'healthy',
                    'database_url': self._mask_url(self.database_url),
                    'connection': 'ok',
                    'timestamp': datetime.now()
                }
                
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.now()
            }

# core/database/models.py  
"""
SQLAlchemy модели для всех таблиц
"""
import uuid
from datetime import datetime
from sqlalchemy import (
    Column, Integer, BigInteger, String, Text, Boolean, DateTime,
    Numeric, ForeignKey, Index, UniqueConstraint, func
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

class RawMessage(Base):
    """Сырые сообщения из Telegram каналов"""
    __tablename__ = 'raw_messages'
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    channel_id = Column(BigInteger, nullable=False)
    message_id = Column(BigInteger, nullable=False)
    
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    text = Column(Text, nullable=False)
    author = Column(String(100))
    
    is_processed = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
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
    
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Метаданные парсинга
    parser_version = Column(String(20), nullable=False)
    confidence_score = Column(Numeric(3, 2))  # 0.00 - 1.00
    
    # Канал и автор
    channel_id = Column(BigInteger, nullable=False)
    trader_id = Column(Integer, ForeignKey('traders.id'), nullable=True)
    author = Column(String(100))
    
    # Исходный текст
    original_text = Column(Text, nullable=False)
    
    # Основные торговые данные
    ticker = Column(String(10), nullable=False, index=True)
    figi = Column(String(12), nullable=True)
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

class Trader(Base):
    """Профили трейдеров для отслеживания статистики"""
    __tablename__ = 'traders'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    telegram_username = Column(String(100))
    channel_id = Column(BigInteger, nullable=False)
    
    # Метаданные
    is_active = Column(Boolean, default=True)
    first_signal_at = Column(DateTime(timezone=True))
    last_signal_at = Column(DateTime(timezone=True))
    total_signals = Column(Integer, default=0)
    
    # Кешированная статистика
    win_rate = Column(Numeric(5, 2))
    avg_profit_pct = Column(Numeric(8, 4))
    max_drawdown_pct = Column(Numeric(8, 4))
    sharpe_ratio = Column(Numeric(6, 3))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
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
    
    # Цены исполнения
    planned_entry_price = Column(Numeric(12, 4))
    actual_entry_price = Column(Numeric(12, 4))
    exit_price = Column(Numeric(12, 4))
    
    # Результаты
    profit_loss_pct = Column(Numeric(8, 4))
    profit_loss_abs = Column(Numeric(12, 4))
    
    # Временные метки
    entry_time = Column(DateTime(timezone=True))
    exit_time = Column(DateTime(timezone=True))
    duration_minutes = Column(Integer)
    
    # Статус позиции
    status = Column(String(20), default='active')  # active, closed, stopped, expired
    exit_reason = Column(String(50))  # take_profit, stop_loss, manual, timeout
    
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

class Instrument(Base):
    """Торговые инструменты"""
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