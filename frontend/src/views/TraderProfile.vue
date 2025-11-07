<template>
  <div class="min-h-screen bg-trading-bg text-white p-4">
    <!-- Список всех трейдеров -->
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
      <!-- Навигация назад -->
      <div class="mb-6">
        <button 
          @click="$router.push('/traders')"
          class="flex items-center gap-2 text-gray-400 hover:text-white transition-colors mb-4"
        >
          ← Назад к списку трейдеров
        </button>
        
        <!-- Заголовок с именем трейдера -->
        <div v-if="traderStats">
          <h1 class="text-2xl font-bold">👤 {{ traderStats.trader_name || 'Трейдер' }}</h1>
          <div class="flex items-center gap-4 text-gray-400 mt-2">
            <span>ID: {{ traderStats.trader_id }}</span>
          </div>
        </div>
        <div v-else-if="!isLoading">
          <h1 class="text-2xl font-bold text-gray-400">👤 Трейдер не найден</h1>
        </div>
      </div>

      <!-- Загрузка -->
      <div v-if="isLoading" class="flex items-center justify-center h-64">
        <div class="text-center">
          <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-trading-green mx-auto mb-4"></div>
          <p>Загрузка данных...</p>
        </div>
      </div>

      <!-- Ошибка -->
      <div v-else-if="error" class="bg-red-900/20 border border-red-500 rounded-lg p-4 text-center">
        <p class="text-red-400">{{ error }}</p>
        <button 
          @click="loadTraderData"
          class="mt-4 px-4 py-2 bg-trading-green hover:bg-green-600 text-black rounded-md transition-colors"
        >
          🔄 Попробовать снова
        </button>
      </div>

      <!-- Данные трейдера -->
      <div v-else-if="traderStats" class="space-y-6">
        <!-- Статистика -->
        <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div class="bg-trading-card rounded-lg border border-trading-border p-4">
            <div class="text-gray-400 text-sm mb-1">Всего сигналов</div>
            <div class="text-2xl font-bold">{{ traderStats.total_signals || 0 }}</div>
          </div>
          
          <div class="bg-trading-card rounded-lg border border-trading-border p-4">
            <div class="text-gray-400 text-sm mb-1">Закрытых сделок</div>
            <div class="text-2xl font-bold">{{ traderStats.closed_results || 0 }}</div>
          </div>
          
          <div class="bg-trading-card rounded-lg border border-trading-border p-4">
            <div class="text-gray-400 text-sm mb-1">Win Rate</div>
            <div class="text-2xl font-bold text-trading-green">
              {{ traderStats.win_rate || 0 }}%
            </div>
          </div>
          
          <div class="bg-trading-card rounded-lg border border-trading-border p-4">
            <div class="text-gray-400 text-sm mb-1">Средняя прибыль</div>
            <div class="text-2xl font-bold" :class="traderStats.avg_profit_pct > 0 ? 'text-trading-green' : 'text-trading-red'">
              {{ traderStats.avg_profit_pct > 0 ? '+' : '' }}{{ traderStats.avg_profit_pct || 0 }}%
            </div>
          </div>
        </div>

        <!-- Топ тикеры -->
        <div v-if="traderStats.top_tickers && traderStats.top_tickers.length > 0" class="bg-trading-card rounded-lg border border-trading-border p-4">
          <h3 class="font-semibold mb-4">📊 Топ тикеры</h3>
          <div class="space-y-2">
            <div 
              v-for="item in traderStats.top_tickers" 
              :key="item.ticker"
              class="flex items-center justify-between p-2 bg-trading-bg rounded hover:bg-gray-800 transition-colors"
            >
              <span class="font-mono">{{ item.ticker }}</span>
              <span class="text-gray-400">{{ item.count }} сигналов</span>
            </div>
          </div>
        </div>

        <!-- Направления -->
        <div v-if="traderStats.by_direction" class="bg-trading-card rounded-lg border border-trading-border p-4">
          <h3 class="font-semibold mb-4">📈 По направлениям</h3>
          <div class="space-y-2">
            <div 
              v-for="(count, direction) in traderStats.by_direction" 
              :key="direction"
              class="flex items-center justify-between p-2 bg-trading-bg rounded"
            >
              <span class="capitalize">{{ direction }}</span>
              <span class="text-gray-400">{{ count }}</span>
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
          <div v-else class="p-4">
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              <div 
                v-for="signal in traderSignals.slice(0, 12)" 
                :key="signal.id"
                @click="onSignalClick(signal)"
                class="cursor-pointer"
              >
                <SignalCard 
                  :signal="signal"
                  :show-details="false"
                />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import tradingAPI from '../services/api.js'
import SignalCard from '../components/SignalCard.vue'

const route = useRoute()
const router = useRouter()

const currentTraderId = ref(route.params.id)

const isLoading = ref(false)
const isLoadingList = ref(false)
const error = ref(null)

const traderStats = ref(null)
const traderSignals = ref([])
const tradersList = ref([])

watch(() => route.params.id, (newId) => {
  console.log('🔄 Route changed to:', newId)
  currentTraderId.value = newId
  
  if (newId) {
    traderStats.value = null
    traderSignals.value = []
    error.value = null
    loadTraderData()
  } else {
    loadTradersList()
  }
}, { immediate: false })

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
    console.log('📈 Fetching trader stats...')
    const stats = await tradingAPI.getTraderStats(currentTraderId.value, 30)
    console.log('📊 Raw trader stats response:', stats)
    traderStats.value = stats
    console.log('✅ Trader stats loaded:', stats)
    
    console.log('🎯 Fetching trader signals...')
    const signalsResponse = await tradingAPI.getTraderSignals(currentTraderId.value, {
      days_back: 90,
      limit: 50
    })
    
    let signalsArray = []
    if (Array.isArray(signalsResponse)) {
      signalsArray = signalsResponse
    } else if (signalsResponse && Array.isArray(signalsResponse.signals)) {
      signalsArray = signalsResponse.signals
    } else if (signalsResponse && signalsResponse.data && Array.isArray(signalsResponse.data)) {
      signalsArray = signalsResponse.data
    }
    
    traderSignals.value = signalsArray
    console.log('✅ Trader signals loaded:', signalsArray.length)
    
  } catch (err) {
    console.error('❌ Error loading trader data:', err)
    console.error('❌ Error details:', err)
    error.value = `Ошибка загрузки данных: ${err.message}`
  } finally {
    isLoading.value = false
  }
}

async function loadMoreSignals() {
  try {
    console.log('📈 Loading more signals...')
    const signalsResponse = await tradingAPI.getTraderSignals(currentTraderId.value, {
      ticker: null,
      limit: 100
    })
    let signalsArray = []
    if (Array.isArray(signalsResponse)) {
      signalsArray = signalsResponse
    } else if (signalsResponse && Array.isArray(signalsResponse.signals)) {
      signalsArray = signalsResponse.signals
    } else if (signalsResponse && signalsResponse.data && Array.isArray(signalsResponse.data)) {
      signalsArray = signalsResponse.data
    }
    
    traderSignals.value = [...traderSignals.value, ...signalsArray]
    console.log('✅ More signals loaded:', traderSignals.value.length)
  } catch (err) {
    console.error('❌ Error loading more signals:', err)
    error.value = `Ошибка загрузки дополнительных сигналов: ${err.message}`
  }
}

function onSignalClick(signal) {
  console.log('🎯 Signal clicked:', signal)
}

onMounted(async () => {
  console.log('🚀 TraderProfile mounted, route params:', route.params)
  
  if (currentTraderId.value) {
    await loadTraderData()
  } else {
    await loadTradersList()
  }
})
</script>

<style scoped>
.transition-transform {
  transition: transform 0.2s ease-in-out;
}
</style>