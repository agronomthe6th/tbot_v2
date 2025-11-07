<!-- frontend/src/views/DataDiagnostics.vue -->
<template>
  <div class="min-h-screen bg-trading-bg text-white">
    <div class="max-w-7xl mx-auto p-4">
      
      <!-- Заголовок -->
      <div class="mb-8">
        <h1 class="text-3xl font-bold mb-2">🔍 Диагностика данных</h1>
        <p class="text-gray-400">Мониторинг и управление историческими данными</p>
      </div>

      <!-- Панель быстрых действий -->
      <div class="bg-trading-card rounded-lg border border-trading-border p-6 mb-6">
        <h2 class="text-lg font-semibold mb-4">⚡ Быстрые действия</h2>
        
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
          <button 
            @click="checkSystemStatus"
            :disabled="isLoading"
            class="px-4 py-3 bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors disabled:opacity-50"
          >
            📊 Статус системы
          </button>
          
          <button 
            @click="loadAllInstruments"
            :disabled="isLoading"
            class="px-4 py-3 bg-green-600 hover:bg-green-700 rounded-lg transition-colors disabled:opacity-50"
          >
            📋 Все инструменты
          </button>
          
          <button 
            @click="refreshAllData"
            :disabled="isLoading"
            class="px-4 py-3 bg-purple-600 hover:bg-purple-700 rounded-lg transition-colors disabled:opacity-50"
          >
            🔄 Обновить все
          </button>
        </div>
      </div>

      <!-- Выбор инструмента для анализа -->
      <div class="bg-trading-card rounded-lg border border-trading-border p-6 mb-6">
        <h2 class="text-lg font-semibold mb-4">🎯 Анализ конкретного инструмента</h2>
        
        <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-4">
          <div>
            <label class="block text-sm font-medium text-gray-300 mb-2">Тикер</label>
            <select 
              v-model="selectedTicker" 
              class="w-full px-3 py-2 bg-trading-bg border border-trading-border rounded-md text-white"
            >
              <option value="">Выберите тикер</option>
              <option v-for="ticker in availableTickers" :key="ticker.ticker" :value="ticker.ticker">
                {{ ticker.ticker }} - {{ ticker.name }}
              </option>
            </select>
          </div>
          
          <div>
            <label class="block text-sm font-medium text-gray-300 mb-2">Период (дни)</label>
            <select 
              v-model="selectedPeriod" 
              class="w-full px-3 py-2 bg-trading-bg border border-trading-border rounded-md text-white"
            >
              <option value="30">30 дней</option>
              <option value="90">90 дней</option>
              <option value="180">180 дней</option>
              <option value="365">1 год</option>
              <option value="730">2 года</option>
              <option value="1095">3 года</option>
            </select>
          </div>
          
          <div>
            <label class="block text-sm font-medium text-gray-300 mb-2">Интервал</label>
            <select 
              v-model="selectedInterval" 
              class="w-full px-3 py-2 bg-trading-bg border border-trading-border rounded-md text-white"
            >
              <option value="5min">5 минут</option>
              <option value="hour">1 час</option>
              <option value="day">1 день</option>
            </select>
          </div>
          
          <div class="flex items-end">
            <button 
              @click="analyzeInstrument"
              :disabled="!selectedTicker || isLoading"
              class="w-full px-4 py-2 bg-trading-green hover:bg-opacity-80 rounded-lg transition-colors disabled:opacity-50"
            >
              🔍 Анализировать
            </button>
          </div>
        </div>
        
        <!-- Результаты анализа -->
        <div v-if="analysisResult" class="mt-4 p-4 bg-trading-bg rounded-lg border border-trading-border">
          <h3 class="font-semibold mb-2">📊 Результат анализа {{ analysisResult.ticker }}</h3>
          
          <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div class="text-center">
              <div class="text-2xl font-bold text-blue-400">{{ analysisResult.available_candles || 0 }}</div>
              <div class="text-sm text-gray-400">Доступно свечей</div>
            </div>
            <div class="text-center">
              <div class="text-2xl font-bold" :class="coverageColor">{{ analysisResult.coverage_percentage || 0 }}%</div>
              <div class="text-sm text-gray-400">Покрытие</div>
            </div>
            <div class="text-center">
              <div class="text-2xl font-bold text-yellow-400">{{ analysisResult.max_days_available || 0 }}</div>
              <div class="text-sm text-gray-400">Макс. дней</div>
            </div>
          </div>
          
          <div v-if="analysisResult.date_range" class="mt-4 text-sm text-gray-400">
            <div><strong>Период данных:</strong> {{ formatDate(analysisResult.date_range.start) }} - {{ formatDate(analysisResult.date_range.end) }}</div>
            <div><strong>Последнее обновление:</strong> {{ formatDate(analysisResult.last_update) }}</div>
          </div>
          
          <!-- Кнопка загрузки данных -->
          <div v-if="analysisResult.coverage_percentage < 101" class="mt-4">
            <button 
              @click="loadMissingData"
              :disabled="isLoadingData"
              class="px-4 py-2 bg-red-600 hover:bg-red-700 rounded-lg transition-colors disabled:opacity-50"
            >
              {{ isLoadingData ? '⏳ Загружаем...' : '📥 Загрузить недостающие данные' }}
            </button>
          </div>
        </div>
      </div>

      <!-- Общая статистика системы -->
      <div v-if="systemStats" class="bg-trading-card rounded-lg border border-trading-border p-6 mb-6">
        <h2 class="text-lg font-semibold mb-4">📈 Статистика системы</h2>
        
        <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-4">
          <div class="bg-trading-bg rounded-lg p-4 border border-trading-border text-center">
            <div class="text-2xl font-bold text-blue-400">{{ systemStats.total_instruments || 0 }}</div>
            <div class="text-sm text-gray-400">Всего инструментов</div>
          </div>
          
          <div class="bg-trading-bg rounded-lg p-4 border border-trading-border text-center">
            <div class="text-2xl font-bold text-green-400">{{ formatNumber(systemStats.total_candles) || 0 }}</div>
            <div class="text-sm text-gray-400">Всего свечей</div>
          </div>
          
          <div class="bg-trading-bg rounded-lg p-4 border border-trading-border text-center">
            <div class="text-2xl font-bold text-yellow-400">{{ systemStats.instruments_with_data || 0 }}</div>
            <div class="text-sm text-gray-400">С данными</div>
          </div>
          
          <div class="bg-trading-bg rounded-lg p-4 border border-trading-border text-center">
            <div class="text-2xl font-bold text-purple-400">{{ systemStats.total_signals || 0 }}</div>
            <div class="text-sm text-gray-400">Всего сигналов</div>
          </div>
        </div>
        
        <div v-if="systemStats.last_update" class="text-sm text-gray-400">
          <strong>Последнее обновление:</strong> {{ formatDate(systemStats.last_update) }}
        </div>
      </div>

      <!-- Список всех инструментов -->
      <div v-if="allInstruments.length > 0" class="bg-trading-card rounded-lg border border-trading-border p-6">
        <div class="flex justify-between items-center mb-4">
          <h2 class="text-lg font-semibold">📋 Все инструменты ({{ allInstruments.length }})</h2>
          
          <!-- Фильтр -->
          <div class="flex gap-2">
            <input 
              v-model="instrumentFilter"
              placeholder="Поиск..."
              class="px-3 py-1 bg-trading-bg border border-trading-border rounded text-white text-sm"
            >
            <select 
              v-model="dataFilter"
              class="px-3 py-1 bg-trading-bg border border-trading-border rounded text-white text-sm"
            >
              <option value="all">Все</option>
              <option value="with_data">С данными</option>
              <option value="no_data">Без данных</option>
              <option value="poor_data">Мало данных</option>
            </select>
          </div>
        </div>
        
        <!-- Таблица инструментов -->
        <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b border-trading-border">
                <th class="text-left py-2">Тикер</th>
                <th class="text-left py-2">Название</th>
                <th class="text-center py-2">Свечей</th>
                <th class="text-center py-2">Покрытие</th>
                <th class="text-center py-2">Последняя</th>
                <th class="text-center py-2">Действия</th>
              </tr>
            </thead>
            <tbody>
              <tr 
                v-for="instrument in filteredInstruments" 
                :key="instrument.ticker"
                class="border-b border-trading-border hover:bg-trading-bg hover:bg-opacity-50"
              >
                <td class="py-2 font-mono">{{ instrument.ticker }}</td>
                <td class="py-2">{{ instrument.name }}</td>
                <td class="py-2 text-center">{{ formatNumber(instrument.candles_count) || 0 }}</td>
                <td class="py-2 text-center">
                  <span 
                    class="px-2 py-1 rounded text-xs font-medium"
                    :class="getCoverageClass(instrument.coverage_percentage)"
                  >
                    {{ instrument.coverage_percentage || 0 }}%
                  </span>
                </td>
                <td class="py-2 text-center text-xs text-gray-400">
                  {{ instrument.latest_candle ? formatDate(instrument.latest_candle) : 'Нет' }}
                </td>
                <td class="py-2 text-center">
                  <button 
                    @click="loadInstrumentData(instrument.ticker)"
                    :disabled="isLoadingData"
                    class="px-2 py-1 bg-trading-green hover:bg-opacity-80 rounded text-xs transition-colors disabled:opacity-50"
                  >
                    📥 Загрузить
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Индикатор загрузки -->
      <div v-if="isLoading" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div class="bg-trading-card rounded-lg p-6 text-center">
          <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-trading-green mx-auto mb-4"></div>
          <div class="text-white">{{ loadingMessage || 'Загрузка...' }}</div>
        </div>
      </div>

    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { tradingAPI } from '../services/api.js'

// Состояние
const isLoading = ref(false)
const isLoadingData = ref(false)
const loadingMessage = ref('')

// Выбранные параметры
const selectedTicker = ref('')
const selectedPeriod = ref(365)
const selectedInterval = ref('5min')

// Фильтры
const instrumentFilter = ref('')
const dataFilter = ref('all')

// Данные
const availableTickers = ref([])
const allInstruments = ref([])
const systemStats = ref(null)
const analysisResult = ref(null)

// Computed
const coverageColor = computed(() => {
  if (!analysisResult.value) return 'text-gray-400'
  const percentage = analysisResult.value.coverage_percentage || 0
  if (percentage >= 80) return 'text-green-400'
  if (percentage >= 50) return 'text-yellow-400'
  return 'text-red-400'
})

const filteredInstruments = computed(() => {
  let filtered = allInstruments.value || []

  // Фильтр по тексту
  if (instrumentFilter.value) {
    const search = instrumentFilter.value.toLowerCase()
    filtered = filtered.filter(inst => {
      if (!inst) return false
      const ticker = inst.ticker || ''
      const name = inst.name || ''
      return ticker.toLowerCase().includes(search) || 
             name.toLowerCase().includes(search)
    })
  }

  // Фильтр по данным
  if (dataFilter.value !== 'all') {
    filtered = filtered.filter(inst => {
      if (!inst) return false
      const candles = inst.candles_count || 0
      const coverage = inst.coverage_percentage || 0
      
      switch (dataFilter.value) {
        case 'with_data':
          return candles > 0
        case 'no_data':
          return candles === 0
        case 'poor_data':
          return candles > 0 && coverage < 50
        default:
          return true
      }
    })
  }

  return filtered
})

// Методы
async function checkSystemStatus() {
  isLoading.value = true
  loadingMessage.value = 'Проверяем статус системы...'
  
  try {
    systemStats.value = await tradingAPI.getSystemStatistics()
    console.log('✅ System stats loaded:', systemStats.value)
  } catch (error) {
    console.error('❌ Error loading system stats:', error)
    alert('Ошибка загрузки статистики: ' + error.message)
  } finally {
    isLoading.value = false
  }
}

async function loadAllInstruments() {
  isLoading.value = true
  loadingMessage.value = 'Загружаем список инструментов...'
  
  try {
    const tickers = await tradingAPI.getAvailableTickers(true, true)
    availableTickers.value = tickers
    
    // ✅ Добавь эти логи:
    console.log('🔍 RAW tickers:', tickers.slice(0, 2))  // первые 2 тикера
    console.log('🔍 SBER data:', tickers.find(t => t.ticker === 'SBER'))
    
    allInstruments.value = tickers.map(ticker => ({
      ...ticker,
      coverage_percentage: calculateCoverage(ticker),
      latest_candle: ticker.latest_candle
    }))
    
    console.log('🔍 SBER after processing:', allInstruments.value.find(t => t.ticker === 'SBER'))
    console.log('✅ Instruments loaded:', allInstruments.value.length)
  } catch (error) {
    console.error('❌ Error loading instruments:', error)
    alert('Ошибка загрузки инструментов: ' + error.message)
  } finally {
    isLoading.value = false
  }
}

async function analyzeInstrument() {
  if (!selectedTicker.value) return
  
  isLoading.value = true
  loadingMessage.value = `Анализируем ${selectedTicker.value}...`
  
  try {
    // Получаем данные за выбранный период
    const candlesResponse = await tradingAPI.getCandles(selectedTicker.value, selectedPeriod.value)
    
    if (candlesResponse && candlesResponse.candles) {
      const candles = candlesResponse.candles
      const requestedDays = selectedPeriod.value
      
      // Анализируем временной диапазон
      let dateRange = null
      let maxDaysAvailable = 0
      
      if (candles.length > 0) {
        const times = candles.map(c => {
          const time = c.time || c.timestamp || c.datetime
          return typeof time === 'string' ? new Date(time) : new Date(time * 1000)
        }).sort((a, b) => a - b)
        
        const firstTime = times[0]
        const lastTime = times[times.length - 1]
        maxDaysAvailable = Math.floor((lastTime - firstTime) / (1000 * 60 * 60 * 24))
        
        dateRange = {
          start: firstTime.toISOString(),
          end: lastTime.toISOString()
        }
      }
      
      const coveragePercentage = Math.round((maxDaysAvailable / requestedDays) * 100)
      
      analysisResult.value = {
        ticker: selectedTicker.value,
        available_candles: candles.length,
        requested_days: requestedDays,
        max_days_available: maxDaysAvailable,
        coverage_percentage: Math.min(coveragePercentage, 100),
        date_range: dateRange,
        last_update: new Date().toISOString()
      }
      
      console.log('✅ Analysis completed:', analysisResult.value)
    } else {
      analysisResult.value = {
        ticker: selectedTicker.value,
        available_candles: 0,
        requested_days: selectedPeriod.value,
        max_days_available: 0,
        coverage_percentage: 0,
        date_range: null,
        last_update: new Date().toISOString()
      }
    }
  } catch (error) {
    console.error('❌ Error analyzing instrument:', error)
    alert('Ошибка анализа: ' + error.message)
  } finally {
    isLoading.value = false
  }
}

async function loadMissingData() {
  if (!selectedTicker.value) return
  
  isLoadingData.value = true
  
  try {
    const response = await tradingAPI.loadHistoricalData(
      selectedTicker.value, 
      selectedPeriod.value, 
      true
    )
    
    console.log('✅ Historical data loading started:', response)
    alert(`Загрузка данных для ${selectedTicker.value} запущена! Проверьте результат через несколько минут.`)
    
    setTimeout(() => {
      analyzeInstrument()
      loadAllInstruments()
    }, 10000)
    
  } catch (error) {
    console.error('❌ Error loading historical data:', error)
    alert('Ошибка загрузки данных: ' + error.message)
  } finally {
    isLoadingData.value = false
  }
}

async function loadInstrumentData(ticker) {
  isLoadingData.value = true
  
  try {
    await tradingAPI.loadHistoricalData(ticker, 365, true)
    alert(`Загрузка данных для ${ticker} запущена!`)
    
    // Обновляем список через 5 секунд
    setTimeout(loadAllInstruments, 5000)
  } catch (error) {
    console.error('❌ Error loading data for', ticker, error)
    alert(`Ошибка загрузки данных для ${ticker}: ` + error.message)
  } finally {
    isLoadingData.value = false
  }
}

async function refreshAllData() {
  isLoading.value = true
  loadingMessage.value = 'Обновляем все данные...'
  
  try {
    await Promise.all([
      checkSystemStatus(),
      loadAllInstruments()
    ])
  } finally {
    isLoading.value = false
  }
}

function calculateCoverage(ticker) {
  if (!ticker.candles_count || !ticker.latest_candle) return 0
  
  // Считаем сколько дней назад была последняя свеча
  const now = Date.now()
  const lastCandleTime = new Date(ticker.latest_candle).getTime()
  const daysSinceLastCandle = Math.floor((now - lastCandleTime) / (1000 * 60 * 60 * 24))
  
  // Если последняя свеча сегодня или вчера = 100%
  if (daysSinceLastCandle <= 1) return 100
  
  // Каждый день без свечей снижает покрытие на 3%
  // Через 30 дней = 10%, через 33 дня = 0%
  const coverage = Math.max(0, 100 - (daysSinceLastCandle * 3))
  return Math.round(coverage)
}

function formatDate(dateString) {
  if (!dateString) return ''
  return new Date(dateString).toLocaleDateString('ru-RU', {
    year: 'numeric',
    month: 'short',
    day: 'numeric'
  })
}

function formatNumber(num) {
  if (!num) return '0'
  return new Intl.NumberFormat('ru-RU').format(num)
}

function getCoverageClass(percentage) {
  if (!percentage) return 'bg-gray-600 text-gray-300'
  if (percentage >= 80) return 'bg-green-600 text-white'
  if (percentage >= 50) return 'bg-yellow-600 text-white'
  return 'bg-red-600 text-white'
}

// Lifecycle
onMounted(async () => {
  console.log('🚀 Data Diagnostics page mounted')
  await refreshAllData()
})
</script>