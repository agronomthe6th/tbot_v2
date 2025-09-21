<!-- frontend/src/components/charts/ChartControls.vue -->
<template>
  <div class="chart-controls">
    <div class="controls-grid">
      <!-- Выбор тикера -->
      <div class="control-group">
        <label class="control-label">Тикер</label>
        <div class="ticker-selector">
          <select 
            :value="selectedTicker" 
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
          
          <!-- Кнопка обновления списка тикеров -->
          <button 
            @click="handleRefreshTickers"
            class="refresh-btn"
            :disabled="isLoadingTickers"
            title="Обновить список тикеров"
          >
            <div v-if="isLoadingTickers" class="w-4 h-4 border-2 border-gray-400 border-t-transparent rounded-full animate-spin"></div>
            <svg v-else class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path>
            </svg>
          </button>
        </div>
      </div>

      <!-- Период данных -->
      <div class="control-group">
        <label class="control-label">Период</label>
        <select 
          :value="chartDays" 
          @change="handleDaysChange"
          class="period-select"
          :disabled="isLoading"
        >
          <option :value="1">1 день</option>
          <option :value="3">3 дня</option>
          <option :value="7">7 дней</option>
          <option :value="14">14 дней</option>
          <option :value="30">30 дней</option>
          <option :value="90">90 дней</option>
        </select>
      </div>

      <!-- Автообновление -->
      <div class="control-group">
        <label class="control-label">Автообновление</label>
        <div class="auto-refresh-toggle">
          <button 
            @click="toggleAutoRefresh"
            class="toggle-btn"
            :class="{ 'toggle-active': autoRefresh }"
            :disabled="isLoading"
          >
            <span class="toggle-indicator"></span>
            <span class="text-sm">{{ autoRefresh ? 'Вкл' : 'Выкл' }}</span>
          </button>
          
          <select 
            v-if="autoRefresh"
            v-model="autoRefreshInterval"
            class="interval-select"
            :disabled="isLoading"
          >
            <option :value="10">10 сек</option>
            <option :value="30">30 сек</option>
            <option :value="60">1 мин</option>
            <option :value="300">5 мин</option>
          </select>
        </div>
      </div>

      <!-- Действия -->
      <div class="control-group actions-group">
        <button 
          @click="handleRefresh"
          class="action-btn refresh"
          :disabled="isLoading"
          title="Обновить данные"
        >
          <div v-if="isLoading" class="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
          <svg v-else class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path>
          </svg>
          <span class="hidden sm:inline">Обновить</span>
        </button>

        <button 
          @click="handleResetView"
          class="action-btn secondary"
          :disabled="isLoading || !hasData"
          title="Сбросить масштаб"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path>
          </svg>
          <span class="hidden sm:inline">Сброс</span>
        </button>
      </div>
    </div>

    <!-- Статус и ошибки -->
    <div v-if="error" class="error-message">
      <div class="flex items-center space-x-2">
        <svg class="w-4 h-4 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
        </svg>
        <span class="text-sm">{{ error }}</span>
        <button @click="clearError" class="text-red-400 hover:text-red-300">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
          </svg>
        </button>
      </div>
    </div>

    <!-- Информация о последнем обновлении -->
    <div v-if="lastUpdate && !error" class="status-info">
      <div class="flex items-center justify-between text-xs text-gray-400">
        <div class="flex items-center space-x-2">
          <div class="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
          <span>Последнее обновление: {{ formatLastUpdate }}</span>
        </div>
        <div v-if="autoRefresh" class="flex items-center space-x-1">
          <span>Следующее через: {{ nextUpdateIn }}с</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'

// Props
const props = defineProps({
  selectedTicker: {
    type: String,
    required: true
  },
  availableTickers: {
    type: Array,
    default: () => []
  },
  chartDays: {
    type: Number,
    default: 7
  },
  isLoading: {
    type: Boolean,
    default: false
  },
  isLoadingTickers: {
    type: Boolean,
    default: false
  },
  hasData: {
    type: Boolean,
    default: false
  },
  error: {
    type: String,
    default: null
  },
  lastUpdate: {
    type: Date,
    default: null
  }
})

// Events
const emit = defineEmits([
  'ticker-change',
  'days-change',
  'refresh',
  'refresh-tickers',
  'reset-view',
  'clear-error'
])

// State
const autoRefresh = ref(false)
const autoRefreshInterval = ref(60) // секунды
const countdown = ref(0)

let refreshTimer = null
let countdownTimer = null

// Computed
const formatLastUpdate = computed(() => {
  if (!props.lastUpdate) return '—'
  return props.lastUpdate.toLocaleTimeString('ru-RU')
})

const nextUpdateIn = computed(() => countdown.value)

// Methods
function handleTickerChange(event) {
  const newTicker = event.target.value
  if (newTicker && newTicker !== props.selectedTicker) {
    emit('ticker-change', newTicker)
  }
}

function handleDaysChange(event) {
  const newDays = parseInt(event.target.value)
  if (newDays && newDays !== props.chartDays) {
    emit('days-change', newDays)
  }
}

function handleRefresh() {
  emit('refresh')
  resetCountdown()
}

function handleRefreshTickers() {
  emit('refresh-tickers')
}

function handleResetView() {
  emit('reset-view')
}

function clearError() {
  emit('clear-error')
}

function toggleAutoRefresh() {
  autoRefresh.value = !autoRefresh.value
  
  if (autoRefresh.value) {
    startAutoRefresh()
  } else {
    stopAutoRefresh()
  }
}

function startAutoRefresh() {
  stopAutoRefresh() // Очищаем предыдущие таймеры
  
  resetCountdown()
  
  refreshTimer = setInterval(() => {
    handleRefresh()
  }, autoRefreshInterval.value * 1000)
  
  countdownTimer = setInterval(() => {
    countdown.value--
    if (countdown.value <= 0) {
      resetCountdown()
    }
  }, 1000)
}

function stopAutoRefresh() {
  if (refreshTimer) {
    clearInterval(refreshTimer)
    refreshTimer = null
  }
  
  if (countdownTimer) {
    clearInterval(countdownTimer)
    countdownTimer = null
  }
  
  countdown.value = 0
}

function resetCountdown() {
  countdown.value = autoRefreshInterval.value
}

// Watchers
function watchAutoRefreshInterval() {
  if (autoRefresh.value) {
    startAutoRefresh()
  }
}

// Lifecycle
onMounted(() => {
  // Автообновление можно включить по умолчанию
  // autoRefresh.value = true
  // startAutoRefresh()
})

onBeforeUnmount(() => {
  stopAutoRefresh()
})

// Watch changes in interval
const intervalWatcher = () => {
  watchAutoRefreshInterval()
}
</script>

<style scoped>
.chart-controls {
  @apply bg-trading-card border border-trading-border rounded-lg p-4 space-y-4;
}

.controls-grid {
  @apply grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4;
}

.control-group {
  @apply space-y-2;
}

.actions-group {
  @apply flex flex-col sm:flex-row gap-2;
}

.control-label {
  @apply block text-sm font-medium text-gray-300;
}

.ticker-selector {
  @apply flex space-x-2;
}

.ticker-select,
.period-select,
.interval-select {
  @apply flex-1 bg-trading-bg border border-trading-border rounded px-3 py-2;
  @apply text-white text-sm focus:outline-none focus:ring-2 focus:ring-trading-green focus:border-transparent;
  @apply disabled:opacity-50 disabled:cursor-not-allowed;
}

.ticker-select {
  @apply min-w-0; /* Разрешаем сжатие */
}

.refresh-btn {
  @apply px-3 py-2 bg-trading-bg border border-trading-border rounded;
  @apply text-gray-300 hover:text-white hover:bg-gray-600;
  @apply disabled:opacity-50 disabled:cursor-not-allowed;
  @apply transition-colors duration-200;
}

.auto-refresh-toggle {
  @apply flex space-x-2;
}

.toggle-btn {
  @apply flex items-center space-x-2 px-3 py-2 rounded border;
  @apply border-trading-border bg-trading-bg text-gray-300;
  @apply hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed;
  @apply transition-all duration-200;
}

.toggle-active {
  @apply border-trading-green bg-trading-green/20 text-trading-green;
}

.toggle-indicator {
  @apply w-2 h-2 rounded-full bg-current;
}

.action-btn {
  @apply flex items-center justify-center space-x-2 px-4 py-2 rounded;
  @apply font-medium text-sm disabled:opacity-50 disabled:cursor-not-allowed;
  @apply transition-all duration-200;
}

.action-btn.refresh {
  @apply bg-trading-green text-black hover:bg-green-400;
}

.action-btn.secondary {
  @apply bg-trading-border text-gray-300 hover:bg-gray-500 hover:text-white;
}

.error-message {
  @apply bg-red-900/50 border border-red-700 rounded p-3 text-red-200;
}

.status-info {
  @apply border-t border-trading-border pt-3;
}

/* Адаптивность */
@media (max-width: 640px) {
  .controls-grid {
    @apply grid-cols-1;
  }
  
  .ticker-selector {
    @apply flex-col space-y-2 space-x-0;
  }
  
  .auto-refresh-toggle {
    @apply flex-col space-y-2 space-x-0;
  }
}
</style>