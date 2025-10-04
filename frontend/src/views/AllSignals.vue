<!-- frontend/src/views/AllSignals.vue -->
<template>
  <div class="min-h-screen bg-trading-bg text-white">
    <div class="max-w-7xl mx-auto p-4">
      
      <!-- Заголовок -->
      <div class="mb-8">
        <h1 class="text-3xl font-bold mb-2">🎯 Все торговые сигналы</h1>
        <p class="text-gray-400">Универсальный просмотр и фильтрация сигналов</p>
      </div>

      <!-- Панель фильтров -->
      <div class="bg-trading-card rounded-lg border border-trading-border p-6 mb-6">
        <h2 class="text-lg font-semibold mb-4">🔍 Фильтры</h2>
        
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
          <!-- Фильтр по тикеру -->
          <div>
            <label class="block text-sm font-medium text-gray-300 mb-2">Тикер</label>
            <select 
              v-model="filters.ticker" 
              @change="onFilterChange"
              class="w-full px-3 py-2 bg-trading-bg border border-trading-border rounded-md text-white focus:ring-2 focus:ring-trading-green"
            >
              <option value="">Все тикеры</option>
              <option v-for="ticker in availableTickers" :key="ticker.ticker" :value="ticker.ticker">
                {{ ticker.ticker }} ({{ ticker.signal_count }})
              </option>
            </select>
          </div>

          <!-- Фильтр по автору -->
          <div>
            <label class="block text-sm font-medium text-gray-300 mb-2">Автор</label>
            <select 
              v-model="filters.author" 
              @change="onFilterChange"
              class="w-full px-3 py-2 bg-trading-bg border border-trading-border rounded-md text-white focus:ring-2 focus:ring-trading-green"
            >
              <option value="">Все авторы</option>
              <option v-for="author in availableAuthors" :key="author" :value="author">
                {{ author }}
              </option>
            </select>
          </div>

          <!-- Фильтр по направлению -->
          <div>
            <label class="block text-sm font-medium text-gray-300 mb-2">Направление</label>
            <select 
              v-model="filters.direction" 
              @change="onFilterChange"
              class="w-full px-3 py-2 bg-trading-bg border border-trading-border rounded-md text-white focus:ring-2 focus:ring-trading-green"
            >
              <option value="all">Все</option>
              <option value="long">Long 📈</option>
              <option value="short">Short 📉</option>
              <option value="exit">Exit 🚪</option>
            </select>
          </div>

          <!-- Фильтр по статусу -->
          <div>
            <label class="block text-sm font-medium text-gray-300 mb-2">Статус</label>
            <select 
              v-model="filters.status" 
              @change="onFilterChange"
              class="w-full px-3 py-2 bg-trading-bg border border-trading-border rounded-md text-white focus:ring-2 focus:ring-trading-green"
            >
              <option value="all">Все</option>
              <option value="active">Активные 🟢</option>
              <option value="closed">Закрытые 🔴</option>
            </select>
          </div>
        </div>

        <!-- Временные фильтры -->
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
          <!-- Период -->
          <div>
            <label class="block text-sm font-medium text-gray-300 mb-2">Период</label>
            <select 
              v-model="filters.period" 
              @change="onFilterChange"
              class="w-full px-3 py-2 bg-trading-bg border border-trading-border rounded-md text-white focus:ring-2 focus:ring-trading-green"
            >
              <option value="">Все время</option>
              <option value="24h">Последние 24 часа</option>
              <option value="7d">Последние 7 дней</option>
              <option value="30d">Последние 30 дней</option>
              <option value="90d">Последние 90 дней</option>
            </select>
          </div>

          <!-- Сортировка -->
          <div>
            <label class="block text-sm font-medium text-gray-300 mb-2">Сортировка</label>
            <select 
              v-model="filters.order_by" 
              @change="onFilterChange"
              class="w-full px-3 py-2 bg-trading-bg border border-trading-border rounded-md text-white focus:ring-2 focus:ring-trading-green"
            >
              <option value="timestamp">По времени</option>
              <option value="ticker">По тикеру</option>
              <option value="author">По автору</option>
              <option value="confidence">По уверенности</option>
            </select>
          </div>

          <!-- Направление сортировки -->
          <div>
            <label class="block text-sm font-medium text-gray-300 mb-2">Направление</label>
            <select 
              v-model="filters.order_dir" 
              @change="onFilterChange"
              class="w-full px-3 py-2 bg-trading-bg border border-trading-border rounded-md text-white focus:ring-2 focus:ring-trading-green"
            >
              <option value="desc">Убывание ⬇️</option>
              <option value="asc">Возрастание ⬆️</option>
            </select>
          </div>
        </div>

        <!-- Кнопки действий -->
        <div class="flex flex-wrap gap-3 mt-4">
          <button 
            @click="clearFilters"
            class="px-4 py-2 bg-gray-600 hover:bg-gray-500 text-white rounded-md transition-colors"
          >
            🗑️ Очистить фильтры
          </button>
          
          <button 
            @click="exportSignals"
            class="px-4 py-2 bg-trading-green hover:bg-green-600 text-black rounded-md transition-colors"
          >
            📁 Экспорт
          </button>
          
          <button 
            @click="refreshSignals"
            :disabled="isLoading"
            class="px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white rounded-md transition-colors"
          >
            {{ isLoading ? '⏳' : '🔄' }} Обновить
          </button>
        </div>
      </div>

      <!-- Статистика -->
      <div v-if="signalsStats" class="bg-trading-card rounded-lg border border-trading-border p-6 mb-6">
        <h2 class="text-lg font-semibold mb-4">📊 Статистика</h2>
        
        <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div class="text-center">
            <div class="text-2xl font-bold text-white">{{ signalsStats.total_signals }}</div>
            <div class="text-sm text-gray-400">Всего сигналов</div>
          </div>
          
          <div class="text-center">
            <div class="text-2xl font-bold text-trading-green">
              {{ signalsStats.by_direction?.long || 0 }}
            </div>
            <div class="text-sm text-gray-400">Long сигналов</div>
          </div>
          
          <div class="text-center">
            <div class="text-2xl font-bold text-trading-red">
              {{ signalsStats.by_direction?.short || 0 }}
            </div>
            <div class="text-sm text-gray-400">Short сигналов</div>
          </div>
          
          <div class="text-center">
            <div class="text-2xl font-bold text-trading-yellow">
              {{ signalsStats.by_status?.active || 0 }}
            </div>
            <div class="text-sm text-gray-400">Активных</div>
          </div>
        </div>
      </div>

      <!-- Результаты -->
      <div class="bg-trading-card rounded-lg border border-trading-border">
        <div class="p-4 border-b border-trading-border flex justify-between items-center">
          <h2 class="text-lg font-semibold">
            🎯 Сигналы 
            <span v-if="signalsResponse?.count" class="text-gray-400">
              ({{ signalsResponse.count }})
            </span>
          </h2>
          
          <!-- Пагинация -->
          <div class="flex items-center gap-2">
            <button 
              @click="prevPage"
              :disabled="currentPage === 0 || isLoading"
              class="px-3 py-1 bg-gray-600 hover:bg-gray-500 disabled:opacity-50 rounded text-sm transition-colors"
            >
              ⬅️ Пред
            </button>
            
            <span class="text-sm text-gray-400">
              Страница {{ currentPage + 1 }}
            </span>
            
            <button 
              @click="nextPage"
              :disabled="!hasMorePages || isLoading"
              class="px-3 py-1 bg-gray-600 hover:bg-gray-500 disabled:opacity-50 rounded text-sm transition-colors"
            >
              След ➡️
            </button>
          </div>
        </div>

        <!-- Состояние загрузки -->
        <div v-if="isLoading" class="p-8 text-center">
          <div class="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-trading-green"></div>
          <p class="mt-2 text-gray-400">Загрузка сигналов...</p>
        </div>

        <!-- Ошибка -->
        <div v-else-if="error" class="p-8 text-center">
          <div class="text-trading-red mb-2">❌ Ошибка загрузки</div>
          <p class="text-gray-400">{{ error }}</p>
          <button 
            @click="loadSignals"
            class="mt-4 px-4 py-2 bg-trading-green hover:bg-green-600 text-black rounded-md transition-colors"
          >
            🔄 Попробовать снова
          </button>
        </div>

        <!-- Список сигналов -->
        <div v-else-if="signals.length > 0" class="divide-y divide-trading-border">
          <SignalCard 
            v-for="signal in signals" 
            :key="signal.id"
            :signal="signal"
            :show-details="true"
            @click="onSignalClick"
            class="hover:bg-trading-bg transition-colors"
          />
        </div>

        <!-- Пустое состояние -->
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
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { tradingAPI } from '../services/api.js'
import SignalCard from '../components/SignalCard.vue'

// Состояние
const isLoading = ref(false)
const error = ref(null)
const signals = ref([])
const signalsResponse = ref(null)
const signalsStats = ref(null)
const availableTickers = ref([])
const availableAuthors = ref([])

// Фильтры
const filters = ref({
  ticker: '',
  author: '',
  direction: 'all',
  status: 'all',
  period: '',
  order_by: 'timestamp',
  order_dir: 'desc'
})

// Пагинация
const currentPage = ref(0)
const pageSize = ref(50)

// Computed
const hasMorePages = computed(() => {
  return signalsResponse.value?.pagination?.has_more || false
})

// Методы
async function loadSignals() {
  if (isLoading.value) return
  
  isLoading.value = true
  error.value = null
  
  try {
    console.log('🎯 Loading signals with filters:', filters.value)
    
    // Подготавливаем параметры запроса
    const params = {
      limit: pageSize.value,
      offset: currentPage.value * pageSize.value,
      order_by: filters.value.order_by,
      order_dir: filters.value.order_dir,
      direction: filters.value.direction,
      status: filters.value.status,
      include_stats: true
    }
    
    // Добавляем фильтры только если они заданы
    if (filters.value.ticker) params.ticker = filters.value.ticker
    if (filters.value.author) params.author = filters.value.author
    
    // Обрабатываем временные фильтры
    if (filters.value.period) {
      switch (filters.value.period) {
        case '24h':
          params.hours_back = 24
          break
        case '7d':
          params.days_back = 7
          break
        case '30d':
          params.days_back = 30
          break
        case '90d':
          params.days_back = 90
          break
      }
    }
    
    // Загружаем сигналы
    const response = await tradingAPI.getSignals(params)
    
    signalsResponse.value = response
    signals.value = response.signals || []
    signalsStats.value = response.stats
    
    console.log('✅ Signals loaded:', {
      count: response.count,
      has_stats: !!response.stats,
      has_more: response.pagination?.has_more
    })
    
  } catch (err) {
    console.error('❌ Error loading signals:', err)
    error.value = err.message
  } finally {
    isLoading.value = false
  }
}

async function loadTickers() {
  try {
    console.log('📋 Loading available tickers...')
    const tickers = await tradingAPI.getAvailableTickers(true)
    availableTickers.value = tickers
    console.log('✅ Tickers loaded:', tickers.length)
  } catch (err) {
    console.error('❌ Error loading tickers:', err)
  }
}

async function loadAuthors() {
  try {
    // Получаем статистику для извлечения авторов
    const stats = await tradingAPI.getSignalsStats()
    availableAuthors.value = stats.top_authors?.map(a => a.author) || []
    console.log('✅ Authors loaded:', availableAuthors.value.length)
  } catch (err) {
    console.error('❌ Error loading authors:', err)
  }
}

function onFilterChange() {
  console.log('🔍 Filter changed:', filters.value)
  currentPage.value = 0  // Сброс на первую страницу
  loadSignals()
}

function clearFilters() {
  console.log('🗑️ Clearing filters')
  filters.value = {
    ticker: '',
    author: '',
    direction: 'all',
    status: 'all',
    period: '',
    order_by: 'timestamp',
    order_dir: 'desc'
  }
  currentPage.value = 0
  loadSignals()
}

function refreshSignals() {
  console.log('🔄 Refreshing signals')
  loadSignals()
}

function nextPage() {
  if (!hasMorePages.value || isLoading.value) return
  currentPage.value++
  loadSignals()
}

function prevPage() {
  if (currentPage.value === 0 || isLoading.value) return
  currentPage.value--
  loadSignals()
}

function onSignalClick(signal) {
  console.log('🎯 Signal clicked:', signal)
  // Можно добавить логику для открытия детального просмотра
  // Например, модальное окно или переход на отдельную страницу
}

function exportSignals() {
  if (signals.value.length === 0) return
  
  // Простой экспорт в CSV
  const headers = ['Время', 'Тикер', 'Направление', 'Автор', 'Статус', 'Цена']
  const rows = signals.value.map(signal => [
    new Date(signal.timestamp).toLocaleString('ru-RU'),
    signal.ticker,
    signal.direction,
    signal.author || 'Неизвестно',
    signal.status || 'Неизвестно',
    signal.target_price || ''
  ])
  
  const csvContent = [headers, ...rows]
    .map(row => row.map(cell => `"${cell}"`).join(','))
    .join('\n')
  
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
  const link = document.createElement('a')
  link.href = URL.createObjectURL(blob)
  link.download = `signals_${new Date().toISOString().split('T')[0]}.csv`
  link.click()
  
  console.log('📁 Signals exported to CSV')
}

// Lifecycle
onMounted(async () => {
  console.log('🚀 AllSignals page mounted')
  
  // Загружаем данные параллельно
  await Promise.allSettled([
    loadTickers(),
    loadAuthors(),
    loadSignals()
  ])
})
</script>

<style scoped>
/* Дополнительные стили для красивых переходов */
.signal-card {
  transition: all 0.2s ease-in-out;
}

.signal-card:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0, 212, 170, 0.1);
}

/* Анимация загрузки */
@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.animate-spin {
  animation: spin 1s linear infinite;
}

/* Стили для селектов */
select {
  background-image: url("data:image/svg+xml,%3csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 20 20'%3e%3cpath stroke='%236b7280' stroke-linecap='round' stroke-linejoin='round' stroke-width='1.5' d='M6 8l4 4 4-4'/%3e%3c/svg%3e");
  background-position: right 0.5rem center;
  background-repeat: no-repeat;
  background-size: 1.5em 1.5em;
  padding-right: 2.5rem;
}
</style>