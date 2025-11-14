"""
Технические индикаторы для анализа торговых данных.
Модуль содержит реализации основных технических индикаторов:
- OBV (On-Balance Volume)
- MACD (Moving Average Convergence Divergence)
- RSI (Relative Strength Index)
- Bollinger Bands
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple


class TechnicalIndicators:
    """
    Класс для вычисления технических индикаторов.
    Может использоваться как на бэкенде для проверки сигналов,
    так и предоставлять данные для фронтенда.
    """

    @staticmethod
    def calculate_obv(df: pd.DataFrame, price_col: str = 'close', volume_col: str = 'volume') -> pd.Series:
        """
        Вычисляет On-Balance Volume (OBV).

        OBV - индикатор накопления/распределения объема.
        Рост OBV сигнализирует о притоке денег, падение - об оттоке.

        Args:
            df: DataFrame с ценовыми данными
            price_col: название колонки с ценой закрытия
            volume_col: название колонки с объемом

        Returns:
            Series с значениями OBV
        """
        if len(df) < 2:
            return pd.Series([0] * len(df), index=df.index)

        obv = pd.Series(0.0, index=df.index)
        obv.iloc[0] = df[volume_col].iloc[0]

        for i in range(1, len(df)):
            if df[price_col].iloc[i] > df[price_col].iloc[i - 1]:
                obv.iloc[i] = obv.iloc[i - 1] + df[volume_col].iloc[i]
            elif df[price_col].iloc[i] < df[price_col].iloc[i - 1]:
                obv.iloc[i] = obv.iloc[i - 1] - df[volume_col].iloc[i]
            else:
                obv.iloc[i] = obv.iloc[i - 1]

        return obv

    @staticmethod
    def calculate_ema(series: pd.Series, period: int) -> pd.Series:
        """
        Вычисляет Exponential Moving Average (EMA).

        Args:
            series: Временной ряд данных
            period: Период для EMA

        Returns:
            Series с значениями EMA
        """
        return series.ewm(span=period, adjust=False).mean()

    @staticmethod
    def calculate_macd(
        df: pd.DataFrame,
        price_col: str = 'close',
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9
    ) -> Dict[str, pd.Series]:
        """
        Вычисляет MACD (Moving Average Convergence Divergence).

        MACD состоит из трех компонентов:
        - MACD линия: разница между быстрой и медленной EMA
        - Сигнальная линия: EMA от MACD линии
        - Гистограмма: разница между MACD и сигнальной линией

        Args:
            df: DataFrame с ценовыми данными
            price_col: название колонки с ценой
            fast_period: период для быстрой EMA (обычно 12)
            slow_period: период для медленной EMA (обычно 26)
            signal_period: период для сигнальной линии (обычно 9)

        Returns:
            Dictionary с ключами 'macd', 'signal', 'histogram'
        """
        prices = df[price_col]

        # Вычисляем быструю и медленную EMA
        ema_fast = TechnicalIndicators.calculate_ema(prices, fast_period)
        ema_slow = TechnicalIndicators.calculate_ema(prices, slow_period)

        # MACD линия
        macd_line = ema_fast - ema_slow

        # Сигнальная линия
        signal_line = TechnicalIndicators.calculate_ema(macd_line, signal_period)

        # Гистограмма
        histogram = macd_line - signal_line

        return {
            'macd': macd_line,
            'signal': signal_line,
            'histogram': histogram
        }

    @staticmethod
    def calculate_rsi(
        df: pd.DataFrame,
        price_col: str = 'close',
        period: int = 14
    ) -> pd.Series:
        """
        Вычисляет Relative Strength Index (RSI).

        RSI - осциллятор импульса, измеряющий скорость и величину
        направленных ценовых движений. Значения от 0 до 100.
        - RSI > 70: перекупленность
        - RSI < 30: перепроданность

        Args:
            df: DataFrame с ценовыми данными
            price_col: название колонки с ценой
            period: период для RSI (обычно 14)

        Returns:
            Series с значениями RSI
        """
        prices = df[price_col]

        # Вычисляем изменения цен
        delta = prices.diff()

        # Отделяем прибыли и убытки
        gains = delta.where(delta > 0, 0.0)
        losses = -delta.where(delta < 0, 0.0)

        # Вычисляем средние прибыли и убытки
        avg_gains = gains.rolling(window=period, min_periods=period).mean()
        avg_losses = losses.rolling(window=period, min_periods=period).mean()

        # Используем EMA для сглаживания после первого периода
        for i in range(period, len(avg_gains)):
            avg_gains.iloc[i] = (avg_gains.iloc[i - 1] * (period - 1) + gains.iloc[i]) / period
            avg_losses.iloc[i] = (avg_losses.iloc[i - 1] * (period - 1) + losses.iloc[i]) / period

        # Вычисляем RS и RSI
        rs = avg_gains / avg_losses
        rsi = 100 - (100 / (1 + rs))

        return rsi

    @staticmethod
    def calculate_bollinger_bands(
        df: pd.DataFrame,
        price_col: str = 'close',
        period: int = 20,
        std_dev: float = 2.0
    ) -> Dict[str, pd.Series]:
        """
        Вычисляет Bollinger Bands.

        Bollinger Bands состоят из трех линий:
        - Средняя линия: SMA
        - Верхняя полоса: SMA + (std_dev * стандартное отклонение)
        - Нижняя полоса: SMA - (std_dev * стандартное отклонение)

        Args:
            df: DataFrame с ценовыми данными
            price_col: название колонки с ценой
            period: период для SMA (обычно 20)
            std_dev: множитель стандартного отклонения (обычно 2)

        Returns:
            Dictionary с ключами 'upper', 'middle', 'lower', 'bandwidth'
        """
        prices = df[price_col]

        # Средняя линия (SMA)
        middle_band = prices.rolling(window=period).mean()

        # Стандартное отклонение
        std = prices.rolling(window=period).std()

        # Верхняя и нижняя полосы
        upper_band = middle_band + (std_dev * std)
        lower_band = middle_band - (std_dev * std)

        # Ширина полос (bandwidth) - полезна для определения волатильности
        bandwidth = (upper_band - lower_band) / middle_band * 100

        # %B - показывает положение цены относительно полос
        percent_b = (prices - lower_band) / (upper_band - lower_band)

        return {
            'upper': upper_band,
            'middle': middle_band,
            'lower': lower_band,
            'bandwidth': bandwidth,
            'percent_b': percent_b
        }

    @staticmethod
    def calculate_sma(series: pd.Series, period: int) -> pd.Series:
        """
        Вычисляет Simple Moving Average (SMA).

        Args:
            series: Временной ряд данных
            period: Период для SMA

        Returns:
            Series с значениями SMA
        """
        return series.rolling(window=period).mean()

    @staticmethod
    def calculate_all_indicators(
        df: pd.DataFrame,
        price_col: str = 'close',
        volume_col: str = 'volume',
        rsi_period: int = 14,
        macd_fast: int = 12,
        macd_slow: int = 26,
        macd_signal: int = 9,
        bb_period: int = 20,
        bb_std: float = 2.0
    ) -> pd.DataFrame:
        """
        Вычисляет все доступные индикаторы и возвращает DataFrame.

        Args:
            df: DataFrame с ценовыми данными
            price_col: название колонки с ценой
            volume_col: название колонки с объемом
            rsi_period: период для RSI
            macd_fast: быстрый период для MACD
            macd_slow: медленный период для MACD
            macd_signal: период сигнальной линии для MACD
            bb_period: период для Bollinger Bands
            bb_std: множитель стандартного отклонения для BB

        Returns:
            DataFrame с исходными данными и всеми индикаторами
        """
        result = df.copy()

        # OBV
        if volume_col in df.columns:
            result['obv'] = TechnicalIndicators.calculate_obv(df, price_col, volume_col)

        # MACD
        macd = TechnicalIndicators.calculate_macd(
            df, price_col, macd_fast, macd_slow, macd_signal
        )
        result['macd'] = macd['macd']
        result['macd_signal'] = macd['signal']
        result['macd_histogram'] = macd['histogram']

        # RSI
        result['rsi'] = TechnicalIndicators.calculate_rsi(df, price_col, rsi_period)

        # Bollinger Bands
        bb = TechnicalIndicators.calculate_bollinger_bands(df, price_col, bb_period, bb_std)
        result['bb_upper'] = bb['upper']
        result['bb_middle'] = bb['middle']
        result['bb_lower'] = bb['lower']
        result['bb_bandwidth'] = bb['bandwidth']
        result['bb_percent_b'] = bb['percent_b']

        return result

    @staticmethod
    def get_indicator_signals(
        df: pd.DataFrame,
        price_col: str = 'close'
    ) -> Dict[str, str]:
        """
        Анализирует индикаторы и возвращает торговые сигналы.

        Args:
            df: DataFrame с индикаторами (должен содержать результаты calculate_all_indicators)
            price_col: название колонки с ценой

        Returns:
            Dictionary с сигналами для каждого индикатора
        """
        signals = {}

        if len(df) < 2:
            return signals

        last_idx = df.index[-1]
        prev_idx = df.index[-2]

        # RSI сигналы
        if 'rsi' in df.columns:
            rsi_current = df.loc[last_idx, 'rsi']
            if not pd.isna(rsi_current):
                if rsi_current > 70:
                    signals['rsi'] = 'overbought'  # Перекупленность
                elif rsi_current < 30:
                    signals['rsi'] = 'oversold'  # Перепроданность
                else:
                    signals['rsi'] = 'neutral'

        # MACD сигналы (пересечение линий)
        if 'macd' in df.columns and 'macd_signal' in df.columns:
            macd_current = df.loc[last_idx, 'macd']
            signal_current = df.loc[last_idx, 'macd_signal']
            macd_prev = df.loc[prev_idx, 'macd']
            signal_prev = df.loc[prev_idx, 'macd_signal']

            if not any(pd.isna([macd_current, signal_current, macd_prev, signal_prev])):
                # Бычье пересечение
                if macd_prev <= signal_prev and macd_current > signal_current:
                    signals['macd'] = 'bullish_crossover'
                # Медвежье пересечение
                elif macd_prev >= signal_prev and macd_current < signal_current:
                    signals['macd'] = 'bearish_crossover'
                elif macd_current > signal_current:
                    signals['macd'] = 'bullish'
                else:
                    signals['macd'] = 'bearish'

        # Bollinger Bands сигналы
        if all(col in df.columns for col in ['bb_upper', 'bb_lower', price_col]):
            price_current = df.loc[last_idx, price_col]
            bb_upper = df.loc[last_idx, 'bb_upper']
            bb_lower = df.loc[last_idx, 'bb_lower']

            if not any(pd.isna([price_current, bb_upper, bb_lower])):
                if price_current >= bb_upper:
                    signals['bollinger'] = 'at_upper_band'  # У верхней границы
                elif price_current <= bb_lower:
                    signals['bollinger'] = 'at_lower_band'  # У нижней границы
                else:
                    signals['bollinger'] = 'within_bands'

        # OBV тренд
        if 'obv' in df.columns and len(df) >= 10:
            obv_current = df.loc[last_idx, 'obv']
            obv_avg = df['obv'].iloc[-10:].mean()

            if not pd.isna(obv_current) and not pd.isna(obv_avg):
                if obv_current > obv_avg * 1.05:
                    signals['obv'] = 'accumulation'  # Накопление
                elif obv_current < obv_avg * 0.95:
                    signals['obv'] = 'distribution'  # Распределение
                else:
                    signals['obv'] = 'neutral'

        return signals
