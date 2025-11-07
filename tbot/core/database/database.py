# core/database/database.py - ПЕРЕПИСАННАЯ ВЕРСИЯ с универсальными методами
"""
Класс для работы с PostgreSQL с универсальными методами для нового API
"""
import logging
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta
from contextlib import contextmanager, asynccontextmanager
from utils.datetime_utils import now_utc, utc_from_days_ago, ensure_timezone_aware
from sqlalchemy import create_engine, func, and_, or_, desc, asc, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError

from .models import *

logger = logging.getLogger(__name__)

class Database:
    """Класс для работы с PostgreSQL (sync + async) с универсальными методами"""
    
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
        
        logger.info(f"Database initialized: {self._mask_url(database_url)}")
    
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
        logger.info("Database connections closed")

    # ===== УНИВЕРСАЛЬНЫЕ МЕТОДЫ ДЛЯ СИГНАЛОВ =====
    
    def get_signals_universal(self, 
                             ticker: Optional[str] = None,
                             author: Optional[str] = None, 
                             trader_id: Optional[int] = None,
                             direction: Optional[str] = None,
                             status: Optional[str] = None,
                             from_date: Optional[datetime] = None,
                             to_date: Optional[datetime] = None,
                             limit: int = 50,
                             offset: int = 0,
                             order_by: str = "timestamp",
                             order_desc: bool = True) -> List[Dict]:
        """
        Универсальный метод получения сигналов с множественными фильтрами
        
        Args:
            ticker: фильтр по тикеру
            author: фильтр по автору (имя)
            trader_id: фильтр по ID трейдера
            direction: фильтр по направлению (long/short/exit)
            status: фильтр по статусу сигнала (active/closed/all)
            from_date: сигналы от даты
            to_date: сигналы до даты
            limit: максимальное количество
            offset: смещение для пагинации
            order_by: поле для сортировки
            order_desc: направление сортировки
            
        Returns:
            List[Dict]: список сигналов
        """
        with self.session() as session:
            # Базовый запрос с JOIN для получения статуса из results
            query = session.query(
                ParsedSignal,
                SignalResult.status.label('result_status')
            ).outerjoin(SignalResult, ParsedSignal.id == SignalResult.signal_id)
            
            # Применяем фильтры
            if ticker:
                query = query.filter(ParsedSignal.ticker.ilike(f"%{ticker.upper()}%"))
            
            if author:
                query = query.filter(ParsedSignal.author.ilike(f"%{author}%"))
            
            if trader_id:
                query = query.filter(ParsedSignal.trader_id == trader_id)
            
            if direction and direction.lower() != 'all':
                query = query.filter(ParsedSignal.direction == direction.lower())
            
            if status and status.lower() != 'all':
                if status.lower() == 'active':
                    query = query.filter(
                        or_(
                            SignalResult.status == 'active',
                            SignalResult.status.is_(None)  # Сигналы без результатов тоже активны
                        )
                    )
                else:
                    query = query.filter(SignalResult.status == status.lower())
            
            if from_date:
                query = query.filter(ParsedSignal.timestamp >= from_date)
            
            if to_date:
                query = query.filter(ParsedSignal.timestamp <= to_date)
            
            # Сортировка
            order_field = getattr(ParsedSignal, order_by, ParsedSignal.timestamp)
            if order_desc:
                query = query.order_by(desc(order_field))
            else:
                query = query.order_by(asc(order_field))
            
            # Пагинация
            if offset > 0:
                query = query.offset(offset)
            
            if limit > 0:
                query = query.limit(limit)
            
            results = query.all()
            
            # Форматируем результат
            signals = []
            for signal, result_status in results:
                signal_dict = {
                    'id': str(signal.id),
                    'timestamp': signal.timestamp.isoformat() if signal.timestamp else None,
                    'ticker': signal.ticker,
                    'direction': signal.direction,
                    'signal_type': signal.signal_type,
                    'target_price': float(signal.target_price) if signal.target_price else None,
                    'stop_loss': float(signal.stop_loss) if signal.stop_loss else None,
                    'take_profit': float(signal.take_profit) if signal.take_profit else None,
                    'author': signal.author,
                    'trader_id': signal.trader_id,
                    'confidence_score': float(signal.confidence_score) if signal.confidence_score else None,
                    'original_text': signal.original_text[:200] + "..." if signal.original_text and len(signal.original_text) > 200 else signal.original_text,
                    'parser_version': signal.parser_version,
                    'channel_id': signal.channel_id,
                    'status': result_status or 'unknown'
                }
                signals.append(signal_dict)
            
            logger.info(f"Retrieved {len(signals)} signals with filters: ticker={ticker}, author={author}, direction={direction}")
            return signals
    
    def get_signals_stats(self,
                         ticker: Optional[str] = None,
                         author: Optional[str] = None,
                         trader_id: Optional[int] = None, 
                         direction: Optional[str] = None,
                         status: Optional[str] = None,
                         from_date: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Статистика по сигналам с теми же фильтрами
        
        Returns:
            Dict: статистика по сигналам
        """
        with self.session() as session:
            # Базовый запрос
            query = session.query(ParsedSignal).outerjoin(SignalResult)
            
            # Применяем те же фильтры
            if ticker:
                query = query.filter(ParsedSignal.ticker.ilike(f"%{ticker.upper()}%"))
            
            if author:
                query = query.filter(ParsedSignal.author.ilike(f"%{author}%"))
            
            if trader_id:
                query = query.filter(ParsedSignal.trader_id == trader_id)
            
            if direction and direction.lower() != 'all':
                query = query.filter(ParsedSignal.direction == direction.lower())
            
            if from_date:
                query = query.filter(ParsedSignal.timestamp >= from_date)
            
            # Основная статистика
            total_signals = query.count()
            
            # Статистика по направлениям
            direction_stats = session.query(
                ParsedSignal.direction,
                func.count(ParsedSignal.id).label('count')
            )
            
            # Применяем фильтры и к статистике направлений
            if ticker:
                direction_stats = direction_stats.filter(ParsedSignal.ticker.ilike(f"%{ticker.upper()}%"))
            if author:
                direction_stats = direction_stats.filter(ParsedSignal.author.ilike(f"%{author}%"))
            if trader_id:
                direction_stats = direction_stats.filter(ParsedSignal.trader_id == trader_id)
            if from_date:
                direction_stats = direction_stats.filter(ParsedSignal.timestamp >= from_date)
            
            direction_stats = direction_stats.group_by(ParsedSignal.direction).all()
            
            # Статистика по статусам результатов
            status_query = query.join(SignalResult, isouter=True)
            status_stats = session.query(
                func.coalesce(SignalResult.status, 'no_result').label('status'),
                func.count(ParsedSignal.id).label('count')
            ).select_from(
                ParsedSignal
            ).outerjoin(SignalResult).group_by(
                func.coalesce(SignalResult.status, 'no_result')
            )
            
            # Применяем фильтры к статистике статусов
            if ticker:
                status_stats = status_stats.filter(ParsedSignal.ticker.ilike(f"%{ticker.upper()}%"))
            if author:
                status_stats = status_stats.filter(ParsedSignal.author.ilike(f"%{author}%"))
            if trader_id:
                status_stats = status_stats.filter(ParsedSignal.trader_id == trader_id)
            if from_date:
                status_stats = status_stats.filter(ParsedSignal.timestamp >= from_date)
            
            status_stats = status_stats.all()
            
            # Топ тикеры (если не фильтруем по тикеру)
            top_tickers = []
            if not ticker:
                ticker_stats = session.query(
                    ParsedSignal.ticker,
                    func.count(ParsedSignal.id).label('count')
                )
                
                if author:
                    ticker_stats = ticker_stats.filter(ParsedSignal.author.ilike(f"%{author}%"))
                if trader_id:
                    ticker_stats = ticker_stats.filter(ParsedSignal.trader_id == trader_id)
                if from_date:
                    ticker_stats = ticker_stats.filter(ParsedSignal.timestamp >= from_date)
                
                top_tickers = ticker_stats.group_by(
                    ParsedSignal.ticker
                ).order_by(
                    desc(func.count(ParsedSignal.id))
                ).limit(10).all()
            
            # Топ авторы (если не фильтруем по автору)
            top_authors = []
            if not author:
                author_stats = session.query(
                    ParsedSignal.author,
                    func.count(ParsedSignal.id).label('count')
                )
                
                if ticker:
                    author_stats = author_stats.filter(ParsedSignal.ticker.ilike(f"%{ticker.upper()}%"))
                if trader_id:
                    author_stats = author_stats.filter(ParsedSignal.trader_id == trader_id)
                if from_date:
                    author_stats = author_stats.filter(ParsedSignal.timestamp >= from_date)
                
                top_authors = author_stats.filter(
                    ParsedSignal.author.isnot(None)
                ).group_by(
                    ParsedSignal.author
                ).order_by(
                    desc(func.count(ParsedSignal.id))
                ).limit(10).all()
            
            return {
                'total_signals': total_signals,
                'by_direction': {direction: count for direction, count in direction_stats},
                'by_status': {status: count for status, count in status_stats},
                'top_tickers': [{'ticker': ticker, 'count': count} for ticker, count in top_tickers],
                'top_authors': [{'author': author, 'count': count} for author, count in top_authors],
                'filters_applied': {
                    'ticker': ticker,
                    'author': author,
                    'trader_id': trader_id,
                    'direction': direction,
                    'from_date': from_date.isoformat() if from_date else None
                }
            }
    
    def get_signal_by_id(self, signal_id: str) -> Optional[Dict]:
        """
        Получение детальной информации о сигнале по ID
        
        Args:
            signal_id: UUID сигнала
            
        Returns:
            Dict: детальная информация о сигнале или None
        """
        with self.session() as session:
            signal = session.query(ParsedSignal).filter(
                ParsedSignal.id == signal_id
            ).first()
            
            if not signal:
                return None
            
            # Получаем результат если есть
            result = session.query(SignalResult).filter(
                SignalResult.signal_id == signal_id
            ).first()
            
            # Получаем сырое сообщение если есть
            raw_message = None
            if signal.raw_message_id:
                raw_message = session.query(RawMessage).filter(
                    RawMessage.id == signal.raw_message_id
                ).first()
            
            # Получаем трейдера если есть
            trader = None
            if signal.trader_id:
                trader = session.query(Trader).filter(
                    Trader.id == signal.trader_id
                ).first()
            
            signal_dict = {
                'id': str(signal.id),
                'timestamp': signal.timestamp.isoformat() if signal.timestamp else None,
                'created_at': signal.created_at.isoformat() if signal.created_at else None,
                'parser_version': signal.parser_version,
                'confidence_score': float(signal.confidence_score) if signal.confidence_score else None,
                'channel_id': signal.channel_id,
                'trader_id': signal.trader_id,
                'author': signal.author,
                'original_text': signal.original_text,
                'ticker': signal.ticker,
                'figi': signal.figi,
                'direction': signal.direction,
                'signal_type': signal.signal_type,
                'target_price': float(signal.target_price) if signal.target_price else None,
                'stop_loss': float(signal.stop_loss) if signal.stop_loss else None,
                'take_profit': float(signal.take_profit) if signal.take_profit else None,
                'entry_condition': signal.entry_condition,
                'confidence_level': signal.confidence_level,
                'timeframe': signal.timeframe,
                'views': signal.views,
                'extracted_data': signal.extracted_data
            }
            
            # Добавляем результат если есть
            if result:
                signal_dict['result'] = {
                    'id': str(result.id),
                    'planned_entry_price': float(result.planned_entry_price) if result.planned_entry_price else None,
                    'actual_entry_price': float(result.actual_entry_price) if result.actual_entry_price else None,
                    'exit_price': float(result.exit_price) if result.exit_price else None,
                    'profit_loss_pct': float(result.profit_loss_pct) if result.profit_loss_pct else None,
                    'profit_loss_abs': float(result.profit_loss_abs) if result.profit_loss_abs else None,
                    'entry_time': result.entry_time.isoformat() if result.entry_time else None,
                    'exit_time': result.exit_time.isoformat() if result.exit_time else None,
                    'duration_minutes': result.duration_minutes,
                    'status': result.status,
                    'exit_reason': result.exit_reason,
                    'tracking_started_at': result.tracking_started_at.isoformat() if result.tracking_started_at else None,
                    'last_updated_at': result.last_updated_at.isoformat() if result.last_updated_at else None
                }
            
            # Добавляем информацию о трейдере
            if trader:
                signal_dict['trader'] = {
                    'id': trader.id,
                    'name': trader.name,
                    'telegram_username': trader.telegram_username,
                    'is_active': trader.is_active
                }
            
            # Добавляем информацию о сыром сообщении
            if raw_message:
                signal_dict['raw_message'] = {
                    'id': raw_message.id,
                    'channel_id': raw_message.channel_id,
                    'message_id': raw_message.message_id,
                    'timestamp': raw_message.timestamp.isoformat() if raw_message.timestamp else None,
                    'author': raw_message.author
                }
            
            return signal_dict

    # ===== МЕТОДЫ ДЛЯ ТРЕЙДЕРОВ =====
    
    def get_traders(self, include_stats: bool = False, active_only: bool = True) -> List[Dict]:
        """
        Получение списка трейдеров с опциональной статистикой
        
        Args:
            include_stats: включить статистику по каждому трейдеру
            active_only: только активные трейдеры
            
        Returns:
            List[Dict]: список трейдеров
        """
        with self.session() as session:
            query = session.query(Trader)
            
            if active_only:
                query = query.filter(Trader.is_active == True)
            
            traders = query.order_by(asc(Trader.name)).all()
            
            result = []
            for trader in traders:
                trader_dict = {
                    'id': trader.id,
                    'name': trader.name,
                    'telegram_username': trader.telegram_username,
                    'channel_id': trader.channel_id,
                    'is_active': trader.is_active,
                    'first_signal_at': trader.first_signal_at.isoformat() if trader.first_signal_at else None,
                    'last_signal_at': trader.last_signal_at.isoformat() if trader.last_signal_at else None,
                    'total_signals': trader.total_signals,
                    'win_rate': float(trader.win_rate) if trader.win_rate else None,
                    'avg_profit_pct': float(trader.avg_profit_pct) if trader.avg_profit_pct else None,
                    'created_at': trader.created_at.isoformat() if trader.created_at else None
                }
                
                # Добавляем свежую статистику если запрошена
                if include_stats:
                    stats = self._calculate_trader_stats(session, trader.id)
                    trader_dict['live_stats'] = stats
                
                result.append(trader_dict)
            
            return result
    
    def get_trader_by_id(self, trader_id: int) -> Optional[Dict]:
        """
        Получение детальной информации о трейдере
        
        Args:
            trader_id: ID трейдера
            
        Returns:
            Dict: информация о трейдере или None
        """
        with self.session() as session:
            trader = session.query(Trader).filter(Trader.id == trader_id).first()
            
            if not trader:
                return None
            
            # Получаем статистику
            stats = self._calculate_trader_stats(session, trader_id)
            
            return {
                'id': trader.id,
                'name': trader.name,
                'telegram_username': trader.telegram_username,
                'channel_id': trader.channel_id,
                'is_active': trader.is_active,
                'first_signal_at': trader.first_signal_at.isoformat() if trader.first_signal_at else None,
                'last_signal_at': trader.last_signal_at.isoformat() if trader.last_signal_at else None,
                'total_signals': trader.total_signals,
                'win_rate': float(trader.win_rate) if trader.win_rate else None,
                'avg_profit_pct': float(trader.avg_profit_pct) if trader.avg_profit_pct else None,
                'max_drawdown_pct': float(trader.max_drawdown_pct) if trader.max_drawdown_pct else None,
                'sharpe_ratio': float(trader.sharpe_ratio) if trader.sharpe_ratio else None,
                'created_at': trader.created_at.isoformat() if trader.created_at else None,
                'updated_at': trader.updated_at.isoformat() if trader.updated_at else None,
                'live_stats': stats
            }
    
    def get_trader_stats(self, trader_id: int, from_date: Optional[datetime] = None) -> Optional[Dict]:
        """
        Получение статистики трейдера за период
        
        Args:
            trader_id: ID трейдера
            from_date: начальная дата для расчета статистики
            
        Returns:
            Dict: статистика трейдера или None
        """
        with self.session() as session:
            trader = session.query(Trader).filter(Trader.id == trader_id).first()
            
            if not trader:
                return None
            
            stats = self._calculate_trader_stats(session, trader_id, from_date)
            
            return {
                'trader_id': trader.id,
                'trader_name': trader.name,
                'period_from': from_date.isoformat() if from_date else None,
                'period_to': datetime.utcnow().isoformat(),
                **stats
            }
    
    def _calculate_trader_stats(self, session: Session, trader_id: int, 
                            from_date: Optional[datetime] = None) -> Dict:
        # ДОБАВЬ ЭТИ ЛОГИ
        signals_query = session.query(ParsedSignal).filter(ParsedSignal.trader_id == trader_id)
        
        if from_date:
            signals_query = signals_query.filter(ParsedSignal.timestamp >= from_date)
        
        total_signals = signals_query.count()
        
        logger.info(f"🔍 _calculate_trader_stats: trader_id={trader_id}, from_date={from_date}, total_signals={total_signals}")
        
        # Статистика по результатам
        results_query = session.query(SignalResult).join(ParsedSignal).filter(
            ParsedSignal.trader_id == trader_id
        )
        
        if from_date:
            results_query = results_query.filter(ParsedSignal.timestamp >= from_date)
        
        total_results = results_query.count()
        closed_results = results_query.filter(SignalResult.status == 'closed').all()
        active_results = results_query.filter(SignalResult.status == 'active').count()
        
        # Расчет винрейта и прибыли
        profitable_trades = [r for r in closed_results if r.profit_loss_pct and r.profit_loss_pct > 0]
        win_count = len(profitable_trades)
        loss_count = len(closed_results) - win_count
        
        win_rate = (win_count / len(closed_results) * 100) if closed_results else 0
        
        avg_profit = sum(float(r.profit_loss_pct or 0) for r in closed_results) / len(closed_results) if closed_results else 0
        
        # Статистика по направлениям
        direction_stats = session.query(
            ParsedSignal.direction,
            func.count(ParsedSignal.id).label('count')
        ).filter(ParsedSignal.trader_id == trader_id)
        
        if from_date:
            direction_stats = direction_stats.filter(ParsedSignal.timestamp >= from_date)
        
        direction_stats = direction_stats.group_by(ParsedSignal.direction).all()
        
        # Топ тикеры трейдера
        top_tickers = session.query(
            ParsedSignal.ticker,
            func.count(ParsedSignal.id).label('count')
        ).filter(ParsedSignal.trader_id == trader_id)
        
        if from_date:
            top_tickers = top_tickers.filter(ParsedSignal.timestamp >= from_date)
        
        top_tickers = top_tickers.group_by(ParsedSignal.ticker).order_by(
            desc(func.count(ParsedSignal.id))
        ).limit(5).all()
        
        return {
            'total_signals': total_signals,
            'total_results': total_results,
            'active_results': active_results,
            'closed_results': len(closed_results),
            'win_count': win_count,
            'loss_count': loss_count,
            'win_rate': round(win_rate, 2),
            'avg_profit_pct': round(avg_profit, 2),
            'by_direction': {direction: count for direction, count in direction_stats},
            'top_tickers': [{'ticker': ticker, 'count': count} for ticker, count in top_tickers]
        }

    # ===== МЕТОДЫ ДЛЯ ТИКЕРОВ =====
    
    def get_available_tickers(self, with_stats: bool = True, include_candles_stats: bool = False) -> List[Dict]:
        """
        Получение списка доступных тикеров с статистикой
        
        Args:
            with_stats: включить статистику по сигналам
            include_candles_stats: включить статистику по свечам (медленная операция)
            
        Returns:
            List[Dict]: список тикеров
        """
        with self.session() as session:
            if with_stats:
                # Запрос с агрегацией статистики из сигналов
                ticker_stats = session.query(
                    ParsedSignal.ticker,
                    func.count(ParsedSignal.id).label('signal_count'),
                    func.max(ParsedSignal.timestamp).label('last_signal'),
                    func.min(ParsedSignal.timestamp).label('first_signal'),
                    func.count(func.distinct(ParsedSignal.author)).label('unique_authors')
                ).group_by(
                    ParsedSignal.ticker
                ).order_by(
                    desc(func.count(ParsedSignal.id))
                ).all()
                
                result = []
                for ticker, count, last_signal, first_signal, unique_authors in ticker_stats:
                    ticker_data = {
                        'ticker': ticker,
                        'signal_count': count,
                        'last_signal': ensure_timezone_aware(last_signal).isoformat() if last_signal else None,
                        'first_signal': ensure_timezone_aware(first_signal).isoformat() if first_signal else None,
                        'unique_authors': unique_authors
                    }
                    
                    # Добавляем информацию об инструменте и свечах только если запрошено
                    if include_candles_stats:
                        instrument = session.query(Instrument).filter(
                            Instrument.ticker == ticker
                        ).first()
                        
                        if instrument:
                            ticker_data['name'] = instrument.name
                            ticker_data['figi'] = instrument.figi
                            
                            # Считаем количество свечей
                            candles_count = session.query(Candle).filter(
                                Candle.instrument_id == instrument.figi
                            ).count()
                            
                            ticker_data['candles_count'] = candles_count
                            
                            # Получаем последнюю свечу
                            latest_candle_obj = session.query(Candle).filter(
                                Candle.instrument_id == instrument.figi
                            ).order_by(Candle.time.desc()).first()
                            
                            if latest_candle_obj:
                                ticker_data['latest_candle'] = ensure_timezone_aware(latest_candle_obj.time).isoformat()
                            else:
                                ticker_data['latest_candle'] = None
                        else:
                            ticker_data['name'] = ticker
                            ticker_data['figi'] = None
                            ticker_data['candles_count'] = 0
                            ticker_data['latest_candle'] = None
                    
                    result.append(ticker_data)
                
                return result
            else:
                # Простой список тикеров без статистики
                tickers = session.query(ParsedSignal.ticker).distinct().all()
                return [{'ticker': t[0]} for t in tickers]

    # ===== МЕТОДЫ ДЛЯ СООБЩЕНИЙ =====
    
    def get_unparsed_messages(self, limit: int = 20) -> List[Dict]:
        """
        Получение неразобранных сообщений
        
        Args:
            limit: максимальное количество сообщений
            
        Returns:
            List[Dict]: список неразобранных сообщений
        """
        with self.session() as session:
            messages = session.query(RawMessage).filter(
                RawMessage.is_processed == False
            ).order_by(
                desc(RawMessage.timestamp)
            ).limit(limit).all()
            
            return [
                {
                    'id': msg.id,
                    'channel_id': msg.channel_id,
                    'message_id': msg.message_id,
                    'timestamp': msg.timestamp.isoformat() if msg.timestamp else None,
                    'text': msg.text[:300] + "..." if len(msg.text) > 300 else msg.text,
                    'text_length': len(msg.text),
                    # 'author': msg.author_username, тут нету автора по скольку мы его парсим уже на следующем шаге
                    'collected_at': msg.collected_at.isoformat() if msg.collected_at else None
                }
                for msg in messages
            ]
    
    def get_unparsed_messages_count(self) -> int:
        """
        Получение общего количества неразобранных сообщений
        
        Returns:
            int: количество неразобранных сообщений
        """
        with self.session() as session:
            count = session.query(RawMessage).filter(
                RawMessage.is_processed == False
            ).count()
            
            return count

    def get_raw_messages_sample(self, limit: int = 10) -> List[Dict]:
        """
        Получение образца сырых сообщений для отладки
        
        Args:
            limit: количество сообщений
            
        Returns:
            List[Dict]: образец сообщений
        """
        with self.session() as session:
            messages = session.query(RawMessage).order_by(
                desc(RawMessage.timestamp)
            ).limit(limit).all()
            
            return [
                {
                    'id': msg.id,
                    'channel_id': msg.channel_id,
                    'message_id': msg.message_id,
                    'timestamp': msg.timestamp.isoformat() if msg.timestamp else None,
                    'text': msg.text[:200] + "..." if len(msg.text) > 200 else msg.text,
                    'author': msg.author_username,
                    'is_processed': msg.is_processed
                }
                for msg in messages
            ]

    # ===== СИСТЕМНЫЕ МЕТОДЫ =====
    
    def get_system_statistics(self) -> Dict[str, Any]:
        """
        Получить общую статистику системы
        
        Returns:
            Dict: статистика по всем таблицам
        """
        with self.session() as session:
            # Основная статистика
            total_messages = session.query(RawMessage).count()
            processed_messages = session.query(RawMessage).filter(RawMessage.is_processed == True).count()
            total_signals = session.query(ParsedSignal).count()
            total_traders = session.query(Trader).count()
            active_traders = session.query(Trader).filter(Trader.is_active == True).count()
            total_results = session.query(SignalResult).count()
            active_results = session.query(SignalResult).filter(SignalResult.status == 'active').count()
            
            # Статистика за последние 24 часа
            last_24h = datetime.utcnow() - timedelta(hours=24)
            recent_signals = session.query(ParsedSignal).filter(
                ParsedSignal.timestamp >= last_24h
            ).count()
            recent_messages = session.query(RawMessage).filter(
                RawMessage.timestamp >= last_24h
            ).count()
            
            # Уникальные тикеры
            unique_tickers = session.query(ParsedSignal.ticker).distinct().count()
            
            # Статистика по инструментам и свечам
            total_instruments = session.query(Instrument).count()
            total_candles = session.query(Candle).count()
            
            return {
                'messages': {
                    'total': total_messages,
                    'processed': processed_messages,
                    'unprocessed': total_messages - processed_messages,
                    'last_24h': recent_messages
                },
                'signals': {
                    'total': total_signals,
                    'unique_tickers': unique_tickers,
                    'last_24h': recent_signals
                },
                'traders': {
                    'total': total_traders,
                    'active': active_traders,
                    'inactive': total_traders - active_traders
                },
                'results': {
                    'total': total_results,
                    'active': active_results,
                    'closed': total_results - active_results
                },
                'market_data': {
                    'instruments': total_instruments,
                    'candles': total_candles
                },
                'timestamp': datetime.utcnow().isoformat()
            }
    
    def get_debug_signals_info(self) -> Dict[str, Any]:
        """
        DEBUG: Детальная информация о сигналах для отладки
        
        Returns:
            Dict: отладочная информация
        """
        with self.session() as session:
            # Основная статистика
            total_signals = session.query(ParsedSignal).count()
            
            # Распределение по годам
            year_distribution = session.query(
                func.extract('year', ParsedSignal.timestamp).label('year'),
                func.count(ParsedSignal.id).label('count')
            ).group_by(
                func.extract('year', ParsedSignal.timestamp)
            ).order_by('year').all()
            
            # Топ авторы
            top_authors = session.query(
                ParsedSignal.author,
                func.count(ParsedSignal.id).label('count')
            ).filter(
                ParsedSignal.author.isnot(None)
            ).group_by(
                ParsedSignal.author
            ).order_by(
                desc(func.count(ParsedSignal.id))
            ).limit(10).all()
            
            # Топ тикеры
            top_tickers = session.query(
                ParsedSignal.ticker,
                func.count(ParsedSignal.id).label('count')
            ).group_by(
                ParsedSignal.ticker
            ).order_by(
                desc(func.count(ParsedSignal.id))
            ).limit(10).all()
            
            # Статистика по направлениям
            direction_stats = session.query(
                ParsedSignal.direction,
                func.count(ParsedSignal.id).label('count')
            ).group_by(
                ParsedSignal.direction
            ).all()
            
            # Статистика по парсерам
            parser_stats = session.query(
                ParsedSignal.parser_version,
                func.count(ParsedSignal.id).label('count')
            ).group_by(
                ParsedSignal.parser_version
            ).all()
            
            # Образцы сигналов
            sample_signals = session.query(ParsedSignal).order_by(
                desc(ParsedSignal.timestamp)
            ).limit(5).all()
            
            samples = []
            for signal in sample_signals:
                samples.append({
                    'id': str(signal.id),
                    'timestamp': signal.timestamp.isoformat() if signal.timestamp else None,
                    'ticker': signal.ticker,
                    'direction': signal.direction,
                    'author': signal.author,
                    'confidence_score': float(signal.confidence_score) if signal.confidence_score else None,
                    'original_text': signal.original_text[:100] + "..." if signal.original_text and len(signal.original_text) > 100 else signal.original_text
                })
            
            return {
                'total_signals': total_signals,
                'by_year': [{'year': int(year), 'count': count} for year, count in year_distribution],
                'top_authors': [{'author': author, 'count': count} for author, count in top_authors],
                'top_tickers': [{'ticker': ticker, 'count': count} for ticker, count in top_tickers],
                'by_direction': [{'direction': direction, 'count': count} for direction, count in direction_stats],
                'by_parser': [{'parser': parser, 'count': count} for parser, count in parser_stats],
                'sample_signals': samples,
                'timestamp': datetime.utcnow().isoformat()
            }
    
    def health_check(self) -> Dict[str, Any]:
        """
        Проверка здоровья БД
        
        Returns:
            Dict: статус подключения и основные метрики
        """
        try:
            with self.session() as session:
                # Простой запрос для проверки соединения
                session.execute(text("SELECT 1"))
                
                # Быстрая проверка основных таблиц
                tables_status = {}
                try:
                    tables_status['raw_messages'] = session.query(RawMessage).count()
                except:
                    tables_status['raw_messages'] = 'error'
                
                try:
                    tables_status['parsed_signals'] = session.query(ParsedSignal).count()
                except:
                    tables_status['parsed_signals'] = 'error'
                
                try:
                    tables_status['traders'] = session.query(Trader).count()
                except:
                    tables_status['traders'] = 'error'
                
                return {
                    'status': 'healthy',
                    'database_url': self._mask_url(self.database_url),
                    'connection': 'ok',
                    'tables': tables_status,
                    'timestamp': datetime.utcnow().isoformat()
                }
                
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'error_type': type(e).__name__,
                'timestamp': datetime.utcnow().isoformat()
            }

    # ===== LEGACY МЕТОДЫ (для обратной совместимости) =====
    
    def save_message(self, channel_id: int, message_id: int, 
                    timestamp: datetime, text: str, author: str = None,
                    is_processed: bool = False) -> int:
        """Сохранить сырое сообщение из Telegram"""
        with self.session() as session:
            # Создаем объект с минимальными данными
            message = RawMessage(
                channel_id=channel_id,
                message_id=message_id,
                timestamp=timestamp,
                text=text,
                is_processed=is_processed
                # author_username можно не указывать - он nullable
            )
            
            try:
                session.add(message)
                session.flush()
                logger.debug(f"Message saved: {message.id}")
                return message.id
                
            except IntegrityError:
                session.rollback()
                # Дубликат - возвращаем существующий ID
                existing = session.query(RawMessage).filter(
                    RawMessage.channel_id == channel_id,
                    RawMessage.message_id == message_id
                ).first()
                
                if existing:
                    # Опционально: обновляем текст если изменился
                    if existing.text != text:
                        existing.text = text
                        existing.is_processed = False  # Переразобрать
                        session.flush()
                    return existing.id
                
                raise

    def save_signal(self, signal_data: Dict) -> str:
        """Сохранить торговый сигнал с автоматическим определением trader_id"""
        with self.session() as session:
            trader_id = signal_data.get('trader_id')
            
            if not trader_id:
                author = signal_data.get('author')
                channel_id = signal_data.get('channel_id')
                
                if author:
                    trader = session.query(Trader).filter(
                        Trader.name == author,
                        Trader.is_active == True
                    ).first()
                    
                    if trader:
                        trader_id = trader.id
                        logger.debug(f"Auto-assigned trader_id={trader_id} by author={author}")
                
                if not trader_id and channel_id:
                    trader = session.query(Trader).filter(
                        Trader.channel_id == channel_id,
                        Trader.is_active == True
                    ).first()
                    
                    if trader:
                        trader_id = trader.id
                        logger.debug(f"Auto-assigned trader_id={trader_id} by channel_id={channel_id}")
            
            signal = ParsedSignal(
                raw_message_id=signal_data.get('raw_message_id'),
                timestamp=signal_data['timestamp'],
                parser_version=signal_data.get('parser_version', '1.0'),
                confidence_score=signal_data.get('confidence_score'),
                channel_id=signal_data['channel_id'],
                trader_id=trader_id,
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
            
            logger.debug(f"Signal saved: {signal.id}, trader_id={trader_id}, author={signal_data.get('author')}")
            return str(signal.id)

    def get_signals(self, ticker: str = None, trader_id: int = None,
                   channel_id: int = None, direction: str = None,
                   from_date: datetime = None, limit: int = 100) -> List[Dict]:
        """Получить сигналы с фильтрацией (legacy метод, перенаправляет на новый)"""
        return self.get_signals_universal(
            ticker=ticker,
            trader_id=trader_id,
            direction=direction,
            from_date=from_date,
            limit=limit
        )
    
    def get_messages(self, channel_id: int = None, is_processed: bool = None,
                    from_date: datetime = None, limit: int = 1000) -> List[Dict]:
        """Получить сообщения с фильтрацией (legacy метод)"""
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
                    'author': msg.author_username,
                    'is_processed': msg.is_processed
                }
                for msg in messages
            ]
    
    def mark_message_processed(self, message_id: int):
        """Отметить сообщение как обработанное (legacy метод)"""
        with self.session() as session:
            session.query(RawMessage).filter(RawMessage.id == message_id).update(
                {'is_processed': True}
            )
    
    def get_trader_id_by_channel(self, channel_id: int) -> Optional[int]:
        with self.session() as session:
            trader = session.query(Trader).filter(
                Trader.channel_id == channel_id,
                Trader.is_active == True
            ).first()
            
            return trader.id if trader else None

    def get_all_traders(self, active_only: bool = True) -> List[Dict]:
        """Получить список всех трейдеров (legacy метод, перенаправляет на новый)"""
        return self.get_traders(include_stats=False, active_only=active_only)

    def get_statistics(self) -> Dict[str, Any]:
        """Получить общую статистику системы (legacy метод, перенаправляет на новый)"""
        return self.get_system_statistics()

    # ===== МЕТОДЫ ДЛЯ РАБОТЫ СО СВЕЧАМИ (из оригинального файла) =====
    
    def save_candles(self, candles_data, figi: str = None, interval: str = None) -> Dict:
        """Массовое сохранение свечных данных с батчингом для PostgreSQL"""
        if not candles_data:
            logger.warning("save_candles called with empty data")
            return {'saved': 0, 'errors': 0}
        
        logger.info(f"Attempting to save {len(candles_data)} candles...")
        
        # Определяем формат данных
        first_item = candles_data[0]
        is_dict_format = isinstance(first_item, dict)
        
        logger.info(f"Data format: {'dict' if is_dict_format else 'tuple'}")
        
        if is_dict_format and (not figi or not interval):
            logger.error("Dict format requires figi and interval parameters")
            return {'saved': 0, 'errors': len(candles_data)}
        
        with self.session() as session:
            try:
                candles_dicts = []
                errors = 0
                seen_times = set()  # Отслеживаем дубликаты по времени
                
                # Обрабатываем данные в правильный формат
                for i, candle in enumerate(candles_data):
                    try:
                        if is_dict_format:
                            # Обработка формата словарей (от Tinkoff API)
                            candle_time = candle['time']
                            
                            # ПРОВЕРЯЕМ ДУБЛИКАТЫ ПО ВРЕМЕНИ
                            time_key = (figi, interval, candle_time)
                            if time_key in seen_times:
                                logger.warning(f"Skipping duplicate candle at {candle_time}")
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
                                logger.error(f"Invalid tuple length at index {i}: {len(candle)}")
                                errors += 1
                                continue
                            
                            # ПРОВЕРЯЕМ ДУБЛИКАТЫ ПО ВРЕМЕНИ
                            time_key = (candle[0], candle[1], candle[2])
                            if time_key in seen_times:
                                logger.warning(f"Skipping duplicate candle at {candle[2]}")
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
                        logger.error(f"Error processing candle at index {i}: {e}")
                        errors += 1
                        continue
                
                if not candles_dicts:
                    logger.error("No valid candles to save after processing")
                    return {'saved': 0, 'errors': len(candles_data)}
                
                logger.info(f"Processed {len(candles_dicts)} valid candles, {errors} errors")
                
                # БАТЧИНГ
                BATCH_SIZE = 500  # Уменьшено для стабильности
                total_saved = 0
                
                # Разбиваем данные на батчи
                for i in range(0, len(candles_dicts), BATCH_SIZE):
                    batch = candles_dicts[i:i + BATCH_SIZE]
                    logger.info(f"Processing batch {i//BATCH_SIZE + 1}: {len(batch)} records")
                    
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
                        session.execute(stmt)
                        session.commit()  # Коммитим каждый батч отдельно
                        total_saved += len(batch)
                        
                        logger.info(f"Saved batch {i//BATCH_SIZE + 1}: {len(batch)} records")
                        
                    except Exception as batch_error:
                        session.rollback()  # Откатываем только текущий батч
                        logger.error(f"Error saving batch {i//BATCH_SIZE + 1}: {batch_error}")
                        continue
                
                logger.info(f"Successfully saved {total_saved} candles to database")
                
                return {'saved': total_saved, 'errors': errors}
                
            except Exception as e:
                session.rollback()
                logger.error(f"Error saving candles: {e}")
                return {'saved': 0, 'errors': len(candles_data)}
    
    def get_candles(self, figi: str, interval: str, 
                    from_time: datetime = None, to_time: datetime = None,
                    limit: int = None) -> List[Dict]:
        """Получить свечные данные (БЕЗ ОБЯЗАТЕЛЬНОГО ЛИМИТА)"""
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
            
            # Применяем лимит только если он явно указан
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
    
    # ===== ДОПОЛНИТЕЛЬНЫЕ МЕТОДЫ =====
    
    def create_trader(self, name: str, channel_id: int, 
                     telegram_username: str = None) -> int:
        """Создать профиль трейдера"""
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
                logger.info(f"Trader created: {trader.name} (ID: {trader.id})")
                return trader.id
                
            except IntegrityError:
                session.rollback()
                # Трейдер уже существует
                existing = session.query(Trader).filter(Trader.name == name).first()
                if existing:
                    return existing.id
                raise
    
    def get_total_messages_count(self) -> int:
        """Получить общее количество сырых сообщений"""
        with self.session() as session:
            return session.query(RawMessage).count()

    def save_signal_result(self, signal_id: str, result_data: Dict) -> str:
        """Сохранить результат отслеживания сигнала"""
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
            
            logger.debug(f"Signal result saved: {result.id}")
            return str(result.id)
    
    def update_signal_result(self, result_id: str, updates: Dict):
        """Обновить результат сигнала"""
        with self.session() as session:
            session.query(SignalResult).filter(SignalResult.id == result_id).update(updates)
    
    def get_active_signals(self) -> List[Dict]:
        """Получить активные сигналы для отслеживания"""
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
    
    def save_instrument(self, figi: str, ticker: str, name: str, 
                       instrument_type: str = 'share') -> str:
        """Сохранить информацию об инструменте"""
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
                logger.error(f"Error saving instrument {ticker}: {e}")
                raise
    
    def get_instrument_by_ticker(self, ticker: str) -> Optional[Dict]:
        """Получить инструмент по тикеру"""
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
    # ===== PATTERN MANAGEMENT METHODS =====

    def get_all_patterns(self, category: Optional[str] = None, 
                        active_only: bool = False) -> List[Dict]:
        """
        Получить все паттерны парсинга
        
        Args:
            category: фильтр по категории
            active_only: только активные паттерны
            
        Returns:
            List[Dict]: список паттернов
        """
        with self.session() as session:
            query = session.query(ParsingPattern)
            
            if category:
                query = query.filter(ParsingPattern.category == category)
            
            if active_only:
                query = query.filter(ParsingPattern.is_active == True)
            
            query = query.order_by(
                ParsingPattern.category,
                desc(ParsingPattern.priority),
                ParsingPattern.name
            )
            
            patterns = query.all()
            
            return [
                {
                    'id': p.id,
                    'name': p.name,
                    'category': p.category,
                    'pattern': p.pattern,
                    'priority': p.priority,
                    'is_active': p.is_active,
                    'description': p.description,
                    'created_at': p.created_at.isoformat() if p.created_at else None,
                    'updated_at': p.updated_at.isoformat() if p.updated_at else None
                }
                for p in patterns
            ]

    def get_pattern_by_id(self, pattern_id: int) -> Optional[Dict]:
        """Получить паттерн по ID"""
        with self.session() as session:
            pattern = session.query(ParsingPattern).filter(
                ParsingPattern.id == pattern_id
            ).first()
            
            if not pattern:
                return None
            
            return {
                'id': pattern.id,
                'name': pattern.name,
                'category': pattern.category,
                'pattern': pattern.pattern,
                'priority': pattern.priority,
                'is_active': pattern.is_active,
                'description': pattern.description,
                'created_at': pattern.created_at.isoformat() if pattern.created_at else None,
                'updated_at': pattern.updated_at.isoformat() if pattern.updated_at else None
            }

    def create_pattern(self, pattern_data: Dict) -> int:
        """
        Создать новый паттерн
        
        Args:
            pattern_data: данные паттерна
            
        Returns:
            int: ID созданного паттерна
        """
        with self.session() as session:
            pattern = ParsingPattern(
                name=pattern_data['name'],
                category=pattern_data['category'],
                pattern=pattern_data['pattern'],
                priority=pattern_data.get('priority', 0),
                is_active=pattern_data.get('is_active', True),
                description=pattern_data.get('description')
            )
            
            try:
                session.add(pattern)
                session.flush()
                pattern_id = pattern.id
                return pattern_id
            except IntegrityError:
                session.rollback()
                raise ValueError(f"Pattern with name '{pattern_data['name']}' already exists")

    def update_pattern(self, pattern_id: int, update_data: Dict) -> bool:
        """
        Обновить паттерн
        
        Args:
            pattern_id: ID паттерна
            update_data: данные для обновления
            
        Returns:
            bool: успешность операции
        """
        with self.session() as session:
            pattern = session.query(ParsingPattern).filter(
                ParsingPattern.id == pattern_id
            ).first()
            
            if not pattern:
                return False
            
            for key, value in update_data.items():
                if hasattr(pattern, key) and key not in ['id', 'created_at']:
                    setattr(pattern, key, value)
            
            session.flush()
            return True

    def delete_pattern(self, pattern_id: int) -> bool:
        """
        Удалить паттерн
        
        Args:
            pattern_id: ID паттерна
            
        Returns:
            bool: успешность операции
        """
        with self.session() as session:
            pattern = session.query(ParsingPattern).filter(
                ParsingPattern.id == pattern_id
            ).first()
            
            if not pattern:
                return False
            
            session.delete(pattern)
            session.flush()
            return True

    def toggle_pattern(self, pattern_id: int) -> Optional[bool]:
        """
        Включить/выключить паттерн
        
        Args:
            pattern_id: ID паттерна
            
        Returns:
            Optional[bool]: новое состояние is_active или None если не найден
        """
        with self.session() as session:
            pattern = session.query(ParsingPattern).filter(
                ParsingPattern.id == pattern_id
            ).first()
            
            if not pattern:
                return None
            
            pattern.is_active = not pattern.is_active
            session.flush()
            return pattern.is_active

    def get_patterns_by_category(self, category: str, 
                                active_only: bool = True) -> List[Dict]:
        """
        Получить паттерны определенной категории
        
        Args:
            category: категория паттернов
            active_only: только активные
            
        Returns:
            List[Dict]: список паттернов
        """
        return self.get_all_patterns(category=category, active_only=active_only)

    def get_channels(self, enabled_only: bool = False) -> List[Dict]:
        """
        Получить список всех Telegram каналов

        Args:
            enabled_only: вернуть только включенные каналы

        Returns:
            List[Dict]: список каналов
        """
        with self.session() as session:
            query = session.execute(
                "SELECT id, channel_id, name, username, is_enabled, last_message_id, total_collected, created_at, updated_at "
                "FROM telegram_channels "
                + ("WHERE is_enabled = TRUE " if enabled_only else "")
                + "ORDER BY name ASC"
            )

            channels = []
            for row in query:
                channels.append({
                    'id': row[0],
                    'channel_id': row[1],
                    'name': row[2],
                    'username': row[3],
                    'is_enabled': row[4],
                    'last_message_id': row[5],
                    'total_collected': row[6],
                    'created_at': row[7].isoformat() if row[7] else None,
                    'updated_at': row[8].isoformat() if row[8] else None
                })

            return channels

    def get_channel_by_id(self, channel_id: int) -> Optional[Dict]:
        """
        Получить канал по его Telegram ID

        Args:
            channel_id: ID канала в Telegram

        Returns:
            Dict: данные канала или None
        """
        with self.session() as session:
            result = session.execute(
                "SELECT id, channel_id, name, username, is_enabled, last_message_id, total_collected, created_at, updated_at "
                "FROM telegram_channels WHERE channel_id = :channel_id",
                {"channel_id": channel_id}
            ).fetchone()

            if not result:
                return None

            return {
                'id': result[0],
                'channel_id': result[1],
                'name': result[2],
                'username': result[3],
                'is_enabled': result[4],
                'last_message_id': result[5],
                'total_collected': result[6],
                'created_at': result[7].isoformat() if result[7] else None,
                'updated_at': result[8].isoformat() if result[8] else None
            }

    def create_channel(self, channel_id: int, name: str, username: str = None, is_enabled: bool = True) -> int:
        """
        Создать новый Telegram канал

        Args:
            channel_id: ID канала в Telegram
            name: название канала
            username: username канала (@channel)
            is_enabled: включен ли канал

        Returns:
            int: ID созданной записи
        """
        with self.session() as session:
            try:
                result = session.execute(
                    "INSERT INTO telegram_channels (channel_id, name, username, is_enabled) "
                    "VALUES (:channel_id, :name, :username, :is_enabled) "
                    "RETURNING id",
                    {
                        "channel_id": channel_id,
                        "name": name,
                        "username": username,
                        "is_enabled": is_enabled
                    }
                )
                session.commit()
                record_id = result.fetchone()[0]
                logger.info(f"Channel created: {name} (ID: {record_id}, channel_id: {channel_id})")
                return record_id

            except IntegrityError:
                session.rollback()
                existing = session.execute(
                    "SELECT id FROM telegram_channels WHERE channel_id = :channel_id",
                    {"channel_id": channel_id}
                ).fetchone()

                if existing:
                    logger.warning(f"Channel already exists: {name} (channel_id: {channel_id})")
                    return existing[0]
                raise

    def update_channel(self, channel_id: int, **kwargs) -> bool:
        """
        Обновить данные канала

        Args:
            channel_id: ID канала в Telegram
            **kwargs: поля для обновления (name, username, is_enabled, last_message_id, total_collected)

        Returns:
            bool: успешность операции
        """
        with self.session() as session:
            allowed_fields = ['name', 'username', 'is_enabled', 'last_message_id', 'total_collected']
            updates = {k: v for k, v in kwargs.items() if k in allowed_fields}

            if not updates:
                return False

            set_clause = ", ".join([f"{k} = :{k}" for k in updates.keys()])
            updates['channel_id'] = channel_id

            result = session.execute(
                f"UPDATE telegram_channels SET {set_clause} WHERE channel_id = :channel_id",
                updates
            )
            session.commit()

            if result.rowcount > 0:
                logger.info(f"Channel updated: channel_id={channel_id}, fields={list(updates.keys())}")
                return True
            return False

    def delete_channel(self, channel_id: int) -> bool:
        """
        Удалить канал

        Args:
            channel_id: ID канала в Telegram

        Returns:
            bool: успешность операции
        """
        with self.session() as session:
            result = session.execute(
                "DELETE FROM telegram_channels WHERE channel_id = :channel_id",
                {"channel_id": channel_id}
            )
            session.commit()

            if result.rowcount > 0:
                logger.info(f"Channel deleted: channel_id={channel_id}")
                return True
            return False

    def increment_channel_messages(self, channel_id: int, count: int = 1) -> bool:
        """
        Увеличить счетчик собранных сообщений

        Args:
            channel_id: ID канала в Telegram
            count: количество для добавления

        Returns:
            bool: успешность операции
        """
        with self.session() as session:
            result = session.execute(
                "UPDATE telegram_channels SET total_collected = total_collected + :count "
                "WHERE channel_id = :channel_id",
                {"channel_id": channel_id, "count": count}
            )
            session.commit()
            return result.rowcount > 0

    def update_channel_last_message(self, channel_id: int, message_id: int) -> bool:
        """
        Обновить ID последнего сообщения канала

        Args:
            channel_id: ID канала в Telegram
            message_id: ID последнего сообщения

        Returns:
            bool: успешность операции
        """
        with self.session() as session:
            result = session.execute(
                "UPDATE telegram_channels SET last_message_id = :message_id "
                "WHERE channel_id = :channel_id",
                {"channel_id": channel_id, "message_id": message_id}
            )
            session.commit()
            return result.rowcount > 0

