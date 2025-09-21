<!-- frontend/src/components/charts/CleanTradingChart.vue -->
<template>
  <div class="clean-chart-container">
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
        
        <div class="flex items-center space-x-3">
          <!-- Информация о данных -->
          <div class="text-sm text-gray-400">
            📊 {{ candlesData.length }} свечей
          </div>
          
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
      <div v-if="error" class="error-overlay">
        <div class="text-center">
          <div class="text-4xl mb-4">⚠️</div>
          <h4 class="text-xl font-semibold mb-2 text-red-400">Ошибка загрузки</h4>
          <p class="text-gray-400 mb-4">{{ error }}</p>
          <button 
            @click="$emit('retry')"
            class="px-4 py-2 bg-trading-green text-black rounded hover:bg-opacity-80 transition-colors"
          >
            🔄 Попробовать снова
          </button>
        </div>
      </div>
      
      <!-- Оверлей "нет данных" -->
      <div v-else-if="!hasData && !isLoading" class="no-data-overlay">
        <div class="text-center">
          <div class="text-4xl mb-4">📭</div>
          <h4 class="text-xl font-semibold mb-2">Нет данных</h4>
          <p class="text-gray-400">Для данного тикера нет данных за указанный период</p>
        </div>
      </div>
    </div>

    <!-- Информация о графике -->
    <div v-if="hasData" class="chart-info">
      <div class="flex justify-between items-center text-sm text-gray-400">
        <div>
          📊 {{ candlesData.length }} свечей за {{ chartDays }} дней
        </div>
        <div>
          📈 Чистый график (без сигналов)
        </div>
        <div>
          ⏰ {{ formatDate(new Date()) }}
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { createChart } from 'lightweight-charts'

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
  currentPrice: {
    type: Number,
    default: null
  },
  isLoading: {
    type: Boolean,
    default: false
  },
  error: {
    type: String,
    default: null
  },
  chartDays: {
    type: Number,
    default: 30
  }
})

// Emits
const emit = defineEmits(['retry'])

// Refs
const chartContainer = ref(null)

// Chart instances
let chart = null
let candlestickSeries = null

// Computed
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
    mode: 1, // Normal crosshair mode
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

function formatDate(date) {
  return date.toLocaleDateString('ru-RU', { 
    day: '2-digit', 
    month: '2-digit' 
  })
}

function initChart() {
  if (!chartContainer.value) {
    console.log('❌ Clean chart container not found')
    return
  }

  try {
    console.log('🚀 Initializing clean chart for', props.ticker)
    
    // Создаем график
    chart = createChart(chartContainer.value, {
      ...chartOptions,
      width: chartContainer.value.clientWidth,
      height: 400,
    })

    // Создаем серию свечей (БЕЗ сигналов!)
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
    
    // Сохраняем observer для cleanup
    chart._resizeObserver = resizeObserver
    
    console.log('✅ Clean chart initialized successfully')
  } catch (error) {
    console.error('❌ Error initializing clean chart:', error)
  }
}

function updateChartData() {
  if (!candlestickSeries || !hasData.value) {
    console.log('⚠️ Cannot update clean chart: missing series or data')
    return
  }

  try {
    // Сортируем данные по времени (на всякий случай)
    const sortedData = [...props.candlesData].sort((a, b) => a.time - b.time)
    
    console.log(`📊 Updating clean chart with ${sortedData.length} candles`)
    
    // Обновляем данные (ТОЛЬКО свечи, без сигналов!)
    candlestickSeries.setData(sortedData)
    
    // Автомасштабирование
    chart.timeScale().fitContent()
    
    console.log(`✅ Clean chart updated: ${sortedData.length} candles for ${props.ticker}`)
  } catch (error) {
    console.error('❌ Error updating clean chart:', error)
  }
}

function destroyChart() {
  if (chart) {
    console.log('🗑️ Destroying clean chart')
    
    if (chart._resizeObserver) {
      chart._resizeObserver.disconnect()
    }
    
    chart.remove()
    chart = null
    candlestickSeries = null
    
    console.log('✅ Clean chart destroyed')
  }
}

// Lifecycle
onMounted(async () => {
  console.log('🔄 CleanTradingChart mounted for', props.ticker)
  await nextTick()
  initChart()
  
  if (hasData.value) {
    updateChartData()
  }
})

onBeforeUnmount(() => {
  console.log('💀 CleanTradingChart unmounting')
  destroyChart()
})

// Watchers
watch(() => props.candlesData, () => {
  console.log('🔄 Clean chart candles data changed, updating chart')
  if (chart && candlestickSeries) {
    updateChartData()
  }
}, { deep: true })

watch(() => props.ticker, () => {
  console.log('🔄 Clean chart ticker changed to', props.ticker)
  // При смене тикера очищаем график
  if (candlestickSeries) {
    candlestickSeries.setData([])
  }
})
</script>

<style scoped>
.clean-chart-container {
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
  min-height: 400px;
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