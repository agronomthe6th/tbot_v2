<!-- frontend/src/views/TraderProfile.vue - ИСПРАВЛЕННАЯ ВЕРСИЯ -->
<template>
  <div class="min-h-screen bg-trading-bg text-white p-4">
    <!-- Если нет ID - показываем список всех трейдеров -->
    <div v-if="!currentTraderId">
      <div class="mb-6">
        <h1 class="text-2xl font-bold">👥 Все трейдеры</h1>
        <p class="text-gray-400">Выберите трейдера для просмотра профиля</p>
      </div>

      <!-- Загрузка списка -->
      <div v-if="isLoadingList" class="flex items-center justify-center h-64">
        <div class="text-center">
          <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-trading-green mx-auto mb-4"></div>
          <p>Загрузка трейдеров...</p>
        </div>
      </div>

      <!-- Список трейдеров -->
      <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <div 
          v-for="trader in tradersList" 
          :key="trader.id"
          @click="$router.push(`/trader/${trader.id}`)"
          class="bg-trading-card rounded-lg border border-trading-border p-4 cursor-pointer hover:border-trading-green transition-colors"
        >
          <div class="flex items-center justify-between mb-3">
            <h3 class="font-semibold">{{ trader.name }}</h3>
            <div :class="trader.is_active ? 'text-trading-green' : 'text-gray-400'" class="text-sm">
              {{ trader.is_active ? '🟢 Активен' : '⚪ Неактивен' }}
            </div>
          </div>
          
          <div class="space-y-2 text-sm">
            <div class="flex justify-between">
              <span class="text-gray-400">Сигналов:</span>
              <span>{{ trader.total_signals || 0 }}</span>
            </div>
            <div v-if="trader.win_rate" class="flex justify-between">
              <span class="text-gray-400">Win Rate:</span>
              <span class="text-trading-green">{{ trader.win_rate }}%</span>
            </div>
            <div v-if="trader.avg_profit_pct" class="flex justify-between">
              <span class="text-gray-400">Средняя прибыль:</span>
              <span :class="trader.avg_profit_pct > 0 ? 'text-trading-green' : 'text-trading-red'">
                {{ trader.avg_profit_pct > 0 ? '+' : '' }}{{ trader.avg_profit_pct }}%
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Профиль конкретного трейдера -->
    <div v-else>
      <!-- Отладочная информация (уберем потом) -->
      <div class="mb-4 p-2 bg-gray-800 rounded text-xs text-gray-300">
        DEBUG: traderId={{ currentTraderId }}, loading={{ isLoading }}, hasStats={{ !!traderStats }}
      </div>

      <!-- Навигация назад -->
      <div class="mb-6">
        <button 
          @click="$router.back()"
          class="flex items-center gap-2 text-gray-400 hover:text-white transition-colors mb-4"
        >
          ← Назад
        </button>
        
        <div v-if="traderStats">
          <h1 class="text-2xl font-bold">👤 {{ traderStats.name }}</h1>
          <div class="flex items-center gap-4 text-gray-400">
            <span v-if="traderStats.telegram_username">@{{ traderStats.telegram_username }}</span>
            <span :class="traderStats.is_active ? 'text-trading-green' : 'text-gray-400'">
              {{ traderStats.is_active ? '🟢 Активен' : '⚪ Неактивен' }}
            </span>
          </div>
        </div>
      </div>

      <!-- Загрузка профиля -->
      <div v-if="isLoading" class="flex items-center justify-center h-64">
        <div class="text-center">
          <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-trading-green mx-auto mb-4"></div>
          <p>Загрузка профиля трейдера {{ currentTraderId }}...</p>
        </div>
      </div>

      <!-- Ошибка -->
      <div v-else-if="error" class="flex items-center justify-center h-64">
        <div class="text-center">
          <div class="text-4xl mb-4">⚠️</div>
          <h3 class="text-xl font-semibold mb-2 text-trading-red">Ошибка загрузки</h3>
          <p class="text-gray-400 mb-4">{{ error }}</p>
          <button 
            @click="loadTraderData"
            class="px-4 py-2 bg-trading-green text-black rounded hover:bg-opacity-80 transition-colors"
          >
            Повторить
          </button>
        </div>
      </div>

      <!-- Данные трейдера -->
      <div v-else-if="traderStats" class="space-y-6">
        <!-- Основная статистика -->
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <div class="bg-trading-card rounded-lg p-4 border border-trading-border">
            <div class="text-sm text-gray-400">Всего сигналов</div>
            <div class="text-2xl font-bold">{{ traderStats.total_signals || 0 }}</div>
          </div>
          <div class="bg-trading-card rounded-lg p-4 border border-trading-border">
            <div class="text-sm text-gray-400">Закрытых сделок</div>
            <div class="text-2xl font-bold">{{ traderStats.closed_results || 0 }}</div>
          </div>
          <div v-if="traderStats.win_rate" class="bg-trading-card rounded-lg p-4 border border-trading-border">
            <div class="text-sm text-gray-400">Win Rate</div>
            <div class="text-2xl font-bold text-trading-green">{{ traderStats.win_rate }}%</div>
          </div>
          <div v-if="traderStats.avg_profit_pct" class="bg-trading-card rounded-lg p-4 border border-trading-border">
            <div class="text-sm text-gray-400">Средняя прибыль</div>
            <div 
              :class="traderStats.avg_profit_pct > 0 ? 'text-trading-green' : 'text-trading-red'"
              class="text-2xl font-bold"
            >
              {{ traderStats.avg_profit_pct > 0 ? '+' : '' }}{{ traderStats.avg_profit_pct }}%
            </div>
          </div>
        </div>

        <!-- Временные данные -->
        <div v-if="traderStats.first_signal_at || traderStats.last_signal_at" class="bg-trading-card rounded-lg p-4 border border-trading-border">
          <h3 class="text-lg font-semibold mb-4">📅 Временная информация</h3>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div v-if="traderStats.first_signal_at">
              <div class="text-sm text-gray-400">Первый сигнал</div>
              <div class="font-semibold">{{ formatDate(traderStats.first_signal_at) }}</div>
            </div>
            <div v-if="traderStats.last_signal_at">
              <div class="text-sm text-gray-400">Последний сигнал</div>
              <div class="font-semibold">{{ formatDate(traderStats.last_signal_at) }}</div>
            </div>
          </div>
        </div>

        <!-- Тикеры -->
        <div class="bg-trading-card rounded-lg p-4 border border-trading-border">
          <h3 class="text-lg font-semibold mb-4">📊 Инструменты</h3>
          <div v-if="traderTickers.length === 0" class="text-gray-400">
            Нет данных об инструментах
          </div>
          <div v-else class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-2">
            <div 
              v-for="ticker in traderTickers" 
              :key="ticker.ticker"
              @click="$router.push(`/signals-chart/${ticker.ticker}`)"
              class="bg-trading-bg p-3 rounded border border-trading-border hover:border-trading-green cursor-pointer transition-colors"
            >
              <div class="font-semibold">{{ ticker.ticker }}</div>
              <div class="text-sm text-gray-400">{{ ticker.count }} сигналов</div>
            </div>
          </div>
        </div>

        <!-- Последние сигналы -->
        <div class="bg-trading-card rounded-lg p-4 border border-trading-border">
          <div class="flex items-center justify-between mb-4">
            <h3 class="text-lg font-semibold">🎯 Последние сигналы</h3>
            <button 
              @click="loadMoreSignals"
              class="text-trading-green hover:text-opacity-80 transition-colors text-sm"
            >
              Показать больше
            </button>
          </div>
          
          <div v-if="traderSignals.length === 0" class="text-gray-400">
            Нет сигналов для отображения
          </div>
          <div v-else class="space-y-3">
            <!-- Используем новый компонент SignalCard -->
            <SignalCard 
              v-for="signal in traderSignals.slice(0, 10)" 
              :key="signal.id"
              :signal="signal"
              @click="onSignalClick"
            />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import tradingAPI from '../services/api.js'
import SignalCard from '../components/SignalCard.vue'

// Данные
const route = useRoute()

// Используем обычную ref вместо computed для лучшего контроля
const currentTraderId = ref(route.params.id)

const isLoading = ref(false)
const isLoadingList = ref(false)
const error = ref(null)

const traderStats = ref(null)
const traderSignals = ref([])
const tradersList = ref([])
const traderTickers = ref([])

// Отслеживаем изменения в роуте
watch(() => route.params.id, (newId) => {
  console.log('🔄 Route changed to:', newId)
  currentTraderId.value = newId
  
  if (newId) {
    // Сбрасываем предыдущие данные
    traderStats.value = null
    traderSignals.value = []
    traderTickers.value = []
    error.value = null
    
    // Загружаем новые данные
    loadTraderData()
  } else {
    loadTradersList()
  }
}, { immediate: false })

// Методы
function formatDate(dateString) {
  return new Date(dateString).toLocaleDateString('ru-RU')
}

async function loadTradersList() {
  console.log('📋 Loading traders list...')
  isLoadingList.value = true
  try {
    const response = await tradingAPI.getTraders()
    tradersList.value = response
    console.log('✅ Loaded traders:', response.length)
  } catch (err) {
    console.error('❌ Error loading traders list:', err)
  } finally {
    isLoadingList.value = false
  }
}

async function loadTraderData() {
  if (!currentTraderId.value) {
    console.log('⚠️ No trader ID provided')
    return
  }
  
  console.log('📊 Loading trader data for ID:', currentTraderId.value)
  isLoading.value = true
  error.value = null
  
  try {
    // Загружаем статистику трейдера
    console.log('📈 Fetching trader stats...')
    const stats = await tradingAPI.getTraderStats(currentTraderId.value)
    console.log('📊 Raw trader stats response:', stats)
    traderStats.value = stats
    console.log('✅ Trader stats loaded:', stats)
    
    // Загружаем сигналы трейдера
    console.log('🎯 Fetching trader signals...')
    const signalsResponse = await tradingAPI.getTraderSignals(currentTraderId.value, {
      ticker: null,  // Явно передаём null, если нет фильтра по тикеру
      limit: 50      // Ограничиваем до 50 сигналов
    })
    console.log('📊 Raw signals response:', signalsResponse)
    
    // Проверяем структуру ответа
    let signalsArray = []
    if (Array.isArray(signalsResponse)) {
      signalsArray = signalsResponse
    } else if (signalsResponse && Array.isArray(signalsResponse.signals)) {
      signalsArray = signalsResponse.signals
    } else if (signalsResponse && signalsResponse.data && Array.isArray(signalsResponse.data)) {
      signalsArray = signalsResponse.data
    } else {
      console.warn('⚠️ Unexpected signals response structure:', signalsResponse)
    }
    
    traderSignals.value = signalsArray
    console.log('✅ Trader signals processed:', traderSignals.value.length, traderSignals.value)
    
    // Группируем по тикерам
    const tickerCounts = {}
    traderSignals.value.forEach(signal => {
      if (signal && signal.ticker) {
        if (!tickerCounts[signal.ticker]) {
          tickerCounts[signal.ticker] = 0
        }
        tickerCounts[signal.ticker]++
      }
    })
    
    traderTickers.value = Object.entries(tickerCounts)
      .map(([ticker, count]) => ({ ticker, count }))
      .sort((a, b) => b.count - a.count)
    
    console.log('✅ Trader tickers processed:', traderTickers.value)
      
  } catch (err) {
    console.error('❌ Error loading trader data:', err)
    console.error('❌ Error details:', err.response?.data || err)
    error.value = err.message
  } finally {
    isLoading.value = false
  }
}

async function loadMoreSignals() {
  try {
    console.log('📈 Loading more signals...')
    const signalsResponse = await tradingAPI.getTraderSignals(currentTraderId.value, {
      ticker: null,  // Явно передаём null
      limit: 100     // Увеличиваем лимит для "Показать больше"
    })
    let signalsArray = []
    if (Array.isArray(signalsResponse)) {
      signalsArray = signalsResponse
    } else if (signalsResponse && Array.isArray(signalsResponse.signals)) {
      signalsArray = signalsResponse.signals
    } else if (signalsResponse && signalsResponse.data && Array.isArray(signalsResponse.data)) {
      signalsArray = signalsResponse.data
    } else {
      console.warn('⚠️ Unexpected signals response structure:', signalsResponse)
    }
    
    // Добавляем новые сигналы к существующим
    traderSignals.value = [...traderSignals.value, ...signalsArray]
    console.log('✅ More signals loaded:', traderSignals.value.length)
  } catch (err) {
    console.error('❌ Error loading more signals:', err)
    error.value = `Ошибка загрузки дополнительных сигналов: ${err.message}`
  }
}

function onSignalClick(signal) {
  console.log('🎯 Signal clicked:', signal)
  // Можно добавить логику для открытия детального просмотра сигнала
}

// Lifecycle
onMounted(async () => {
  console.log('🚀 TraderProfile mounted, route params:', route.params)
  
  if (currentTraderId.value) {
    await loadTraderData()
  } else {
    await loadTradersList()
  }
})
</script>