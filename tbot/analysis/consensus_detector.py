"""
Сервис детекции консенсуса трейдеров
Event-driven подход: проверяем консенсус при каждом новом сигнале
MVP версия с заготовкой под V1
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from uuid import UUID

from sqlalchemy import and_, func
from core.database.database import Database
from core.database.models import ParsedSignal, ConsensusEvent, ConsensusSignal
from utils.datetime_utils import now_utc, ensure_timezone_aware

logger = logging.getLogger(__name__)


class ConsensusDetector:
    """
    Детектор консенсуса трейдеров
    MVP версия с заготовкой под V1
    """
    
    def __init__(self, db: Database):
        self.db = db

        # Параметры консенсуса (можно настроить)
        self.default_window_minutes = 10  # Окно времени для поиска консенсуса
        self.default_min_traders = 2  # Минимум уникальных трейдеров
        self.strict_consensus = True  # Все сигналы должны быть в одном направлении

        logger.info(
            f"✅ ConsensusDetector initialized: "
            f"window={self.default_window_minutes}min, "
            f"min_traders={self.default_min_traders}, "
            f"strict={self.strict_consensus}"
        )
    
    def check_new_signal_sync(self, signal_id: UUID) -> Optional[Dict]:
        """
        Синхронная версия проверки консенсуса для интеграции в синхронный код

        Args:
            signal_id: UUID нового сигнала

        Returns:
            Dict с информацией о консенсусе если найден, иначе None
        """
        try:
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

                consensus_data = self._find_consensus_window(session, signal)

                if consensus_data:
                    consensus_event = self._create_consensus_event(
                        session,
                        signal,
                        consensus_data
                    )

                    logger.info(
                        f"🔥 CONSENSUS DETECTED: {consensus_event.ticker} {consensus_event.direction} "
                        f"- {consensus_event.traders_count} traders in {consensus_event.window_minutes}min"
                    )

                    return {
                        'consensus_id': str(consensus_event.id),
                        'ticker': consensus_event.ticker,
                        'direction': consensus_event.direction,
                        'traders_count': consensus_event.traders_count,
                        'window_minutes': consensus_event.window_minutes,
                        'strength': consensus_event.consensus_strength
                    }

                return None

        except Exception as e:
            logger.error(f"Error checking signal {signal_id}: {e}", exc_info=True)
            return None

    async def check_new_signal(self, signal_id: UUID) -> Optional[Dict]:
        """
        Event-driven проверка: анализируем окно вокруг нового сигнала (async версия)

        Args:
            signal_id: UUID нового сигнала

        Returns:
            Dict с информацией о консенсусе если найден, иначе None
        """
        return self.check_new_signal_sync(signal_id)
    
    def _find_consensus_window(self, session, signal: ParsedSignal) -> Optional[Dict]:
        """Ищем консенсус в окне вокруг сигнала"""
        ticker = signal.ticker
        direction = signal.direction
        signal_time = signal.timestamp
        
        window_start = signal_time - timedelta(minutes=self.default_window_minutes / 2)
        window_end = signal_time + timedelta(minutes=self.default_window_minutes / 2)
        
        window_signals = session.query(ParsedSignal).filter(
            and_(
                ParsedSignal.ticker == ticker,
                ParsedSignal.signal_type == 'entry',
                ParsedSignal.timestamp >= window_start,
                ParsedSignal.timestamp <= window_end,
                ParsedSignal.direction.isnot(None)
            )
        ).all()
        
        if len(window_signals) < self.default_min_traders:
            logger.debug(
                f"Not enough signals: {len(window_signals)} < {self.default_min_traders}"
            )
            return None
        
        direction_groups = self._group_by_direction(window_signals)
        
        if self.strict_consensus:
            if len(direction_groups) > 1:
                logger.debug(f"Mixed directions: {list(direction_groups.keys())}")
                return None
            
            consensus_direction = list(direction_groups.keys())[0]
            consensus_signals = direction_groups[consensus_direction]
        else:
            consensus_direction = max(direction_groups, key=lambda d: len(direction_groups[d]))
            consensus_signals = direction_groups[consensus_direction]
        
        unique_authors = set(s.author for s in consensus_signals if s.author)
        
        if len(unique_authors) < self.default_min_traders:
            logger.debug(
                f"Not enough unique authors: {len(unique_authors)} < {self.default_min_traders}"
            )
            return None
        
        return {
            'signals': consensus_signals,
            'direction': consensus_direction,
            'unique_authors': unique_authors,
            'window_start': window_start,
            'window_end': window_end
        }
    
    def _group_by_direction(self, signals: List[ParsedSignal]) -> Dict[str, List[ParsedSignal]]:
        """Группируем сигналы по направлению"""
        groups = {}
        for signal in signals:
            direction = signal.direction
            if direction not in groups:
                groups[direction] = []
            groups[direction].append(signal)
        return groups
    
    def _create_consensus_event(self, session, trigger_signal: ParsedSignal, consensus_data: Dict) -> ConsensusEvent:
        """Создаем событие консенсуса"""
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
            window_minutes=self.default_window_minutes,
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