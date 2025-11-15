"""
Сервис детекции консенсуса трейдеров
Event-driven подход: проверяем консенсус при каждом новом сигнале
MVP версия с заготовкой под V1
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from uuid import UUID
import pandas as pd

from sqlalchemy import and_, func
from core.database.database import Database
from core.database.models import ParsedSignal, ConsensusEvent, ConsensusSignal, Candle
from utils.datetime_utils import now_utc, ensure_timezone_aware
from analysis.technical_indicators import TechnicalIndicators

logger = logging.getLogger(__name__)


class ConsensusDetector:
    """
    Детектор консенсуса трейдеров с гибкой системой правил из БД
    """

    def __init__(self, db: Database):
        self.db = db

        # Дефолтные параметры (fallback если нет правил в БД)
        self.default_window_minutes = 10
        self.default_min_traders = 2
        self.strict_consensus = True

        logger.info("✅ ConsensusDetector initialized with rule-based system")
    
    def check_new_signal_sync(self, signal_id: UUID) -> Optional[Dict]:
        """
        Синхронная версия проверки консенсуса для интеграции в синхронный код
        Использует правила из БД для гибкой настройки

        Args:
            signal_id: UUID нового сигнала

        Returns:
            Dict с информацией о консенсусе если найден, иначе None
        """
        try:
            from core.database.models import ConsensusRule

            with self.db.session() as session:
                signal = session.query(ParsedSignal).filter(
                    ParsedSignal.id == signal_id
                ).first()

                if not signal:
                    logger.warning(f"Signal {signal_id} not found")
                    return None

                if signal.signal_type != 'entry':
                    logger.debug(f"Signal {signal_id} is not entry type, skipping")
                    return None

                existing = session.query(ConsensusSignal).filter(
                    ConsensusSignal.signal_id == signal_id
                ).first()

                if existing:
                    logger.debug(f"Signal {signal_id} already in consensus")
                    return None

                logger.info(f"🔍 Checking consensus for: {signal.ticker} {signal.direction} by {signal.author}")

                # Загружаем активные правила по приоритету
                rules = session.query(ConsensusRule).filter(
                    ConsensusRule.is_active == True
                ).order_by(ConsensusRule.priority.desc()).all()

                if not rules:
                    logger.debug("No active consensus rules found, using defaults")
                    # Fallback на дефолтное правило
                    consensus_data = self._find_consensus_window(
                        session, signal,
                        window_minutes=self.default_window_minutes,
                        min_traders=self.default_min_traders,
                        strict_consensus=self.strict_consensus,
                        rule=None
                    )
                    if consensus_data:
                        consensus_event = self._create_consensus_event(
                            session, signal, consensus_data, rule_id=None
                        )
                        logger.info(
                            f"🔥 CONSENSUS DETECTED (default): {consensus_event.ticker} {consensus_event.direction} "
                            f"- {consensus_event.traders_count} traders"
                        )
                        return self._format_consensus_result(consensus_event)
                    return None

                # Проверяем каждое правило по приоритету
                for rule in rules:
                    # Фильтр по тикеру
                    if rule.ticker_filter:
                        tickers = [t.strip().upper() for t in rule.ticker_filter.split(',')]
                        if signal.ticker.upper() not in tickers:
                            continue

                    # Фильтр по направлению
                    if rule.direction_filter:
                        if signal.direction != rule.direction_filter:
                            continue

                    logger.debug(f"Applying rule: {rule.name} (priority={rule.priority})")

                    consensus_data = self._find_consensus_window(
                        session, signal,
                        window_minutes=rule.window_minutes,
                        min_traders=rule.min_traders,
                        strict_consensus=rule.strict_consensus,
                        rule=rule
                    )

                    if consensus_data:
                        consensus_event = self._create_consensus_event(
                            session, signal, consensus_data, rule_id=rule.id
                        )

                        logger.info(
                            f"🔥 CONSENSUS DETECTED by rule '{rule.name}': {consensus_event.ticker} {consensus_event.direction} "
                            f"- {consensus_event.traders_count} traders in {consensus_event.window_minutes}min"
                        )

                        return self._format_consensus_result(consensus_event)

                return None

        except Exception as e:
            logger.error(f"Error checking signal {signal_id}: {e}", exc_info=True)
            return None

    def _format_consensus_result(self, consensus_event: ConsensusEvent) -> Dict:
        """Форматирование результата консенсуса"""
        return {
            'consensus_id': str(consensus_event.id),
            'ticker': consensus_event.ticker,
            'direction': consensus_event.direction,
            'traders_count': consensus_event.traders_count,
            'window_minutes': consensus_event.window_minutes,
            'strength': consensus_event.consensus_strength,
            'rule_id': consensus_event.rule_id
        }

    async def check_new_signal(self, signal_id: UUID) -> Optional[Dict]:
        """
        Event-driven проверка: анализируем окно вокруг нового сигнала (async версия)

        Args:
            signal_id: UUID нового сигнала

        Returns:
            Dict с информацией о консенсусе если найден, иначе None
        """
        return self.check_new_signal_sync(signal_id)
    
    def _find_consensus_window(self, session, signal: ParsedSignal,
                               window_minutes: int, min_traders: int,
                               strict_consensus: bool, rule) -> Optional[Dict]:
        """Ищем консенсус в окне вокруг сигнала с параметрами из правила"""
        ticker = signal.ticker
        direction = signal.direction
        signal_time = signal.timestamp

        window_start = signal_time - timedelta(minutes=window_minutes / 2)
        window_end = signal_time + timedelta(minutes=window_minutes / 2)

        window_signals = session.query(ParsedSignal).filter(
            and_(
                ParsedSignal.ticker == ticker,
                ParsedSignal.signal_type == 'entry',
                ParsedSignal.timestamp >= window_start,
                ParsedSignal.timestamp <= window_end,
                ParsedSignal.direction.isnot(None)
            )
        ).all()

        if len(window_signals) < min_traders:
            logger.debug(
                f"Not enough signals: {len(window_signals)} < {min_traders}"
            )
            return None

        direction_groups = self._group_by_direction(window_signals)

        if strict_consensus:
            if len(direction_groups) > 1:
                logger.debug(f"Mixed directions: {list(direction_groups.keys())}")
                return None

            consensus_direction = list(direction_groups.keys())[0]
            consensus_signals = direction_groups[consensus_direction]
        else:
            consensus_direction = max(direction_groups, key=lambda d: len(direction_groups[d]))
            consensus_signals = direction_groups[consensus_direction]

        unique_authors = set(s.author for s in consensus_signals if s.author)

        if len(unique_authors) < min_traders:
            logger.debug(
                f"Not enough unique authors: {len(unique_authors)} < {min_traders}"
            )
            return None

        # Проверяем условия технических индикаторов, если они заданы
        if rule and rule.indicator_conditions:
            if not self._check_indicator_conditions(session, ticker, signal_time, rule.indicator_conditions):
                logger.debug(f"Indicator conditions not met for {ticker}")
                return None

        return {
            'signals': consensus_signals,
            'direction': consensus_direction,
            'unique_authors': unique_authors,
            'window_start': window_start,
            'window_end': window_end,
            'window_minutes': window_minutes
        }

    def _check_indicator_conditions(self, session, ticker: str, timestamp: datetime,
                                   conditions: Dict) -> bool:
        """
        Проверяет условия технических индикаторов

        Args:
            session: Сессия БД
            ticker: Тикер
            timestamp: Временная метка сигнала
            conditions: Словарь с условиями индикаторов

        Returns:
            True если все условия выполнены, False иначе
        """
        if not conditions:
            return True

        # Загружаем исторические данные (последние 100 свечей)
        candles = session.query(Candle).filter(
            and_(
                Candle.instrument_id.in_(
                    session.query(Candle.instrument_id).join(
                        ParsedSignal, ParsedSignal.figi == Candle.instrument_id
                    ).filter(ParsedSignal.ticker == ticker).limit(1)
                ),
                Candle.time <= timestamp,
                Candle.interval == 'hour'  # Используем часовые свечи
            )
        ).order_by(Candle.time.desc()).limit(100).all()

        if len(candles) < 30:
            logger.debug(f"Not enough candles for {ticker}: {len(candles)}")
            return True  # Пропускаем проверку если недостаточно данных

        # Преобразуем в DataFrame
        df = pd.DataFrame([{
            'time': c.time,
            'open': float(c.open),
            'high': float(c.high),
            'low': float(c.low),
            'close': float(c.close),
            'volume': int(c.volume) if c.volume else 0
        } for c in reversed(candles)])

        df.set_index('time', inplace=True)

        # Вычисляем индикаторы
        df_with_indicators = TechnicalIndicators.calculate_all_indicators(df)
        signals = TechnicalIndicators.get_indicator_signals(df_with_indicators)

        # Проверяем каждое условие
        for indicator_name, condition in conditions.items():
            if not condition.get('enabled', False):
                continue

            if indicator_name == 'rsi':
                rsi_value = df_with_indicators['rsi'].iloc[-1]
                if pd.isna(rsi_value):
                    continue

                min_rsi = condition.get('min')
                max_rsi = condition.get('max')

                if min_rsi is not None and rsi_value < min_rsi:
                    logger.debug(f"RSI {rsi_value} < {min_rsi}")
                    return False
                if max_rsi is not None and rsi_value > max_rsi:
                    logger.debug(f"RSI {rsi_value} > {max_rsi}")
                    return False

            elif indicator_name == 'macd':
                expected_signal = condition.get('signal')
                if expected_signal and signals.get('macd') != expected_signal:
                    logger.debug(f"MACD signal {signals.get('macd')} != {expected_signal}")
                    return False

            elif indicator_name == 'bollinger':
                expected_signal = condition.get('signal')
                if expected_signal and signals.get('bollinger') != expected_signal:
                    logger.debug(f"Bollinger signal {signals.get('bollinger')} != {expected_signal}")
                    return False

            elif indicator_name == 'obv':
                expected_signal = condition.get('signal')
                if expected_signal and signals.get('obv') != expected_signal:
                    logger.debug(f"OBV signal {signals.get('obv')} != {expected_signal}")
                    return False

        logger.debug(f"All indicator conditions met for {ticker}")
        return True
    
    def _group_by_direction(self, signals: List[ParsedSignal]) -> Dict[str, List[ParsedSignal]]:
        """Группируем сигналы по направлению"""
        groups = {}
        for signal in signals:
            direction = signal.direction
            if direction not in groups:
                groups[direction] = []
            groups[direction].append(signal)
        return groups
    
    def _create_consensus_event(self, session, trigger_signal: ParsedSignal,
                               consensus_data: Dict, rule_id: Optional[int]) -> ConsensusEvent:
        """Создаем событие консенсуса с указанием правила"""
        signals = consensus_data['signals']

        signals_sorted = sorted(signals, key=lambda s: s.timestamp)
        first_signal = signals_sorted[0]
        last_signal = signals_sorted[-1]

        prices = [s.target_price for s in signals if s.target_price]

        avg_price = sum(prices) / len(prices) if prices else None
        min_price = min(prices) if prices else None
        max_price = max(prices) if prices else None

        price_spread = None
        if avg_price and min_price and max_price and avg_price > 0:
            price_spread = ((max_price - min_price) / avg_price) * 100

        strength = self._calculate_strength(consensus_data, price_spread)

        consensus_event = ConsensusEvent(
            ticker=trigger_signal.ticker,
            direction=consensus_data['direction'],
            traders_count=len(consensus_data['unique_authors']),
            window_minutes=consensus_data['window_minutes'],
            rule_id=rule_id,
            first_signal_at=first_signal.timestamp,
            last_signal_at=last_signal.timestamp,
            avg_entry_price=avg_price,
            min_entry_price=min_price,
            max_entry_price=max_price,
            price_spread_pct=price_spread,
            consensus_strength=strength,
            status='active',
            consensus_metadata={
                'authors': list(consensus_data['unique_authors']),
                'trigger_signal_id': str(trigger_signal.id),
                'total_signals': len(signals)
            }
        )

        session.add(consensus_event)
        session.flush()

        for signal in signals:
            consensus_signal = ConsensusSignal(
                consensus_id=consensus_event.id,
                signal_id=signal.id,
                is_initiator=(signal.id == trigger_signal.id)
            )
            session.add(consensus_signal)

        session.commit()

        return consensus_event
    
    def _calculate_strength(self, consensus_data: Dict, price_spread: Optional[float]) -> int:
        """
        Рассчитываем силу консенсуса (0-100)
        
        Факторы:
        - Количество трейдеров (больше = лучше)
        - Разброс цен (меньше = лучше)
        - Временная кучность (все сигналы близко по времени = лучше)
        """
        strength = 50
        
        traders_count = len(consensus_data['unique_authors'])
        if traders_count >= 5:
            strength += 20
        elif traders_count >= 4:
            strength += 10
        
        if price_spread is not None:
            if price_spread < 1:
                strength += 15
            elif price_spread < 2:
                strength += 5
            elif price_spread > 5:
                strength -= 10
        
        signals = consensus_data['signals']
        if len(signals) > 1:
            time_span = (max(s.timestamp for s in signals) - min(s.timestamp for s in signals)).total_seconds() / 60
            if time_span < 10:
                strength += 15
            elif time_span < 20:
                strength += 5
        
        return max(0, min(100, strength))
    
    def get_consensus_stats(self, ticker: Optional[str] = None, days_back: int = 30) -> Dict:
        """Получить статистику по консенсусам"""
        try:
            with self.db.session() as session:
                query = session.query(ConsensusEvent)
                
                if ticker:
                    query = query.filter(ConsensusEvent.ticker == ticker)
                
                if days_back:
                    cutoff_date = now_utc() - timedelta(days=days_back)
                    query = query.filter(ConsensusEvent.detected_at >= cutoff_date)
                
                total = query.count()
                
                by_status = {}
                for status in ['active', 'closed', 'expired']:
                    count = query.filter(ConsensusEvent.status == status).count()
                    by_status[status] = count
                
                avg_strength = session.query(func.avg(ConsensusEvent.consensus_strength)).filter(
                    query.whereclause
                ).scalar()
                
                return {
                    'total': total,
                    'by_status': by_status,
                    'avg_strength': float(avg_strength) if avg_strength else 0,
                    'period_days': days_back,
                    'ticker': ticker
                }
                
        except Exception as e:
            logger.error(f"Error getting consensus stats: {e}", exc_info=True)
            return {}


consensus_detector_instance = None

def get_consensus_detector(db: Database) -> ConsensusDetector:
    """Получить экземпляр детектора консенсуса"""
    global consensus_detector_instance
    if consensus_detector_instance is None:
        consensus_detector_instance = ConsensusDetector(db)
    return consensus_detector_instance