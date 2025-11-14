#!/usr/bin/env python3
"""
Пример использования технических индикаторов.

Этот скрипт демонстрирует:
1. Вычисление всех технических индикаторов
2. Получение торговых сигналов
3. Анализ подтверждения сигналов
"""

import sys
import os
from pathlib import Path

# Добавляем корневую директорию в путь
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from tbot.analysis.technical_indicators import TechnicalIndicators


def generate_sample_data(num_candles=100, base_price=100.0, trend='sideways'):
    """
    Генерирует примерные данные свечей для тестирования.

    Args:
        num_candles: Количество свечей
        base_price: Базовая цена
        trend: Тип тренда ('up', 'down', 'sideways')

    Returns:
        DataFrame с данными свечей
    """
    np.random.seed(42)

    data = []
    current_price = base_price
    current_time = datetime.now() - timedelta(minutes=5 * num_candles)

    for i in range(num_candles):
        # Генерируем тренд
        if trend == 'up':
            trend_component = 0.1
        elif trend == 'down':
            trend_component = -0.1
        else:  # sideways
            trend_component = 0.0

        # Добавляем случайную волатильность
        volatility = np.random.randn() * 0.5

        # Вычисляем цены
        price_change = trend_component + volatility
        current_price = current_price * (1 + price_change / 100)

        open_price = current_price
        high_price = open_price * (1 + abs(np.random.randn()) * 0.005)
        low_price = open_price * (1 - abs(np.random.randn()) * 0.005)
        close_price = low_price + (high_price - low_price) * np.random.rand()

        volume = np.random.randint(1000, 10000)

        data.append({
            'time': current_time.isoformat(),
            'open': round(open_price, 2),
            'high': round(high_price, 2),
            'low': round(low_price, 2),
            'close': round(close_price, 2),
            'volume': volume
        })

        current_price = close_price
        current_time += timedelta(minutes=5)

    return pd.DataFrame(data)


def print_indicator_values(df_with_indicators, num_last=5):
    """Выводит значения индикаторов для последних свечей."""
    print(f"\n{'='*80}")
    print(f"Последние {num_last} значения индикаторов:")
    print(f"{'='*80}\n")

    # Выбираем последние строки
    last_rows = df_with_indicators.tail(num_last)

    for idx, row in last_rows.iterrows():
        print(f"Свеча #{idx} - {row['time']}")
        print(f"  Цена: O={row['open']:.2f} H={row['high']:.2f} L={row['low']:.2f} C={row['close']:.2f}")
        print(f"  Объем: {row['volume']}")
        print(f"  OBV: {row['obv']:.0f}" if not pd.isna(row['obv']) else "  OBV: N/A")

        if not pd.isna(row['rsi']):
            rsi_status = "Перекупленность" if row['rsi'] > 70 else "Перепроданность" if row['rsi'] < 30 else "Нейтральная зона"
            print(f"  RSI: {row['rsi']:.2f} ({rsi_status})")
        else:
            print(f"  RSI: N/A")

        if not pd.isna(row['macd']):
            print(f"  MACD: {row['macd']:.4f}")
            print(f"  MACD Signal: {row['macd_signal']:.4f}" if not pd.isna(row['macd_signal']) else "  MACD Signal: N/A")
            print(f"  MACD Histogram: {row['macd_histogram']:.4f}" if not pd.isna(row['macd_histogram']) else "  MACD Histogram: N/A")

        if not pd.isna(row['bb_upper']):
            print(f"  Bollinger Bands:")
            print(f"    Верхняя: {row['bb_upper']:.2f}")
            print(f"    Средняя: {row['bb_middle']:.2f}")
            print(f"    Нижняя: {row['bb_lower']:.2f}")
            print(f"    %B: {row['bb_percent_b']:.2f}" if not pd.isna(row['bb_percent_b']) else "    %B: N/A")

        print()


def print_signals(signals):
    """Выводит торговые сигналы."""
    print(f"\n{'='*80}")
    print("ТОРГОВЫЕ СИГНАЛЫ")
    print(f"{'='*80}\n")

    signal_descriptions = {
        'rsi': {
            'overbought': '🔴 RSI: Перекупленность (возможна коррекция вниз)',
            'oversold': '🟢 RSI: Перепроданность (возможен отскок вверх)',
            'neutral': '⚪ RSI: Нейтральная зона'
        },
        'macd': {
            'bullish_crossover': '🟢 MACD: Бычье пересечение (сигнал на покупку)',
            'bearish_crossover': '🔴 MACD: Медвежье пересечение (сигнал на продажу)',
            'bullish': '🟢 MACD: Бычий тренд',
            'bearish': '🔴 MACD: Медвежий тренд'
        },
        'bollinger': {
            'at_upper_band': '🔴 Bollinger: Цена у верхней границы (возможна перекупленность)',
            'at_lower_band': '🟢 Bollinger: Цена у нижней границы (возможна перепроданность)',
            'within_bands': '⚪ Bollinger: Цена в пределах полос'
        },
        'obv': {
            'accumulation': '🟢 OBV: Накопление (приток денег)',
            'distribution': '🔴 OBV: Распределение (отток денег)',
            'neutral': '⚪ OBV: Нейтральный'
        }
    }

    for indicator, signal in signals.items():
        if indicator in signal_descriptions and signal in signal_descriptions[indicator]:
            print(signal_descriptions[indicator][signal])
        else:
            print(f"  {indicator}: {signal}")

    print()


def analyze_trade_opportunity(signals):
    """Анализирует торговые возможности на основе сигналов."""
    print(f"\n{'='*80}")
    print("АНАЛИЗ ТОРГОВЫХ ВОЗМОЖНОСТЕЙ")
    print(f"{'='*80}\n")

    long_confirmations = 0
    short_confirmations = 0

    # Анализ для LONG позиции
    if signals.get('rsi') == 'oversold':
        long_confirmations += 1
        print("✅ RSI поддерживает LONG (перепроданность)")
    elif signals.get('rsi') == 'overbought':
        short_confirmations += 1
        print("✅ RSI поддерживает SHORT (перекупленность)")

    if signals.get('macd') in ['bullish', 'bullish_crossover']:
        long_confirmations += 1
        print("✅ MACD поддерживает LONG")
    elif signals.get('macd') in ['bearish', 'bearish_crossover']:
        short_confirmations += 1
        print("✅ MACD поддерживает SHORT")

    if signals.get('bollinger') == 'at_lower_band':
        long_confirmations += 1
        print("✅ Bollinger Bands поддерживает LONG (цена у нижней границы)")
    elif signals.get('bollinger') == 'at_upper_band':
        short_confirmations += 1
        print("✅ Bollinger Bands поддерживает SHORT (цена у верхней границы)")

    if signals.get('obv') == 'accumulation':
        long_confirmations += 1
        print("✅ OBV поддерживает LONG (накопление)")
    elif signals.get('obv') == 'distribution':
        short_confirmations += 1
        print("✅ OBV поддерживает SHORT (распределение)")

    print(f"\nПодтверждения для LONG: {long_confirmations}/4")
    print(f"Подтверждения для SHORT: {short_confirmations}/4")

    if long_confirmations >= 2:
        print("\n🟢 РЕКОМЕНДАЦИЯ: Рассмотреть LONG позицию")
        print(f"   Уверенность: {long_confirmations}/4 индикатора подтверждают")
    elif short_confirmations >= 2:
        print("\n🔴 РЕКОМЕНДАЦИЯ: Рассмотреть SHORT позицию")
        print(f"   Уверенность: {short_confirmations}/4 индикатора подтверждают")
    else:
        print("\n⚪ РЕКОМЕНДАЦИЯ: Недостаточно подтверждений для входа в позицию")
        print("   Дождитесь более четких сигналов")

    print()


def main():
    """Основная функция примера."""
    print("="*80)
    print("ПРИМЕР ИСПОЛЬЗОВАНИЯ ТЕХНИЧЕСКИХ ИНДИКАТОРОВ")
    print("="*80)

    # Генерируем тестовые данные
    print("\n1. Генерация тестовых данных...")
    df = generate_sample_data(num_candles=100, base_price=100.0, trend='sideways')
    print(f"   ✅ Создано {len(df)} свечей")

    # Вычисляем индикаторы
    print("\n2. Вычисление технических индикаторов...")
    df_with_indicators = TechnicalIndicators.calculate_all_indicators(
        df,
        price_col='close',
        volume_col='volume',
        rsi_period=14,
        macd_fast=12,
        macd_slow=26,
        macd_signal=9,
        bb_period=20,
        bb_std=2.0
    )
    print("   ✅ Индикаторы вычислены")
    print(f"   Колонки: {', '.join(df_with_indicators.columns.tolist())}")

    # Выводим значения последних свечей
    print_indicator_values(df_with_indicators, num_last=3)

    # Получаем торговые сигналы
    print("\n3. Анализ торговых сигналов...")
    signals = TechnicalIndicators.get_indicator_signals(df_with_indicators)
    print_signals(signals)

    # Анализируем торговые возможности
    analyze_trade_opportunity(signals)

    # Демонстрация вычисления отдельных индикаторов
    print(f"\n{'='*80}")
    print("4. ПРИМЕР: Вычисление отдельных индикаторов")
    print(f"{'='*80}\n")

    print("Вычисление только RSI:")
    rsi = TechnicalIndicators.calculate_rsi(df, price_col='close', period=14)
    print(f"  Последнее значение RSI: {rsi.iloc[-1]:.2f}")

    print("\nВычисление только MACD:")
    macd = TechnicalIndicators.calculate_macd(df, price_col='close')
    print(f"  MACD: {macd['macd'].iloc[-1]:.4f}")
    print(f"  Signal: {macd['signal'].iloc[-1]:.4f}")
    print(f"  Histogram: {macd['histogram'].iloc[-1]:.4f}")

    print("\nВычисление только Bollinger Bands:")
    bb = TechnicalIndicators.calculate_bollinger_bands(df, price_col='close')
    print(f"  Верхняя полоса: {bb['upper'].iloc[-1]:.2f}")
    print(f"  Средняя полоса: {bb['middle'].iloc[-1]:.2f}")
    print(f"  Нижняя полоса: {bb['lower'].iloc[-1]:.2f}")

    print("\nВычисление только OBV:")
    obv = TechnicalIndicators.calculate_obv(df, price_col='close', volume_col='volume')
    print(f"  Последнее значение OBV: {obv.iloc[-1]:.0f}")

    print(f"\n{'='*80}")
    print("ПРИМЕР ЗАВЕРШЕН")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    main()
