/**
 * Технические индикаторы для анализа торговых данных.
 * Модуль содержит реализации основных технических индикаторов:
 * - OBV (On-Balance Volume)
 * - MACD (Moving Average Convergence Divergence)
 * - RSI (Relative Strength Index)
 * - Bollinger Bands
 *
 * Используется для визуализации на графиках и клиентского анализа.
 */

export class TechnicalIndicators {
  /**
   * Вычисляет On-Balance Volume (OBV).
   *
   * OBV - индикатор накопления/распределения объема.
   * Рост OBV сигнализирует о притоке денег, падение - об оттоке.
   *
   * @param {Array} data - Массив свечей [{close, volume, ...}, ...]
   * @returns {Array} Массив значений OBV
   */
  static calculateOBV(data) {
    if (!data || data.length < 2) {
      return data.map(() => 0);
    }

    const obv = new Array(data.length);
    obv[0] = data[0].volume || 0;

    for (let i = 1; i < data.length; i++) {
      const currentPrice = data[i].close;
      const previousPrice = data[i - 1].close;
      const currentVolume = data[i].volume || 0;

      if (currentPrice > previousPrice) {
        obv[i] = obv[i - 1] + currentVolume;
      } else if (currentPrice < previousPrice) {
        obv[i] = obv[i - 1] - currentVolume;
      } else {
        obv[i] = obv[i - 1];
      }
    }

    return obv;
  }

  /**
   * Вычисляет Exponential Moving Average (EMA).
   *
   * @param {Array} data - Массив значений
   * @param {number} period - Период для EMA
   * @returns {Array} Массив значений EMA
   */
  static calculateEMA(data, period) {
    if (!data || data.length === 0) {
      return [];
    }

    const ema = new Array(data.length);
    const multiplier = 2 / (period + 1);

    // Первое значение EMA - это SMA
    let sum = 0;
    for (let i = 0; i < period && i < data.length; i++) {
      sum += data[i];
      ema[i] = null;
    }
    ema[period - 1] = sum / period;

    // Вычисляем EMA для остальных значений
    for (let i = period; i < data.length; i++) {
      ema[i] = (data[i] - ema[i - 1]) * multiplier + ema[i - 1];
    }

    return ema;
  }

  /**
   * Вычисляет Simple Moving Average (SMA).
   *
   * @param {Array} data - Массив значений
   * @param {number} period - Период для SMA
   * @returns {Array} Массив значений SMA
   */
  static calculateSMA(data, period) {
    if (!data || data.length === 0) {
      return [];
    }

    const sma = new Array(data.length);

    for (let i = 0; i < data.length; i++) {
      if (i < period - 1) {
        sma[i] = null;
      } else {
        let sum = 0;
        for (let j = 0; j < period; j++) {
          sum += data[i - j];
        }
        sma[i] = sum / period;
      }
    }

    return sma;
  }

  /**
   * Вычисляет MACD (Moving Average Convergence Divergence).
   *
   * MACD состоит из трех компонентов:
   * - MACD линия: разница между быстрой и медленной EMA
   * - Сигнальная линия: EMA от MACD линии
   * - Гистограмма: разница между MACD и сигнальной линией
   *
   * @param {Array} data - Массив свечей [{close, ...}, ...]
   * @param {number} fastPeriod - Период для быстрой EMA (обычно 12)
   * @param {number} slowPeriod - Период для медленной EMA (обычно 26)
   * @param {number} signalPeriod - Период для сигнальной линии (обычно 9)
   * @returns {Object} {macd: [], signal: [], histogram: []}
   */
  static calculateMACD(data, fastPeriod = 12, slowPeriod = 26, signalPeriod = 9) {
    if (!data || data.length === 0) {
      return { macd: [], signal: [], histogram: [] };
    }

    const prices = data.map(d => d.close);

    // Вычисляем быструю и медленную EMA
    const emaFast = this.calculateEMA(prices, fastPeriod);
    const emaSlow = this.calculateEMA(prices, slowPeriod);

    // MACD линия
    const macdLine = emaFast.map((fast, i) => {
      if (fast === null || emaSlow[i] === null) return null;
      return fast - emaSlow[i];
    });

    // Сигнальная линия (EMA от MACD)
    const macdValues = macdLine.filter(v => v !== null);
    const signalEMA = this.calculateEMA(macdValues, signalPeriod);

    // Выравниваем сигнальную линию с исходным массивом
    const signalLine = new Array(data.length).fill(null);
    let signalIndex = 0;
    for (let i = 0; i < macdLine.length; i++) {
      if (macdLine[i] !== null) {
        signalLine[i] = signalEMA[signalIndex];
        signalIndex++;
      }
    }

    // Гистограмма
    const histogram = macdLine.map((macd, i) => {
      if (macd === null || signalLine[i] === null) return null;
      return macd - signalLine[i];
    });

    return {
      macd: macdLine,
      signal: signalLine,
      histogram: histogram
    };
  }

  /**
   * Вычисляет Relative Strength Index (RSI).
   *
   * RSI - осциллятор импульса, измеряющий скорость и величину
   * направленных ценовых движений. Значения от 0 до 100.
   * - RSI > 70: перекупленность
   * - RSI < 30: перепроданность
   *
   * @param {Array} data - Массив свечей [{close, ...}, ...]
   * @param {number} period - Период для RSI (обычно 14)
   * @returns {Array} Массив значений RSI
   */
  static calculateRSI(data, period = 14) {
    if (!data || data.length < period + 1) {
      return new Array(data.length).fill(null);
    }

    const prices = data.map(d => d.close);
    const rsi = new Array(prices.length).fill(null);

    // Вычисляем изменения цен
    const changes = [];
    for (let i = 1; i < prices.length; i++) {
      changes.push(prices[i] - prices[i - 1]);
    }

    // Отделяем прибыли и убытки
    const gains = changes.map(change => change > 0 ? change : 0);
    const losses = changes.map(change => change < 0 ? -change : 0);

    // Первое среднее значение - простое среднее
    let avgGain = 0;
    let avgLoss = 0;
    for (let i = 0; i < period; i++) {
      avgGain += gains[i];
      avgLoss += losses[i];
    }
    avgGain /= period;
    avgLoss /= period;

    // Вычисляем RSI для первого периода
    let rs = avgGain / avgLoss;
    rsi[period] = 100 - (100 / (1 + rs));

    // Используем сглаженное среднее для остальных значений
    for (let i = period; i < changes.length; i++) {
      avgGain = (avgGain * (period - 1) + gains[i]) / period;
      avgLoss = (avgLoss * (period - 1) + losses[i]) / period;
      rs = avgGain / avgLoss;
      rsi[i + 1] = 100 - (100 / (1 + rs));
    }

    return rsi;
  }

  /**
   * Вычисляет Bollinger Bands.
   *
   * Bollinger Bands состоят из трех линий:
   * - Средняя линия: SMA
   * - Верхняя полоса: SMA + (stdDev * стандартное отклонение)
   * - Нижняя полоса: SMA - (stdDev * стандартное отклонение)
   *
   * @param {Array} data - Массив свечей [{close, ...}, ...]
   * @param {number} period - Период для SMA (обычно 20)
   * @param {number} stdDev - Множитель стандартного отклонения (обычно 2)
   * @returns {Object} {upper: [], middle: [], lower: [], bandwidth: [], percentB: []}
   */
  static calculateBollingerBands(data, period = 20, stdDev = 2) {
    if (!data || data.length < period) {
      const empty = new Array(data.length).fill(null);
      return { upper: empty, middle: empty, lower: empty, bandwidth: empty, percentB: empty };
    }

    const prices = data.map(d => d.close);
    const middle = this.calculateSMA(prices, period);
    const upper = new Array(prices.length);
    const lower = new Array(prices.length);
    const bandwidth = new Array(prices.length);
    const percentB = new Array(prices.length);

    for (let i = 0; i < prices.length; i++) {
      if (middle[i] === null) {
        upper[i] = null;
        lower[i] = null;
        bandwidth[i] = null;
        percentB[i] = null;
        continue;
      }

      // Вычисляем стандартное отклонение
      let sum = 0;
      for (let j = 0; j < period; j++) {
        const diff = prices[i - j] - middle[i];
        sum += diff * diff;
      }
      const std = Math.sqrt(sum / period);

      upper[i] = middle[i] + (stdDev * std);
      lower[i] = middle[i] - (stdDev * std);

      // Ширина полос (bandwidth)
      bandwidth[i] = ((upper[i] - lower[i]) / middle[i]) * 100;

      // %B - положение цены относительно полос
      percentB[i] = (prices[i] - lower[i]) / (upper[i] - lower[i]);
    }

    return {
      upper,
      middle,
      lower,
      bandwidth,
      percentB
    };
  }

  /**
   * Вычисляет все доступные индикаторы для массива данных.
   *
   * @param {Array} data - Массив свечей [{close, volume, ...}, ...]
   * @param {Object} options - Параметры индикаторов
   * @returns {Object} Объект со всеми индикаторами
   */
  static calculateAllIndicators(data, options = {}) {
    const {
      rsiPeriod = 14,
      macdFast = 12,
      macdSlow = 26,
      macdSignal = 9,
      bbPeriod = 20,
      bbStdDev = 2
    } = options;

    const obv = this.calculateOBV(data);
    const macd = this.calculateMACD(data, macdFast, macdSlow, macdSignal);
    const rsi = this.calculateRSI(data, rsiPeriod);
    const bb = this.calculateBollingerBands(data, bbPeriod, bbStdDev);

    return {
      obv,
      macd: macd.macd,
      macdSignal: macd.signal,
      macdHistogram: macd.histogram,
      rsi,
      bbUpper: bb.upper,
      bbMiddle: bb.middle,
      bbLower: bb.lower,
      bbBandwidth: bb.bandwidth,
      bbPercentB: bb.percentB
    };
  }

  /**
   * Анализирует индикаторы и возвращает торговые сигналы.
   *
   * @param {Array} data - Массив свечей с индикаторами
   * @param {Object} indicators - Объект с вычисленными индикаторами
   * @returns {Object} Объект с сигналами
   */
  static getIndicatorSignals(data, indicators) {
    if (!data || data.length < 2) {
      return {};
    }

    const signals = {};
    const lastIdx = data.length - 1;
    const prevIdx = lastIdx - 1;

    // RSI сигналы
    if (indicators.rsi && indicators.rsi[lastIdx] !== null) {
      const rsiCurrent = indicators.rsi[lastIdx];
      if (rsiCurrent > 70) {
        signals.rsi = 'overbought'; // Перекупленность
      } else if (rsiCurrent < 30) {
        signals.rsi = 'oversold'; // Перепроданность
      } else {
        signals.rsi = 'neutral';
      }
    }

    // MACD сигналы (пересечение линий)
    if (indicators.macd && indicators.macdSignal) {
      const macdCurrent = indicators.macd[lastIdx];
      const signalCurrent = indicators.macdSignal[lastIdx];
      const macdPrev = indicators.macd[prevIdx];
      const signalPrev = indicators.macdSignal[prevIdx];

      if (macdCurrent !== null && signalCurrent !== null &&
          macdPrev !== null && signalPrev !== null) {
        // Бычье пересечение
        if (macdPrev <= signalPrev && macdCurrent > signalCurrent) {
          signals.macd = 'bullish_crossover';
        }
        // Медвежье пересечение
        else if (macdPrev >= signalPrev && macdCurrent < signalCurrent) {
          signals.macd = 'bearish_crossover';
        }
        else if (macdCurrent > signalCurrent) {
          signals.macd = 'bullish';
        } else {
          signals.macd = 'bearish';
        }
      }
    }

    // Bollinger Bands сигналы
    if (indicators.bbUpper && indicators.bbLower && data[lastIdx]) {
      const priceCurrent = data[lastIdx].close;
      const bbUpper = indicators.bbUpper[lastIdx];
      const bbLower = indicators.bbLower[lastIdx];

      if (priceCurrent !== null && bbUpper !== null && bbLower !== null) {
        if (priceCurrent >= bbUpper) {
          signals.bollinger = 'at_upper_band'; // У верхней границы
        } else if (priceCurrent <= bbLower) {
          signals.bollinger = 'at_lower_band'; // У нижней границы
        } else {
          signals.bollinger = 'within_bands';
        }
      }
    }

    // OBV тренд
    if (indicators.obv && data.length >= 10) {
      const obvCurrent = indicators.obv[lastIdx];
      const obvSlice = indicators.obv.slice(-10);
      const obvAvg = obvSlice.reduce((a, b) => a + b, 0) / obvSlice.length;

      if (obvCurrent > obvAvg * 1.05) {
        signals.obv = 'accumulation'; // Накопление
      } else if (obvCurrent < obvAvg * 0.95) {
        signals.obv = 'distribution'; // Распределение
      } else {
        signals.obv = 'neutral';
      }
    }

    return signals;
  }
}

export default TechnicalIndicators;
