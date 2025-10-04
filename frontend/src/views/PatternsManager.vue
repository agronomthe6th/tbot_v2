<template>
  <div class="min-h-screen bg-trading-bg p-6">
    <div class="max-w-7xl mx-auto">
      <!-- Заголовок -->
      <div class="mb-6">
        <h1 class="text-3xl font-bold text-white mb-2">🎯 Управление паттернами парсинга</h1>
        <p class="text-gray-400">Настройка регулярных выражений для распознавания торговых сигналов</p>
      </div>

      <!-- Статистика и кнопки действий -->
      <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <div class="bg-trading-card border border-trading-border rounded-lg p-4">
          <div class="text-gray-400 text-sm">Всего паттернов</div>
          <div class="text-2xl font-bold text-white">{{ totalPatterns }}</div>
        </div>
        <div class="bg-trading-card border border-trading-border rounded-lg p-4">
          <div class="text-gray-400 text-sm">Активных</div>
          <div class="text-2xl font-bold text-trading-green">{{ activePatterns }}</div>
        </div>
        <div class="bg-trading-card border border-trading-border rounded-lg p-4">
          <div class="text-gray-400 text-sm">Категорий</div>
          <div class="text-2xl font-bold text-blue-400">{{ categoriesCount }}</div>
        </div>
        <div class="bg-trading-card border border-trading-border rounded-lg p-4 flex items-center justify-center">
          <button 
            @click="showCreateModal = true"
            class="w-full px-4 py-2 bg-trading-green hover:bg-green-600 text-white rounded-lg transition-colors font-semibold"
          >
            ➕ Добавить паттерн
          </button>
        </div>
      </div>

      <!-- Фильтры -->
      <div class="bg-trading-card border border-trading-border rounded-lg p-4 mb-6">
        <div class="flex flex-wrap gap-4 items-center">
          <div>
            <label class="text-gray-400 text-sm mb-1 block">Категория</label>
            <select 
              v-model="selectedCategory"
              @change="loadPatterns"
              class="bg-trading-bg border border-trading-border rounded px-3 py-2 text-white"
            >
              <option value="">Все категории</option>
              <option v-for="cat in categories" :key="cat" :value="cat">{{ cat }}</option>
            </select>
          </div>
          
          <div>
            <label class="text-gray-400 text-sm mb-1 block">Статус</label>
            <select 
              v-model="activeOnly"
              @change="loadPatterns"
              class="bg-trading-bg border border-trading-border rounded px-3 py-2 text-white"
            >
              <option :value="false">Все</option>
              <option :value="true">Только активные</option>
            </select>
          </div>

          <div class="ml-auto">
            <button 
              @click="loadPatterns"
              class="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded transition-colors"
              :disabled="loading"
            >
              🔄 Обновить
            </button>
          </div>
        </div>
      </div>

      <!-- Таблица паттернов -->
      <div class="bg-trading-card border border-trading-border rounded-lg overflow-hidden">
        <div v-if="loading" class="p-8 text-center text-gray-400">
          <div class="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-trading-green"></div>
          <p class="mt-2">Загрузка паттернов...</p>
        </div>

        <div v-else-if="filteredPatterns.length === 0" class="p-8 text-center text-gray-400">
          <p>Паттернов не найдено</p>
          <button 
            @click="showCreateModal = true"
            class="mt-4 px-4 py-2 bg-trading-green hover:bg-green-600 text-white rounded transition-colors"
          >
            Создать первый паттерн
          </button>
        </div>

        <div v-else class="overflow-x-auto">
          <table class="w-full">
            <thead class="bg-trading-bg border-b border-trading-border">
              <tr>
                <th class="px-4 py-3 text-left text-gray-400 text-sm font-semibold">Статус</th>
                <th class="px-4 py-3 text-left text-gray-400 text-sm font-semibold">Название</th>
                <th class="px-4 py-3 text-left text-gray-400 text-sm font-semibold">Категория</th>
                <th class="px-4 py-3 text-left text-gray-400 text-sm font-semibold">Паттерн</th>
                <th class="px-4 py-3 text-left text-gray-400 text-sm font-semibold">Приоритет</th>
                <th class="px-4 py-3 text-right text-gray-400 text-sm font-semibold">Действия</th>
              </tr>
            </thead>
            <tbody>
              <tr 
                v-for="pattern in filteredPatterns" 
                :key="pattern.id"
                class="border-b border-trading-border hover:bg-trading-bg transition-colors"
              >
                <td class="px-4 py-3">
                  <button
                    @click="togglePattern(pattern)"
                    :class="[
                      'px-2 py-1 rounded text-xs font-semibold transition-colors',
                      pattern.is_active 
                        ? 'bg-green-900 text-trading-green hover:bg-green-800' 
                        : 'bg-gray-700 text-gray-400 hover:bg-gray-600'
                    ]"
                  >
                    {{ pattern.is_active ? '✓ Активен' : '✗ Выкл' }}
                  </button>
                </td>
                <td class="px-4 py-3">
                  <div class="text-white font-medium">{{ pattern.name }}</div>
                  <div class="text-gray-400 text-xs mt-1">{{ pattern.description || 'Без описания' }}</div>
                </td>
                <td class="px-4 py-3">
                  <span :class="getCategoryColor(pattern.category)" class="px-2 py-1 rounded text-xs font-semibold">
                    {{ pattern.category }}
                  </span>
                </td>
                <td class="px-4 py-3">
                  <code class="text-xs bg-gray-900 px-2 py-1 rounded text-blue-400 font-mono">
                    {{ truncatePattern(pattern.pattern) }}
                  </code>
                </td>
                <td class="px-4 py-3 text-white">{{ pattern.priority }}</td>
                <td class="px-4 py-3 text-right">
                  <div class="flex gap-2 justify-end">
                    <button
                      @click="testPattern(pattern)"
                      class="px-3 py-1 bg-blue-600 hover:bg-blue-700 text-white rounded text-sm transition-colors"
                      title="Тестировать"
                    >
                      🧪
                    </button>
                    <button
                      @click="editPattern(pattern)"
                      class="px-3 py-1 bg-yellow-600 hover:bg-yellow-700 text-white rounded text-sm transition-colors"
                      title="Редактировать"
                    >
                      ✏️
                    </button>
                    <button
                      @click="deletePattern(pattern)"
                      class="px-3 py-1 bg-red-600 hover:bg-red-700 text-white rounded text-sm transition-colors"
                      title="Удалить"
                    >
                      🗑️
                    </button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Модальное окно создания/редактирования -->
      <PatternFormModal
        v-if="showCreateModal || editingPattern"
        :pattern="editingPattern"
        @close="closeModal"
        @saved="onPatternSaved"
      />

      <!-- Модальное окно тестирования -->
      <PatternTesterModal
        v-if="testingPattern"
        :pattern="testingPattern"
        @close="testingPattern = null"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { tradingAPI } from '../services/api'
import PatternFormModal from '../components/patterns/PatternFormModal.vue'
import PatternTesterModal from '../components/patterns/PatternTesterModal.vue'

const patterns = ref([])
const loading = ref(false)
const selectedCategory = ref('')
const activeOnly = ref(false)
const showCreateModal = ref(false)
const editingPattern = ref(null)
const testingPattern = ref(null)

const categories = computed(() => {
  const cats = new Set(patterns.value.map(p => p.category))
  return Array.from(cats).sort()
})

const filteredPatterns = computed(() => {
  let filtered = patterns.value
  
  if (selectedCategory.value) {
    filtered = filtered.filter(p => p.category === selectedCategory.value)
  }
  
  if (activeOnly.value) {
    filtered = filtered.filter(p => p.is_active)
  }
  
  return filtered.sort((a, b) => {
    if (a.category !== b.category) {
      return a.category.localeCompare(b.category)
    }
    return b.priority - a.priority
  })
})

const totalPatterns = computed(() => patterns.value.length)
const activePatterns = computed(() => patterns.value.filter(p => p.is_active).length)
const categoriesCount = computed(() => categories.value.length)

async function loadPatterns() {
  loading.value = true
  try {
    const params = {}
    if (selectedCategory.value) params.category = selectedCategory.value
    if (activeOnly.value) params.active_only = true
    
    const response = await tradingAPI.get('/api/patterns', { params })
    patterns.value = response.data.patterns
  } catch (error) {
    console.error('Failed to load patterns:', error)
    alert('Ошибка загрузки паттернов')
  } finally {
    loading.value = false
  }
}

async function togglePattern(pattern) {
  try {
    await tradingAPI.patch(`/api/patterns/${pattern.id}/toggle`)
    pattern.is_active = !pattern.is_active
  } catch (error) {
    console.error('Failed to toggle pattern:', error)
    alert('Ошибка переключения паттерна')
  }
}

function editPattern(pattern) {
  editingPattern.value = { ...pattern }
}

function testPattern(pattern) {
  testingPattern.value = pattern
}

async function deletePattern(pattern) {
  if (!confirm(`Удалить паттерн "${pattern.name}"?`)) return
  
  try {
    await tradingAPI.delete(`/api/patterns/${pattern.id}`)
    await loadPatterns()
  } catch (error) {
    console.error('Failed to delete pattern:', error)
    alert('Ошибка удаления паттерна')
  }
}

function closeModal() {
  showCreateModal.value = false
  editingPattern.value = null
}

async function onPatternSaved() {
  closeModal()
  await loadPatterns()
}

function truncatePattern(pattern) {
  return pattern.length > 60 ? pattern.substring(0, 60) + '...' : pattern
}

function getCategoryColor(category) {
  const colors = {
    'ticker': 'bg-blue-900 text-blue-400',
    'direction_long': 'bg-green-900 text-green-400',
    'direction_short': 'bg-red-900 text-red-400',
    'operation_exit': 'bg-yellow-900 text-yellow-400',
    'trading_keyword': 'bg-purple-900 text-purple-400',
    'author': 'bg-pink-900 text-pink-400',
    'price_target': 'bg-cyan-900 text-cyan-400',
    'price_stop': 'bg-orange-900 text-orange-400',
    'price_take': 'bg-teal-900 text-teal-400',
    'garbage': 'bg-gray-900 text-gray-400'
  }
  return colors[category] || 'bg-gray-900 text-gray-400'
}

onMounted(() => {
  loadPatterns()
})
</script>