# Технические индикаторы

Реализация основных технических индикаторов для анализа торговых данных.

## Поддерживаемые индикаторы

### 1. OBV (On-Balance Volume)
Индикатор накопления/распределения объема.
- **Рост OBV**: Сигнализирует о притоке денег (накопление)
- **Падение OBV**: Сигнализирует об оттоке денег (распределение)

### 2. MACD (Moving Average Convergence Divergence)
Индикатор импульса, показывающий отношение между двумя скользящими средними.

Компоненты:
- **MACD линия**: Разница между быстрой EMA (12) и медленной EMA (26)
- **Сигнальная линия**: EMA(9) от MACD линии
- **Гистограмма**: Разница между MACD и сигнальной линией

Сигналы:
- **Бычье пересечение**: MACD пересекает сигнальную линию снизу вверх
- **Медвежье пересечение**: MACD пересекает сигнальную линию сверху вниз

### 3. RSI (Relative Strength Index)
Осциллятор импульса, измеряющий скорость и величину направленных ценовых движений.

Значения: 0-100
- **RSI > 70**: Перекупленность (возможна коррекция вниз)
- **RSI < 30**: Перепроданность (возможен отскок вверх)
- **RSI 30-70**: Нейтральная зона

### 4. Bollinger Bands
Индикатор волатильности, состоящий из трех линий.

Компоненты:
- **Средняя линия**: SMA(20)
- **Верхняя полоса**: SMA + (2 × стандартное отклонение)
- **Нижняя полоса**: SMA - (2 × стандартное отклонение)

Сигналы:
- **Цена у верхней границы**: Возможна перекупленность
- **Цена у нижней границы**: Возможна перепроданность
- **Узкие полосы**: Низкая волатильность, возможен сильный ход
- **Широкие полосы**: Высокая волатильность

## Использование на бэкенде (Python)

### Базовое использование

```python
import pandas as pd
from tbot.analysis.technical_indicators import TechnicalIndicators

# Подготовка данных
candles_data = [
    {'time': '2024-01-01 10:00', 'open': 100, 'high': 105, 'low': 99, 'close': 103, 'volume': 1000},
    {'time': '2024-01-01 10:05', 'open': 103, 'high': 107, 'low': 102, 'close': 106, 'volume': 1500},
    # ... больше данных
]

df = pd.DataFrame(candles_data)

# Вычисление всех индикаторов
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

# Получение торговых сигналов
signals = TechnicalIndicators.get_indicator_signals(df_with_indicators)
print(signals)
# Вывод: {'rsi': 'neutral', 'macd': 'bullish', 'bollinger': 'within_bands', 'obv': 'accumulation'}
```

### Вычисление отдельных индикаторов

```python
# RSI
rsi = TechnicalIndicators.calculate_rsi(df, price_col='close', period=14)

# MACD
macd = TechnicalIndicators.calculate_macd(df, price_col='close', fast_period=12, slow_period=26, signal_period=9)
macd_line = macd['macd']
signal_line = macd['signal']
histogram = macd['histogram']

# Bollinger Bands
bb = TechnicalIndicators.calculate_bollinger_bands(df, price_col='close', period=20, std_dev=2.0)
upper_band = bb['upper']
middle_band = bb['middle']
lower_band = bb['lower']

# OBV
obv = TechnicalIndicators.calculate_obv(df, price_col='close', volume_col='volume')
```

### Использование в анализе сигналов

```python
from tbot.core.database import Database
from tbot.analysis.technical_indicators import TechnicalIndicators

def check_signal_with_indicators(ticker: str, signal_direction: str):
    """Проверка сигнала с использованием технических индикаторов"""
    db = Database()

    # Получаем данные свечей
    instrument = db.get_instrument_by_ticker(ticker)
    candles = db.get_candles(instrument['figi'], interval='5min', limit=100)

    # Вычисляем индикаторы
    df = pd.DataFrame(candles)
    df_with_indicators = TechnicalIndicators.calculate_all_indicators(df)

    # Получаем сигналы
    signals = TechnicalIndicators.get_indicator_signals(df_with_indicators)

    # Анализируем подтверждение
    confirmations = 0

    if signal_direction == 'long':
        if signals.get('rsi') == 'oversold':
            confirmations += 1
        if signals.get('macd') in ['bullish', 'bullish_crossover']:
            confirmations += 1
        if signals.get('bollinger') == 'at_lower_band':
            confirmations += 1
        if signals.get('obv') == 'accumulation':
            confirmations += 1
    elif signal_direction == 'short':
        if signals.get('rsi') == 'overbought':
            confirmations += 1
        if signals.get('macd') in ['bearish', 'bearish_crossover']:
            confirmations += 1
        if signals.get('bollinger') == 'at_upper_band':
            confirmations += 1
        if signals.get('obv') == 'distribution':
            confirmations += 1

    return {
        'confirmed': confirmations >= 2,
        'confirmations': confirmations,
        'signals': signals
    }
```

## Использование на фронтенде (JavaScript)

### Через API

```javascript
import axios from 'axios';

// Получение данных с индикаторами через API
async function loadCandlesWithIndicators(ticker, days = 30) {
  const response = await axios.get(`/api/candles/${ticker}/indicators`, {
    params: {
      days: days,
      interval: '5min',
      rsi_period: 14,
      macd_fast: 12,
      macd_slow: 26,
      macd_signal: 9,
      bb_period: 20,
      bb_std: 2.0
    }
  });

  return response.data;
}

// Использование
const data = await loadCandlesWithIndicators('SBER');
console.log('Candles:', data.candles);
console.log('Signals:', data.signals);
```

### Локальное вычисление на клиенте

```javascript
import TechnicalIndicators from '@/utils/technicalIndicators.js';

// Подготовка данных
const candles = [
  { time: 1704106800, open: 100, high: 105, low: 99, close: 103, volume: 1000 },
  { time: 1704107100, open: 103, high: 107, low: 102, close: 106, volume: 1500 },
  // ... больше данных
];

// Вычисление всех индикаторов
const indicators = TechnicalIndicators.calculateAllIndicators(candles, {
  rsiPeriod: 14,
  macdFast: 12,
  macdSlow: 26,
  macdSignal: 9,
  bbPeriod: 20,
  bbStdDev: 2
});

console.log('RSI:', indicators.rsi);
console.log('MACD:', indicators.macd);
console.log('Bollinger Bands Upper:', indicators.bbUpper);

// Получение сигналов
const signals = TechnicalIndicators.getIndicatorSignals(candles, indicators);
console.log('Signals:', signals);
```

### Визуализация с lightweight-charts

```javascript
import { createChart } from 'lightweight-charts';
import TechnicalIndicators from '@/utils/technicalIndicators.js';

// Создание графика
const chart = createChart(document.getElementById('chart'), {
  width: 800,
  height: 400
});

// Основной график свечей
const candlestickSeries = chart.addCandlestickSeries();
candlestickSeries.setData(candles);

// Вычисляем индикаторы
const indicators = TechnicalIndicators.calculateAllIndicators(candles);

// Добавляем Bollinger Bands
const bbUpperSeries = chart.addLineSeries({ color: 'rgba(0, 150, 136, 0.5)' });
const bbMiddleSeries = chart.addLineSeries({ color: 'rgba(0, 150, 136, 1)' });
const bbLowerSeries = chart.addLineSeries({ color: 'rgba(0, 150, 136, 0.5)' });

bbUpperSeries.setData(candles.map((c, i) => ({
  time: c.time,
  value: indicators.bbUpper[i]
})).filter(d => d.value !== null));

bbMiddleSeries.setData(candles.map((c, i) => ({
  time: c.time,
  value: indicators.bbMiddle[i]
})).filter(d => d.value !== null));

bbLowerSeries.setData(candles.map((c, i) => ({
  time: c.time,
  value: indicators.bbLower[i]
})).filter(d => d.value !== null));

// Создаем отдельный график для RSI
const rsiChart = createChart(document.getElementById('rsi-chart'), {
  width: 800,
  height: 150
});

const rsiSeries = rsiChart.addLineSeries({ color: 'rgb(41, 98, 255)' });
rsiSeries.setData(candles.map((c, i) => ({
  time: c.time,
  value: indicators.rsi[i]
})).filter(d => d.value !== null));

// Добавляем уровни перекупленности/перепроданности
const overboughtLine = rsiChart.addLineSeries({
  color: 'rgba(255, 0, 0, 0.5)',
  lineStyle: 2 // пунктир
});
overboughtLine.setData(candles.map(c => ({ time: c.time, value: 70 })));

const oversoldLine = rsiChart.addLineSeries({
  color: 'rgba(0, 255, 0, 0.5)',
  lineStyle: 2
});
oversoldLine.setData(candles.map(c => ({ time: c.time, value: 30 })));
```

## API Endpoints

### GET /api/candles/{ticker}/indicators

Получение свечных данных с вычисленными техническими индикаторами.

**Параметры запроса:**
- `days` (int, optional): Количество дней истории (по умолчанию 30, от 1 до 365)
- `interval` (string, optional): Интервал свечей - '1min', '5min', 'hour', 'day' (по умолчанию '5min')
- `rsi_period` (int, optional): Период RSI (по умолчанию 14, от 2 до 100)
- `macd_fast` (int, optional): Быстрый период MACD (по умолчанию 12, от 2 до 100)
- `macd_slow` (int, optional): Медленный период MACD (по умолчанию 26, от 2 до 100)
- `macd_signal` (int, optional): Период сигнальной линии MACD (по умолчанию 9, от 2 до 100)
- `bb_period` (int, optional): Период Bollinger Bands (по умолчанию 20, от 2 до 100)
- `bb_std` (float, optional): Стандартное отклонение BB (по умолчанию 2.0, от 0.1 до 5.0)

**Пример запроса:**
```
GET /api/candles/SBER/indicators?days=30&interval=5min&rsi_period=14
```

**Пример ответа:**
```json
{
  "ticker": "SBER",
  "figi": "BBG004730N88",
  "interval": "5min",
  "count": 1440,
  "period_days": 30,
  "candles": [
    {
      "time": "2024-01-01T10:00:00Z",
      "open": 100.0,
      "high": 105.0,
      "low": 99.0,
      "close": 103.0,
      "volume": 1000,
      "obv": 1000.0,
      "macd": null,
      "macd_signal": null,
      "macd_histogram": null,
      "rsi": null,
      "bb_upper": null,
      "bb_middle": null,
      "bb_lower": null,
      "bb_bandwidth": null,
      "bb_percent_b": null
    },
    ...
  ],
  "indicators": {
    "rsi_period": 14,
    "macd_fast": 12,
    "macd_slow": 26,
    "macd_signal": 9,
    "bb_period": 20,
    "bb_std": 2.0
  },
  "signals": {
    "rsi": "neutral",
    "macd": "bullish",
    "bollinger": "within_bands",
    "obv": "accumulation"
  }
}
```

## Интеграция с системой консенсуса

Технические индикаторы можно использовать для подтверждения торговых сигналов:

```python
# Пример правила консенсуса с техническими индикаторами
consensus_rule = {
    "name": "Консенсус с подтверждением индикаторов",
    "timeframe_minutes": 30,
    "min_signals": 3,
    "require_technical_confirmation": True,
    "technical_conditions": {
        "long": {
            "rsi": ["oversold", "neutral"],
            "macd": ["bullish", "bullish_crossover"],
            "min_confirmations": 2
        },
        "short": {
            "rsi": ["overbought", "neutral"],
            "macd": ["bearish", "bearish_crossover"],
            "min_confirmations": 2
        }
    }
}
```

## Рекомендации по использованию

1. **Не используйте один индикатор**: Комбинируйте несколько индикаторов для подтверждения сигналов
2. **Учитывайте контекст рынка**: Индикаторы работают по-разному на трендовых и боковых рынках
3. **Настраивайте параметры**: Стандартные параметры могут не подходить для всех инструментов
4. **Комбинируйте с Price Action**: Технический анализ лучше работает в комбинации с анализом ценовых паттернов
5. **Бэктестинг**: Всегда тестируйте стратегии на исторических данных перед использованием

## Примеры торговых стратегий

### Стратегия 1: RSI + MACD
```
LONG сигнал:
- RSI < 30 (перепроданность)
- MACD пересекает сигнальную линию снизу вверх
- Цена выше SMA(20)

SHORT сигнал:
- RSI > 70 (перекупленность)
- MACD пересекает сигнальную линию сверху вниз
- Цена ниже SMA(20)
```

### Стратегия 2: Bollinger Bands + RSI
```
LONG сигнал:
- Цена касается нижней полосы Bollinger Bands
- RSI < 40
- Увеличение OBV (накопление)

SHORT сигнал:
- Цена касается верхней полосы Bollinger Bands
- RSI > 60
- Снижение OBV (распределение)
```

## Производительность

- **Backend**: Вычисление индикаторов для 1000 свечей занимает ~10-20ms
- **Frontend**: Вычисление индикаторов для 1000 свечей занимает ~50-100ms
- **Рекомендация**: Для больших объемов данных используйте вычисление на бэкенде через API
