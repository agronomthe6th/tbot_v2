<!-- frontend/src/components/charts/UnifiedTradingChart.vue -->
<template>
  <div class="unified-chart-container">
    <!-- Заголовок с информацией -->
    <div class="chart-header">
      <div class="flex items-center justify-between">
        <div class="flex items-center space-x-4">
          <h3 class="text-xl font-bold text-white">
            {{ ticker }}
          </h3>
          <div v-if="currentPrice" class="text-lg font-mono text-trading-green">
            {{ formatPrice(currentPrice) }} ₽
          </div>
          <div v-if="priceChange" class="text-sm" :class="priceChangeColor">
            {{ priceChange > 0 ? '+' : '' }}{{ priceChange.toFixed(2) }}%
          </div>
        </div>
        
        <div class="flex items-center space-x-6 text-sm">
          <!-- Информация о свечах (всегда показываем) -->
          <div class="text-gray-400">
            📊 {{ candlesData.length }} свечей
          </div>
          
          <!-- Статистика сигналов (только если показываем сигналы) -->
          <template v-if="showSignals && signalsData.length > 0">
            <div class="flex items-center space-x-2">
              <div class="w-3 h-3 bg-trading-green rounded-full"></div>
              <span>Покупки: {{ buySignalsCount }}</span>
            </div>
            <div class="flex items-center space-x-2">
              <div class="w-3 h-3 bg-trading-red rounded-full"></div>
              <span>Продажи: {{ sellSignalsCount }}</span>
            </div>
            <div class="text-gray-400">
              Всего: {{ totalSignalsCount }}
            </div>
          </template>
          
          <!-- Кнопка обновления -->
          <button 
            v-if="!isLoading" 
            @click="$emit('retry')"
            class="px-3 py-1 bg-trading-green text-black rounded hover:bg-opacity-80 transition-colors text-sm"
          >
            🔄 Обновить
          </button>
        </div>
      </div>
    </div>

    <!-- Контейнер графика -->
    <div class="chart-wrapper">
      <div 
        ref="chartContainer" 
        class="chart-container"
        :class="{ 'chart-loading': isLoading }"
      ></div>
      
      <!-- Оверлей ошибки -->
      <div v-if="anyError" class="error-overlay">
        <div class="text-center">
          <div class="text-4xl mb-4">⚠️</div>
          <h4 class="text-xl font-semibold mb-2 text-red-400">Ошибка загрузки</h4>
          <p class="text-gray-400 mb-4">{{ anyError }}</p>
          <button 
            @click="$emit('retry')"
            class="px-4 py-2 bg-trading-green text-black rounded hover:bg-opacity-80 transition-colors"
          >
            🔄 Попробовать снова
          </button>
        </div>
      </div>
      
      <!-- Оверлей "нет данных" -->
      <div v-if="!isLoading && !anyError && candlesData.length === 0" class="no-data-overlay">
        <div class="text-center">
          <div class="text-4xl mb-4">📈</div>
          <h4 class="text-xl font-semibold mb-2">Нет данных</h4>
          <p class="text-gray-400 mb-4">Данные для {{ ticker }} отсутствуют</p>
          <button 
            @click="$emit('retry')"
            class="px-4 py-2 bg-trading-green text-black rounded hover:bg-opacity-80 transition-colors"
          >
            🔄 Загрузить данные
          </button>
        </div>
      </div>
    </div>

    <!-- Дополнительная информация -->
    <div v-if="showChartInfo && !anyError && candlesData.length > 0" class="chart-info">
      <div class="flex items-center justify-between text-sm text-gray-400">
        <div>
          Период: {{ formatDateRange() }}
        </div>
        <div v-if="showSignals">
          Режим: с торговыми сигналами
        </div>
        <div v-else>
          Режим: чистый график
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { createChart } from 'lightweight-charts'
import TechnicalIndicators from '@/utils/technicalIndicators.js'

// Props
const props = defineProps({
  ticker: {
    type: String,
    required: true
  },
  candlesData: {
    type: Array,
    default: () => []
  },
  signalsData: {
    type: Array,
    default: () => []
  },
  showSignals: {
    type: Boolean,
    default: false
  },
  currentPrice: {
    type: Number,
    default: null
  },
  isLoading: {
    type: Boolean,
    default: false
  },
  candlesError: {
    type: String,
    default: null
  },
  signalsError: {
    type: String,
    default: null
  },
  showChartInfo: {
    type: Boolean,
    default: true
  },
  chartHeight: {
    type: Number,
    default: 500
  },
  indicators: {
    type: Object,
    default: () => ({
      rsi: { enabled: false },
      macd: { enabled: false },
      bollingerBands: { enabled: false },
      obv: { enabled: false }
    })
  }
})

// Emits
const emit = defineEmits(['retry'])

// Refs
const chartContainer = ref(null)

// Chart instances
let chart = null
let candlestickSeries = null

// Indicator series
let bbUpperSeries = null
let bbMiddleSeries = null
let bbLowerSeries = null
let rsiSeries = null
let macdSeries = null
let macdSignalSeries = null
let macdHistogramSeries = null
let obvSeries = null

// Indicator line references for level lines
let rsiOverboughtLine = null
let rsiOversoldLine = null
let macdZeroLine = null

// Computed
const anyError = computed(() => {
  return props.candlesError || props.signalsError
})

const hasData = computed(() => {
  return props.candlesData && props.candlesData.length > 0
})

const priceChange = computed(() => {
  if (!hasData.value || props.candlesData.length < 2) return null
  
  const firstPrice = props.candlesData[0].open
  const lastPrice = props.candlesData[props.candlesData.length - 1].close
  
  return ((lastPrice - firstPrice) / firstPrice) * 100
})

const priceChangeColor = computed(() => {
  if (!priceChange.value) return 'text-gray-400'
  return priceChange.value > 0 ? 'text-trading-green' : 'text-trading-red'
})

// Сигналы статистика
const buySignalsCount = computed(() => {
  if (!props.showSignals || !props.signalsData) return 0
  return props.signalsData.filter(s => s.direction === 'BUY').length
})

const sellSignalsCount = computed(() => {
  if (!props.showSignals || !props.signalsData) return 0
  return props.signalsData.filter(s => s.direction === 'SELL').length
})

const totalSignalsCount = computed(() => {
  return buySignalsCount.value + sellSignalsCount.value
})

// Chart options
const chartOptions = {
  layout: {
    background: { type: 'solid', color: '#1a1a1a' },
    textColor: '#d1d5db',
  },
  grid: {
    vertLines: { color: '#2d2d2d' },
    horzLines: { color: '#2d2d2d' },
  },
  crosshair: {
    mode: 1,
  },
  rightPriceScale: {
    borderColor: '#404040',
  },
  timeScale: {
    borderColor: '#404040',
    timeVisible: true,
    secondsVisible: false,
  },
  localization: {
    locale: 'ru-RU',
  }
}

const candlestickOptions = {
  upColor: '#00d4aa',
  downColor: '#ff4747',
  borderDownColor: '#ff4747',
  borderUpColor: '#00d4aa',
  wickDownColor: '#ff4747',
  wickUpColor: '#00d4aa',
}

// Methods
function formatPrice(price) {
  if (!price) return '0'
  return new Intl.NumberFormat('ru-RU', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 4
  }).format(price)
}

function formatDateRange() {
  if (!hasData.value) return ''
  
  const firstCandle = props.candlesData[0]
  const lastCandle = props.candlesData[props.candlesData.length - 1]
  
  const startDate = new Date(firstCandle.time * 1000).toLocaleDateString('ru-RU')
  const endDate = new Date(lastCandle.time * 1000).toLocaleDateString('ru-RU')
  
  return `${startDate} — ${endDate}`
}

function initChart() {
  if (!chartContainer.value) {
    console.log('⚠️ Chart container not found')
    return
  }

  try {
    console.log('🚀 Initializing unified chart for', props.ticker, 'with signals:', props.showSignals)
    
    // Создаем график
    chart = createChart(chartContainer.value, {
      ...chartOptions,
      width: chartContainer.value.clientWidth,
      height: props.chartHeight,
    })

    // Создаем серию свечей
    candlestickSeries = chart.addCandlestickSeries(candlestickOptions)

    // Обработчик изменения размера
    const resizeObserver = new ResizeObserver(() => {
      if (chart && chartContainer.value) {
        chart.applyOptions({
          width: chartContainer.value.clientWidth,
        })
      }
    })
    
    resizeObserver.observe(chartContainer.value)
    chart._resizeObserver = resizeObserver
    
    console.log('✅ Unified chart initialized successfully')
  } catch (error) {
    console.error('❌ Error initializing unified chart:', error)
  }
}

function updateChartData() {
  if (!candlestickSeries || !hasData.value) {
    console.log('⚠️ Cannot update chart: missing series or data')
    return
  }

  try {
    // Преобразуем и сортируем данные по времени
    const processedData = props.candlesData.map(candle => ({
      ...candle,
      time: typeof candle.time === 'string'
        ? Math.floor(new Date(candle.time).getTime() / 1000)
        : candle.time
    })).sort((a, b) => a.time - b.time)

    console.log(`📊 Updating chart with ${processedData.length} candles`)
    console.log('🔍 Sample candle time format:', processedData[0]?.time, typeof processedData[0]?.time)

    // Обновляем данные свечей
    candlestickSeries.setData(processedData)

    // Обновляем индикаторы
    updateIndicators(processedData)

    // Если нужно показывать сигналы - добавляем маркеры
    if (props.showSignals && props.signalsData && props.signalsData.length > 0) {
      updateSignalsMarkers()
    } else {
      // Очищаем маркеры если сигналы не нужны
      candlestickSeries.setMarkers([])
    }

    // Автомасштабирование
    chart.timeScale().fitContent()

    console.log(`✅ Chart updated successfully`)
  } catch (error) {
    console.error('❌ Error updating chart:', error)
  }
}

function updateIndicators(processedData) {
  if (!processedData || processedData.length === 0) {
    return
  }

  try {
    // Вычисляем индикаторы
    const indicatorsData = TechnicalIndicators.calculateAllIndicators(processedData, {
      rsiPeriod: props.indicators.rsi.period || 14,
      macdFast: props.indicators.macd.fastPeriod || 12,
      macdSlow: props.indicators.macd.slowPeriod || 26,
      macdSignal: props.indicators.macd.signalPeriod || 9,
      bbPeriod: props.indicators.bollingerBands.period || 20,
      bbStdDev: props.indicators.bollingerBands.stdDev || 2
    })

    // Bollinger Bands - отображаем на основном графике
    if (props.indicators.bollingerBands.enabled) {
      updateBollingerBands(processedData, indicatorsData)
    } else {
      clearBollingerBands()
    }

    // RSI - отдельная панель
    if (props.indicators.rsi.enabled) {
      updateRSI(processedData, indicatorsData)
    } else {
      clearRSI()
    }

    // MACD - отдельная панель
    if (props.indicators.macd.enabled) {
      updateMACD(processedData, indicatorsData)
    } else {
      clearMACD()
    }

    // OBV - отдельная панель
    if (props.indicators.obv.enabled) {
      updateOBV(processedData, indicatorsData)
    } else {
      clearOBV()
    }
  } catch (error) {
    console.error('❌ Error updating indicators:', error)
  }
}

function updateBollingerBands(processedData, indicatorsData) {
  if (!bbUpperSeries) {
    const color = props.indicators.bollingerBands.color || '#089981'
    bbUpperSeries = chart.addLineSeries({
      color: color,
      lineWidth: 1,
      lineStyle: 0,
      priceLineVisible: false
    })
    bbMiddleSeries = chart.addLineSeries({
      color: color,
      lineWidth: 2,
      lineStyle: 0,
      priceLineVisible: false
    })
    bbLowerSeries = chart.addLineSeries({
      color: color,
      lineWidth: 1,
      lineStyle: 0,
      priceLineVisible: false
    })
  }

  const upperData = []
  const middleData = []
  const lowerData = []

  for (let i = 0; i < processedData.length; i++) {
    if (indicatorsData.bbUpper[i] !== null) {
      upperData.push({ time: processedData[i].time, value: indicatorsData.bbUpper[i] })
      middleData.push({ time: processedData[i].time, value: indicatorsData.bbMiddle[i] })
      lowerData.push({ time: processedData[i].time, value: indicatorsData.bbLower[i] })
    }
  }

  bbUpperSeries.setData(upperData)
  bbMiddleSeries.setData(middleData)
  bbLowerSeries.setData(lowerData)
}

function clearBollingerBands() {
  if (bbUpperSeries) {
    chart.removeSeries(bbUpperSeries)
    bbUpperSeries = null
  }
  if (bbMiddleSeries) {
    chart.removeSeries(bbMiddleSeries)
    bbMiddleSeries = null
  }
  if (bbLowerSeries) {
    chart.removeSeries(bbLowerSeries)
    bbLowerSeries = null
  }
}

function updateRSI(processedData, indicatorsData) {
  if (!rsiSeries) {
    const color = props.indicators.rsi.color || '#2962FF'
    rsiSeries = chart.addLineSeries({
      color: color,
      lineWidth: 2,
      priceLineVisible: false,
      priceFormat: {
        type: 'price',
        precision: 2,
        minMove: 0.01
      }
    })

    // Добавляем линии уровней
    rsiOverboughtLine = chart.addLineSeries({
      color: 'rgba(255, 82, 82, 0.3)',
      lineWidth: 1,
      lineStyle: 2,
      priceLineVisible: false,
      lastValueVisible: false
    })

    rsiOversoldLine = chart.addLineSeries({
      color: 'rgba(38, 166, 154, 0.3)',
      lineWidth: 1,
      lineStyle: 2,
      priceLineVisible: false,
      lastValueVisible: false
    })

    // Устанавливаем линии уровней
    const overboughtData = processedData.map(candle => ({ time: candle.time, value: 70 }))
    const oversoldData = processedData.map(candle => ({ time: candle.time, value: 30 }))
    rsiOverboughtLine.setData(overboughtData)
    rsiOversoldLine.setData(oversoldData)
  }

  const rsiData = []
  for (let i = 0; i < processedData.length; i++) {
    if (indicatorsData.rsi[i] !== null && !isNaN(indicatorsData.rsi[i])) {
      rsiData.push({ time: processedData[i].time, value: indicatorsData.rsi[i] })
    }
  }

  rsiSeries.setData(rsiData)
}

function clearRSI() {
  if (rsiSeries) {
    chart.removeSeries(rsiSeries)
    rsiSeries = null
  }
  if (rsiOverboughtLine) {
    chart.removeSeries(rsiOverboughtLine)
    rsiOverboughtLine = null
  }
  if (rsiOversoldLine) {
    chart.removeSeries(rsiOversoldLine)
    rsiOversoldLine = null
  }
}

function updateMACD(processedData, indicatorsData) {
  if (!macdSeries) {
    const macdColor = props.indicators.macd.macdColor || '#2962FF'
    const signalColor = props.indicators.macd.signalColor || '#FF6D00'

    macdSeries = chart.addLineSeries({
      color: macdColor,
      lineWidth: 2,
      priceLineVisible: false
    })

    macdSignalSeries = chart.addLineSeries({
      color: signalColor,
      lineWidth: 2,
      priceLineVisible: false
    })

    macdHistogramSeries = chart.addHistogramSeries({
      color: '#26a69a',
      priceFormat: {
        type: 'volume'
      },
      priceLineVisible: false,
      priceScaleId: ''
    })

    macdZeroLine = chart.addLineSeries({
      color: 'rgba(128, 128, 128, 0.3)',
      lineWidth: 1,
      lineStyle: 2,
      priceLineVisible: false,
      lastValueVisible: false
    })

    const zeroData = processedData.map(candle => ({ time: candle.time, value: 0 }))
    macdZeroLine.setData(zeroData)
  }

  const macdData = []
  const signalData = []
  const histogramData = []

  for (let i = 0; i < processedData.length; i++) {
    if (indicatorsData.macd[i] !== null && !isNaN(indicatorsData.macd[i])) {
      macdData.push({ time: processedData[i].time, value: indicatorsData.macd[i] })
    }
    if (indicatorsData.macdSignal[i] !== null && !isNaN(indicatorsData.macdSignal[i])) {
      signalData.push({ time: processedData[i].time, value: indicatorsData.macdSignal[i] })
    }
    if (indicatorsData.macdHistogram[i] !== null && !isNaN(indicatorsData.macdHistogram[i])) {
      const value = indicatorsData.macdHistogram[i]
      histogramData.push({
        time: processedData[i].time,
        value: value,
        color: value >= 0 ? '#26a69a' : '#ef5350'
      })
    }
  }

  macdSeries.setData(macdData)
  macdSignalSeries.setData(signalData)
  macdHistogramSeries.setData(histogramData)
}

function clearMACD() {
  if (macdSeries) {
    chart.removeSeries(macdSeries)
    macdSeries = null
  }
  if (macdSignalSeries) {
    chart.removeSeries(macdSignalSeries)
    macdSignalSeries = null
  }
  if (macdHistogramSeries) {
    chart.removeSeries(macdHistogramSeries)
    macdHistogramSeries = null
  }
  if (macdZeroLine) {
    chart.removeSeries(macdZeroLine)
    macdZeroLine = null
  }
}

function updateOBV(processedData, indicatorsData) {
  if (!obvSeries) {
    const color = props.indicators.obv.color || '#9C27B0'
    obvSeries = chart.addLineSeries({
      color: color,
      lineWidth: 2,
      priceLineVisible: false
    })
  }

  const obvData = []
  for (let i = 0; i < processedData.length; i++) {
    if (indicatorsData.obv[i] !== null && !isNaN(indicatorsData.obv[i])) {
      obvData.push({ time: processedData[i].time, value: indicatorsData.obv[i] })
    }
  }

  obvSeries.setData(obvData)
}

function clearOBV() {
  if (obvSeries) {
    chart.removeSeries(obvSeries)
    obvSeries = null
  }
}

function updateSignalsMarkers() {
  if (!candlestickSeries || !props.showSignals || !props.signalsData) {
    return
  }

  try {
    console.log('🎯 Updating signals markers:', props.signalsData.length)
    
    const markers = props.signalsData.map(signal => {
      // Обрабатываем время сигнала - конвертируем в Unix timestamp (секунды)
      let signalTime
      const timeField = signal.issued_at || signal.timestamp
      
      if (typeof timeField === 'string') {
        signalTime = Math.floor(new Date(timeField).getTime() / 1000)
      } else {
        signalTime = timeField
      }
      
      let priceText = ''
      if (signal.price) {
        priceText = ` (${parseFloat(signal.price).toFixed(2)}₽)`
      }
      
      let authorText = ''
      if (signal.author) {
        authorText = ` - ${signal.author}`
      }

      return {
        time: signalTime,
        position: signal.direction === 'BUY' || signal.direction === 'long' ? 'belowBar' : 'aboveBar',
        color: signal.direction === 'BUY' || signal.direction === 'long' ? '#00d4aa' : '#ff4747',
        shape: signal.direction === 'BUY' || signal.direction === 'long' ? 'arrowUp' : 'arrowDown',
        text: `${signal.direction} ${signal.ticker || props.ticker}${priceText}${authorText}`,
        size: 1
      }
    })
    
    // Сортируем маркеры по времени
    const sortedMarkers = markers.sort((a, b) => a.time - b.time)
    
    console.log('📊 Setting markers:', sortedMarkers.length)
    console.log('🔍 Sample marker time:', sortedMarkers[0]?.time, typeof sortedMarkers[0]?.time)
    candlestickSeries.setMarkers(sortedMarkers)
    
    console.log(`✅ Applied ${sortedMarkers.length} signal markers to chart`)
  } catch (error) {
    console.error('❌ Error updating signals markers:', error)
  }
}

function destroyChart() {
  if (chart) {
    console.log('🗑️ Destroying unified chart')

    if (chart._resizeObserver) {
      chart._resizeObserver.disconnect()
    }

    // Очищаем все индикаторы
    clearBollingerBands()
    clearRSI()
    clearMACD()
    clearOBV()

    chart.remove()
    chart = null
    candlestickSeries = null

    console.log('✅ Chart destroyed')
  }
}

// Lifecycle
onMounted(async () => {
  console.log('📄 UnifiedTradingChart mounted for', props.ticker)
  await nextTick()
  initChart()
  
  if (hasData.value) {
    updateChartData()
  }
})

onBeforeUnmount(() => {
  console.log('💀 UnifiedTradingChart unmounting')
  destroyChart()
})

// Watchers
watch(() => props.candlesData, () => {
  console.log('📄 Candles data changed, updating chart')
  if (chart && candlestickSeries) {
    updateChartData()
  }
}, { deep: true })

watch(() => props.signalsData, () => {
  console.log('📄 Signals data changed, updating markers')
  if (chart && candlestickSeries && props.showSignals) {
    updateSignalsMarkers()
  }
}, { deep: true })

watch(() => props.showSignals, () => {
  console.log('📄 Show signals changed to', props.showSignals)
  if (chart && candlestickSeries) {
    updateChartData() // Перерисовываем с учетом нового режима
  }
})

watch(() => props.ticker, () => {
  console.log('📄 Ticker changed to', props.ticker)
  // При смене тикера очищаем график
  if (candlestickSeries) {
    candlestickSeries.setData([])
    candlestickSeries.setMarkers([])
  }
})

watch(() => props.indicators, () => {
  console.log('📄 Indicators changed, updating chart')
  if (chart && candlestickSeries && hasData.value) {
    updateChartData()
  }
}, { deep: true })
</script>

<style scoped>
.unified-chart-container {
  @apply bg-trading-card border border-trading-border rounded-lg overflow-hidden;
}

.chart-header {
  @apply p-4 border-b border-trading-border bg-gradient-to-r from-trading-card to-trading-bg;
}

.chart-wrapper {
  @apply relative;
}

.chart-container {
  @apply w-full transition-opacity duration-300;
}

.chart-loading {
  @apply opacity-60;
}

.error-overlay,
.no-data-overlay {
  @apply absolute inset-0 flex items-center justify-center;
  @apply bg-black/20 backdrop-blur-sm;
}

.chart-info {
  @apply p-3 bg-trading-bg border-t border-trading-border;
}

/* Анимация загрузки */
@keyframes pulse-loading {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}

.chart-loading {
  animation: pulse-loading 2s ease-in-out infinite;
}
</style>