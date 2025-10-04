<template>
  <div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
    <div class="bg-trading-card border border-trading-border rounded-lg max-w-4xl w-full max-h-[90vh] overflow-y-auto">
      <!-- Заголовок -->
      <div class="sticky top-0 bg-trading-card border-b border-trading-border px-6 py-4">
        <div class="flex justify-between items-center">
          <h2 class="text-xl font-bold text-white">🧪 Тестер паттерна</h2>
          <button @click="$emit('close')" class="text-gray-400 hover:text-white transition-colors">
            ✕
          </button>
        </div>
      </div>

      <!-- Контент -->
      <div class="p-6 space-y-6">
        <!-- Информация о паттерне -->
        <div class="bg-trading-bg border border-trading-border rounded-lg p-4">
          <div class="grid grid-cols-2 gap-4">
            <div>
              <div class="text-gray-400 text-sm">Название</div>
              <div class="text-white font-semibold">{{ pattern.name }}</div>
            </div>
            <div>
              <div class="text-gray-400 text-sm">Категория</div>
              <div class="text-white font-semibold">{{ pattern.category }}</div>
            </div>
          </div>
          <div class="mt-3">
            <div class="text-gray-400 text-sm mb-1">Паттерн</div>
            <code class="block bg-gray-900 px-3 py-2 rounded text-blue-400 font-mono text-sm">
              {{ pattern.pattern }}
            </code>
          </div>
          <div class="mt-3" v-if="pattern.description">
            <div class="text-gray-400 text-sm mb-1">Описание</div>
            <div class="text-white text-sm">{{ pattern.description }}</div>
          </div>
        </div>

        <!-- Поле ввода текста -->
        <div>
          <label class="block text-gray-400 text-sm mb-2">Тестовый текст</label>
          <textarea
            v-model="testText"
            rows="6"
            placeholder="Введите текст для тестирования паттерна..."
            class="w-full bg-trading-bg border border-trading-border rounded px-3 py-2 text-white focus:outline-none focus:border-trading-green"
          ></textarea>
          <div class="flex gap-2 mt-2">
            <button
              @click="testPattern"
              :disabled="testing || !testText.trim()"
              class="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {{ testing ? 'Тестирование...' : '▶️ Проверить' }}
            </button>
            <button
              @click="loadExample"
              class="px-4 py-2 bg-gray-600 hover:bg-gray-700 text-white rounded transition-colors"
            >
              📝 Пример текста
            </button>
            <button
              @click="testText = ''"
              class="px-4 py-2 bg-gray-600 hover:bg-gray-700 text-white rounded transition-colors"
            >
              🗑️ Очистить
            </button>
          </div>
        </div>

        <!-- Результаты -->
        <div v-if="results !== null" class="bg-trading-bg border border-trading-border rounded-lg p-4">
          <div class="flex items-center justify-between mb-3">
            <h3 class="text-white font-semibold">Результаты теста</h3>
            <span 
              :class="[
                'px-3 py-1 rounded text-sm font-semibold',
                results.matches_count > 0 
                  ? 'bg-green-900 text-trading-green' 
                  : 'bg-gray-700 text-gray-400'
              ]"
            >
              {{ results.matches_count }} совпадений
            </span>
          </div>

          <!-- Совпадения -->
          <div v-if="results.matches_count > 0" class="space-y-3">
            <div 
              v-for="(match, index) in results.matches" 
              :key="index"
              class="bg-trading-card border border-trading-border rounded p-3"
            >
              <div class="flex items-start justify-between mb-2">
                <span class="text-gray-400 text-sm">Совпадение {{ index + 1 }}</span>
                <span class="text-gray-500 text-xs">
                  Позиция: {{ match.start }} - {{ match.end }}
                </span>
              </div>
              <div class="bg-gray-900 px-3 py-2 rounded">
                <code class="text-trading-green font-mono text-sm">{{ match.match }}</code>
              </div>
              <div v-if="match.groups && match.groups.length > 0" class="mt-2">
                <div class="text-gray-400 text-xs mb-1">Захваченные группы:</div>
                <div class="flex flex-wrap gap-2">
                  <span 
                    v-for="(group, gIndex) in match.groups" 
                    :key="gIndex"
                    class="bg-blue-900 text-blue-400 px-2 py-1 rounded text-xs font-mono"
                  >
                    {{ gIndex + 1 }}: {{ group }}
                  </span>
                </div>
              </div>
            </div>
          </div>

          <!-- Нет совпадений -->
          <div v-else class="text-center py-8 text-gray-400">
            <div class="text-4xl mb-2">🔍</div>
            <p>Совпадений не найдено</p>
            <p class="text-sm mt-1">Попробуйте другой текст или проверьте паттерн</p>
          </div>

          <!-- Текст с подсветкой -->
          <div v-if="results.matches_count > 0" class="mt-4">
            <div class="text-gray-400 text-sm mb-2">Текст с подсветкой совпадений:</div>
            <div class="bg-gray-900 px-3 py-2 rounded text-white text-sm leading-relaxed font-mono whitespace-pre-wrap">
              {{ highlightedText }}
            </div>
          </div>
        </div>

        <!-- Ошибка -->
        <div v-if="error" class="bg-red-900 border border-red-700 rounded-lg p-4">
          <div class="text-red-400 font-semibold mb-1">Ошибка тестирования</div>
          <div class="text-red-300 text-sm">{{ error }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { tradingAPI } from '../../services/api'

const props = defineProps({
  pattern: {
    type: Object,
    required: true
  }
})

defineEmits(['close'])

const testText = ref('')
const testing = ref(false)
const results = ref(null)
const error = ref(null)

const highlightedText = computed(() => {
  if (!results.value || results.value.matches_count === 0) return ''
  
  let text = testText.value
  const matches = [...results.value.matches].sort((a, b) => b.start - a.start)
  
  for (const match of matches) {
    const before = text.substring(0, match.start)
    const matched = text.substring(match.start, match.end)
    const after = text.substring(match.end)
    text = before + `⟪${matched}⟫` + after
  }
  
  return text
})

async function testPattern() {
  if (!testText.value.trim()) return
  
  testing.value = true
  error.value = null
  results.value = null
  
  try {
    const response = await tradingAPI.post('/api/patterns/test', {
      pattern: props.pattern.pattern,
      text: testText.value
    })
    
    if (response.data.success) {
      results.value = response.data
    } else {
      error.value = response.data.error || 'Неизвестная ошибка'
    }
  } catch (err) {
    console.error('Failed to test pattern:', err)
    error.value = err.response?.data?.detail || 'Ошибка тестирования паттерна'
  } finally {
    testing.value = false
  }
}

function loadExample() {
  const examples = {
    'ticker': '$SBER купил по 250₽',
    'direction_long': 'Вход лонг по 100₽ от текущих',
    'direction_short': 'Открыл шорт по 50',
    'operation_exit': 'Закрыл лонг с профитом',
    'trading_keyword': 'Открыта позиция на лонг',
    'author': '#TraderPro - сигнал на покупку',
    'price_target': 'Цель: 300₽, стоп: 240₽',
    'price_stop': 'Стоп по лонгу: 95₽',
    'price_take': 'Тейк профит: 120₽',
    'garbage': 'Больше информации в канале @copybot'
  }
  
  const category = props.pattern.category
  const baseExample = examples[category] || 'Тестовое сообщение для проверки'
  
  testText.value = `${baseExample}\n\n$SBER лонг по 250₽\nЦель: 280₽\nСтоп: 240₽\n\n#Trader - сделка дня`
}
</script>