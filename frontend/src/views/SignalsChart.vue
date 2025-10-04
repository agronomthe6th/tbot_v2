<template>
  <div class="min-h-screen bg-trading-bg text-white">
    <div class="max-w-7xl mx-auto p-4">
      
      <!-- Заголовок страницы -->
      <div class="mb-6 fade-in">
        <h1 class="text-3xl font-bold mb-2">📈 График с сигналами трейдеров</h1>
        <p class="text-gray-400">Анализ торговых сигналов на графике свечей</p>
      </div>

      <!-- Основные контролы -->
      <div class="mb-6 slide-up">
        <div class="bg-trading-card rounded-lg border border-trading-border p-4 hover:border-trading-green/30 transition-colors duration-300">
          <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
            
            <!-- Поиск тикера -->
            <div class="control-group">
              <label class="control-label">Тикер</label>
              <div class="relative">
                <input
                  v-model="tickerSearch"
                  @input="filterTickers"
                  @focus="showTickerDropdown = true"
                  @blur="hideTickerDropdown"
                  :placeholder="selectedTicker || 'Поиск тикера...'"
                  class="ticker-search-input"
                  :disabled="isLoading || isLoadingSignals"
                />
                
                <!-- Dropdown со списком тикеров -->
                <div 
                  v-if="showTickerDropdown && filteredTickers.length > 0" 
                  class="ticker-dropdown"
                >
                  <div
                    v-for="ticker in filteredTickers.slice(0, 10)"
                    :key="ticker.ticker"
                    @mousedown="selectTicker(ticker.ticker)"
                    class="ticker-option"
                  >
                    <span class="font-medium">{{ ticker.ticker }}</span>
                    <span class="text-sm text-gray-400">({{ ticker.signal_count || 0 }})</span>
                  </div>
                </div>
              </div>
            </div>

            <!-- Период для графика -->
            <div class="control-group">
              <label class="control-label">Период графика</label>
              <select 
                v-model="chartDays"
                @change="handleDaysChange"
                class="period-select smooth-transition"
                :disabled="isLoading"
              >
                <option value="7">7 дней</option>
                <option value="30">30 дней</option>
                <option value="90">90 дней</option>
                <option value="180">180 дней</option>
              </select>
            </div>

            <!-- Кнопка обновления -->
            <div class="control-group">
              <label class="control-label">&nbsp;</label>
              <button 
                @click="handleRefresh"
                :disabled="isLoading || isLoadingSignals"
                class="refresh-button"
              >
                <span v-if="isLoading || isLoadingSignals" class="inline-flex items-center">
                  <svg class="animate-spin -ml-1 mr-2 h-4 w-4" fill="none" viewBox="0 0 24 24">
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                    <path class="opacity-75" fill="currentColor" d="m4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Загрузка...
                </span>
                <span v-else>🔄 Обновить</span>
              </button>
            </div>
          </div>
        </div>

        <!-- Фильтры сигналов -->
        <div v-if="selectedTicker" class="bg-trading-card rounded-lg border border-trading-border p-4 mt-4 slide-up-delayed">
          <h3 class="text-lg font-semibold mb-3">🔍 Фильтры сигналов</h3>
          <div class="grid grid-cols-1 md:grid-cols-5 gap-4">
            
            <!-- Период сигналов -->
            <div class="control-group">
              <label class="control-label">Период сигналов</label>
              <select 
                v-model="signalsDays"
                @change="loadSignalsForTicker"
                class="filter-select smooth-transition"
                :disabled="isLoadingSignals"
              >
                <option value="7">7 дней</option>
                <option value="30">30 дней</option>
                <option value="90">90 дней</option>
                <option value="180">180 дней</option>
              </select>
            </div>

            <!-- Направление -->
            <div class="control-group">
              <label class="control-label">Направление</label>
              <select v-model="signalsFilters.direction" @change="applySignalsFilters" class="filter-select smooth-transition">
                <option value="all">Все</option>
                <option value="long">Long</option>
                <option value="short">Short</option>
                <option value="exit">Exit</option>
              </select>
            </div>

            <!-- Автор -->
            <div class="control-group">
              <label class="control-label">Автор</label>
              <select v-model="signalsFilters.author" @change="applySignalsFilters" class="filter-select smooth-transition">
                <option value="">Все авторы</option>
                <option v-for="author in availableAuthors" :key="author" :value="author">
                  {{ author }}
                </option>
              </select>
            </div>

            <!-- Период фильтра -->
            <div class="control-group">
              <label class="control-label">Период</label>
              <select v-model="signalsFilters.period" @change="applySignalsFilters" class="filter-select smooth-transition">
                <option value="">Весь период</option>
                <option value="1d">За день</option>
                <option value="3d">За 3 дня</option>
                <option value="7d">За неделю</option>
                <option value="30d">За месяц</option>
              </select>
            </div>

            <!-- Сортировка -->
            <div class="control-group">
              <label class="control-label">Сортировка</label>
              <select v-model="signalsFilters.order_by" @change="applySignalsFilters" class="filter-select smooth-transition">
                <option value="timestamp">По времени</option>
                <option value="ticker">По тикеру</option>
                <option value="author">По автору</option>
              </select>
            </div>
          </div>

          <!-- Статистика фильтрации -->
          <div class="mt-3 flex items-center justify-between text-sm text-gray-400 counter-animation">
            <div>
              Найдено: <span class="text-white font-medium">{{ filteredSignals.length }}</span> из {{ allSignals.length }} сигналов
            </div>
            <div class="flex gap-4">
              <span class="signal-counter text-trading-green">Long: {{ longSignalsCount }}</span>
              <span class="signal-counter text-trading-red">Short: {{ shortSignalsCount }}</span>
              <span class="signal-counter text-purple-400">Exit: {{ exitSignalsCount }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Статистика -->
      <div v-if="selectedTicker" class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6 slide-up">
        <div class="stat-card">
          <div class="flex items-center justify-between">
            <div>
              <div class="text-2xl font-bold text-white">{{ selectedTicker }}</div>
              <div class="text-sm text-gray-400">Тикер</div>
            </div>
            <div class="text-3xl">🎯</div>
          </div>
        </div>

        <div class="stat-card">
          <div class="flex items-center justify-between">
            <div>
              <div class="text-2xl font-bold text-trading-green counter-up">{{ allSignals.length }}</div>
              <div class="text-sm text-gray-400">Сигналов</div>
            </div>
            <div class="text-3xl">📊</div>
          </div>
        </div>

        <div class="stat-card">
          <div class="flex items-center justify-between">
            <div>
              <div class="text-2xl font-bold text-trading-yellow">{{ chartDays }}</div>
              <div class="text-sm text-gray-400">Дней графика</div>
            </div>
            <div class="text-3xl">📅</div>
          </div>
        </div>

        <div class="stat-card">
          <div class="flex items-center justify-between">
            <div>
              <div class="text-2xl font-bold" :class="priceChangeColor">
                {{ priceChange ? (priceChange > 0 ? '+' : '') + priceChange.toFixed(2) + '%' : '—' }}
              </div>
              <div class="text-sm text-gray-400">Изменение</div>
            </div>
            <div class="text-3xl">📈</div>
          </div>
        </div>
      </div>

      <!-- Ошибки -->
      <div v-if="anyError" class="mb-6 slide-up">
        <div class="error-message">
          ❌ {{ anyError }}
          <button 
            @click="clearErrors" 
            class="ml-4 underline hover:no-underline transition-colors"
          >
            Скрыть
          </button>
        </div>
      </div>

      <!-- График -->
      <div class="mb-6 slide-up">
        <div class="chart-container">
          <!-- Заголовок графика -->
          <div class="px-4 py-3 border-b border-trading-border">
            <div class="flex items-center justify-between">
              <h2 class="text-xl font-semibold">
                📊 {{ selectedTicker || 'Выберите тикер' }}
                <span v-if="selectedTicker" class="text-sm text-gray-400 ml-2">
                  ({{ chartDays }} дн. / {{ signalsDays }} дн. сигналов)
                </span>
              </h2>
              
              <!-- Управление сигналами на графике -->
              <div class="flex items-center space-x-2">
                <button 
                  @click="toggleSignalsOnChart"
                  :class="showSignalsOnChart ? 'bg-trading-green text-black' : 'bg-gray-600 text-white'"
                  class="px-3 py-1 text-sm rounded transition-all duration-300 hover:scale-105"
                >
                  {{ showSignalsOnChart ? '👁️ Скрыть сигналы' : '👁️‍🗨️ Показать сигналы' }}
                </button>
              </div>
            </div>
          </div>

          <!-- График -->
          <div class="p-4">
            <UnifiedTradingChart
              :ticker="selectedTicker"
              :candles-data="candlesData"
              :signals-data="showSignalsOnChart ? filteredSignals : []"
              :show-signals="showSignalsOnChart"
              :current-price="currentPrice"
              :is-loading="isLoading"
              :candles-error="candlesError"
              :signals-error="signalsError"
              :chart-height="400"
              @retry="handleRefresh"
              class="rounded-lg"
            />
          </div>
        </div>
      </div>

      <!-- Список сигналов ПОД графиком -->
      <div class="signals-list-container slide-up">
        <!-- Заголовок списка сигналов -->
        <div class="px-4 py-3 border-b border-trading-border">
          <div class="flex items-center justify-between">
            <h3 class="text-lg font-semibold">
              🔍 Сигналы{{ selectedTicker ? ` для ${selectedTicker}` : '' }}
            </h3>
            <div class="text-sm text-gray-400">
              {{ filteredSignals.length > 0 ? `Показано ${filteredSignals.length} сигналов` : 'Нет сигналов' }}
            </div>
          </div>
        </div>

        <!-- Список сигналов -->
        <div class="max-h-96 overflow-y-auto">
          <!-- Скелетон загрузки -->
          <div v-if="isLoadingSignals" class="p-8">
            <div class="space-y-4 animate-pulse">
              <div class="flex items-center space-x-4">
                <div class="h-10 bg-gray-700 rounded-full w-10"></div>
                <div class="flex-1 space-y-2">
                  <div class="h-4 bg-gray-700 rounded w-3/4"></div>
                  <div class="h-3 bg-gray-700 rounded w-1/2"></div>
                </div>
              </div>
              <div class="flex items-center space-x-4">
                <div class="h-10 bg-gray-700 rounded-full w-10"></div>
                <div class="flex-1 space-y-2">
                  <div class="h-4 bg-gray-700 rounded w-2/3"></div>
                  <div class="h-3 bg-gray-700 rounded w-1/3"></div>
                </div>
              </div>
              <div class="flex items-center space-x-4">
                <div class="h-10 bg-gray-700 rounded-full w-10"></div>
                <div class="flex-1 space-y-2">
                  <div class="h-4 bg-gray-700 rounded w-4/5"></div>
                  <div class="h-3 bg-gray-700 rounded w-2/5"></div>
                </div>
              </div>
            </div>
          </div>

          <!-- Ошибка -->
          <div v-else-if="signalsError" class="p-8 text-center">
            <div class="text-6xl mb-4">❌</div>
            <h3 class="text-lg font-semibold mb-2">Ошибка загрузки</h3>
            <p class="text-gray-400 mb-4">{{ signalsError }}</p>
            <button 
              @click="loadSignalsForTicker"
              class="px-4 py-2 bg-trading-green hover:bg-green-600 text-black rounded-md transition-all duration-300 hover:scale-105"
            >
              🔄 Попробовать снова
            </button>
          </div>

          <!-- Список сигналов -->
          <div v-else-if="filteredSignals.length > 0" class="divide-y divide-trading-border">
            <div 
              v-for="(signal, index) in paginatedSignals" 
              :key="signal.id"
              @click="onSignalClick(signal)"
              class="signal-item"
              :style="{ animationDelay: `${index * 50}ms` }"
            >
              <SignalCard 
                :signal="signal"
                :show-details="true"
              />
            </div>
            
            <!-- Пагинация -->
            <div v-if="totalSignalsPages > 1" class="p-4 border-t border-trading-border">
              <div class="flex items-center justify-between">
                <button 
                  @click="prevSignalsPage"
                  :disabled="currentSignalsPage <= 1"
                  class="pagination-button"
                >
                  ← Предыдущая
                </button>
                <span class="text-sm text-gray-400">
                  Страница {{ currentSignalsPage }} из {{ totalSignalsPages }}
                </span>
                <button 
                  @click="nextSignalsPage"
                  :disabled="currentSignalsPage >= totalSignalsPages"
                  class="pagination-button"
                >
                  Следующая →
                </button>
              </div>
            </div>
          </div>

          <!-- Пустое состояние -->
          <div v-else class="p-8 text-center">
            <div class="text-6xl mb-4">🎯</div>
            <h3 class="text-lg font-semibold mb-2">Сигналов не найдено</h3>
            <p class="text-gray-400 mb-4">
              {{ selectedTicker ? 
                `Для тикера ${selectedTicker} нет сигналов или они не соответствуют фильтрам` : 
                'Выберите тикер для просмотра сигналов' 
              }}
            </p>
            <button 
              v-if="selectedTicker"
              @click="resetSignalsFilters"
              class="px-4 py-2 bg-gray-600 hover:bg-gray-500 rounded transition-all duration-300 hover:scale-105"
            >
              🔄 Сбросить фильтры
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useTradingStore } from '../stores/tradingStore.js'
import { tradingAPI } from '../services/api'
import UnifiedTradingChart from '../components/charts/UnifiedTradingChart.vue'
import SignalCard from '../components/SignalCard.vue'

// Router
const route = useRoute()
const router = useRouter()

// Store
const store = useTradingStore()

const selectedTicker = computed({
  get: () => store.selectedTicker,
  set: (value) => store.selectedTicker = value
})

const chartDays = computed({
  get: () => store.chartDays,
  set: (value) => store.chartDays = value
})

const formattedCandles = computed(() => {
  const formatted = store.formattedCandles || []
  console.log('📊 SignalsChart: Using formattedCandles:', formatted.slice(0, 2))
  return formatted
})
const candlesData = computed(() => store.candlesData || [])
const availableTickers = computed(() => store.availableTickers || [])
const currentPrice = computed(() => store.currentPrice)
const isLoading = computed(() => store.isLoading)
const candlesError = computed(() => store.candlesError)
const anyError = computed(() => {
  return store.candlesError || store.tickersError || signalsError.value
})

const priceChange = computed(() => {
  if (!formattedCandles.value || formattedCandles.value.length < 2) return null
  
  const firstPrice = formattedCandles.value[0].open
  const lastPrice = formattedCandles.value[formattedCandles.value.length - 1].close
  
  return ((lastPrice - firstPrice) / firstPrice) * 100
})

const priceChangeColor = computed(() => {
  if (!priceChange.value) return 'text-gray-400'
  return priceChange.value > 0 ? 'text-trading-green' : 'text-trading-red'
})

// Поиск тикеров
const tickerSearch = ref('')
const showTickerDropdown = ref(false)
const filteredTickers = ref([])

function filterTickers() {
  if (!tickerSearch.value.trim()) {
    filteredTickers.value = availableTickers.value
  } else {
    const searchTerm = tickerSearch.value.toLowerCase()
    filteredTickers.value = availableTickers.value.filter(ticker => 
      ticker.ticker.toLowerCase().includes(searchTerm)
    )
  }
}

function selectTicker(ticker) {
  selectedTicker.value = ticker
  tickerSearch.value = ''
  showTickerDropdown.value = false
  handleTickerChange()
}

function hideTickerDropdown() {
  setTimeout(() => {
    showTickerDropdown.value = false
  }, 200)
}

// Инициализация поиска тикеров
watch(() => availableTickers.value, () => {
  filteredTickers.value = availableTickers.value
}, { immediate: true })

// Сигналы - локальное состояние
const signalsDays = ref(30)
const showSignalsOnChart = ref(true)
const allSignals = ref([])
const isLoadingSignals = ref(false)
const signalsError = ref(null)
const availableAuthors = ref([])

// Фильтры сигналов
const signalsFilters = ref({
  direction: 'all',
  author: '',
  period: '',
  order_by: 'timestamp'
})

const currentSignalsPage = ref(1)
const signalsPerPage = ref(20)
const filteredSignals = computed(() => {
  let filtered = [...allSignals.value]

  if (signalsFilters.value.direction !== 'all') {
    filtered = filtered.filter(signal => {
      const direction = signal.direction?.toLowerCase()
      return direction === signalsFilters.value.direction || 
             (signalsFilters.value.direction === 'long' && (direction === 'buy' || direction === 'long')) ||
             (signalsFilters.value.direction === 'short' && (direction === 'sell' || direction === 'short'))
    })
  }

  if (signalsFilters.value.author) {
    filtered = filtered.filter(signal => signal.author === signalsFilters.value.author)
  }

  if (signalsFilters.value.period) {
    const now = new Date()
    const periodMs = {
      '1d': 24 * 60 * 60 * 1000,
      '3d': 3 * 24 * 60 * 60 * 1000,
      '7d': 7 * 24 * 60 * 60 * 1000,
      '30d': 30 * 24 * 60 * 60 * 1000
    }[signalsFilters.value.period]

    if (periodMs) {
      const cutoff = new Date(now.getTime() - periodMs)
      filtered = filtered.filter(signal => {
        const signalDate = new Date(signal.timestamp || signal.datetime)
        return signalDate >= cutoff
      })
    }
  }

  filtered.sort((a, b) => {
    const field = signalsFilters.value.order_by
    if (field === 'timestamp') {
      return new Date(b.timestamp || b.datetime) - new Date(a.timestamp || a.timestamp)
    } else if (field === 'ticker') {
      return (a.ticker || '').localeCompare(b.ticker || '')
    } else if (field === 'author') {
      return (a.author || '').localeCompare(b.author || '')
    }
    return 0
  })

  return filtered
})

const totalSignalsPages = computed(() => Math.ceil(filteredSignals.value.length / signalsPerPage.value))
const paginatedSignals = computed(() => {
  const start = (currentSignalsPage.value - 1) * signalsPerPage.value
  const end = start + signalsPerPage.value
  return filteredSignals.value.slice(start, end)
})

const longSignalsCount = computed(() => 
  filteredSignals.value.filter(s => {
    const dir = s.direction?.toLowerCase()
    return dir === 'long' || dir === 'buy'
  }).length
)

const shortSignalsCount = computed(() => 
  filteredSignals.value.filter(s => {
    const dir = s.direction?.toLowerCase()
    return dir === 'short' || dir === 'sell'
  }).length
)

const exitSignalsCount = computed(() => 
  filteredSignals.value.filter(s => {
    const dir = s.direction?.toLowerCase()
    return dir === 'exit' || dir === 'close'
  }).length
)

async function handleTickerChange() {
  if (selectedTicker.value) {
    console.log('🔄 Changing ticker to:', selectedTicker.value)
    
    resetSignalsFilters()
    
    await store.setTicker(selectedTicker.value)
    
    await loadSignalsForTicker()
    
    if (route.params.ticker !== selectedTicker.value) {
      await router.replace(`/signals-chart/${selectedTicker.value}`)
    }
  }
}

async function handleDaysChange() {
  if (selectedTicker.value) {
    console.log('📅 Changing days to:', chartDays.value)
    store.setChartDays(chartDays.value)
    await store.loadCandles(selectedTicker.value, chartDays.value)
  }
}

async function handleRefresh() {
  console.log('🔄 Force refresh')
  await Promise.all([
    store.forceReloadData(),
    loadSignalsForTicker()
  ])
}

function clearErrors() {
  signalsError.value = null
  store.clearErrors()
}

// Методы загрузки сигналов
async function loadSignalsForTicker() {
  if (!selectedTicker.value) {
    allSignals.value = []
    availableAuthors.value = []
    return
  }

  isLoadingSignals.value = true
  signalsError.value = null

  try {
    console.log('🎯 Loading signals for ticker:', selectedTicker.value)

    const response = await tradingAPI.getSignals({
      ticker: selectedTicker.value,
      days_back: signalsDays.value,
      limit: 500,
      include_stats: true
    })

    allSignals.value = response.signals || []
    
    // Собираем уникальных авторов
    const authors = new Set()
    allSignals.value.forEach(signal => {
      if (signal.author) {
        authors.add(signal.author)
      }
    })
    availableAuthors.value = Array.from(authors).sort()

    console.log('✅ Loaded signals:', allSignals.value.length)

  } catch (error) {
    console.error('❌ Error loading signals:', error)
    signalsError.value = error.message || 'Ошибка загрузки сигналов'
    allSignals.value = []
    availableAuthors.value = []
  } finally {
    isLoadingSignals.value = false
  }
}

function applySignalsFilters() {
  console.log('🔍 Applying signals filters:', signalsFilters.value)
  currentSignalsPage.value = 1
}

function resetSignalsFilters() {
  console.log('🗑️ Resetting signals filters')
  signalsFilters.value = {
    direction: 'all',
    author: '',
    period: '',
    order_by: 'timestamp'
  }
  currentSignalsPage.value = 1
}

function toggleSignalsOnChart() {
  showSignalsOnChart.value = !showSignalsOnChart.value
  console.log('👁️ Toggled signals on chart:', showSignalsOnChart.value)
}

// Пагинация
function nextSignalsPage() {
  if (currentSignalsPage.value < totalSignalsPages.value) {
    currentSignalsPage.value++
  }
}

function prevSignalsPage() {
  if (currentSignalsPage.value > 1) {
    currentSignalsPage.value--
  }
}

function onSignalClick(signal) {
  console.log('🎯 Signal clicked:', signal)
}

// Lifecycle - как в CleanChart
onMounted(async () => {
  console.log('📊 SignalsChart mounted, route params:', route.params)
  
  try {
    // Определяем правильный тикер из URL
    const routeTicker = route.params.ticker?.toUpperCase()
    
    if (routeTicker) {
      console.log('🎯 Setting ticker from URL:', routeTicker)
      store.selectedTicker = routeTicker
    }
    
    await store.initialize()
    if (routeTicker && routeTicker !== store.selectedTicker) {
      await store.setTicker(routeTicker)
    }
    
    // Загружаем сигналы если есть тикер
    if (store.selectedTicker) {
      await loadSignalsForTicker()
    }
    
  } catch (error) {
    console.error('❌ Error initializing SignalsChart:', error)
  }
})

// Watchers - как в CleanChart
watch(() => route.params.ticker, async (newTicker) => {
  if (newTicker && newTicker.toUpperCase() !== selectedTicker.value) {
    selectedTicker.value = newTicker.toUpperCase()
    await handleTickerChange()
  }
})

watch(() => signalsFilters.value, () => {
  currentSignalsPage.value = 1
}, { deep: true })

watch(() => signalsDays.value, (newDays) => {
  if (selectedTicker.value && newDays) {
    console.log('📅 Signals days changed to:', newDays)
    loadSignalsForTicker()
  }
})
</script>

<style scoped>
/* Анимации появления */
@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes slideUp {
  from { 
    opacity: 0; 
    transform: translateY(20px); 
  }
  to { 
    opacity: 1; 
    transform: translateY(0); 
  }
}

@keyframes slideInSignal {
  from { 
    opacity: 0; 
    transform: translateX(-20px); 
  }
  to { 
    opacity: 1; 
    transform: translateX(0); 
  }
}

/* Классы анимации */
.fade-in {
  animation: fadeIn 0.6s ease-out;
}

.slide-up {
  animation: slideUp 0.6s ease-out;
}

.slide-up-delayed {
  animation: slideUp 0.6s ease-out 0.2s both;
}

.signal-item {
  animation: slideInSignal 0.3s ease-out both;
}

.counter-animation {
  animation: fadeIn 0.8s ease-out;
}

/* Базовые стили */
.control-group {
  @apply space-y-2;
}

.control-label {
  @apply block text-sm font-medium text-gray-300;
}

.smooth-transition {
  @apply transition-all duration-300;
}

/* Поиск тикеров */
.ticker-search-input {
  @apply w-full px-3 py-2 bg-trading-bg border border-trading-border rounded;
  @apply text-white focus:ring-2 focus:ring-trading-green focus:border-trading-green;
  @apply transition-all duration-300;
}

.ticker-dropdown {
  @apply absolute top-full left-0 right-0 z-50 bg-trading-card border border-trading-border rounded-md mt-1;
  @apply max-h-64 overflow-y-auto shadow-lg;
}

.ticker-option {
  @apply px-3 py-2 hover:bg-trading-green hover:text-black cursor-pointer transition-colors duration-200;
  @apply flex items-center justify-between;
}

/* Селекты */
.period-select,
.filter-select {
  @apply w-full px-3 py-2 bg-trading-bg border border-trading-border rounded;
  @apply text-white focus:ring-2 focus:ring-trading-green focus:border-trading-green;
  @apply transition-all duration-300 hover:border-trading-green/50;
}

/* Кнопки */
.refresh-button {
  @apply w-full px-3 py-2 bg-trading-green hover:bg-green-600 text-black rounded;
  @apply font-medium transition-all duration-300 hover:scale-105;
  @apply disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100;
}

.pagination-button {
  @apply px-3 py-1 text-sm bg-gray-600 hover:bg-gray-500 disabled:opacity-50 disabled:cursor-not-allowed;
  @apply rounded transition-all duration-300 hover:scale-105 disabled:hover:scale-100;
}

/* Карточки статистики */
.stat-card {
  @apply bg-trading-card rounded-lg border border-trading-border p-4;
  @apply hover:border-trading-green/30 transition-all duration-300 hover:scale-105;
}

/* Контейнеры */
.chart-container {
  @apply bg-trading-card rounded-lg border border-trading-border overflow-hidden;
  @apply hover:border-trading-green/30 transition-colors duration-300;
}

.signals-list-container {
  @apply bg-trading-card rounded-lg border border-trading-border;
  @apply hover:border-trading-green/30 transition-colors duration-300;
}

/* Сообщения об ошибках */
.error-message {
  @apply bg-red-900/20 border border-red-500 text-red-300 px-4 py-3 rounded-lg;
  @apply transition-all duration-300;
}

/* Интерактивные элементы сигналов */
.signal-item {
  @apply p-4 hover:bg-trading-bg cursor-pointer transition-all duration-300;
  @apply border-l-4 border-transparent hover:border-trading-green;
  @apply hover:transform hover:scale-[1.02];
}

/* Счетчики */
.signal-counter {
  @apply transition-all duration-300 hover:scale-110;
}

.counter-up {
  animation: fadeIn 0.8s ease-out;
}

/* Кастомный скроллбар */
.overflow-y-auto::-webkit-scrollbar {
  width: 6px;
}

.overflow-y-auto::-webkit-scrollbar-track {
  background: #1a1a1a;
}

.overflow-y-auto::-webkit-scrollbar-thumb {
  background: #404040;
  border-radius: 3px;
  transition: background-color 0.3s;
}

.overflow-y-auto::-webkit-scrollbar-thumb:hover {
  background: #00d4aa;
}

/* Отзывчивость */
@media (max-width: 768px) {
  .stat-card {
    @apply hover:scale-100;
  }
  
  .signal-item {
    @apply hover:scale-100;
  }
}
</style>