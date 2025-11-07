<template>
  <div class="min-h-screen bg-trading-bg text-white">
    <div class="max-w-7xl mx-auto p-4">
      
      <div class="mb-8">
        <h1 class="text-3xl font-bold mb-2">🎯 Все торговые сигналы</h1>
        <p class="text-gray-400">Универсальный просмотр и фильтрация сигналов</p>
      </div>

      <!-- Tabs -->
      <div class="mb-6 border-b border-trading-border">
        <div class="flex gap-4">
          <button
            @click="activeTab = 'signals'"
            :class="[
              'px-4 py-2 font-medium transition-colors',
              activeTab === 'signals'
                ? 'text-trading-green border-b-2 border-trading-green'
                : 'text-gray-400 hover:text-white'
            ]"
          >
            ✅ Успешные сигналы ({{ signalsStats?.total_signals || 0 }})
          </button>
          <button
            @click="activeTab = 'failed'"
            :class="[
              'px-4 py-2 font-medium transition-colors',
              activeTab === 'failed'
                ? 'text-red-500 border-b-2 border-red-500'
                : 'text-gray-400 hover:text-white'
            ]"
          >
            ❌ Failed сообщения ({{ signalsStats?.failed_messages || 0 }})
          </button>
        </div>
      </div>

      <!-- Панель фильтров (только для успешных сигналов) -->
      <div v-if="activeTab === 'signals'" class="bg-trading-card rounded-lg border border-trading-border p-6 mb-6">
        <h2 class="text-lg font-semibold mb-4">🔍 Фильтры</h2>
        
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
          <!-- Тикер -->
          <div class="relative">
            <label class="block text-sm font-medium text-gray-300 mb-2">Тикер</label>
            <input 
              v-model="tickerSearch"
              @focus="showTickerDropdown = true"
              @input="handleTickerInput"
              type="text"
              placeholder="Начните вводить..."
              class="w-full px-3 py-2 bg-trading-bg border border-trading-border rounded text-white focus:border-trading-green focus:outline-none"
            />
            
            <div 
              v-if="showTickerDropdown && filteredTickers.length > 0" 
              class="absolute z-10 w-full mt-1 bg-trading-card border border-trading-border rounded shadow-lg max-h-60 overflow-y-auto"
            >
              <div 
                v-for="ticker in filteredTickers"
                :key="ticker.ticker"
                @click="selectTicker(ticker.ticker)"
                class="px-3 py-2 hover:bg-trading-bg cursor-pointer transition-colors"
              >
                <div class="font-medium">{{ ticker.ticker }}</div>
                <div class="text-xs text-gray-400">{{ ticker.signals_count }} сигналов</div>
              </div>
            </div>
          </div>

          <!-- Автор -->
          <div>
            <label class="block text-sm font-medium text-gray-300 mb-2">Автор</label>
            <select 
              v-model="filters.author"
              class="w-full px-3 py-2 bg-trading-bg border border-trading-border rounded text-white focus:border-trading-green focus:outline-none"
            >
              <option value="">Все авторы</option>
              <option v-for="author in availableAuthors" :key="author" :value="author">
                {{ author }}
              </option>
            </select>
          </div>

          <!-- Направление -->
          <div>
            <label class="block text-sm font-medium text-gray-300 mb-2">Направление</label>
            <select 
              v-model="filters.direction"
              class="w-full px-3 py-2 bg-trading-bg border border-trading-border rounded text-white focus:border-trading-green focus:outline-none"
            >
              <option value="all">Все направления</option>
              <option value="long">Long</option>
              <option value="short">Short</option>
              <option value="exit">Exit</option>
            </select>
          </div>

          <!-- Статус -->
          <div>
            <label class="block text-sm font-medium text-gray-300 mb-2">Статус</label>
            <select 
              v-model="filters.status"
              class="w-full px-3 py-2 bg-trading-bg border border-trading-border rounded text-white focus:border-trading-green focus:outline-none"
            >
              <option value="all">Все статусы</option>
              <option value="active">Активные</option>
              <option value="closed">Закрытые</option>
              <option value="stopped">Stopped</option>
            </select>
          </div>
        </div>

        <!-- Кнопки -->
        <div class="flex justify-between items-center">
          <button 
            @click="loadSignals"
            :disabled="isLoading"
            class="px-4 py-2 bg-trading-green hover:bg-green-600 text-black font-medium rounded transition-colors disabled:opacity-50"
          >
            🔍 Применить фильтры
          </button>
          <button 
            @click="clearFilters"
            class="px-4 py-2 bg-gray-600 hover:bg-gray-700 text-white font-medium rounded transition-colors"
          >
            🗑️ Сбросить
          </button>
          <button 
            @click="exportToCSV"
            :disabled="signals.length === 0"
            class="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded transition-colors disabled:opacity-50"
          >
            📥 Экспорт CSV
          </button>
        </div>
      </div>

      <!-- Loading -->
      <div v-if="isLoading" class="flex justify-center items-center p-12">
        <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-trading-green"></div>
      </div>

      <!-- Error -->
      <div v-else-if="error" class="bg-red-900/50 border border-red-700 rounded p-4 mb-6">
        <div class="text-red-200">⚠️ {{ error }}</div>
      </div>

      <!-- Signals List -->
      <div v-else-if="activeTab === 'signals'">
        <div v-if="signals.length > 0" class="p-4">
          <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            <div 
              v-for="signal in signals" 
              :key="signal.id"
              @click="onSignalClick(signal)"
              class="cursor-pointer"
            >
              <SignalCard 
                :signal="signal"
                :show-details="true"
              />
            </div>
          </div>
        </div>

        <div v-else class="p-8 text-center">
          <div class="text-6xl mb-4">🎯</div>
          <h3 class="text-lg font-semibold mb-2">Сигналов не найдено</h3>
          <p class="text-gray-400 mb-4">Попробуйте изменить фильтры или загрузить больше данных</p>
          <button 
            @click="clearFilters"
            class="px-4 py-2 bg-trading-green hover:bg-green-600 text-black rounded-md transition-colors"
          >
            🗑️ Сбросить фильтры
          </button>
        </div>
      </div>

      <!-- Failed Messages List -->
      <div v-else-if="activeTab === 'failed'">
        <div v-if="failedMessages.length === 0 && !isLoading" class="text-center py-12 bg-trading-card rounded-lg border border-trading-border">
          <p class="text-gray-400 text-lg">Failed сообщений не найдено</p>
          <p class="text-gray-500 text-sm mt-2">Все сообщения успешно распарсены! 🎉</p>
        </div>

        <div v-else class="space-y-4">
          <div
            v-for="message in failedMessages"
            :key="message.id"
            class="bg-trading-card rounded-lg p-4 border border-red-900/50 hover:border-red-500/50 transition-colors"
          >
            <div class="flex items-start justify-between mb-3">
              <div class="flex items-center gap-3">
                <span class="text-red-500 font-bold">❌ Failed</span>
                <span class="text-sm text-gray-400">ID: {{ message.id }}</span>
                <span class="text-xs text-gray-500">Channel: {{ message.channel_id }}</span>
              </div>
              <span class="text-sm text-gray-400">
                {{ formatDate(message.timestamp) }}
              </span>
            </div>

            <div v-if="message.author" class="flex items-center gap-2 mb-3">
              <span class="text-xs text-gray-400">Автор:</span>
              <span class="text-sm text-white">{{ message.author }}</span>
            </div>

            <div class="bg-trading-bg rounded p-3 border border-trading-border">
              <div class="flex justify-between items-center mb-2">
                <div class="text-xs text-gray-400">Текст сообщения ({{ message.text_length }} символов):</div>
              </div>
              <div class="text-sm text-gray-300 whitespace-pre-wrap">{{ message.text }}</div>
            </div>

            <div class="mt-3 flex gap-2">
              <button
                @click="copyToClipboard(message.text)"
                class="px-3 py-1 text-xs bg-blue-600 hover:bg-blue-700 rounded transition-colors"
              >
                📋 Копировать текст
              </button>
            </div>
          </div>
        </div>

        <!-- Pagination for Failed Messages -->
        <div v-if="failedMessages.length > 0" class="mt-6 flex justify-center gap-2">
          <button
            @click="prevFailedPage"
            :disabled="failedOffset === 0"
            class="px-4 py-2 bg-trading-card border border-trading-border rounded-lg hover:bg-trading-bg transition-colors disabled:opacity-50"
          >
            ← Назад
          </button>
          <span class="px-4 py-2 text-gray-400">
            Показано: {{ failedOffset + 1 }} - {{ failedOffset + failedMessages.length }} из {{ failedTotal }}
          </span>
          <button
            @click="nextFailedPage"
            :disabled="failedOffset + failedMessages.length >= failedTotal"
            class="px-4 py-2 bg-trading-card border border-trading-border rounded-lg hover:bg-trading-bg transition-colors disabled:opacity-50"
          >
            Вперед →
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import tradingAPI from '../services/api.js'
import SignalCard from '../components/SignalCard.vue'

const activeTab = ref('signals')
const isLoading = ref(false)
const error = ref(null)
const signals = ref([])
const failedMessages = ref([])
const signalsResponse = ref(null)
const signalsStats = ref(null)
const availableTickers = ref([])
const availableAuthors = ref([])

const tickerSearch = ref('')
const showTickerDropdown = ref(false)

const filters = ref({
  ticker: '',
  author: '',
  direction: 'all',
  status: 'all',
  period: '',
  order_by: 'timestamp',
  order_dir: 'desc'
})

const currentPage = ref(0)
const pageSize = ref(50)

const failedOffset = ref(0)
const failedLimit = ref(50)
const failedTotal = ref(0)

const filteredTickers = computed(() => {
  if (!tickerSearch.value) return availableTickers.value
  const search = tickerSearch.value.toLowerCase()
  return availableTickers.value.filter(t => 
    t.ticker.toLowerCase().includes(search)
  )
})

watch(activeTab, () => {
  if (activeTab.value === 'signals') {
    loadSignals()
  } else {
    loadFailedMessages()
  }
})

async function loadSignals() {
  try {
    isLoading.value = true
    error.value = null
    
    const params = {
      limit: pageSize.value,
      offset: currentPage.value * pageSize.value,
      order_by: filters.value.order_by,
      order_dir: filters.value.order_dir
    }
    
    if (filters.value.ticker) params.ticker = filters.value.ticker
    if (filters.value.author) params.author = filters.value.author
    if (filters.value.direction && filters.value.direction !== 'all') {
      params.direction = filters.value.direction
    }
    if (filters.value.status && filters.value.status !== 'all') {
      params.status = filters.value.status
    }
    
    const response = await tradingAPI.getSignals(params)
    signalsResponse.value = response
    signals.value = response.signals || []
    
  } catch (err) {
    error.value = 'Ошибка загрузки сигналов: ' + err.message
    signals.value = []
  } finally {
    isLoading.value = false
  }
}

async function loadFailedMessages() {
  try {
    isLoading.value = true
    error.value = null
    
    const response = await tradingAPI.getFailedMessages(failedLimit.value, failedOffset.value)
    failedMessages.value = response.messages || []
    failedTotal.value = response.count || 0
    
  } catch (err) {
    error.value = 'Ошибка загрузки failed сообщений: ' + err.message
    failedMessages.value = []
  } finally {
    isLoading.value = false
  }
}

async function loadTickers() {
  try {
    const response = await tradingAPI.getAvailableTickers()
    availableTickers.value = response
  } catch (err) {
    console.error('Failed to load tickers:', err)
  }
}

async function loadAuthors() {
  try {
    const response = await tradingAPI.getAvailableAuthors()
    availableAuthors.value = response
  } catch (err) {
    console.error('Failed to load authors:', err)
  }
}

async function loadStats() {
  try {
    const response = await tradingAPI.getSignalStats()
    signalsStats.value = response
  } catch (err) {
    console.error('Failed to load stats:', err)
  }
}

function handleTickerInput() {
  showTickerDropdown.value = true
}

function selectTicker(ticker) {
  filters.value.ticker = ticker
  tickerSearch.value = ticker
  showTickerDropdown.value = false
  loadSignals()
}

function clearFilters() {
  filters.value = {
    ticker: '',
    author: '',
    direction: 'all',
    status: 'all',
    period: '',
    order_by: 'timestamp',
    order_dir: 'desc'
  }
  tickerSearch.value = ''
  currentPage.value = 0
  loadSignals()
}

function onSignalClick(signal) {
  console.log('Signal clicked:', signal)
}

function handleClickOutside(event) {
  if (!event.target.closest('.relative')) {
    showTickerDropdown.value = false
  }
}

function exportToCSV() {
  const csvContent = [
    ['Ticker', 'Direction', 'Author', 'Timestamp', 'Target Price', 'Stop Loss', 'Take Profit'].join(','),
    ...signals.value.map(s => [
      s.ticker,
      s.direction || '',
      s.author || '',
      s.timestamp || '',
      s.target_price || '',
      s.stop_loss || '',
      s.take_profit || ''
    ].join(','))
  ].join('\n')
  
  const blob = new Blob([csvContent], { type: 'text/csv' })
  const url = window.URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `signals_${new Date().toISOString()}.csv`
  a.click()
  window.URL.revokeObjectURL(url)
}

function nextFailedPage() {
  failedOffset.value += failedLimit.value
  loadFailedMessages()
}

function prevFailedPage() {
  if (failedOffset.value >= failedLimit.value) {
    failedOffset.value -= failedLimit.value
    loadFailedMessages()
  }
}

function formatDate(dateString) {
  if (!dateString) return 'N/A'
  const date = new Date(dateString)
  return date.toLocaleString('ru-RU', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

function copyToClipboard(text) {
  navigator.clipboard.writeText(text).then(() => {
    alert('✅ Текст скопирован в буфер обмена')
  }).catch(err => {
    console.error('Failed to copy:', err)
  })
}

onMounted(async () => {
  document.addEventListener('click', handleClickOutside)
  
  await Promise.allSettled([
    loadTickers(),
    loadAuthors(),
    loadStats(),
    loadSignals()
  ])
})

onBeforeUnmount(() => {
  document.removeEventListener('click', handleClickOutside)
})
</script>

<style scoped>
/* Dropdown styles */
</style>