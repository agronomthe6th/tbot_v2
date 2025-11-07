<!-- frontend/src/components/SignalCard.vue -->
<template>
  <div 
    class="signal-card-modern"
    :class="directionClass"
  >
    <div class="signal-border" :class="borderClass"></div>
    
    <div class="signal-content">
      
      <div class="signal-ticker">
        {{ signal.ticker }}
      </div>
      
      <div class="signal-direction" :class="directionBadgeClass">
        <span class="direction-icon">{{ directionIcon }}</span>
        <span class="direction-text">{{ directionText }}</span>
      </div>
      
      <div class="signal-author">
        <span class="author-icon">👤</span>
        <span class="author-name">{{ signal.author || 'Unknown' }}</span>
      </div>
      
      <div class="signal-time">
        <span class="time-icon">🕐</span>
        <span class="time-text">{{ formatTime(signal.timestamp) }}</span>
      </div>
      
      <div v-if="showDetails" class="signal-details">
        <div v-if="signal.target_price" class="detail-item">
          <span class="detail-label">Target:</span>
          <span class="detail-value">{{ formatPrice(signal.target_price) }}</span>
        </div>
        <div v-if="signal.stop_loss" class="detail-item">
          <span class="detail-label">Stop:</span>
          <span class="detail-value">{{ formatPrice(signal.stop_loss) }}</span>
        </div>
      </div>
      
      <div class="confidence-bar">
        <div class="confidence-fill" :style="{ width: `${confidence * 100}%` }"></div>
      </div>
      
      <button 
        v-if="hasRawText"
        @click.stop="toggleRawText"
        class="toggle-text-btn"
        :class="{ 'active': isRawTextVisible }"
      >
        <span class="btn-icon">{{ isRawTextVisible ? '▼' : '▶' }}</span>
        <span class="btn-text">{{ isRawTextVisible ? 'Скрыть текст' : 'Показать полный текст' }}</span>
      </button>
      
      <transition name="accordion">
        <div v-if="isRawTextVisible" class="raw-text-container">
          <div class="raw-text-content">
            {{ rawText }}
          </div>
        </div>
      </transition>
      
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  signal: {
    type: Object,
    required: true
  },
  showDetails: {
    type: Boolean,
    default: false
  }
})

defineEmits(['click'])

const isRawTextVisible = ref(false)

const hasRawText = computed(() => {
  return !!(props.signal.original_text || props.signal.raw_text)
})

const rawText = computed(() => {
  return props.signal.original_text || props.signal.raw_text || 'Текст не доступен'
})

const directionClass = computed(() => {
  const dir = props.signal.direction?.toLowerCase() || 'mixed'
  return `signal-${dir}`
})

const borderClass = computed(() => {
  const dir = props.signal.direction?.toLowerCase() || 'mixed'
  return `border-${dir}`
})

const directionBadgeClass = computed(() => {
  const dir = props.signal.direction?.toLowerCase() || 'mixed'
  return `badge-${dir}`
})

const directionIcon = computed(() => {
  const dir = props.signal.direction?.toLowerCase()
  if (dir === 'long') return '📈'
  if (dir === 'short') return '📉'
  if (dir === 'exit') return '🚪'
  return '↔️'
})

const directionText = computed(() => {
  const dir = props.signal.direction?.toLowerCase()
  if (dir === 'long') return 'LONG'
  if (dir === 'short') return 'SHORT'
  if (dir === 'exit') return 'EXIT'
  return 'MIXED'
})

const confidence = computed(() => {
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
})

function toggleRawText() {
  isRawTextVisible.value = !isRawTextVisible.value
}

function formatPrice(price) {
  if (!price) return '—'
  return parseFloat(price).toLocaleString('ru-RU', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 4
  })
}

function formatTime(dateString) {
  const date = new Date(dateString)
  return date.toLocaleTimeString('ru-RU', {
    hour: '2-digit',
    minute: '2-digit'
  })
}
</script>

<style scoped>
.signal-card-modern {
  position: relative;
  background: linear-gradient(135deg, #2d2d2d 0%, #1a1a1a 100%);
  border-radius: 16px;
  padding: 0;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  overflow: hidden;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
}

.signal-card-modern:hover {
  transform: translateY(-4px) scale(1.02);
  box-shadow: 0 12px 24px rgba(0, 0, 0, 0.5);
}

.signal-border {
  height: 4px;
  width: 100%;
  transition: all 0.3s ease;
}

.border-long {
  background: linear-gradient(90deg, #00d4aa 0%, #00ffc8 100%);
}

.border-short {
  background: linear-gradient(90deg, #ff4747 0%, #ff6b6b 100%);
}

.border-exit {
  background: linear-gradient(90deg, #ffa500 0%, #ffb84d 100%);
}

.border-mixed {
  background: linear-gradient(90deg, #6b7280 0%, #9ca3af 100%);
}

.signal-card-modern:hover .signal-border {
  height: 6px;
}

.signal-content {
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.signal-ticker {
  font-size: 32px;
  font-weight: 800;
  letter-spacing: 1px;
  color: #ffffff;
  text-align: center;
  text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.5);
  margin-bottom: 8px;
}

.signal-direction {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 8px 16px;
  border-radius: 12px;
  font-weight: 700;
  font-size: 14px;
  letter-spacing: 0.5px;
  transition: all 0.3s ease;
}

.badge-long {
  background: rgba(0, 212, 170, 0.2);
  border: 2px solid #00d4aa;
  color: #00ffc8;
}

.badge-short {
  background: rgba(255, 71, 71, 0.2);
  border: 2px solid #ff4747;
  color: #ff6b6b;
}

.badge-exit {
  background: rgba(255, 165, 0, 0.2);
  border: 2px solid #ffa500;
  color: #ffb84d;
}

.badge-mixed {
  background: rgba(107, 114, 128, 0.2);
  border: 2px solid #6b7280;
  color: #9ca3af;
}

.signal-card-modern:hover .signal-direction {
  transform: scale(1.05);
}

.direction-icon {
  font-size: 18px;
}

.direction-text {
  font-size: 13px;
}

.signal-author {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: #9ca3af;
  font-size: 14px;
  font-weight: 500;
}

.author-icon {
  font-size: 16px;
  opacity: 0.8;
}

.author-name {
  color: #d1d5db;
}

.signal-time {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: #6b7280;
  font-size: 13px;
  font-weight: 500;
}

.time-icon {
  font-size: 14px;
}

.time-text {
  font-family: 'Monaco', 'Courier New', monospace;
}

.signal-details {
  display: flex;
  gap: 12px;
  justify-content: space-around;
  padding-top: 12px;
  border-top: 1px solid rgba(107, 114, 128, 0.3);
  margin-top: 4px;
}

.detail-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.detail-label {
  font-size: 10px;
  color: #6b7280;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.detail-value {
  font-size: 13px;
  font-weight: 600;
  color: #d1d5db;
  font-family: 'Monaco', 'Courier New', monospace;
}

.confidence-bar {
  position: relative;
  width: 100%;
  height: 3px;
  background: rgba(107, 114, 128, 0.2);
  border-radius: 2px;
  overflow: hidden;
  margin-top: 8px;
}

.confidence-fill {
  position: absolute;
  left: 0;
  top: 0;
  height: 100%;
  transition: width 0.5s ease;
}

.signal-long .confidence-fill {
  background: linear-gradient(90deg, #00d4aa 0%, #00ffc8 100%);
}

.signal-short .confidence-fill {
  background: linear-gradient(90deg, #ff4747 0%, #ff6b6b 100%);
}

.signal-exit .confidence-fill {
  background: linear-gradient(90deg, #ffa500 0%, #ffb84d 100%);
}

.signal-mixed .confidence-fill {
  background: linear-gradient(90deg, #6b7280 0%, #9ca3af 100%);
}

.signal-card-modern:hover .confidence-fill {
  box-shadow: 0 0 8px currentColor;
}

.toggle-text-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  width: 100%;
  padding: 10px 16px;
  margin-top: 8px;
  background: rgba(107, 114, 128, 0.15);
  border: 1px solid rgba(107, 114, 128, 0.3);
  border-radius: 8px;
  color: #9ca3af;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
}

.toggle-text-btn:hover {
  background: rgba(107, 114, 128, 0.25);
  border-color: rgba(107, 114, 128, 0.5);
  color: #d1d5db;
  transform: translateY(-1px);
}

.toggle-text-btn.active {
  background: rgba(107, 114, 128, 0.3);
  border-color: rgba(107, 114, 128, 0.6);
  color: #ffffff;
}

.btn-icon {
  font-size: 12px;
  transition: transform 0.3s ease;
}

.toggle-text-btn.active .btn-icon {
  transform: rotate(0deg);
}

.btn-text {
  letter-spacing: 0.3px;
}

.raw-text-container {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid rgba(107, 114, 128, 0.3);
}

.raw-text-content {
  padding: 12px;
  background: rgba(0, 0, 0, 0.3);
  border-radius: 8px;
  border: 1px solid rgba(107, 114, 128, 0.2);
  color: #d1d5db;
  font-size: 13px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-wrap: break-word;
  max-height: 300px;
  overflow-y: auto;
}

.raw-text-content::-webkit-scrollbar {
  width: 6px;
}

.raw-text-content::-webkit-scrollbar-track {
  background: rgba(0, 0, 0, 0.2);
  border-radius: 3px;
}

.raw-text-content::-webkit-scrollbar-thumb {
  background: rgba(107, 114, 128, 0.5);
  border-radius: 3px;
}

.raw-text-content::-webkit-scrollbar-thumb:hover {
  background: rgba(107, 114, 128, 0.7);
}

.accordion-enter-active,
.accordion-leave-active {
  transition: all 0.3s ease;
  overflow: hidden;
}

.accordion-enter-from,
.accordion-leave-to {
  max-height: 0;
  opacity: 0;
  transform: translateY(-10px);
}

.accordion-enter-to,
.accordion-leave-from {
  max-height: 400px;
  opacity: 1;
  transform: translateY(0);
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.signal-card-modern {
  animation: slideIn 0.4s ease-out;
}
</style>