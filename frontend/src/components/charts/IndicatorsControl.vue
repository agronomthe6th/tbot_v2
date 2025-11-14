<template>
  <div class="indicators-control">
    <div class="control-header" @click="togglePanel">
      <div class="flex items-center space-x-2">
        <span class="text-lg">📊</span>
        <h3 class="font-semibold">Технические индикаторы</h3>
        <span class="text-xs text-gray-400">({{ activeCount }}/{{ totalCount }})</span>
      </div>
      <div class="toggle-icon" :class="{ 'rotate-180': isExpanded }">
        ▼
      </div>
    </div>

    <transition name="slide-down">
      <div v-if="isExpanded" class="control-body">

        <!-- RSI -->
        <div class="indicator-item">
          <div class="indicator-header">
            <label class="indicator-checkbox">
              <input
                type="checkbox"
                v-model="localIndicators.rsi.enabled"
                @change="emitChange"
              />
              <span class="indicator-name">RSI (Relative Strength Index)</span>
            </label>
            <button
              v-if="localIndicators.rsi.enabled"
              @click="toggleSettings('rsi')"
              class="settings-btn"
            >
              ⚙️
            </button>
          </div>

          <transition name="fade">
            <div v-if="localIndicators.rsi.enabled && showSettings.rsi" class="indicator-settings">
              <div class="setting-item">
                <label class="setting-label">Период:</label>
                <input
                  type="number"
                  v-model.number="localIndicators.rsi.period"
                  @change="emitChange"
                  min="2"
                  max="100"
                  class="setting-input"
                />
              </div>
              <div class="setting-item">
                <label class="setting-label">Цвет линии:</label>
                <input
                  type="color"
                  v-model="localIndicators.rsi.color"
                  @change="emitChange"
                  class="setting-color"
                />
              </div>
            </div>
          </transition>
        </div>

        <!-- MACD -->
        <div class="indicator-item">
          <div class="indicator-header">
            <label class="indicator-checkbox">
              <input
                type="checkbox"
                v-model="localIndicators.macd.enabled"
                @change="emitChange"
              />
              <span class="indicator-name">MACD</span>
            </label>
            <button
              v-if="localIndicators.macd.enabled"
              @click="toggleSettings('macd')"
              class="settings-btn"
            >
              ⚙️
            </button>
          </div>

          <transition name="fade">
            <div v-if="localIndicators.macd.enabled && showSettings.macd" class="indicator-settings">
              <div class="setting-row">
                <div class="setting-item">
                  <label class="setting-label">Быстрый:</label>
                  <input
                    type="number"
                    v-model.number="localIndicators.macd.fastPeriod"
                    @change="emitChange"
                    min="2"
                    max="100"
                    class="setting-input"
                  />
                </div>
                <div class="setting-item">
                  <label class="setting-label">Медленный:</label>
                  <input
                    type="number"
                    v-model.number="localIndicators.macd.slowPeriod"
                    @change="emitChange"
                    min="2"
                    max="100"
                    class="setting-input"
                  />
                </div>
                <div class="setting-item">
                  <label class="setting-label">Сигнальный:</label>
                  <input
                    type="number"
                    v-model.number="localIndicators.macd.signalPeriod"
                    @change="emitChange"
                    min="2"
                    max="100"
                    class="setting-input"
                  />
                </div>
              </div>
              <div class="setting-row">
                <div class="setting-item">
                  <label class="setting-label">MACD:</label>
                  <input
                    type="color"
                    v-model="localIndicators.macd.macdColor"
                    @change="emitChange"
                    class="setting-color"
                  />
                </div>
                <div class="setting-item">
                  <label class="setting-label">Сигнал:</label>
                  <input
                    type="color"
                    v-model="localIndicators.macd.signalColor"
                    @change="emitChange"
                    class="setting-color"
                  />
                </div>
              </div>
            </div>
          </transition>
        </div>

        <!-- Bollinger Bands -->
        <div class="indicator-item">
          <div class="indicator-header">
            <label class="indicator-checkbox">
              <input
                type="checkbox"
                v-model="localIndicators.bollingerBands.enabled"
                @change="emitChange"
              />
              <span class="indicator-name">Bollinger Bands</span>
            </label>
            <button
              v-if="localIndicators.bollingerBands.enabled"
              @click="toggleSettings('bollingerBands')"
              class="settings-btn"
            >
              ⚙️
            </button>
          </div>

          <transition name="fade">
            <div v-if="localIndicators.bollingerBands.enabled && showSettings.bollingerBands" class="indicator-settings">
              <div class="setting-row">
                <div class="setting-item">
                  <label class="setting-label">Период:</label>
                  <input
                    type="number"
                    v-model.number="localIndicators.bollingerBands.period"
                    @change="emitChange"
                    min="2"
                    max="100"
                    class="setting-input"
                  />
                </div>
                <div class="setting-item">
                  <label class="setting-label">Std Dev:</label>
                  <input
                    type="number"
                    v-model.number="localIndicators.bollingerBands.stdDev"
                    @change="emitChange"
                    min="0.1"
                    max="5"
                    step="0.1"
                    class="setting-input"
                  />
                </div>
              </div>
              <div class="setting-item">
                <label class="setting-label">Цвет:</label>
                <input
                  type="color"
                  v-model="localIndicators.bollingerBands.color"
                  @change="emitChange"
                  class="setting-color"
                />
              </div>
            </div>
          </transition>
        </div>

        <!-- OBV -->
        <div class="indicator-item">
          <div class="indicator-header">
            <label class="indicator-checkbox">
              <input
                type="checkbox"
                v-model="localIndicators.obv.enabled"
                @change="emitChange"
              />
              <span class="indicator-name">OBV (On-Balance Volume)</span>
            </label>
            <button
              v-if="localIndicators.obv.enabled"
              @click="toggleSettings('obv')"
              class="settings-btn"
            >
              ⚙️
            </button>
          </div>

          <transition name="fade">
            <div v-if="localIndicators.obv.enabled && showSettings.obv" class="indicator-settings">
              <div class="setting-item">
                <label class="setting-label">Цвет линии:</label>
                <input
                  type="color"
                  v-model="localIndicators.obv.color"
                  @change="emitChange"
                  class="setting-color"
                />
              </div>
            </div>
          </transition>
        </div>

        <!-- Кнопки управления -->
        <div class="control-actions">
          <button @click="enableAll" class="action-btn action-btn-primary">
            Включить все
          </button>
          <button @click="disableAll" class="action-btn action-btn-secondary">
            Выключить все
          </button>
          <button @click="resetToDefaults" class="action-btn action-btn-secondary">
            Сбросить
          </button>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'

// Props
const props = defineProps({
  modelValue: {
    type: Object,
    default: () => ({
      rsi: {
        enabled: false,
        period: 14,
        color: '#2962FF'
      },
      macd: {
        enabled: false,
        fastPeriod: 12,
        slowPeriod: 26,
        signalPeriod: 9,
        macdColor: '#2962FF',
        signalColor: '#FF6D00'
      },
      bollingerBands: {
        enabled: false,
        period: 20,
        stdDev: 2,
        color: '#089981'
      },
      obv: {
        enabled: false,
        color: '#9C27B0'
      }
    })
  }
})

// Emits
const emit = defineEmits(['update:modelValue'])

// State
const isExpanded = ref(false)
const showSettings = ref({
  rsi: false,
  macd: false,
  bollingerBands: false,
  obv: false
})

// Local copy of indicators
const localIndicators = ref(JSON.parse(JSON.stringify(props.modelValue)))

// Computed
const activeCount = computed(() => {
  return Object.values(localIndicators.value).filter(ind => ind.enabled).length
})

const totalCount = computed(() => {
  return Object.keys(localIndicators.value).length
})

// Methods
function togglePanel() {
  isExpanded.value = !isExpanded.value
}

function toggleSettings(indicator) {
  showSettings.value[indicator] = !showSettings.value[indicator]
}

function emitChange() {
  emit('update:modelValue', JSON.parse(JSON.stringify(localIndicators.value)))
}

function enableAll() {
  Object.keys(localIndicators.value).forEach(key => {
    localIndicators.value[key].enabled = true
  })
  emitChange()
}

function disableAll() {
  Object.keys(localIndicators.value).forEach(key => {
    localIndicators.value[key].enabled = false
  })
  emitChange()
}

function resetToDefaults() {
  localIndicators.value = {
    rsi: {
      enabled: false,
      period: 14,
      color: '#2962FF'
    },
    macd: {
      enabled: false,
      fastPeriod: 12,
      slowPeriod: 26,
      signalPeriod: 9,
      macdColor: '#2962FF',
      signalColor: '#FF6D00'
    },
    bollingerBands: {
      enabled: false,
      period: 20,
      stdDev: 2,
      color: '#089981'
    },
    obv: {
      enabled: false,
      color: '#9C27B0'
    }
  }
  emitChange()
}

// Watchers
watch(() => props.modelValue, (newValue) => {
  localIndicators.value = JSON.parse(JSON.stringify(newValue))
}, { deep: true })
</script>

<style scoped>
.indicators-control {
  @apply bg-trading-card border border-trading-border rounded-lg overflow-hidden;
}

.control-header {
  @apply flex items-center justify-between p-4 cursor-pointer;
  @apply hover:bg-trading-bg transition-colors;
}

.toggle-icon {
  @apply text-gray-400 transition-transform duration-300;
}

.control-body {
  @apply p-4 pt-0 space-y-3 border-t border-trading-border;
}

.indicator-item {
  @apply bg-trading-bg rounded p-3 space-y-2;
}

.indicator-header {
  @apply flex items-center justify-between;
}

.indicator-checkbox {
  @apply flex items-center space-x-2 cursor-pointer;
}

.indicator-checkbox input[type="checkbox"] {
  @apply w-4 h-4 rounded border-trading-border bg-trading-bg;
  @apply checked:bg-trading-green checked:border-trading-green;
  @apply focus:ring-2 focus:ring-trading-green focus:ring-offset-0;
  @apply cursor-pointer;
}

.indicator-name {
  @apply text-sm font-medium text-gray-200;
}

.settings-btn {
  @apply text-gray-400 hover:text-white transition-colors;
  @apply text-sm px-2 py-1 rounded hover:bg-trading-card;
}

.indicator-settings {
  @apply mt-2 p-3 bg-trading-card rounded space-y-2;
}

.setting-row {
  @apply grid grid-cols-3 gap-2;
}

.setting-item {
  @apply flex flex-col space-y-1;
}

.setting-label {
  @apply text-xs text-gray-400;
}

.setting-input {
  @apply w-full px-2 py-1 bg-trading-bg border border-trading-border rounded;
  @apply text-white text-sm focus:border-trading-green focus:outline-none;
}

.setting-color {
  @apply w-full h-8 bg-trading-bg border border-trading-border rounded cursor-pointer;
}

.control-actions {
  @apply flex space-x-2 mt-4 pt-3 border-t border-trading-border;
}

.action-btn {
  @apply flex-1 px-3 py-2 rounded text-sm font-medium transition-colors;
}

.action-btn-primary {
  @apply bg-trading-green text-black hover:bg-green-400;
}

.action-btn-secondary {
  @apply bg-trading-bg border border-trading-border text-gray-300;
  @apply hover:bg-trading-card hover:border-gray-500;
}

/* Transitions */
.slide-down-enter-active,
.slide-down-leave-active {
  transition: all 0.3s ease;
  max-height: 1000px;
  overflow: hidden;
}

.slide-down-enter-from,
.slide-down-leave-to {
  max-height: 0;
  opacity: 0;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
