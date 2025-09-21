<!-- frontend/src/views/SignalsChart.vue - ИСПРАВЛЕННАЯ ВЕРСИЯ -->
<template>
  <div class="min-h-screen bg-trading-bg text-white">
    <div class="max-w-7xl mx-auto p-4">
      
      <!-- Заголовок страницы -->
      <div class="mb-6">
        <h1 class="text-3xl font-bold mb-2">📈 График с сигналами трейдеров</h1>
        <p class="text-gray-400">Анализ торговых сигналов на графике свечей</p>
      </div>

      <!-- Простые контролы (без ChartControls) -->
      <div class="mb-6">
        <div class="bg-trading-card rounded-lg border border-trading-border p-4">
          <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
            
            <!-- Выбор тикера -->
            <div class="control-group">
              <label class="control-label">Тикер</label>
              <div class="ticker-selector">
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
                    {{ ticker.ticker }} ({{ ticker.signal_count }} сигналов)
                  </option>
                </select>
              </div>
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
              </select>
            </div>

            <!-- Действия -->
            <div class="control-group">
              <label class="control-label">Действия</label>
              <div class="flex space-x-2">
                <button 
                  @click="handleRefresh"
                  :disabled="isLoading"
                  class="action-btn refresh"
                >
                  <span v-if="isLoading">🔄</span>
                  <span v-else>🔄</span>
                  Обновить
                </button>
              </div>
            </div>
          </div>

          <!-- Ошибки -->
          <div v-if="anyError" class="mt-4 error-message">
            ⚠️ {{ anyError }}
            <button @click="clearErrors" class="ml-2 underline">Скрыть</button>
          </div>
        </div>
      </div>

      <!-- График -->
      <div class="bg-trading-card rounded-lg border border-trading-border overflow-hidden">
        <div class="p-4 border-b border-trading-border">
          <h2 class="text-xl font-semibold">
            {{ selectedTicker ? `${selectedTicker} - График с сигналами` : 'Выберите тикер для просмотра' }}
          </h2>
        </div>
        
        <div class="p-4">
          <!-- Реальный график -->
          <TradingChart
            v-if="selectedTicker && candlesData.length > 0"
            :ticker="selectedTicker"
            :candles-data="formattedCandles"
            :signals-data="signalsData"
            :current-price="currentPrice"
            :is-loading="isLoading"
            :error="anyError"
            :chart-days="chartDays"
            @retry="handleRefresh"
          />
          
          <!-- Загрузка -->
          <div v-else-if="isLoading" class="text-center py-20">
            <div class="animate-spin w-8 h-8 border-2 border-trading-green border-t-transparent rounded-full mx-auto mb-4"></div>
            <div class="text-gray-400">Загрузка данных...</div>
          </div>
          
          <!-- Нет тикера -->
          <div v-else-if="!selectedTicker" class="text-center py-20 text-gray-400">
            <div class="text-6xl mb-4">📈</div>
            <div class="text-xl mb-2">Выберите инструмент</div>
            <div class="text-sm">Выберите тикер из списка выше для просмотра графика</div>
          </div>

          <!-- Нет данных -->
          <div v-else class="text-center py-20 text-gray-400">
            <div class="text-6xl mb-4">📭</div>
            <div class="text-xl mb-2">Нет данных</div>
            <div class="text-sm">Для выбранного тикера нет данных за указанный период</div>
          </div>
        </div>
      </div>

      <!-- Дополнительная информация -->
      <div v-if="selectedTicker && (candlesData.length > 0 || signalsData.length > 0)" class="mt-6 grid grid-cols-1 md:grid-cols-2 gap-6">
        
        <!-- Статистика сигналов -->
        <div class="bg-trading-card rounded-lg border border-trading-border">
          <div class="p-4 border-b border-trading-border">
            <h3 class="text-lg font-semibold">📊 Статистика сигналов</h3>
          </div>
          <div class="p-4">
            <div v-if="signalsData.length > 0" class="grid grid-cols-2 gap-4 text-center">
              <div>
                <div class="text-2xl font-bold text-white">{{ signalsData.length }}</div>
                <div class="text-sm text-gray-400">Всего сигналов</div>
              </div>
              <div>
                <div class="text-2xl font-bold text-trading-green">{{ buySignalsCount }}</div>
                <div class="text-sm text-gray-400">Покупок</div>
              </div>
              <div>
                <div class="text-2xl font-bold text-trading-red">{{ sellSignalsCount }}</div>
                <div class="text-sm text-gray-400">Продаж</div>
              </div>
              <div>
                <div class="text-2xl font-bold text-trading-yellow">{{ signalsRatio }}</div>
                <div class="text-sm text-gray-400">Соотношение</div>
              </div>
            </div>
            <div v-else class="text-center py-8 text-gray-400">
              <div class="text-2xl mb-2">📈</div>
              <div>Статистика будет доступна после загрузки сигналов</div>
            </div>
          </div>
        </div>

        <!-- Последние сигналы -->
        <div class="bg-trading-card rounded-lg border border-trading-border">
          <div class="p-4 border-b border-trading-border">
            <h3 class="text-lg font-semibold">🎯 Последние сигналы</h3>
          </div>
          <div class="p-4">
            <div v-if="signalsData.length > 0" class="space-y-3 max-h-64 overflow-y-auto">
              <div 
                v-for="signal in signalsData.slice(0, 5)" 
                :key="signal.id"
                class="p-3 bg-trading-bg border border-trading-border rounded"
              >
                <div class="flex justify-between items-center mb-1">
                  <span class="font-semibold text-white">{{ signal.ticker }}</span>
                  <span 
                    class="text-sm font-medium"
                    :class="getDirectionColor(signal.direction)"
                  >
                    {{ getDirectionIcon(signal.direction) }} {{ getDirectionText(signal.direction) }}
                  </span>
                </div>
                <div class="flex justify-between items-center text-xs text-gray-400">
                  <span>{{ formatDate(signal.timestamp) }}</span>
                  <span>{{ signal.author || 'Unknown' }}</span>
                </div>
              </div>
            </div>
            <div v-else class="text-center py-8 text-gray-400">
              <div class="text-2xl mb-2">🎯</div>
              <div>Нет сигналов для отображения</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useTradingStore } from '../stores/tradingStore.js'
import TradingChart from '../components/charts/TradingChart.vue'

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
const signalsData = computed(() => store.signalsData || [])
const availableTickers = computed(() => store.availableTickers || [])
const currentPrice = computed(() => store.currentPrice)
const formattedCandles = computed(() => store.formattedCandles || [])

// Loading states
const isLoading = computed(() => store.isLoading)

// Errors
const anyError = computed(() => {
  return store.candlesError || store.signalsError || store.tickersError
})

// Signal statistics - ИСПРАВЛЕННАЯ ЛОГИКА с DEBUG
const buySignalsCount = computed(() => {
  if (!signalsData.value) return 0
  
  // DEBUG: Логируем все направления сигналов
  if (signalsData.value.length > 0) {
    console.log('🔍 DEBUG: All signal directions:', signalsData.value.map(s => s.direction))
  }
  
  return signalsData.value.filter(s => {
    const direction = s.direction?.toLowerCase()
    const isBuy = direction === 'buy' || direction === 'long' || direction === 'покупка'
    
    if (isBuy) {
      console.log(`✅ BUY signal detected: "${s.direction}" -> ${direction}`)
    }
    
    return isBuy
  }).length
})

const sellSignalsCount = computed(() => {
  if (!signalsData.value) return 0
  
  return signalsData.value.filter(s => {
    const direction = s.direction?.toLowerCase()  
    const isSell = direction === 'sell' || direction === 'short' || direction === 'продажа'
    
    if (isSell) {
      console.log(`✅ SELL signal detected: "${s.direction}" -> ${direction}`)
    }
    
    return isSell
  }).length
})

const signalsRatio = computed(() => {
  if (buySignalsCount.value === 0 && sellSignalsCount.value === 0) return '0:0'
  return `${buySignalsCount.value}:${sellSignalsCount.value}`
})

// Methods
async function handleTickerChange() {
  if (selectedTicker.value) {
    console.log('🔄 Changing ticker to:', selectedTicker.value)
    await store.setTicker(selectedTicker.value)
    
    // Обновляем URL
    if (route.params.ticker !== selectedTicker.value) {
      await router.replace(`/signals-chart/${selectedTicker.value}`)
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

function formatDate(dateString) {
  try {
    const date = new Date(dateString)
    return date.toLocaleDateString('ru-RU', {
      day: '2-digit',
      month: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    })
  } catch {
    return 'N/A'
  }
}

// НОВЫЕ ФУНКЦИИ для правильного отображения направлений с DEBUG
function getDirectionIcon(direction) {
  const dir = direction?.toLowerCase()
  console.log(`🔍 getDirectionIcon: "${direction}" -> "${dir}"`)
  
  if (dir === 'buy' || dir === 'long' || dir === 'покупка') return '🟢'
  if (dir === 'sell' || dir === 'short' || dir === 'продажа') return '🔴'
  return '⚪'
}

function getDirectionText(direction) {
  const dir = direction?.toLowerCase()
  console.log(`🔍 getDirectionText: "${direction}" -> "${dir}"`)
  
  if (dir === 'buy' || dir === 'long' || dir === 'покупка') return 'Покупка'
  if (dir === 'sell' || dir === 'short' || dir === 'продажа') return 'Продажа'
  return direction || 'Unknown'
}

function getDirectionColor(direction) {
  const dir = direction?.toLowerCase()
  if (dir === 'buy' || dir === 'long' || dir === 'покупка') return 'text-trading-green'
  if (dir === 'sell' || dir === 'short' || dir === 'продажа') return 'text-trading-red'
  return 'text-gray-400'
}

// Lifecycle
onMounted(async () => {
  console.log('📈 SignalsChart mounted, route params:', route.params)
  
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
    console.error('❌ Error initializing SignalsChart:', error)
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