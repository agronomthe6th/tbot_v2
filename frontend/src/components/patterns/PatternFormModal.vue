<template>
  <div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
    <div class="bg-trading-card border border-trading-border rounded-lg max-w-2xl w-full max-h-[90vh] overflow-y-auto">
      <!-- Заголовок -->
      <div class="sticky top-0 bg-trading-card border-b border-trading-border px-6 py-4">
        <div class="flex justify-between items-center">
          <h2 class="text-xl font-bold text-white">
            {{ isEditing ? '✏️ Редактировать паттерн' : '➕ Создать паттерн' }}
          </h2>
          <button @click="$emit('close')" class="text-gray-400 hover:text-white transition-colors">
            ✕
          </button>
        </div>
      </div>

      <!-- Форма -->
      <form @submit.prevent="savePattern" class="p-6 space-y-4">
        <!-- Название -->
        <div>
          <label class="block text-gray-400 text-sm mb-2">Название паттерна *</label>
          <input
            v-model="form.name"
            type="text"
            required
            placeholder="entry_long_action"
            class="w-full bg-trading-bg border border-trading-border rounded px-3 py-2 text-white focus:outline-none focus:border-trading-green"
          />
          <p class="text-gray-500 text-xs mt-1">Уникальное имя для идентификации паттерна</p>
        </div>

        <!-- Категория -->
        <div>
          <label class="block text-gray-400 text-sm mb-2">Категория *</label>
          <select
            v-model="form.category"
            required
            class="w-full bg-trading-bg border border-trading-border rounded px-3 py-2 text-white focus:outline-none focus:border-trading-green"
          >
            <option value="">Выберите категорию</option>
            <option value="ticker">ticker - Тикеры</option>
            <option value="direction_long">direction_long - Вход в лонг</option>
            <option value="direction_short">direction_short - Вход в шорт</option>
            <option value="operation_exit">operation_exit - Выход из позиции</option>
            <option value="trading_keyword">trading_keyword - Торговые ключевые слова</option>
            <option value="author">author - Автор сигнала</option>
            <option value="price_target">price_target - Целевая цена</option>
            <option value="price_stop">price_stop - Стоп-лосс</option>
            <option value="price_take">price_take - Тейк-профит</option>
            <option value="garbage">garbage - Мусор для очистки</option>
          </select>
        </div>

        <!-- Паттерн (regex) -->
        <div>
          <label class="block text-gray-400 text-sm mb-2">Регулярное выражение *</label>
          <textarea
            v-model="form.pattern"
            required
            rows="3"
            placeholder="(?i)\b(вход|купил|покупк|buy|набрал)\s+лонг\b"
            class="w-full bg-trading-bg border border-trading-border rounded px-3 py-2 text-white font-mono text-sm focus:outline-none focus:border-trading-green"
          ></textarea>
          <p class="text-gray-500 text-xs mt-1">JavaScript regex паттерн (без слешей и флагов)</p>
        </div>

        <!-- Приоритет -->
        <div>
          <label class="block text-gray-400 text-sm mb-2">Приоритет</label>
          <input
            v-model.number="form.priority"
            type="number"
            min="0"
            max="1000"
            class="w-full bg-trading-bg border border-trading-border rounded px-3 py-2 text-white focus:outline-none focus:border-trading-green"
          />
          <p class="text-gray-500 text-xs mt-1">Чем выше число, тем раньше проверяется паттерн (0-1000)</p>
        </div>

        <!-- Описание -->
        <div>
          <label class="block text-gray-400 text-sm mb-2">Описание</label>
          <textarea
            v-model="form.description"
            rows="2"
            placeholder="Вход в длинную позицию с действием (купил лонг, вход лонг)"
            class="w-full bg-trading-bg border border-trading-border rounded px-3 py-2 text-white focus:outline-none focus:border-trading-green"
          ></textarea>
        </div>

        <!-- Активность -->
        <div class="flex items-center gap-2">
          <input
            v-model="form.is_active"
            type="checkbox"
            id="is_active"
            class="w-4 h-4"
          />
          <label for="is_active" class="text-gray-400 text-sm cursor-pointer">
            Паттерн активен
          </label>
        </div>

        <!-- Кнопки -->
        <div class="flex gap-3 pt-4">
          <button
            type="submit"
            :disabled="saving"
            class="flex-1 px-4 py-2 bg-trading-green hover:bg-green-600 text-white rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed font-semibold"
          >
            {{ saving ? 'Сохранение...' : (isEditing ? 'Сохранить изменения' : 'Создать паттерн') }}
          </button>
          <button
            type="button"
            @click="$emit('close')"
            class="px-4 py-2 bg-gray-600 hover:bg-gray-700 text-white rounded transition-colors"
          >
            Отмена
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { tradingAPI } from '../../services/api'

const props = defineProps({
  pattern: {
    type: Object,
    default: null
  }
})

const emit = defineEmits(['close', 'saved'])

const isEditing = computed(() => !!props.pattern)

const form = ref({
  name: '',
  category: '',
  pattern: '',
  priority: 0,
  description: '',
  is_active: true
})

const saving = ref(false)

async function savePattern() {
  saving.value = true
  try {
    if (isEditing.value) {
      await tradingAPI.put(`/api/patterns/${props.pattern.id}`, form.value)
    } else {
      await tradingAPI.post('/api/patterns', form.value)
    }
    emit('saved')
  } catch (error) {
    console.error('Failed to save pattern:', error)
    const errorMsg = error.response?.data?.detail || 'Ошибка сохранения паттерна'
    alert(errorMsg)
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  if (props.pattern) {
    form.value = {
      name: props.pattern.name,
      category: props.pattern.category,
      pattern: props.pattern.pattern,
      priority: props.pattern.priority,
      description: props.pattern.description || '',
      is_active: props.pattern.is_active
    }
  }
})
</script>