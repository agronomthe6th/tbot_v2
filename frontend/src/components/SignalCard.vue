<!-- frontend/src/components/SignalCard.vue -->
<template>
  <div 
    class="signal-card"
    :class="[
      'bg-trading-bg p-4 rounded-lg border transition-all cursor-pointer',
      directionClass,
      'hover:border-opacity-80 hover:transform hover:scale-[1.02]'
    ]"
    @click="$emit('click', signal)"
  >
    <!-- Заголовок с тикером и направлением -->
    <div class="flex items-center justify-between mb-3">
      <div class="flex items-center gap-3">
        <!-- Иконка направления -->
        <div 
          class="w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold"
          :class="signal.direction === 'long' ? 'bg-trading-green text-black' : 'bg-trading-red text-white'"
        >
          {{ signal.direction === 'long' ? '🟢' : '🔴' }}
        </div>
        
        <!-- Тикер -->
        <div>
          <div class="font-bold text-lg">{{ signal.ticker }}</div>
          <div class="text-xs text-gray-400">
            {{ signal.direction === 'long' ? 'LONG' : 'SHORT' }} позиция
          </div>
        </div>
      </div>
      
      <!-- Время и статус -->
      <div class="text-right">
        <div class="text-sm font-medium">{{ formatTime(signal.timestamp) }}</div>
        <div class="text-xs text-gray-400">{{ formatDate(signal.timestamp) }}</div>
        <div v-if="signal.signal_type" class="text-xs font-medium mt-1" :class="typeClass">
          {{ getTypeLabel(signal.signal_type) }}
        </div>
      </div>
    </div>

    <!-- Цены -->
    <div class="grid grid-cols-3 gap-3 mb-3">
      <!-- Цена входа -->
      <div v-if="signal.target_price" class="text-center">
        <div class="text-xs text-gray-400">Вход</div>
        <div class="font-semibold">{{ formatPrice(signal.target_price) }}</div>
      </div>
      
      <!-- Stop Loss -->
      <div v-if="signal.stop_loss" class="text-center">
        <div class="text-xs text-gray-400">Stop Loss</div>
        <div class="font-semibold text-trading-red">{{ formatPrice(signal.stop_loss) }}</div>
      </div>
      
      <!-- Take Profit -->
      <div v-if="signal.take_profit" class="text-center">
        <div class="text-xs text-gray-400">Take Profit</div>
        <div class="font-semibold text-trading-green">{{ formatPrice(signal.take_profit) }}</div>
      </div>
    </div>

    <!-- Уровень уверенности -->
    <div v-if="signal.confidence_score || signal.confidence_level" class="mb-3">
      <div class="flex items-center gap-2">
        <span class="text-xs text-gray-400">Уверенность:</span>
        <div class="flex-1 bg-trading-card rounded-full h-2">
          <div 
            class="h-2 rounded-full transition-all"
            :class="confidenceClass"
            :style="{ width: confidenceWidth }"
          ></div>
        </div>
        <span class="text-xs font-medium">{{ confidenceText }}</span>
      </div>
    </div>

    <!-- Автор -->
    <div v-if="signal.author" class="flex items-center justify-between text-sm">
      <div class="flex items-center gap-2">
        <span class="text-gray-400">Трейдер:</span>
        <span class="font-medium">{{ signal.author }}</span>
      </div>
      
      <!-- Дополнительная информация -->
      <div class="flex items-center gap-2 text-xs text-gray-400">
        <span v-if="signal.timeframe">{{ signal.timeframe }}</span>
        <span v-if="signal.views" title="Просмотры">👁 {{ signal.views }}</span>
      </div>
    </div>

    <!-- Оригинальный текст (скрытый, раскрывается по клику) -->
    <div v-if="showFullText && signal.original_text" class="mt-3 pt-3 border-t border-trading-border">
      <div class="text-xs text-gray-400 mb-1">Оригинальный текст:</div>
      <div class="text-sm bg-trading-card p-2 rounded text-gray-300 leading-relaxed">
        {{ signal.original_text }}
      </div>
    </div>

    <!-- Кнопка развернуть -->
    <div v-if="signal.original_text && !showFullText" class="mt-2 text-center">
      <button 
        @click.stop="showFullText = true"
        class="text-xs text-trading-green hover:text-opacity-80 transition-colors"
      >
        Показать оригинальный текст ↓
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

// Props
const props = defineProps({
  signal: {
    type: Object,
    required: true
  }
})

// Events
defineEmits(['click'])

// Состояние
const showFullText = ref(false)

// Вычисляемые свойства
const directionClass = computed(() => {
  return props.signal.direction === 'long' 
    ? 'border-trading-green border-opacity-30' 
    : 'border-trading-red border-opacity-30'
})

const typeClass = computed(() => {
  const type = props.signal.signal_type
  switch (type) {
    case 'entry': return 'text-trading-green'
    case 'exit': return 'text-trading-red'
    case 'update': return 'text-trading-yellow'
    default: return 'text-gray-400'
  }
})

const confidenceClass = computed(() => {
  const confidence = getConfidenceValue()
  if (confidence >= 0.8) return 'bg-trading-green'
  if (confidence >= 0.6) return 'bg-trading-yellow'
  if (confidence >= 0.4) return 'bg-orange-500'
  return 'bg-trading-red'
})

const confidenceWidth = computed(() => {
  const confidence = getConfidenceValue()
  return `${confidence * 100}%`
})

const confidenceText = computed(() => {
  const confidence = getConfidenceValue()
  if (props.signal.confidence_level) {
    return props.signal.confidence_level.toUpperCase()
  }
  return `${Math.round(confidence * 100)}%`
})

// Методы
function getConfidenceValue() {
  if (props.signal.confidence_score) {
    return parseFloat(props.signal.confidence_score)
  }
  
  const level = props.signal.confidence_level
  switch (level) {
    case 'high': return 0.9
    case 'medium': return 0.7
    case 'low': return 0.4
    default: return 0.5
  }
}

function getTypeLabel(type) {
  switch (type) {
    case 'entry': return 'ВХОД'
    case 'exit': return 'ВЫХОД'
    case 'update': return 'ОБНОВЛЕНИЕ'
    default: return type?.toUpperCase() || 'СИГНАЛ'
  }
}

function formatPrice(price) {
  if (!price) return '—'
  return parseFloat(price).toLocaleString('ru-RU', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 4
  })
}

function formatTime(dateString) {
  return new Date(dateString).toLocaleTimeString('ru-RU', {
    hour: '2-digit',
    minute: '2-digit'
  })
}

function formatDate(dateString) {
  return new Date(dateString).toLocaleDateString('ru-RU', {
    day: '2-digit',
    month: '2-digit'
  })
}
</script>

<style scoped>
.signal-card {
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.signal-card:hover {
  box-shadow: 0 4px 12px rgba(0, 212, 170, 0.15);
}
</style>