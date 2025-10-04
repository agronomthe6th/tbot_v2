<!-- frontend/src/views/CleanChart.vue -->
<template>
  <div class="min-h-screen bg-trading-bg text-white">
    <div class="max-w-7xl mx-auto p-4">
      
      <div class="mb-6">
        <h1 class="text-3xl font-bold mb-2">📊 Чистый график</h1>
        <p class="text-gray-400">График свечей без торговых сигналов</p>
      </div>

      <div class="mb-6">
        <div class="bg-trading-card rounded-lg border border-trading-border p-4">
          <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
            
            <!-- Выбор тикера -->
            <div class="control-group">
              <label class="control-label">Тикер</label>
              <select 
                v-model="selectedTicker" 
                @change="handleTickerChange"
                class="ticker-select"
                :disabled="isLoading"
              >
                <option value="" disabled>Выберите тикер</option>
                <option 
                  v-for="ticker in availableTickers" 
                  :key="ticker.ticker"
                  :value="ticker.ticker"
                >
                  {{ ticker.ticker }}
                </option>
              </select>
            </div>

            <!-- Период -->
            <div class="control-group">
              <label class="control-label">Период</label>
              <select 
                v-model="chartDays" 
                @change="handleDaysChange"
                class="period-select"
                :disabled="isLoading"
              >
                <option :value="7">7 дней</option>
                <option :value="14">14 дней</option>
                <option :value="30">30 дней</option>
                <option :value="60">60 дней</option>
                <option :value="90">90 дней</option>
                <option :value="180">180 дней</option>
                <option :value="365">365 дней</option>
              </select>
            </div>

            <!-- Кнопка обновления -->
            <div class="control-group">
              <label class="control-label">&nbsp;</label>
              <button 
                @click="handleRefresh"
                :disabled="isLoading"
                class="action-btn refresh w-full"
              >
                {{ isLoading ? '⏳ Загрузка...' : '🔄 Обновить' }}
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Информационные карточки -->
      <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <div class="bg-trading-card rounded-lg border border-trading-border p-4">
          <div class="flex items-center justify-between">
            <div>
              <div class="text-2xl font-bold text-blue-400">{{ selectedTicker || '—' }}</div>
              <div class="text-sm text-gray-400">Тикер</div>
            </div>
            <div class="text-3xl">📊</div>
          </div>
        </div>
        
        <div class="bg-trading-card rounded-lg border border-trading-border p-4">
          <div class="flex items-center justify-between">
            <div>
              <div class="text-2xl font-bold text-trading-green">{{ formatPrice(currentPrice) }}</div>
              <div class="text-sm text-gray-400">Цена</div>
            </div>
            <div class="text-3xl">💰</div>
          </div>
        </div>
        
        <div class="bg-trading-card rounded-lg border border-trading-border p-4">
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

        <div class="bg-trading-card rounded-lg border border-trading-border p-4">
          <div class="flex items-center justify-between">
            <div>
              <div class="text-2xl font-bold text-trading-yellow">{{ chartDays }}</div>
              <div class="text-sm text-gray-400">Дней</div>
            </div>
            <div class="text-3xl">📅</div>
          </div>
        </div>
      </div>

      <!-- Ошибки -->
      <div v-if="anyError" class="mb-6">
        <div class="error-message">
          ❌ {{ anyError }}
          <button 
            @click="clearErrors" 
            class="ml-4 underline hover:no-underline"
          >
            Скрыть
          </button>
        </div>
      </div>

      <!-- ЕДИНЫЙ ГРАФИК БЕЗ СИГНАЛОВ -->
      <UnifiedTradingChart
        :ticker="selectedTicker"
        :candles-data="candlesData"
        :signals-data="[]"
        :show-signals="false"
        :current-price="currentPrice"
        :is-loading="isLoading"
        :candles-error="candlesError"
        :signals-error="null"
        :chart-height="400"
        @retry="handleRefresh"
      />

    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useTradingStore } from '../stores/tradingStore.js'
import UnifiedTradingChart from '../components/charts/UnifiedTradingChart.vue'

// Router
const route = useRoute()
const router = useRouter()

// Store
const store = useTradingStore()

// Computed properties из store
const selectedTicker = computed({
  get: () => store.selectedTicker,
  set: (value) => store.selectedTicker = value
})

const chartDays = computed({
  get: () => store.chartDays,
  set: (value) => store.chartDays = value
})

const candlesData = computed(() => store.candlesData || [])
const availableTickers = computed(() => store.availableTickers || [])
const currentPrice = computed(() => store.currentPrice)
const formattedCandles = computed(() => store.formattedCandles || [])

// Loading states
const isLoading = computed(() => store.isLoading)

// Errors
const candlesError = computed(() => store.candlesError)
const anyError = computed(() => {
  return store.candlesError || store.tickersError
})

// Price change calculation
const priceChange = computed(() => {
  if (!candlesData.value || candlesData.value.length < 2) return null
  
  const firstPrice = candlesData.value[0].open
  const lastPrice = candlesData.value[candlesData.value.length - 1].close
  
  return ((lastPrice - firstPrice) / firstPrice) * 100
})

const priceChangeColor = computed(() => {
  if (!priceChange.value) return 'text-gray-400'
  return priceChange.value > 0 ? 'text-trading-green' : 'text-trading-red'
})

// Methods
async function handleTickerChange() {
  if (selectedTicker.value) {
    console.log('📄 Changing ticker to:', selectedTicker.value)
    await store.setTicker(selectedTicker.value)
    
    // Обновляем URL
    if (route.params.ticker !== selectedTicker.value) {
      await router.replace(`/clean-chart/${selectedTicker.value}`)
    }
  }
}

function handleDaysChange() {
  if (selectedTicker.value) {
    console.log('📅 Changing days to:', chartDays.value)
    store.setChartDays(chartDays.value)
  }
}

async function handleRefresh() {
  console.log('🔄 Force refresh')
  await store.forceReloadData()
}

function clearErrors() {
  store.clearErrors()
}

function formatPrice(price) {
  if (!price) return '0'
  return new Intl.NumberFormat('ru-RU', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 4
  }).format(price)
}

// Lifecycle
onMounted(async () => {
  console.log('📊 CleanChart mounted, route params:', route.params)
  
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
    
  } catch (error) {
    console.error('❌ Error initializing CleanChart:', error)
  }
})

// Watchers
watch(() => route.params.ticker, async (newTicker) => {
  if (newTicker && newTicker.toUpperCase() !== selectedTicker.value) {
    selectedTicker.value = newTicker.toUpperCase()
    await handleTickerChange()
  }
})
</script>

<style scoped>
.control-group {
  @apply space-y-2;
}

.control-label {
  @apply block text-sm font-medium text-gray-300;
}

.ticker-select,
.period-select {
  @apply w-full px-3 py-2 bg-trading-bg border border-trading-border rounded;
  @apply text-white focus:border-trading-green focus:outline-none;
  @apply disabled:opacity-50 disabled:cursor-not-allowed;
}

.ticker-selector {
  @apply flex items-center space-x-2;
}

.action-btn {
  @apply flex items-center justify-center space-x-2 px-4 py-2 rounded;
  @apply font-medium text-sm disabled:opacity-50 disabled:cursor-not-allowed;
  @apply transition-all duration-200;
}

.action-btn.refresh {
  @apply bg-trading-green text-black hover:bg-green-400;
}

.error-message {
  @apply bg-red-900/50 border border-red-700 rounded p-3 text-red-200;
}

/* Адаптивность */
@media (max-width: 640px) {
  .control-group {
    @apply space-y-2;
  }
}
</style>