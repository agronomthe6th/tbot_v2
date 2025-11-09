<template>
  <div class="data-management-page">
    <div class="min-h-screen bg-trading-dark p-6">
    <div class="max-w-7xl mx-auto">
      <h1 class="text-3xl font-bold text-white mb-6">📊 Управление данными</h1>
      
      <!-- Telegram Monitoring Control -->
      <div class="bg-trading-card rounded-lg p-6 mb-6 border border-trading-border">
        <div class="flex justify-between items-center mb-4">
          <h2 class="text-xl font-bold text-white">🔄 Real-time мониторинг</h2>
          <div class="flex items-center gap-3">
            <span 
              :class="monitoringStatus?.is_running ? 'text-green-400' : 'text-gray-400'"
              class="text-sm font-medium"
            >
              {{ monitoringStatus?.is_running ? '🟢 Активен' : '⚫ Остановлен' }}
            </span>
          </div>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
          <div>
            <label class="block text-gray-400 text-sm mb-2">Интервал проверки (сек)</label>
            <input 
              v-model.number="monitoringInterval" 
              type="number"
              min="10"
              max="600"
              class="w-full bg-trading-dark border border-trading-border rounded px-4 py-2 text-white focus:outline-none focus:border-trading-green"
              :disabled="monitoringStatus?.is_running"
            />
          </div>
        </div>

        <div class="flex gap-4">
          <button 
            v-if="!monitoringStatus?.is_running"
            @click="startMonitoring"
            :disabled="startingMonitoring"
            class="px-6 py-3 bg-trading-green hover:bg-green-600 text-white rounded font-semibold disabled:opacity-50 transition-colors"
          >
            {{ startingMonitoring ? '⏳ Запуск...' : '▶️ Запустить мониторинг' }}
          </button>
          
          <button 
            v-else
            @click="stopMonitoring"
            :disabled="stoppingMonitoring"
            class="px-6 py-3 bg-red-600 hover:bg-red-700 text-white rounded font-semibold disabled:opacity-50 transition-colors"
          >
            {{ stoppingMonitoring ? '⏳ Остановка...' : '⏸️ Остановить мониторинг' }}
          </button>
        </div>
      </div>

      <!-- Channels Management -->
      <div class="bg-trading-card rounded-lg p-6 mb-6 border border-trading-border">
        <div class="flex justify-between items-center mb-4">
          <h2 class="text-xl font-bold text-white">📡 Управление каналами</h2>
          <button 
            @click="showAddChannelModal = true"
            class="px-4 py-2 bg-trading-green hover:bg-green-600 text-white rounded font-semibold transition-colors"
          >
            ➕ Добавить канал
          </button>
        </div>

        <!-- Channels Table -->
        <div v-if="channels.length > 0" class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b border-trading-border">
                <th class="text-left py-3 px-4 text-gray-400 font-semibold">Канал</th>
                <th class="text-left py-3 px-4 text-gray-400 font-semibold">Channel ID</th>
                <th class="text-center py-3 px-4 text-gray-400 font-semibold">Статус</th>
                <th class="text-center py-3 px-4 text-gray-400 font-semibold">Сообщений</th>
                <th class="text-center py-3 px-4 text-gray-400 font-semibold">Действия</th>
              </tr>
            </thead>
            <tbody>
              <tr 
                v-for="channel in channels" 
                :key="channel.id"
                class="border-b border-trading-border hover:bg-trading-dark transition-colors"
              >
                <td class="py-3 px-4">
                  <div class="font-semibold text-white">{{ channel.name }}</div>
                  <div v-if="channel.username" class="text-xs text-gray-400">@{{ channel.username }}</div>
                </td>
                <td class="py-3 px-4 text-gray-300 font-mono text-xs">{{ channel.channel_id }}</td>
                <td class="py-3 px-4 text-center">
                  <span 
                    :class="channel.is_enabled ? 'bg-green-900 text-green-300' : 'bg-gray-700 text-gray-400'"
                    class="px-3 py-1 rounded-full text-xs font-semibold"
                  >
                    {{ channel.is_enabled ? '✓ Активен' : '✗ Отключен' }}
                  </span>
                </td>
                <td class="py-3 px-4 text-center text-white font-semibold">
                  {{ channel.total_collected || 0 }}
                </td>
                <td class="py-3 px-4">
                  <div class="flex justify-center gap-2">
                    <!-- Toggle Enable/Disable -->
                    <button 
                      @click="toggleChannel(channel)"
                      :class="channel.is_enabled ? 'bg-yellow-600 hover:bg-yellow-700' : 'bg-green-600 hover:bg-green-700'"
                      class="px-3 py-1 text-white rounded text-xs font-semibold transition-colors"
                    >
                      {{ channel.is_enabled ? '⏸ Отключить' : '▶ Включить' }}
                    </button>
                    
                    <!-- Fetch Latest -->
                    <button 
                      @click="fetchChannelMessages(channel)"
                      :disabled="fetchingChannel === channel.channel_id"
                      class="px-3 py-1 bg-blue-600 hover:bg-blue-700 text-white rounded text-xs font-semibold disabled:opacity-50 transition-colors"
                    >
                      {{ fetchingChannel === channel.channel_id ? '⏳' : '📥' }} Загрузить
                    </button>
                    
                    <!-- Parse -->
                    <button 
                      @click="parseChannelMessages(channel)"
                      :disabled="parsingChannel === channel.channel_id"
                      class="px-3 py-1 bg-purple-600 hover:bg-purple-700 text-white rounded text-xs font-semibold disabled:opacity-50 transition-colors"
                    >
                      {{ parsingChannel === channel.channel_id ? '⏳' : '🔄' }} Парсить
                    </button>
                    
                    <!-- Delete -->
                    <button 
                      @click="deleteChannel(channel)"
                      class="px-3 py-1 bg-red-600 hover:bg-red-700 text-white rounded text-xs font-semibold transition-colors"
                    >
                      🗑️
                    </button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div v-else class="text-center py-8 text-gray-400">
          Каналы не добавлены. Нажмите "➕ Добавить канал" чтобы начать.
        </div>
      </div>

      <!-- Message Processing Pipeline -->
      <div class="bg-trading-card rounded-lg p-6 mb-6 border border-trading-border">
        <h2 class="text-xl font-bold text-white mb-4">⚙️ Обработка сообщений</h2>
        
        <!-- Stats -->
        <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <div class="bg-trading-bg rounded-lg p-4 border border-trading-border">
            <div class="text-sm text-gray-400 mb-1">Необработанные</div>
            <div class="text-2xl font-bold text-yellow-400">{{ unparsedCount || 0 }}</div>
          </div>
          
          <div class="bg-trading-bg rounded-lg p-4 border border-trading-border">
            <div class="text-sm text-gray-400 mb-1">Всего сообщений</div>
            <div class="text-2xl font-bold text-blue-400">{{ signalStats?.total_messages || 0 }}</div>
          </div>
          
          <div class="bg-trading-bg rounded-lg p-4 border border-trading-border">
            <div class="text-sm text-gray-400 mb-1">Создано сигналов</div>
            <div class="text-2xl font-bold text-green-400">{{ signalStats?.total_signals || 0 }}</div>
          </div>
          
          <div class="bg-trading-bg rounded-lg p-4 border border-trading-border">
            <div class="text-sm text-gray-400 mb-1">Успешность</div>
            <div class="text-2xl font-bold text-purple-400">
              {{ signalStats?.processed_messages > 0
                ? Math.round((signalStats.successfully_parsed / signalStats.processed_messages) * 100)
                : 0 }}%
            </div>
          </div>
        </div>

        <!-- Parsing Controls -->
        <div class="space-y-4">
          <div>
            <label class="block text-gray-400 text-sm mb-2">
              Количество сообщений для обработки за раз (батч)
            </label>
            <input 
              v-model.number="parseLimit" 
              type="number"
              min="100"
              max="1000"
              step="100"
              class="w-full max-w-xs bg-trading-dark border border-trading-border rounded px-4 py-2 text-white focus:outline-none focus:border-trading-green"
            />
            <p class="text-gray-500 text-xs mt-1">
              Рекомендуется 200-500 для оптимальной производительности
            </p>
          </div>

          <div class="flex gap-3">
            <button 
              @click="parseMessages"
              :disabled="parsing || unparsedCount === 0"
              class="px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded font-semibold disabled:opacity-50 transition-colors"
            >
              {{ parsing ? '⏳ Обработка...' : '🚀 Обработать новые сообщения' }}
            </button>

            <button 
              @click="refreshStats"
              :disabled="refreshing"
              class="px-6 py-3 bg-gray-600 hover:bg-gray-700 text-white rounded font-semibold disabled:opacity-50 transition-colors"
            >
              {{ refreshing ? '⏳ Обновление...' : '🔄 Обновить статистику' }}
            </button>
          </div>

          <!-- Progress Info -->
          <div v-if="parsing" class="bg-blue-900 bg-opacity-20 border border-blue-700 rounded-lg p-4">
            <div class="flex items-center gap-3">
              <div class="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-400"></div>
              <div>
                <div class="text-blue-300 font-semibold">Идёт обработка сообщений</div>
                <div class="text-blue-400 text-sm mt-1">
                  Обрабатывается до {{ parseLimit }} сообщений. Это может занять несколько секунд...
                </div>
              </div>
            </div>
          </div>

          <div v-if="parsingComplete && parsingResult" class="bg-green-900 bg-opacity-20 border border-green-700 rounded-lg p-4">
            <div class="text-green-300 font-semibold mb-2">✅ Обработка завершена</div>
            <div class="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm mb-3">
              <div>
                <div class="text-gray-400">Обработано:</div>
                <div class="text-white font-semibold">{{ parsingResult.total_processed || 0 }}</div>
              </div>
              <div>
                <div class="text-gray-400">Успешно:</div>
                <div class="text-green-400 font-semibold">{{ parsingResult.successful_parses || 0 }}</div>
              </div>
              <div>
                <div class="text-gray-400">Не торговые:</div>
                <div class="text-yellow-400 font-semibold">{{ parsingResult.non_trading_messages || 0 }}</div>
              </div>
              <div>
                <div class="text-gray-400">Ошибки:</div>
                <div class="text-red-400 font-semibold">{{ parsingResult.failed_parses || 0 }}</div>
              </div>
            </div>

            <!-- Детали ошибок -->
            <div v-if="parsingResult.errors && parsingResult.errors.length > 0" class="mt-3 pt-3 border-t border-green-700">
              <div class="text-yellow-300 font-semibold text-xs mb-2">⚠️ Детали ошибок:</div>
              <div class="max-h-32 overflow-y-auto space-y-1">
                <div
                  v-for="(err, idx) in parsingResult.errors.slice(0, 10)"
                  :key="idx"
                  class="text-xs text-gray-300 bg-red-900 bg-opacity-20 rounded px-2 py-1"
                >
                  <span v-if="err.message_id" class="text-yellow-400">Msg #{{ err.message_id }}:</span>
                  <span class="text-red-300">{{ err.error }}</span>
                </div>
                <div v-if="parsingResult.errors.length > 10" class="text-xs text-gray-400 italic">
                  ... и еще {{ parsingResult.errors.length - 10 }} ошибок
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Signal Processing -->
      <div class="bg-trading-card rounded-lg p-6 border border-trading-border">
        <h2 class="text-xl font-bold text-white mb-4">🎯 Дополнительные действия</h2>
        
        <div class="flex gap-3">
          <button 
            @click="processSignals"
            :disabled="processing"
            class="px-6 py-3 bg-purple-600 hover:bg-purple-700 text-white rounded font-semibold disabled:opacity-50 transition-colors"
          >
            {{ processing ? '⏳ Обработка...' : '📊 Обработать сигналы' }}
          </button>
        </div>

        <p class="text-gray-400 text-sm mt-3">
          Запуск обработки созданных сигналов (матчинг с ценами, обновление статусов)
        </p>
      </div>
    </div>
  </div>

  <!-- Add Channel Modal -->
  <div
    v-if="showAddChannelModal"
    class="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50"
    @click.self="showAddChannelModal = false"
  >
    <div class="bg-trading-card rounded-lg p-6 max-w-md w-full border border-trading-border">
      <h3 class="text-xl font-bold text-white mb-4">➕ Добавить канал</h3>

      <div class="space-y-4">
        <div>
          <label class="block text-gray-400 text-sm mb-2">Channel ID *</label>
          <input
            v-model="newChannel.channel_id"
            type="number"
            placeholder="-1001234567890"
            class="w-full bg-white border border-trading-border rounded px-4 py-2 text-black focus:outline-none focus:border-trading-green"
          />
          <p class="text-gray-500 text-xs mt-1">Число ID канала (может быть отрицательным)</p>
        </div>

        <div>
          <label class="block text-gray-400 text-sm mb-2">Название канала *</label>
          <input
            v-model="newChannel.name"
            type="text"
            placeholder="Crypto Signals"
            class="w-full bg-white border border-trading-border rounded px-4 py-2 text-black focus:outline-none focus:border-trading-green"
          />
        </div>

        <div>
          <label class="block text-gray-400 text-sm mb-2">Username (необязательно)</label>
          <input
            v-model="newChannel.username"
            type="text"
            placeholder="cryptosignals"
            class="w-full bg-white border border-trading-border rounded px-4 py-2 text-black focus:outline-none focus:border-trading-green"
          />
          <p class="text-gray-500 text-xs mt-1">Без символа @</p>
        </div>

        <div class="flex items-center">
          <input
            v-model="newChannel.enabled"
            type="checkbox"
            id="channel-enabled"
            class="w-4 h-4 text-trading-green bg-trading-dark border-trading-border rounded focus:ring-trading-green"
          />
          <label for="channel-enabled" class="ml-2 text-white">Включить мониторинг сразу</label>
        </div>
      </div>

      <div class="flex gap-3 mt-6">
        <button
          @click="addChannel"
          :disabled="!newChannel.channel_id || !newChannel.name || addingChannel"
          class="flex-1 px-4 py-2 bg-trading-green hover:bg-green-600 text-white rounded font-semibold disabled:opacity-50 transition-colors"
        >
          {{ addingChannel ? '⏳ Добавление...' : '✓ Добавить' }}
        </button>
        <button
          @click="showAddChannelModal = false"
          class="flex-1 px-4 py-2 bg-gray-600 hover:bg-gray-700 text-white rounded font-semibold transition-colors"
        >
          Отмена
        </button>
      </div>
    </div>
  </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { tradingAPI } from '../services/api.js'

const monitoringStatus = ref(null)
const monitoringInterval = ref(30)
const startingMonitoring = ref(false)
const stoppingMonitoring = ref(false)

const channels = ref([])
const showAddChannelModal = ref(false)
const newChannel = ref({
  channel_id: null,
  name: '',
  username: '',
  enabled: true
})
const addingChannel = ref(false)
const fetchingChannel = ref(null)
const parsingChannel = ref(null)

const unparsedCount = ref(0)
const signalStats = ref(null)
const parsing = ref(false)
const processing = ref(false)
const refreshing = ref(false)
const parseLimit = ref(300)

const parsingComplete = ref(false)
const parsingResult = ref(null)

let refreshInterval = null

async function getMonitoringStatus() {
  try {
    monitoringStatus.value = await tradingAPI.telegram.getStatus()
  } catch (error) {
    console.error('Failed to get monitoring status:', error)
  }
}

async function startMonitoring() {
  try {
    startingMonitoring.value = true
    await tradingAPI.telegram.startMonitoring(monitoringInterval.value)
    showNotification('✅ Мониторинг запущен')
    await getMonitoringStatus()
  } catch (error) {
    console.error('Failed to start monitoring:', error)
    showNotification(`❌ Ошибка: ${error.message}`, 'error')
  } finally {
    startingMonitoring.value = false
  }
}

async function stopMonitoring() {
  try {
    stoppingMonitoring.value = true
    await tradingAPI.telegram.stopMonitoring()
    showNotification('✅ Мониторинг остановлен')
    await getMonitoringStatus()
  } catch (error) {
    console.error('Failed to stop monitoring:', error)
    showNotification(`❌ Ошибка: ${error.message}`, 'error')
  } finally {
    stoppingMonitoring.value = false
  }
}

async function loadChannels() {
  try {
    const response = await tradingAPI.telegram.getChannels()
    channels.value = response.channels || []
  } catch (error) {
    console.error('Failed to load channels:', error)
  }
}

async function addChannel() {
  if (!newChannel.value.channel_id || !newChannel.value.name) {
    return
  }
  
  addingChannel.value = true
  try {
    await tradingAPI.telegram.addChannel(
      newChannel.value.channel_id,
      newChannel.value.name,
      newChannel.value.enabled
    )
    
    showAddChannelModal.value = false
    newChannel.value = {
      channel_id: null,
      name: '',
      username: '',
      enabled: true
    }
    
    await loadChannels()
    showNotification('✅ Канал добавлен')
  } catch (error) {
    console.error('Failed to add channel:', error)
    alert('Ошибка при добавлении канала: ' + error.message)
  } finally {
    addingChannel.value = false
  }
}

async function toggleChannel(channel) {
  try {
    if (channel.is_enabled) {
      await tradingAPI.telegram.disableChannel(channel.channel_id)
    } else {
      await tradingAPI.telegram.enableChannel(channel.channel_id)
    }
    
    await loadChannels()
    showNotification(`✅ Канал ${channel.is_enabled ? 'отключен' : 'включен'}`)
  } catch (error) {
    console.error('Failed to toggle channel:', error)
    alert('Ошибка при изменении статуса канала')
  }
}

async function fetchChannelMessages(channel) {
  const limit = prompt('Сколько последних сообщений загрузить?', '100')
  if (!limit) return
  
  fetchingChannel.value = channel.channel_id
  try {
    const response = await tradingAPI.telegram.fetchLatestMessages(
      channel.channel_id,
      parseInt(limit)
    )
    
    showNotification(`✅ Загружено ${response.messages_collected} сообщений из канала "${channel.name}"`)
    await loadChannels()
    await refreshStats()
  } catch (error) {
    console.error('Failed to fetch messages:', error)
    alert('Ошибка при загрузке сообщений: ' + error.message)
  } finally {
    fetchingChannel.value = null
  }
}

async function parseChannelMessages(channel) {
  if (!confirm(`Парсить все неразобранные сообщения из канала "${channel.name}"?`)) {
    return
  }
  
  parsingChannel.value = channel.channel_id
  try {
    const response = await tradingAPI.telegram.parseChannelMessages(channel.channel_id)
    
    showNotification(`✅ Парсинг завершен! Разобрано: ${response.parsed}, Ошибок: ${response.failed}`)
    await refreshStats()
  } catch (error) {
    console.error('Failed to parse channel messages:', error)
    alert('Ошибка при парсинге сообщений')
  } finally {
    parsingChannel.value = null
  }
}

async function deleteChannel(channel) {
  if (!confirm(`Удалить канал "${channel.name}"?`)) {
    return
  }
  
  try {
    await tradingAPI.telegram.deleteChannel(channel.channel_id)
    await loadChannels()
    showNotification(`✅ Канал "${channel.name}" удален`)
  } catch (error) {
    console.error('Failed to delete channel:', error)
    alert('Ошибка при удалении канала')
  }
}

async function parseMessages() {
  try {
    parsing.value = true
    parsingComplete.value = false
    parsingResult.value = null

    const response = await tradingAPI.messages.parseAll(parseLimit.value)

    // Используем результат из ответа API
    parsingResult.value = response

    showNotification(`✅ Парсинг завершён: ${response.successful_parses || 0} успешно`)

    // Обновляем статистику
    await refreshStats()

    parsing.value = false
    parsingComplete.value = true

    // Скрываем результаты через 15 секунд
    setTimeout(() => {
      parsingComplete.value = false
      parsingResult.value = null
    }, 15000)

  } catch (error) {
    console.error('Failed to parse messages:', error)
    showNotification(`❌ Ошибка: ${error.message}`, 'error')
    parsing.value = false
  }
}

async function getUnparsedCount() {
  try {
    const response = await tradingAPI.messages.getUnparsed(1)
    unparsedCount.value = response.count || 0
  } catch (error) {
    console.error('Failed to get unparsed count:', error)
  }
}

async function processSignals() {
  try {
    processing.value = true
    await tradingAPI.signals.process()
    showNotification('✅ Обработка сигналов запущена')
    setTimeout(async () => {
      await getSignalStats()
      processing.value = false
    }, 3000)
  } catch (error) {
    console.error('Failed to process signals:', error)
    showNotification(`❌ Ошибка: ${error.message}`, 'error')
    processing.value = false
  }
}

async function getSignalStats() {
  try {
    signalStats.value = await tradingAPI.getSignalsStats()
  } catch (error) {
    console.error('Failed to get signal stats:', error)
  }
}

async function refreshStats() {
  try {
    refreshing.value = true
    await Promise.all([
      getUnparsedCount(),
      getSignalStats()
    ])
  } catch (error) {
    console.error('Failed to refresh stats:', error)
  } finally {
    refreshing.value = false
  }
}

function showNotification(message, type = 'success') {
  console.log(`[${type}]`, message)
}

onMounted(async () => {
  await getMonitoringStatus()
  await loadChannels()
  await refreshStats()
  
  refreshInterval = setInterval(async () => {
    if (!parsing.value) {
      await getUnparsedCount()
    }
  }, 10000)
})

onBeforeUnmount(() => {
  if (refreshInterval) {
    clearInterval(refreshInterval)
  }
})
</script>