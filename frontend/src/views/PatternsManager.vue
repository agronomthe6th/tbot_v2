<template>
  <div class="min-h-screen bg-trading-dark p-6">
    <div class="max-w-7xl mx-auto">
      <!-- Header -->
      <div class="flex justify-between items-center mb-6">
        <div>
          <h1 class="text-3xl font-bold text-white">🎯 Управление паттернами</h1>
          <p class="text-gray-400 mt-1">Регулярные выражения для парсинга сигналов</p>
        </div>
        <div class="flex gap-3">
          <button
            @click="showCreateModal = true"
            class="px-4 py-2 bg-trading-green hover:bg-opacity-80 rounded-lg transition-colors"
          >
            ➕ Создать паттерн
          </button>
          <button
            @click="reparseAllMessages"
            :disabled="isReparsing"
            class="px-4 py-2 bg-purple-600 hover:bg-purple-700 rounded-lg transition-colors disabled:opacity-50"
          >
            {{ isReparsing ? '⏳ Репарсинг...' : '🔄 Перепарсить все' }}
          </button>
        </div>
      </div>

      <!-- Stats -->
      <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <div class="bg-trading-card rounded-lg border border-trading-border p-4">
          <div class="text-2xl font-bold text-blue-400">{{ totalPatterns }}</div>
          <div class="text-sm text-gray-400">Всего паттернов</div>
        </div>
        <div class="bg-trading-card rounded-lg border border-trading-border p-4">
          <div class="text-2xl font-bold text-green-400">{{ activePatterns }}</div>
          <div class="text-sm text-gray-400">Активных</div>
        </div>
        <div class="bg-trading-card rounded-lg border border-trading-border p-4">
          <div class="text-2xl font-bold text-yellow-400">{{ categoriesCount }}</div>
          <div class="text-sm text-gray-400">Категорий</div>
        </div>
        <div class="bg-trading-card rounded-lg border border-trading-border p-4">
          <div class="text-2xl font-bold text-purple-400">{{ totalPatterns - activePatterns }}</div>
          <div class="text-sm text-gray-400">Неактивных</div>
        </div>
      </div>

      <!-- Filters -->
      <div class="bg-trading-card rounded-lg border border-trading-border p-4 mb-6">
        <div class="flex flex-wrap gap-4">
          <div class="flex-1 min-w-[200px]">
            <input
              v-model="searchQuery"
              placeholder="🔍 Поиск по названию..."
              class="w-full px-3 py-2 bg-trading-bg border border-trading-border rounded text-white"
            >
          </div>
          <select
            v-model="selectedCategory"
            class="px-3 py-2 bg-trading-bg border border-trading-border rounded text-white"
          >
            <option value="">Все категории</option>
            <option v-for="cat in categories" :key="cat" :value="cat">
              {{ getCategoryLabel(cat) }}
            </option>
          </select>
          <label class="flex items-center gap-2 px-3 py-2 bg-trading-bg border border-trading-border rounded cursor-pointer">
            <input
              v-model="activeOnly"
              type="checkbox"
              class="rounded"
            >
            <span class="text-white">Только активные</span>
          </label>
        </div>
      </div>

      <!-- Loading -->
      <div v-if="loading" class="text-center py-12">
        <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-trading-green mx-auto mb-4"></div>
        <div class="text-gray-400">Загрузка паттернов...</div>
      </div>

      <!-- Patterns List -->
      <div v-else class="grid grid-cols-1 gap-4">
        <div
          v-for="pattern in filteredPatterns"
          :key="pattern.id"
          class="bg-trading-card rounded-lg border border-trading-border p-6 hover:border-trading-green transition-colors"
        >
          <div class="flex justify-between items-start mb-4">
            <div class="flex-1">
              <div class="flex items-center gap-3 mb-2">
                <h3 class="text-xl font-semibold text-white">{{ pattern.name }}</h3>
                <span
                  class="px-2 py-1 rounded text-xs font-medium"
                  :class="getCategoryColor(pattern.category)"
                >
                  {{ getCategoryLabel(pattern.category) }}
                </span>
                <span
                  class="px-2 py-1 rounded text-xs font-medium"
                  :class="pattern.is_active ? 'bg-green-600 text-white' : 'bg-gray-600 text-gray-300'"
                >
                  {{ pattern.is_active ? '✓ Активен' : '✗ Неактивен' }}
                </span>
              </div>
              <p v-if="pattern.description" class="text-gray-400 text-sm mb-3">
                {{ pattern.description }}
              </p>
              <div class="bg-trading-bg rounded p-3 font-mono text-sm text-gray-300 overflow-x-auto">
                {{ pattern.pattern }}
              </div>
            </div>
          </div>

          <!-- Actions -->
          <div class="flex gap-2 mt-4">
            <button
              @click="togglePattern(pattern)"
              class="px-3 py-1 rounded text-sm transition-colors"
              :class="pattern.is_active 
                ? 'bg-gray-600 hover:bg-gray-700 text-white' 
                : 'bg-green-600 hover:bg-green-700 text-white'"
            >
              {{ pattern.is_active ? '✗ Деактивировать' : '✓ Активировать' }}
            </button>
            <button
              @click="testPattern(pattern)"
              class="px-3 py-1 bg-blue-600 hover:bg-blue-700 rounded text-sm text-white transition-colors"
            >
              🧪 Тест на тексте
            </button>
            <button
              @click="testPatternOnMessages(pattern)"
              :disabled="testingPatternId === pattern.id"
              class="px-3 py-1 bg-purple-600 hover:bg-purple-700 rounded text-sm text-white transition-colors disabled:opacity-50"
            >
              {{ testingPatternId === pattern.id ? '⏳ Тестируем...' : '📊 Тест на 1000 сообщениях' }}
            </button>
            <button
              @click="editPattern(pattern)"
              class="px-3 py-1 bg-yellow-600 hover:bg-yellow-700 rounded text-sm text-white transition-colors"
            >
              ✏️ Изменить
            </button>
            <button
              @click="deletePattern(pattern)"
              class="px-3 py-1 bg-red-600 hover:bg-red-700 rounded text-sm text-white transition-colors"
            >
              🗑️ Удалить
            </button>
          </div>
        </div>

        <!-- Empty State -->
        <div v-if="filteredPatterns.length === 0" class="text-center py-12">
          <div class="text-gray-400 text-lg">Паттерны не найдены</div>
          <button
            @click="showCreateModal = true"
            class="mt-4 px-4 py-2 bg-trading-green hover:bg-opacity-80 rounded-lg transition-colors"
          >
            ➕ Создать первый паттерн
          </button>
        </div>
      </div>
    </div>

    <!-- Create/Edit Modal -->
    <div
      v-if="showCreateModal || editingPattern"
      class="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50 p-4"
      @click.self="closeModal"
    >
      <div class="bg-trading-card rounded-lg border border-trading-border p-6 max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        <h2 class="text-2xl font-bold text-white mb-4">
          {{ editingPattern ? '✏️ Редактировать паттерн' : '➕ Создать паттерн' }}
        </h2>

        <div class="space-y-4">
          <!-- Name -->
          <div>
            <label class="block text-sm font-medium text-gray-300 mb-2">Название</label>
            <input
              v-model="formData.name"
              placeholder="Например: Ticker detection"
              class="w-full px-3 py-2 bg-trading-bg border border-trading-border rounded text-white"
            >
          </div>

          <!-- Category -->
          <div>
            <label class="block text-sm font-medium text-gray-300 mb-2">Категория</label>
            <select
              v-model="formData.category"
              class="w-full px-3 py-2 bg-trading-bg border border-trading-border rounded text-white"
            >
              <option value="">Выберите категорию</option>
              <option value="ticker">Ticker</option>
              <option value="direction_long">Direction: Long</option>
              <option value="direction_short">Direction: Short</option>
              <option value="operation_exit">Operation: Exit</option>
              <option value="trading_keyword">Trading Keyword</option>
              <option value="author">Author</option>
              <option value="price_target">Price: Target</option>
              <option value="price_stop">Price: Stop</option>
              <option value="price_take">Price: Take</option>
              <option value="garbage">Garbage</option>
            </select>
          </div>

          <!-- Pattern -->
          <div>
            <label class="block text-sm font-medium text-gray-300 mb-2">Регулярное выражение</label>
            <textarea
              v-model="formData.pattern"
              placeholder="(?:^|\s)\$([A-Z]{4,6})(?:\s|$)"
              rows="3"
              class="w-full px-3 py-2 bg-trading-bg border border-trading-border rounded text-white font-mono text-sm"
            ></textarea>
            <p class="text-xs text-gray-500 mt-1">Python regex синтаксис</p>
          </div>

          <!-- Description -->
          <div>
            <label class="block text-sm font-medium text-gray-300 mb-2">Описание (опционально)</label>
            <textarea
              v-model="formData.description"
              placeholder="Краткое описание паттерна..."
              rows="2"
              class="w-full px-3 py-2 bg-trading-bg border border-trading-border rounded text-white"
            ></textarea>
          </div>

          <!-- Priority -->
          <div>
            <label class="block text-sm font-medium text-gray-300 mb-2">
              Приоритет: {{ formData.priority }}
            </label>
            <input
              v-model.number="formData.priority"
              type="range"
              min="1"
              max="100"
              class="w-full"
            >
            <p class="text-xs text-gray-500 mt-1">Чем выше приоритет, тем раньше применяется</p>
          </div>

          <!-- Active -->
          <label class="flex items-center gap-2 cursor-pointer">
            <input
              v-model="formData.is_active"
              type="checkbox"
              class="rounded"
            >
            <span class="text-white">Активен</span>
          </label>
        </div>

        <!-- Actions -->
        <div class="flex gap-3 mt-6">
          <button
            @click="savePattern"
            :disabled="!isFormValid || saving"
            class="flex-1 px-4 py-2 bg-trading-green hover:bg-opacity-80 rounded-lg transition-colors disabled:opacity-50"
          >
            {{ saving ? '⏳ Сохранение...' : '💾 Сохранить' }}
          </button>
          <button
            @click="closeModal"
            class="px-4 py-2 bg-gray-600 hover:bg-gray-700 rounded-lg transition-colors"
          >
            ✕ Отмена
          </button>
        </div>
      </div>
    </div>

    <!-- Test on Text Modal -->
    <div
      v-if="testingPattern"
      class="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50 p-4"
      @click.self="testingPattern = null"
    >
      <div class="bg-trading-card rounded-lg border border-trading-border p-6 max-w-4xl w-full max-h-[90vh] overflow-y-auto">
        <h2 class="text-2xl font-bold text-white mb-4">
          🧪 Тест паттерна: {{ testingPattern.name }}
        </h2>

        <div class="mb-4">
          <label class="block text-sm font-medium text-gray-300 mb-2">Тестовый текст</label>
          <textarea
            v-model="testText"
            placeholder="Вставьте текст для проверки..."
            rows="6"
            class="w-full px-3 py-2 bg-trading-bg border border-trading-border rounded text-white font-mono text-sm"
          ></textarea>
        </div>

        <div class="flex gap-2 mb-4">
          <button
            @click="runTextTest"
            :disabled="!testText || testing"
            class="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors disabled:opacity-50"
          >
            {{ testing ? '⏳ Тестируем...' : '▶️ Запустить тест' }}
          </button>
          <button
            @click="loadExample"
            class="px-4 py-2 bg-gray-600 hover:bg-gray-700 rounded-lg transition-colors"
          >
            📝 Загрузить пример
          </button>
        </div>

        <!-- Test Results -->
        <div v-if="testResults" class="bg-trading-bg rounded p-4">
          <h3 class="font-semibold text-white mb-2">
            Результат: {{ testResults.matches_count }} совпадений
          </h3>
          <div v-if="testResults.matches && testResults.matches.length > 0" class="space-y-2">
            <div
              v-for="(match, idx) in testResults.matches"
              :key="idx"
              class="bg-trading-card p-3 rounded border border-trading-border"
            >
              <div class="font-mono text-green-400">{{ match.match }}</div>
              <div class="text-xs text-gray-500 mt-1">
                Position: {{ match.start }}-{{ match.end }}
                <span v-if="match.groups && match.groups.length">
                  | Groups: {{ match.groups.join(', ') }}
                </span>
              </div>
            </div>
          </div>
          <div v-else class="text-gray-400">Совпадений не найдено</div>
        </div>

        <button
          @click="testingPattern = null"
          class="mt-4 px-4 py-2 bg-gray-600 hover:bg-gray-700 rounded-lg transition-colors"
        >
          ✕ Закрыть
        </button>
      </div>
    </div>

    <!-- Test on Messages Modal -->
    <div
      v-if="messagesTestResults"
      class="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50 p-4"
      @click.self="messagesTestResults = null"
    >
      <div class="bg-trading-card rounded-lg border border-trading-border p-6 max-w-6xl w-full max-h-[90vh] overflow-y-auto">
        <h2 class="text-2xl font-bold text-white mb-4">
          📊 Результаты теста на реальных сообщениях
        </h2>

        <div class="grid grid-cols-3 gap-4 mb-6">
          <div class="bg-trading-bg rounded-lg p-4">
            <div class="text-2xl font-bold text-blue-400">{{ messagesTestResults.messages_tested }}</div>
            <div class="text-sm text-gray-400">Сообщений протестировано</div>
          </div>
          <div class="bg-trading-bg rounded-lg p-4">
            <div class="text-2xl font-bold text-green-400">{{ messagesTestResults.matches_found }}</div>
            <div class="text-sm text-gray-400">Совпадений найдено</div>
          </div>
          <div class="bg-trading-bg rounded-lg p-4">
            <div class="text-2xl font-bold text-yellow-400">
              {{ Math.round((messagesTestResults.matches_found / messagesTestResults.messages_tested) * 100) }}%
            </div>
            <div class="text-sm text-gray-400">Процент срабатывания</div>
          </div>
        </div>

        <div v-if="messagesTestResults.matches && messagesTestResults.matches.length > 0" class="space-y-3">
          <h3 class="font-semibold text-white">Найденные совпадения:</h3>
          <div
            v-for="match in messagesTestResults.matches"
            :key="match.message_id"
            class="bg-trading-bg rounded-lg p-4 border border-trading-border"
          >
            <div class="flex justify-between items-start mb-2">
              <div class="text-sm text-gray-400">
                {{ match.author }} • {{ formatDate(match.timestamp) }}
              </div>
              <div class="text-xs text-green-400 font-semibold">
                {{ match.match_count }} совпадений
              </div>
            </div>
            <div class="text-white text-sm mb-2 whitespace-pre-wrap">{{ match.text }}</div>
            <div class="space-y-1">
              <div
                v-for="(m, idx) in match.matches"
                :key="idx"
                class="text-xs bg-green-900 bg-opacity-30 text-green-400 px-2 py-1 rounded font-mono inline-block mr-2"
              >
                {{ m.matched_text }}
              </div>
            </div>
          </div>
        </div>
        <div v-else class="text-center py-8 text-gray-400">
          Совпадений не найдено в протестированных сообщениях
        </div>

        <button
          @click="messagesTestResults = null"
          class="mt-4 px-4 py-2 bg-gray-600 hover:bg-gray-700 rounded-lg transition-colors"
        >
          ✕ Закрыть
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { tradingAPI } from '../services/api'

// State
const loading = ref(false)
const saving = ref(false)
const testing = ref(false)
const isReparsing = ref(false)
const testingPatternId = ref(null)

const patterns = ref([])
const searchQuery = ref('')
const selectedCategory = ref('')
const activeOnly = ref(false)

const showCreateModal = ref(false)
const editingPattern = ref(null)
const testingPattern = ref(null)
const testText = ref('')
const testResults = ref(null)
const messagesTestResults = ref(null)

const formData = ref({
  name: '',
  category: '',
  pattern: '',
  description: '',
  priority: 50,
  is_active: true
})

// Computed
const categories = computed(() => {
  const cats = new Set(patterns.value.map(p => p.category))
  return Array.from(cats).sort()
})

const totalPatterns = computed(() => patterns.value.length)
const activePatterns = computed(() => patterns.value.filter(p => p.is_active).length)
const categoriesCount = computed(() => categories.value.length)

const filteredPatterns = computed(() => {
  let filtered = patterns.value

  if (searchQuery.value) {
    const search = searchQuery.value.toLowerCase()
    filtered = filtered.filter(p =>
      p.name.toLowerCase().includes(search) ||
      p.pattern.toLowerCase().includes(search) ||
      (p.description && p.description.toLowerCase().includes(search))
    )
  }

  if (selectedCategory.value) {
    filtered = filtered.filter(p => p.category === selectedCategory.value)
  }

  if (activeOnly.value) {
    filtered = filtered.filter(p => p.is_active)
  }

  return filtered.sort((a, b) => {
    if (a.is_active !== b.is_active) return b.is_active - a.is_active
    if (a.category !== b.category) return a.category.localeCompare(b.category)
    return b.priority - a.priority
  })
})

const isFormValid = computed(() => {
  return formData.value.name.trim() &&
    formData.value.category &&
    formData.value.pattern.trim()
})

// Methods
async function loadPatterns() {
  loading.value = true
  try {
    const response = await tradingAPI.get('/api/patterns')
    patterns.value = response.data.patterns || []
  } catch (error) {
    console.error('Failed to load patterns:', error)
    alert('Ошибка загрузки паттернов')
  } finally {
    loading.value = false
  }
}

async function togglePattern(pattern) {
  try {
    await tradingAPI.togglePattern(pattern.id)
    pattern.is_active = !pattern.is_active
  } catch (error) {
    console.error('Failed to toggle pattern:', error)
    alert('Ошибка переключения паттерна')
  }
}

function editPattern(pattern) {
  editingPattern.value = pattern
  formData.value = {
    name: pattern.name,
    category: pattern.category,
    pattern: pattern.pattern,
    description: pattern.description || '',
    priority: pattern.priority,
    is_active: pattern.is_active
  }
}

async function savePattern() {
  if (!isFormValid.value) return

  saving.value = true
  try {
    if (editingPattern.value) {
      await tradingAPI.put(`/api/patterns/${editingPattern.value.id}`, formData.value)
    } else {
      await tradingAPI.post('/api/patterns', formData.value)
    }
    await loadPatterns()
    closeModal()
  } catch (error) {
    console.error('Failed to save pattern:', error)
    alert('Ошибка сохранения: ' + error.message)
  } finally {
    saving.value = false
  }
}

async function deletePattern(pattern) {
  if (!confirm(`Удалить паттерн "${pattern.name}"?`)) return

  try {
    await tradingAPI.delete(`/api/patterns/${pattern.id}`)
    await loadPatterns()
  } catch (error) {
    console.error('Failed to delete pattern:', error)
    alert('Ошибка удаления')
  }
}

function testPattern(pattern) {
  testingPattern.value = pattern
  testText.value = ''
  testResults.value = null
}

async function runTextTest() {
  if (!testText.value) return

  testing.value = true
  testResults.value = null

  try {
    const response = await tradingAPI.testPattern({
      pattern: testingPattern.value.pattern,
      text: testText.value
    })
    testResults.value = response
  } catch (error) {
    console.error('Failed to test pattern:', error)
    alert('Ошибка тестирования')
  } finally {
    testing.value = false
  }
}

async function testPatternOnMessages(pattern) {
  testingPatternId.value = pattern.id

  try {
    const response = await tradingAPI.testPatternOnMessages(pattern.id, 1000)
    messagesTestResults.value = response
  } catch (error) {
    console.error('Failed to test on messages:', error)
    alert('Ошибка тестирования на сообщениях: ' + error.message)
  } finally {
    testingPatternId.value = null
  }
}

async function reparseAllMessages() {
  if (!confirm('Перепарсить все сообщения? Это может занять время.')) return

  const force = confirm(
    'Удалить существующие сигналы перед репарсингом?\n\n' +
    'ДА = удалить и создать заново\n' +
    'НЕТ = добавить к существующим'
  )

  isReparsing.value = true

  try {
    const result = await tradingAPI.reparseAllMessages(force)
    alert(
      `Репарсинг запущен!\n\n` +
      `Сообщений: ${result.total_messages}\n` +
      `Режим: ${force ? 'Полная замена' : 'Дополнение'}`
    )
  } catch (error) {
    console.error('Failed to start reparse:', error)
    alert('Ошибка запуска репарсинга: ' + error.message)
  } finally {
    setTimeout(() => {
      isReparsing.value = false
    }, 5000)
  }
}

function loadExample() {
  const examples = {
    'ticker': '$SBER купил по 250₽\n$GAZP long entry',
    'direction_long': 'Вход лонг по 100₽ от текущих\nоткрыл лонг',
    'direction_short': 'Открыл шорт по 50\nshort position',
    'operation_exit': 'Закрыл лонг с профитом\nexit short',
    'trading_keyword': 'Открыта позиция на лонг\nвошел в сделку',
    'author': '#TraderPro - сигнал на покупку\n@TradingMaster',
    'price_target': 'Цель: 300₽, стоп: 240₽\ntarget 120',
    'price_stop': 'Стоп по лонгу: 95₽\nstop loss at 50',
    'price_take': 'Тейк профит: 120₽\ntake profit 300',
    'garbage': 'Больше информации в канале @copybot'
  }

  const category = testingPattern.value.category
  const example = examples[category] || 'Тестовое сообщение для проверки'

  testText.value = `${example}\n\n$SBER лонг по 250₽\nЦель: 280₽\nСтоп: 240₽\n\n#Trader - сделка дня`
}

function closeModal() {
  showCreateModal.value = false
  editingPattern.value = null
  formData.value = {
    name: '',
    category: '',
    pattern: '',
    description: '',
    priority: 50,
    is_active: true
  }
}

function getCategoryLabel(category) {
  const labels = {
    'ticker': '🎯 Ticker',
    'direction_long': '📈 Long',
    'direction_short': '📉 Short',
    'operation_exit': '🚪 Exit',
    'trading_keyword': '🔑 Keyword',
    'author': '👤 Author',
    'price_target': '🎯 Target',
    'price_stop': '🛑 Stop',
    'price_take': '💰 Take',
    'garbage': '🗑️ Garbage'
  }
  return labels[category] || category
}

function getCategoryColor(category) {
  const colors = {
    'ticker': 'bg-blue-600 text-white',
    'direction_long': 'bg-green-600 text-white',
    'direction_short': 'bg-red-600 text-white',
    'operation_exit': 'bg-purple-600 text-white',
    'trading_keyword': 'bg-yellow-600 text-white',
    'author': 'bg-pink-600 text-white',
    'price_target': 'bg-cyan-600 text-white',
    'price_stop': 'bg-orange-600 text-white',
    'price_take': 'bg-emerald-600 text-white',
    'garbage': 'bg-gray-600 text-white'
  }
  return colors[category] || 'bg-gray-600 text-white'
}

function formatDate(dateString) {
  if (!dateString) return ''
  return new Date(dateString).toLocaleString('ru-RU')
}

// Lifecycle
onMounted(() => {
  loadPatterns()
})
</script>

<style scoped>
input[type="range"] {
  @apply accent-trading-green;
}
</style>