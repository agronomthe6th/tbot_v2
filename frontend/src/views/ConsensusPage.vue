<template>
  <div class="min-h-screen bg-trading-bg text-white p-4">
    <div class="max-w-7xl mx-auto">
      
      <!-- Заголовок -->
      <div class="mb-8">
        <h1 class="text-3xl font-bold mb-2">🔥 Консенсус Трейдеров</h1>
        <p class="text-gray-400">
          Моменты когда несколько трейдеров независимо дают сигналы на один актив
        </p>
      </div>

      <!-- Статистика -->
      <div v-if="stats" class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <div class="bg-trading-card p-4 rounded-lg border border-trading-border">
          <div class="text-gray-400 text-sm mb-1">Всего консенсусов</div>
          <div class="text-2xl font-bold">{{ stats.total || 0 }}</div>
        </div>
        
        <div class="bg-trading-card p-4 rounded-lg border border-trading-border">
          <div class="text-gray-400 text-sm mb-1">Активные</div>
          <div class="text-2xl font-bold text-trading-green">
            {{ stats.by_status?.active || 0 }}
          </div>
        </div>
        
        <div class="bg-trading-card p-4 rounded-lg border border-trading-border">
          <div class="text-gray-400 text-sm mb-1">Средняя сила</div>
          <div class="text-2xl font-bold">
            {{ Math.round(stats.avg_strength || 0) }}/100
          </div>
        </div>
        
        <div class="bg-trading-card p-4 rounded-lg border border-trading-border">
          <div class="text-gray-400 text-sm mb-1">Период</div>
          <div class="text-2xl font-bold">{{ stats.period_days || 30 }} дней</div>
        </div>
      </div>

      <!-- Фильтры -->
      <div class="bg-trading-card p-4 rounded-lg border border-trading-border mb-6">
        <div class="grid grid-cols-1 md:grid-cols-5 gap-4">
          <div>
            <label class="block text-sm text-gray-400 mb-2">Тикер</label>
            <input 
              v-model="filters.ticker" 
              @change="applyFilters"
              type="text" 
              placeholder="SBER, GAZP..."
              class="w-full bg-trading-bg border border-trading-border rounded px-3 py-2 text-white"
            />
          </div>
          
          <div>
            <label class="block text-sm text-gray-400 mb-2">Направление</label>
            <select 
              v-model="filters.direction" 
              @change="applyFilters"
              class="w-full bg-trading-bg border border-trading-border rounded px-3 py-2 text-white"
            >
              <option value="">Все</option>
              <option value="long">LONG</option>
              <option value="short">SHORT</option>
            </select>
          </div>
          
          <div>
            <label class="block text-sm text-gray-400 mb-2">Статус</label>
            <select 
              v-model="filters.status" 
              @change="applyFilters"
              class="w-full bg-trading-bg border border-trading-border rounded px-3 py-2 text-white"
            >
              <option value="all">Все</option>
              <option value="active">Активные</option>
              <option value="closed">Закрытые</option>
            </select>
          </div>
          
          <div>
            <label class="block text-sm text-gray-400 mb-2">Мин. сила</label>
            <input 
              v-model.number="filters.min_strength" 
              @change="applyFilters"
              type="number" 
              min="0" 
              max="100"
              placeholder="0-100"
              class="w-full bg-trading-bg border border-trading-border rounded px-3 py-2 text-white"
            />
          </div>
          
          <div>
            <label class="block text-sm text-gray-400 mb-2">Период</label>
            <select 
              v-model.number="filters.days_back" 
              @change="applyFilters"
              class="w-full bg-trading-bg border border-trading-border rounded px-3 py-2 text-white"
            >
              <option :value="7">7 дней</option>
              <option :value="30">30 дней</option>
              <option :value="90">90 дней</option>
            </select>
          </div>
        </div>
        
        <div class="mt-4 flex gap-2">
          <button 
            @click="resetFilters"
            class="px-4 py-2 bg-trading-bg border border-trading-border rounded hover:bg-gray-700 transition-colors"
          >
            Сбросить
          </button>
          
          <button 
            @click="triggerDetection"
            :disabled="isDetecting"
            class="px-4 py-2 bg-trading-green text-black rounded hover:bg-green-500 transition-colors disabled:opacity-50"
          >
            {{ isDetecting ? 'Поиск...' : '🔍 Найти консенсусы' }}
          </button>
        </div>
      </div>

      <!-- Список консенсусов -->
      <div v-if="isLoading" class="text-center py-12">
        <div class="text-gray-400">Загрузка консенсусов...</div>
      </div>

      <div v-else-if="error" class="bg-red-900/20 border border-red-500 rounded-lg p-4 mb-6">
        <div class="text-red-400">{{ error }}</div>
      </div>

      <div v-else-if="consensusEvents.length === 0" class="text-center py-12">
        <div class="text-gray-400 mb-4">Консенсусы не найдены</div>
        <button 
          @click="triggerDetection"
          class="px-6 py-3 bg-trading-green text-black rounded-lg hover:bg-green-500 transition-colors"
        >
          🔍 Запустить поиск консенсусов
        </button>
      </div>

      <div v-else class="space-y-4">
        <div 
          v-for="consensus in consensusEvents" 
          :key="consensus.id"
          @click="showConsensusDetails(consensus)"
          class="bg-trading-card p-4 rounded-lg border border-trading-border hover:border-trading-green transition-colors cursor-pointer"
        >
          <div class="flex items-start justify-between mb-3">
            <div class="flex items-center gap-3">
              <div class="text-2xl font-bold">{{ consensus.ticker }}</div>
              <div 
                :class="{
                  'text-trading-green': consensus.direction === 'long',
                  'text-trading-red': consensus.direction === 'short'
                }"
                class="px-3 py-1 rounded text-sm font-semibold"
              >
                {{ consensus.direction === 'long' ? '📈 LONG' : '📉 SHORT' }}
              </div>
              
              <div class="px-3 py-1 bg-trading-bg rounded text-sm">
                💪 Сила: {{ consensus.consensus_strength }}/100
              </div>
            </div>
            
            <div class="text-right text-sm text-gray-400">
              {{ formatDate(consensus.detected_at) }}
            </div>
          </div>
          
          <div class="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm mb-3">
            <div>
              <div class="text-gray-400">Трейдеров</div>
              <div class="font-semibold">{{ consensus.traders_count }}</div>
            </div>
            
            <div>
              <div class="text-gray-400">Сигналов</div>
              <div class="font-semibold">{{ consensus.signals_count }}</div>
            </div>
            
            <div>
              <div class="text-gray-400">Окно</div>
              <div class="font-semibold">{{ consensus.window_minutes }} мин</div>
            </div>
            
            <div>
              <div class="text-gray-400">Средняя цена</div>
              <div class="font-semibold">
                {{ consensus.avg_entry_price ? consensus.avg_entry_price.toFixed(2) + ' ₽' : '—' }}
              </div>
            </div>
          </div>
          
          <div v-if="consensus.authors && consensus.authors.length > 0" class="flex flex-wrap gap-2">
            <span 
              v-for="author in consensus.authors.slice(0, 5)" 
              :key="author"
              class="px-2 py-1 bg-trading-bg rounded text-xs text-gray-300"
            >
              {{ author }}
            </span>
            <span 
              v-if="consensus.authors.length > 5"
              class="px-2 py-1 bg-trading-bg rounded text-xs text-gray-400"
            >
              +{{ consensus.authors.length - 5 }}
            </span>
          </div>
        </div>
      </div>

      <!-- Пагинация -->
      <div v-if="totalConsensus > filters.limit" class="mt-6 flex justify-center gap-2">
        <button 
          @click="prevPage"
          :disabled="currentPage === 1"
          class="px-4 py-2 bg-trading-card border border-trading-border rounded hover:bg-gray-700 disabled:opacity-50 transition-colors"
        >
          ← Предыдущая
        </button>
        
        <div class="px-4 py-2 bg-trading-card border border-trading-border rounded">
          Страница {{ currentPage }} из {{ totalPages }}
        </div>
        
        <button 
          @click="nextPage"
          :disabled="currentPage === totalPages"
          class="px-4 py-2 bg-trading-card border border-trading-border rounded hover:bg-gray-700 disabled:opacity-50 transition-colors"
        >
          Следующая →
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { tradingAPI } from '../services/api'

const isLoading = ref(false)
const isDetecting = ref(false)
const error = ref(null)
const consensusEvents = ref([])
const stats = ref(null)
const totalConsensus = ref(0)
const currentPage = ref(1)

const filters = ref({
  ticker: '',
  direction: '',
  status: 'all',
  min_strength: null,
  days_back: 30,
  limit: 20
})

const totalPages = computed(() => {
  return Math.ceil(totalConsensus.value / filters.value.limit)
})

async function loadConsensusEvents() {
  isLoading.value = true
  error.value = null
  
  try {
    console.log('📊 Loading consensus events...')
    
    const offset = (currentPage.value - 1) * filters.value.limit
    
    const response = await tradingAPI.getConsensusEvents({
      ticker: filters.value.ticker || null,
      direction: filters.value.direction || null,
      status: filters.value.status,
      min_strength: filters.value.min_strength,
      days_back: filters.value.days_back,
      limit: filters.value.limit,
      offset: offset
    })
    
    consensusEvents.value = response.consensus_events || []
    totalConsensus.value = response.count || 0
    
    console.log('✅ Loaded consensus events:', consensusEvents.value.length)
    
  } catch (err) {
    console.error('❌ Error loading consensus events:', err)
    error.value = err.message || 'Ошибка загрузки консенсусов'
  } finally {
    isLoading.value = false
  }
}

async function loadStats() {
  try {
    const response = await tradingAPI.getConsensusStats(
      filters.value.ticker || null,
      filters.value.days_back
    )
    stats.value = response
  } catch (err) {
    console.error('❌ Error loading consensus stats:', err)
  }
}

function applyFilters() {
  currentPage.value = 1
  loadConsensusEvents()
  loadStats()
}

function resetFilters() {
  filters.value = {
    ticker: '',
    direction: '',
    status: 'all',
    min_strength: null,
    days_back: 30,
    limit: 20
  }
  currentPage.value = 1
  loadConsensusEvents()
  loadStats()
}

async function triggerDetection() {
  isDetecting.value = true
  
  try {
    console.log('🔍 Triggering consensus detection...')
    
    await tradingAPI.triggerConsensusDetection(
      filters.value.ticker || null,
      24
    )
    
    setTimeout(() => {
      loadConsensusEvents()
      loadStats()
    }, 2000)
    
  } catch (err) {
    console.error('❌ Error triggering detection:', err)
    error.value = err.message
  } finally {
    setTimeout(() => {
      isDetecting.value = false
    }, 2000)
  }
}

function showConsensusDetails(consensus) {
  console.log('📊 Show consensus details:', consensus)
}

function formatDate(dateString) {
  const date = new Date(dateString)
  const now = new Date()
  const diffMs = now - date
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMs / 3600000)
  
  if (diffMins < 60) {
    return `${diffMins} мин назад`
  } else if (diffHours < 24) {
    return `${diffHours} ч назад`
  } else {
    return date.toLocaleDateString('ru-RU', {
      day: '2-digit',
      month: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    })
  }
}

function nextPage() {
  if (currentPage.value < totalPages.value) {
    currentPage.value++
    loadConsensusEvents()
  }
}

function prevPage() {
  if (currentPage.value > 1) {
    currentPage.value--
    loadConsensusEvents()
  }
}

onMounted(() => {
  console.log('🚀 ConsensusPage mounted')
  loadConsensusEvents()
  loadStats()
})
</script>