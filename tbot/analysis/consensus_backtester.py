"""
Система бэктестинга правил консенсуса
Позволяет тестировать правила на исторических данных
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from decimal import Decimal
import time

from sqlalchemy import and_
from core.database.database import Database
from core.database.models import (
    ConsensusRule, ParsedSignal, ConsensusBacktest, Candle, Instrument
)
from analysis.consensus_detector import ConsensusDetector
from utils.datetime_utils import ensure_timezone_aware

logger = logging.getLogger(__name__)


class ConsensusBacktester:
    """
    Бэктестер для правил консенсуса
    Симулирует работу детектора на исторических данных
    """

    def __init__(self, db: Database):
        self.db = db
        self.detector = ConsensusDetector(db)

    def run_backtest(
        self,
        rule_id: int,
        start_date: datetime,
        end_date: datetime,
        tickers: Optional[List[str]] = None,
        take_profit_pct: float = 5.0,  # % для take profit
        stop_loss_pct: float = 3.0,  # % для stop loss
        holding_hours: int = 24  # Время удержания позиции
    ) -> Dict:
        """
        Запускает бэктест для правила консенсуса

        Args:
            rule_id: ID правила
            start_date: Начало периода
            end_date: Конец периода
            tickers: Список тикеров (None = все)
            take_profit_pct: Процент для фиксации прибыли
            stop_loss_pct: Процент для стоп-лосса
            holding_hours: Максимальное время удержания позиции

        Returns:
            Словарь с результатами бэктеста
        """
        start_time = time.time()

        try:
            with self.db.session() as session:
                # Загружаем правило
                rule = session.query(ConsensusRule).filter(
                    ConsensusRule.id == rule_id
                ).first()

                if not rule:
                    raise ValueError(f"Rule {rule_id} not found")

                logger.info(
                    f"🔬 Starting backtest for rule '{rule.name}' "
                    f"from {start_date} to {end_date}"
                )

                # Получаем все сигналы в периоде
                query = session.query(ParsedSignal).filter(
                    and_(
                        ParsedSignal.timestamp >= start_date,
                        ParsedSignal.timestamp <= end_date,
                        ParsedSignal.signal_type == 'entry'
                    )
                )

                if tickers:
                    query = query.filter(ParsedSignal.ticker.in_(tickers))
                elif rule.ticker_filter:
                    tickers = [t.strip() for t in rule.ticker_filter.split(',')]
                    query = query.filter(ParsedSignal.ticker.in_(tickers))

                signals = query.order_by(ParsedSignal.timestamp).all()

                logger.info(f"Found {len(signals)} signals in period")

                # Детектируем консенсусы
                consensus_events = []
                processed_signal_ids = set()

                for signal in signals:
                    if signal.id in processed_signal_ids:
                        continue

                    # Проверяем консенсус для этого сигнала
                    consensus_data = self.detector._find_consensus_window(
                        session, signal,
                        window_minutes=rule.window_minutes,
                        min_traders=rule.min_traders,
                        strict_consensus=rule.strict_consensus,
                        rule=rule
                    )

                    if consensus_data:
                        # Помечаем все сигналы как обработанные
                        for cs in consensus_data['signals']:
                            processed_signal_ids.add(cs.id)

                        consensus_events.append({
                            'ticker': signal.ticker,
                            'direction': consensus_data['direction'],
                            'timestamp': signal.timestamp,
                            'traders_count': len(consensus_data['unique_authors']),
                            'avg_price': consensus_data.get('avg_price'),
                            'signals': consensus_data['signals']
                        })

                logger.info(f"Detected {len(consensus_events)} consensus events")

                # Симулируем торговлю по каждому консенсусу
                results = []
                for event in consensus_events:
                    result = self._simulate_trade(
                        session, event,
                        take_profit_pct=take_profit_pct,
                        stop_loss_pct=stop_loss_pct,
                        holding_hours=holding_hours
                    )
                    if result:
                        results.append(result)

                # Агрегируем результаты
                stats = self._calculate_statistics(results)

                # Сохраняем результаты в БД
                backtest_record = ConsensusBacktest(
                    rule_id=rule_id,
                    start_date=start_date,
                    end_date=end_date,
                    tickers=','.join(tickers) if tickers else None,
                    total_consensus_found=len(consensus_events),
                    profitable_count=stats['profitable_count'],
                    loss_count=stats['loss_count'],
                    win_rate=Decimal(str(stats['win_rate'])),
                    avg_profit_pct=Decimal(str(stats['avg_profit_pct'])),
                    avg_loss_pct=Decimal(str(stats['avg_loss_pct'])),
                    max_profit_pct=Decimal(str(stats['max_profit_pct'])),
                    max_loss_pct=Decimal(str(stats['max_loss_pct'])),
                    total_return_pct=Decimal(str(stats['total_return_pct'])),
                    results_by_ticker=stats['by_ticker'],
                    consensus_details=results,
                    execution_time_seconds=Decimal(str(time.time() - start_time)),
                    status='completed'
                )

                session.add(backtest_record)
                session.commit()

                logger.info(
                    f"✅ Backtest completed: {stats['profitable_count']} wins, "
                    f"{stats['loss_count']} losses, {stats['win_rate']:.1f}% win rate"
                )

                return {
                    'backtest_id': str(backtest_record.id),
                    'stats': stats,
                    'results': results
                }

        except Exception as e:
            logger.error(f"Backtest failed: {e}", exc_info=True)
            raise

    def _simulate_trade(
        self,
        session,
        event: Dict,
        take_profit_pct: float,
        stop_loss_pct: float,
        holding_hours: int
    ) -> Optional[Dict]:
        """
        Симулирует сделку по консенсусу

        Args:
            session: Сессия БД
            event: Событие консенсуса
            take_profit_pct: % для take profit
            stop_loss_pct: % для stop loss
            holding_hours: Максимальное время удержания

        Returns:
            Результат сделки или None
        """
        ticker = event['ticker']
        direction = event['direction']
        entry_time = event['timestamp']

        # Получаем FIGI для тикера
        figi = session.query(Instrument.figi).filter(
            Instrument.ticker == ticker
        ).scalar()

        if not figi:
            logger.debug(f"No FIGI found for {ticker}")
            return None

        # Получаем цену входа (первая свеча после консенсуса)
        entry_candle = session.query(Candle).filter(
            and_(
                Candle.instrument_id == figi,
                Candle.time >= entry_time,
                Candle.interval == 'hour'
            )
        ).order_by(Candle.time).first()

        if not entry_candle:
            logger.debug(f"No entry candle for {ticker} at {entry_time}")
            return None

        entry_price = float(entry_candle.close)

        # Устанавливаем целевые уровни
        if direction == 'long':
            take_profit_price = entry_price * (1 + take_profit_pct / 100)
            stop_loss_price = entry_price * (1 - stop_loss_pct / 100)
        else:  # short
            take_profit_price = entry_price * (1 - take_profit_pct / 100)
            stop_loss_price = entry_price * (1 + stop_loss_pct / 100)

        # Симулируем движение цены
        exit_time = entry_time + timedelta(hours=holding_hours)

        candles = session.query(Candle).filter(
            and_(
                Candle.instrument_id == figi,
                Candle.time > entry_candle.time,
                Candle.time <= exit_time,
                Candle.interval == 'hour'
            )
        ).order_by(Candle.time).all()

        exit_reason = 'timeout'
        exit_price = entry_price
        exit_candle_time = entry_candle.time

        for candle in candles:
            high = float(candle.high)
            low = float(candle.low)
            close = float(candle.close)

            if direction == 'long':
                # Проверяем take profit
                if high >= take_profit_price:
                    exit_price = take_profit_price
                    exit_reason = 'take_profit'
                    exit_candle_time = candle.time
                    break
                # Проверяем stop loss
                if low <= stop_loss_price:
                    exit_price = stop_loss_price
                    exit_reason = 'stop_loss'
                    exit_candle_time = candle.time
                    break
            else:  # short
                # Проверяем take profit
                if low <= take_profit_price:
                    exit_price = take_profit_price
                    exit_reason = 'take_profit'
                    exit_candle_time = candle.time
                    break
                # Проверяем stop loss
                if high >= stop_loss_price:
                    exit_price = stop_loss_price
                    exit_reason = 'stop_loss'
                    exit_candle_time = candle.time
                    break

            exit_price = close
            exit_candle_time = candle.time

        # Вычисляем P&L
        if direction == 'long':
            pnl_pct = ((exit_price - entry_price) / entry_price) * 100
        else:  # short
            pnl_pct = ((entry_price - exit_price) / entry_price) * 100

        return {
            'ticker': ticker,
            'direction': direction,
            'entry_time': entry_time.isoformat(),
            'exit_time': exit_candle_time.isoformat(),
            'entry_price': entry_price,
            'exit_price': exit_price,
            'pnl_pct': round(pnl_pct, 2),
            'exit_reason': exit_reason,
            'traders_count': event['traders_count']
        }

    def _calculate_statistics(self, results: List[Dict]) -> Dict:
        """Вычисляет статистику по результатам"""
        if not results:
            return {
                'profitable_count': 0,
                'loss_count': 0,
                'win_rate': 0,
                'avg_profit_pct': 0,
                'avg_loss_pct': 0,
                'max_profit_pct': 0,
                'max_loss_pct': 0,
                'total_return_pct': 0,
                'by_ticker': {}
            }

        profits = [r for r in results if r['pnl_pct'] > 0]
        losses = [r for r in results if r['pnl_pct'] <= 0]

        profitable_count = len(profits)
        loss_count = len(losses)
        win_rate = (profitable_count / len(results)) * 100 if results else 0

        avg_profit_pct = sum(r['pnl_pct'] for r in profits) / len(profits) if profits else 0
        avg_loss_pct = sum(r['pnl_pct'] for r in losses) / len(losses) if losses else 0

        max_profit_pct = max((r['pnl_pct'] for r in results), default=0)
        max_loss_pct = min((r['pnl_pct'] for r in results), default=0)

        total_return_pct = sum(r['pnl_pct'] for r in results)

        # Статистика по тикерам
        by_ticker = {}
        for result in results:
            ticker = result['ticker']
            if ticker not in by_ticker:
                by_ticker[ticker] = {
                    'count': 0,
                    'profitable': 0,
                    'total_pnl': 0
                }
            by_ticker[ticker]['count'] += 1
            if result['pnl_pct'] > 0:
                by_ticker[ticker]['profitable'] += 1
            by_ticker[ticker]['total_pnl'] += result['pnl_pct']

        return {
            'profitable_count': profitable_count,
            'loss_count': loss_count,
            'win_rate': round(win_rate, 2),
            'avg_profit_pct': round(avg_profit_pct, 2),
            'avg_loss_pct': round(avg_loss_pct, 2),
            'max_profit_pct': round(max_profit_pct, 2),
            'max_loss_pct': round(max_loss_pct, 2),
            'total_return_pct': round(total_return_pct, 2),
            'by_ticker': by_ticker
        }

    def get_backtest_results(self, backtest_id: str) -> Optional[Dict]:
        """Получает результаты бэктеста по ID"""
        try:
            with self.db.session() as session:
                backtest = session.query(ConsensusBacktest).filter(
                    ConsensusBacktest.id == backtest_id
                ).first()

                if not backtest:
                    return None

                return {
                    'id': str(backtest.id),
                    'rule_id': backtest.rule_id,
                    'start_date': backtest.start_date.isoformat(),
                    'end_date': backtest.end_date.isoformat(),
                    'tickers': backtest.tickers,
                    'stats': {
                        'total_consensus_found': backtest.total_consensus_found,
                        'profitable_count': backtest.profitable_count,
                        'loss_count': backtest.loss_count,
                        'win_rate': float(backtest.win_rate) if backtest.win_rate else 0,
                        'avg_profit_pct': float(backtest.avg_profit_pct) if backtest.avg_profit_pct else 0,
                        'avg_loss_pct': float(backtest.avg_loss_pct) if backtest.avg_loss_pct else 0,
                        'max_profit_pct': float(backtest.max_profit_pct) if backtest.max_profit_pct else 0,
                        'max_loss_pct': float(backtest.max_loss_pct) if backtest.max_loss_pct else 0,
                        'total_return_pct': float(backtest.total_return_pct) if backtest.total_return_pct else 0,
                        'by_ticker': backtest.results_by_ticker
                    },
                    'results': backtest.consensus_details,
                    'execution_time': float(backtest.execution_time_seconds) if backtest.execution_time_seconds else 0,
                    'status': backtest.status
                }
        except Exception as e:
            logger.error(f"Error getting backtest results: {e}", exc_info=True)
            return None


# Singleton instance
backtester_instance = None


def get_consensus_backtester(db: Database) -> ConsensusBacktester:
    """Получить экземпляр бэктестера"""
    global backtester_instance
    if backtester_instance is None:
        backtester_instance = ConsensusBacktester(db)
    return backtester_instance
