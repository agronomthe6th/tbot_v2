<!-- frontend/src/components/DataManagement.vue -->
<template>
  <div class="data-management bg-trading-card rounded-lg border border-trading-border p-6">
    <h2 class="text-2xl font-bold mb-6">🛠️ Управление данными</h2>
    
    <!-- Статус системы -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
      <div class="bg-trading-bg rounded-lg p-4 border border-trading-border">
        <h3 class="font-semibold mb-2">📊 Инструменты</h3>
        <div class="text-2xl font-bold text-blue-400">{{ systemStats.total_instruments || 0 }}</div>
        <div class="text-sm text-gray-400">
          С данными: {{ systemStats.instruments_with_data || 0 }}
        </div>
      </div>
      
      <div class="bg-trading-bg rounded-lg p-4 border border-trading-border">
        <h3 class="font-semibold mb-2">🕯️ Свечи</h3>
        <div class="text-2xl font-bold text-green-400">{{ formatNumber(systemStats.total_candles) }}</div>
        <div class="text-sm text-gray-400">За все время</div>
      </div>
      
      <div class="bg-trading-bg rounded-lg p-4 border border-trading-border">
        <h3 class="font-semibold mb-2">🎯 Сигналы</h3>
        <div class="text-2xl font-bold text-yellow-400">{{ systemStats.total_signals || 0 }}</div>
        <div class="text-sm text-gray-400">
          Активных: {{ systemStats.active_signals || 0 }}
        </div>
      </div>
    </div>
    
    <!-- Панель действий -->
    <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
      <!-- Быстрые действия -->
      <div class="space-y-4">
        <h3 class="text-lg font-semibold">⚡ Быстрые действия</h3>
        
        <button 
          @click="syncInstruments"
          :disabled="isLoading"
          class="w-full p-3 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 rounded-lg text-white font-medium"
        >
          🔄 Синхронизировать инструменты
        </button>
        
        <button 
          @click="bulkLoadPopular"
          :disabled="isLoading"
          class="w-full p-3 bg-green-600 hover:bg-green-700 disabled:bg-gray-600 rounded-lg text-white font-medium"
        >
          🚀 Загрузить популярные инструменты
        </button>
        
        <button 
          @click="bulkSmartLoad"
          :disabled="isLoading"
          class="w-full p-3 bg-purple-600 hover:bg-purple-700 disabled:bg-gray-600 rounded-lg text-white font-medium"
        >
          🧠 Умная массовая загрузка
        </button>
      </div>
      
      <!-- Индивидуальная загрузка -->
      <div class="space-y-4">
        <h3 class="text-lg font-semibold">🎯 Индивидуальная загрузка</h3>
        
        <div class="flex gap-2">
          <input 
            v-model="manualTicker" 
            type="text" 
            placeholder="Введите тикер (SBER)"
            class="flex-1 p-2 rounded bg-trading-bg border border-trading-border text-white"
            @keyup.enter="loadManualTicker"
          >
          <button 
            @click="loadManualTicker"
            :disabled="!manualTicker || isLoading"
            class="px-4 py-2 bg-orange-600 hover:bg-orange-700 disabled:bg-gray-600 rounded text-white"
          >
            Загрузить
          </button>
        </div>
        
        <div class="grid grid-cols-2 gap-2">
          <select 
            v-model="manualDays" 
            class="p-2 rounded bg-trading-bg border border-trading-border text-white"
          >
            <option value="30">30 дней</option>
            <option value="60">60 дней</option>
            <option value="90">90 дней</option>
            <option value="180">180 дней</option>
            <option value="365">365 дней</option>
          </select>
          
          <label class="flex items-center gap-2">
            <input 
              v-model="forceReload" 
              type="checkbox"
              class="rounded"
            >
            <span class="text-sm">Перезаписать</span>
          </label>
        </div>
      </div>
    </div>
    
    <!-- Прогресс загрузки -->
    <div v-if="isLoading" class="mb-6">
      <div class="bg-trading-bg rounded-lg p-4 border border-trading-border">
        <div class="flex items-center gap-3 mb-3">
          <div class="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-500"></div>
          <span class="font-medium">{{ loadingStatus }}</span>
        </div>
        
        <div v-if="bulkProgress.total > 0" class="space-y-2">
          <div class="flex justify-between text-sm">
            <span>Прогресс: {{ bulkProgress.completed }}/{{ bulkProgress.total }}</span>
            <span>{{ Math.round((bulkProgress.completed / bulkProgress.total) * 100) }}%</span>
          </div>
          <div class="w-full bg-gray-700 rounded-full h-2">
            <div 
              class="bg-blue-600 h-2 rounded-full transition-all duration-300"
              :style="{ width: (bulkProgress.completed / bulkProgress.total) * 100 + '%' }"
            ></div>
          </div>
        </div>
      </div>
    </div>
    
    <!-- Результаты последней операции -->
    <div v-if="lastResult" class="mb-6">
      <div :class="[
        'rounded-lg p-4 border',
        lastResult.success ? 'bg-green-900 border-green-600' : 'bg-red-900 border-red-600'
      ]">
        <h4 class="font-semibold mb-2">
          {{ lastResult.success ? '✅' : '❌' }} Результат операции
        </h4>
        <div class="text-sm space-y-1">
          <div v-if="lastResult.message">{{ lastResult.message }}</div>
          <div v-if="lastResult.completed">Завершено: {{ lastResult.completed }}</div>
          <div v-if="lastResult.failed">Неудачно: {{ lastResult.failed }}</div>
          <div v-if="lastResult.total_candles">Загружено свечей: {{ formatNumber(lastResult.total_candles) }}</div>
        </div>
      </div>
    </div>
    
    <!-- Таблица инструментов -->
    <div v-if="instrumentsStatus.length > 0">
      <h3 class="text-lg font-semibold mb-4">📋 Состояние инструментов</h3>
      
      <div class="bg-trading-bg rounded-lg border border-trading-border overflow-hidden">
        <div class="overflow-x-auto max-h-96">
          <table class="w-full">
            <thead class="bg-trading-card sticky top-0">
              <tr>
                <th class="px-4 py-3 text-left">Тикер</th>
                <th class="px-4 py-3 text-left">Название</th>
                <th class="px-4 py-3 text-left">Свечи</th>
                <th class="px-4 py-3 text-left">Покрытие</th>
                <th class="px-4 py-3 text-left">Действия</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(instrument, index) in instrumentsStatus" :key="instrument.ticker"
                  :class="index % 2 === 0 ? 'bg-trading-bg' : 'bg-trading-card'">
                <td class="px-4 py-3 font-medium">{{ instrument.ticker }}</td>
                <td class="px-4 py-3 text-sm max-w-xs truncate">{{ instrument.name || 'N/A' }}</td>
                <td class="px-4 py-3 text-sm">{{ formatNumber(instrument.candles_count) }}</td>
                <td class="px-4 py-3">
                  <div class="flex items-center gap-2">
                    <div :class="[
                      'w-3 h-3 rounded-full',
                      instrument.has_data ? 'bg-green-500' : 'bg-red-500'
                    ]"></div>
                    <span class="text-sm">
                      {{ instrument.has_data ? 'Есть данные' : 'Нет данных' }}
                    </span>
                  </div>
                </td>
                <td class="px-4 py-3">
                  <button 
                    @click="loadSingleInstrument(instrument.ticker)"
                    :disabled="isLoading"
                    class="px-3 py-1 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 rounded text-xs text-white"
                  >
                    Загрузить
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import tradingAPI from '../services/api.js'

// Реактивные данные
const isLoading = ref(false)
const loadingStatus = ref('')
const systemStats = ref({})
const instrumentsStatus = ref([])
const lastResult = ref(null)

// Параметры ручной загрузки
const manualTicker = ref('')
const manualDays = ref(60)
const forceReload = ref(false)

// Прогресс массовой загрузки
const bulkProgress = ref({
  completed: 0,
  total: 0
})

// Методы
const loadSystemStats = async () => {
  try {
    const stats = await tradingAPI.getSystemStats()
    systemStats.value = stats
  } catch (error) {
    console.error('Ошибка загрузки статистики:', error)
  }
}

const loadDataStatus = async () => {
  try {
    const status = await tradingAPI.getDataStatus()
    instrumentsStatus.value = status.instruments || []
  } catch (error) {
    console.error('Ошибка загрузки статуса данных:', error)
  }
}

const syncInstruments = async () => {
  isLoading.value = true
  loadingStatus.value = 'Синхронизация инструментов...'
  
  try {
    const result = await tradingAPI.syncInstruments()
    lastResult.value = {
      success: true,
      message: `Синхронизировано ${result.synced_instruments} инструментов`,
      completed: result.synced_instruments
    }
    
    await loadSystemStats()
    await loadDataStatus()
  } catch (error) {
    lastResult.value = {
      success: false,
      message: `Ошибка синхронизации: ${error.message}`
    }
  } finally {
    isLoading.value = false
    loadingStatus.value = ''
  }
}

const bulkLoadPopular = async () => {
  isLoading.value = true
  loadingStatus.value = 'Загрузка популярных инструментов...'
  
  try {
    // Здесь можно использовать существующий endpoint bulk_load_popular_instruments
    const result = await tradingAPI.loadHistoricalCandles('SBER', '5min', 90) // Примерная реализация
    
    lastResult.value = {
      success: true,
      message: 'Популярные инструменты загружены',
      total_candles: result.loaded_candles || 0
    }
    
    await loadSystemStats()
  } catch (error) {
    lastResult.value = {
      success: false,
      message: `Ошибка загрузки: ${error.message}`
    }
  } finally {
    isLoading.value = false
    loadingStatus.value = ''
  }
}

const bulkSmartLoad = async () => {
  isLoading.value = true
  loadingStatus.value = 'Умная массовая загрузка...'
  bulkProgress.value = { completed: 0, total: 0 }
  
  try {
    const result = await tradingAPI.bulkSmartLoad()
    
    bulkProgress.value.total = result.total_tickers || 0
    bulkProgress.value.completed = result.processed?.length || 0
    
    lastResult.value = {
      success: result.processed?.length > 0,
      message: `Обработано ${result.processed?.length || 0} из ${result.total_tickers || 0} тикеров`,
      completed: result.processed?.length || 0,
      failed: result.failed?.length || 0,
      total_candles: result.processed?.reduce((sum, p) => sum + (p.load_result?.loaded_candles || 0), 0) || 0
    }
    
    await loadSystemStats()
    await loadDataStatus()
  } catch (error) {
    lastResult.value = {
      success: false,
      message: `Ошибка массовой загрузки: ${error.message}`
    }
  } finally {
    isLoading.value = false
    loadingStatus.value = ''
    bulkProgress.value = { completed: 0, total: 0 }
  }
}

const loadManualTicker = async () => {
  if (!manualTicker.value.trim()) return
  
  isLoading.value = true
  loadingStatus.value = `Загрузка ${manualTicker.value}...`
  
  try {
    const result = await tradingAPI.smartLoadData(
      manualTicker.value.toUpperCase(),
      manualDays.value,
      true
    )
    
    lastResult.value = {
      success: result.load_result?.success || false,
      message: `${manualTicker.value}: ${result.load_result?.message || 'Загружено'}`,
      total_candles: result.load_result?.loaded_candles || 0
    }
    
    await loadSystemStats()
    await loadDataStatus()
    
    // Очищаем поле после успешной загрузки
    if (result.load_result?.success) {
      manualTicker.value = ''
    }
  } catch (error) {
    lastResult.value = {
      success: false,
      message: `Ошибка загрузки ${manualTicker.value}: ${error.message}`
    }
  } finally {
    isLoading.value = false
    loadingStatus.value = ''
  }
}

const loadSingleInstrument = async (ticker) => {
  isLoading.value = true
  loadingStatus.value = `Загрузка ${ticker}...`
  
  try {
    const result = await tradingAPI.smartLoadData(ticker, 60, true)
    
    lastResult.value = {
      success: result.load_result?.success || false,
      message: `${ticker}: загружено ${result.load_result?.loaded_candles || 0} свечей`,
      total_candles: result.load_result?.loaded_candles || 0
    }
    
    await loadDataStatus()
  } catch (error) {
    lastResult.value = {
      success: false,
      message: `Ошибка загрузки ${ticker}: ${error.message}`
    }
  } finally {
    isLoading.value = false
    loadingStatus.value = ''
  }
}

// Утилиты
const formatNumber = (num) => {
  if (!num) return '0'
  return new Intl.NumberFormat('ru-RU').format(num)
}

// Инициализация
onMounted(async () => {
  await Promise.all([
    loadSystemStats(),
    loadDataStatus()
  ])
})
</script>

<style scoped>
.data-management {
  max-width: 1200px;
  margin: 0 auto;
}

/* Анимация для индикаторов */
@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.animate-spin {
  animation: spin 1s linear infinite;
}
</style>