<template>
  <div class="consensus-page">
    <div class="min-h-screen bg-trading-bg text-white p-4">
      <div class="max-w-7xl mx-auto">

        <!-- Заголовок -->
        <div class="mb-6">
          <h1 class="text-3xl font-bold mb-2">🔥 Консенсус Трейдеров</h1>
          <p class="text-gray-400">
            Моменты когда несколько трейдеров независимо дают сигналы на один актив
          </p>
        </div>

        <!-- Вкладки -->
        <div class="mb-6 border-b border-trading-border">
          <div class="flex gap-4">
            <button
              @click="activeTab = 'events'"
              :class="activeTab === 'events' ? 'border-trading-green text-white' : 'border-transparent text-gray-400 hover:text-gray-300'"
              class="px-4 py-3 border-b-2 font-semibold transition-colors"
            >
              📊 События консенсуса
            </button>
            <button
              @click="activeTab = 'rules'"
              :class="activeTab === 'rules' ? 'border-trading-green text-white' : 'border-transparent text-gray-400 hover:text-gray-300'"
              class="px-4 py-3 border-b-2 font-semibold transition-colors"
            >
              📋 Правила детекции
            </button>
            <button
              @click="activeTab = 'backtest'"
              :class="activeTab === 'backtest' ? 'border-trading-green text-white' : 'border-transparent text-gray-400 hover:text-gray-300'"
              class="px-4 py-3 border-b-2 font-semibold transition-colors"
            >
              🧪 Бэктестинг
            </button>
          </div>
        </div>

        <!-- Вкладка: События консенсуса -->
        <div v-if="activeTab === 'events'">
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

          <div v-else-if="error" class="result-panel-error mb-6">
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

        <!-- Вкладка: Правила -->
        <div v-if="activeTab === 'rules'">
          <!-- Заголовок секции правил -->
          <div class="flex justify-between items-center mb-6">
            <div>
              <h2 class="text-xl font-bold">Правила детекции консенсуса</h2>
              <p class="text-gray-400 text-sm mt-1">
                Настройте условия для автоматического обнаружения консенсусов
              </p>
            </div>
            <button
              @click="openRuleModal()"
              class="px-4 py-2 bg-trading-green text-black rounded font-semibold hover:bg-green-500 transition-colors"
            >
              ➕ Создать правило
            </button>
          </div>

          <!-- Список правил -->
          <div v-if="rulesLoading" class="text-center py-12">
            <div class="text-gray-400">Загрузка правил...</div>
          </div>

          <div v-else-if="rules.length === 0" class="text-center py-12">
            <div class="text-gray-400 mb-4">Правил пока нет. Создайте первое правило!</div>
            <button
              @click="openRuleModal()"
              class="px-6 py-3 bg-trading-green text-black rounded-lg hover:bg-green-500 transition-colors"
            >
              ➕ Создать первое правило
            </button>
          </div>

          <div v-else class="space-y-4">
            <div
              v-for="rule in rules"
              :key="rule.id"
              class="bg-trading-card p-5 rounded-lg border border-trading-border"
            >
              <div class="flex items-start justify-between mb-4">
                <div class="flex-1">
                  <div class="flex items-center gap-3 mb-2">
                    <h3 class="text-lg font-bold">{{ rule.name }}</h3>
                    <span
                      :class="rule.is_active ? 'bg-green-900 text-green-300' : 'bg-gray-700 text-gray-400'"
                      class="px-2 py-1 rounded text-xs font-semibold"
                    >
                      {{ rule.is_active ? '✓ Активно' : '✗ Отключено' }}
                    </span>
                    <span class="px-2 py-1 bg-trading-bg rounded text-xs text-gray-400">
                      Приоритет: {{ rule.priority }}
                    </span>
                  </div>
                  <p v-if="rule.description" class="text-gray-400 text-sm">{{ rule.description }}</p>
                </div>
                <div class="flex gap-2 ml-4">
                  <button
                    @click="toggleRule(rule)"
                    :class="rule.is_active ? 'bg-yellow-600 hover:bg-yellow-700' : 'bg-green-600 hover:bg-green-700'"
                    class="px-3 py-1 text-white rounded text-sm font-semibold transition-colors"
                  >
                    {{ rule.is_active ? '⏸ Отключить' : '▶ Включить' }}
                  </button>
                  <button
                    @click="openRuleModal(rule)"
                    class="px-3 py-1 bg-blue-600 hover:bg-blue-700 text-white rounded text-sm font-semibold transition-colors"
                  >
                    ✏️ Изменить
                  </button>
                  <button
                    @click="deleteRule(rule)"
                    class="px-3 py-1 bg-red-600 hover:bg-red-700 text-white rounded text-sm font-semibold transition-colors"
                  >
                    🗑️
                  </button>
                </div>
              </div>

              <!-- Детали правила -->
              <div class="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                <div>
                  <div class="text-gray-400">Мин. трейдеров</div>
                  <div class="font-semibold">{{ rule.min_traders }}</div>
                </div>
                <div>
                  <div class="text-gray-400">Окно времени</div>
                  <div class="font-semibold">{{ rule.window_minutes }} мин</div>
                </div>
                <div>
                  <div class="text-gray-400">Направление</div>
                  <div class="font-semibold">{{ rule.direction_filter || 'Любое' }}</div>
                </div>
                <div>
                  <div class="text-gray-400">Тикеры</div>
                  <div class="font-semibold">{{ rule.ticker_filter || 'Все' }}</div>
                </div>
              </div>

              <div v-if="rule.min_confidence || rule.min_strength" class="mt-3 pt-3 border-t border-trading-border">
                <div class="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                  <div v-if="rule.min_confidence">
                    <div class="text-gray-400">Мин. уверенность</div>
                    <div class="font-semibold">{{ rule.min_confidence }}%</div>
                  </div>
                  <div v-if="rule.min_strength">
                    <div class="text-gray-400">Мин. сила</div>
                    <div class="font-semibold">{{ rule.min_strength }}/100</div>
                  </div>
                  <div>
                    <div class="text-gray-400">Строгий консенсус</div>
                    <div class="font-semibold">{{ rule.strict_consensus ? 'Да' : 'Нет' }}</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Вкладка: Бэктестинг -->
        <div v-if="activeTab === 'backtest'">
          <ConsensusBacktest :rules="rules" />
        </div>
      </div>
    </div>

    <!-- Модальное окно создания/редактирования правила -->
    <div
      v-if="showRuleModal"
      class="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50 p-4"
      @click.self="closeRuleModal"
    >
      <div class="bg-trading-card rounded-lg p-6 max-w-2xl w-full border border-trading-border max-h-[90vh] overflow-y-auto">
        <h3 class="text-xl font-bold text-white mb-4">
          {{ editingRule ? '✏️ Редактировать правило' : '➕ Создать правило' }}
        </h3>

        <div class="space-y-4">
          <!-- Название -->
          <div>
            <label class="block text-gray-400 text-sm mb-2">Название правила *</label>
            <input
              v-model="ruleForm.name"
              type="text"
              placeholder="Например: SBER Quick Consensus"
              class="w-full bg-trading-bg border border-trading-border rounded px-4 py-2 text-white focus:outline-none focus:border-trading-green"
            />
          </div>

          <!-- Описание -->
          <div>
            <label class="block text-gray-400 text-sm mb-2">Описание</label>
            <textarea
              v-model="ruleForm.description"
              placeholder="Краткое описание правила..."
              rows="2"
              class="w-full bg-trading-bg border border-trading-border rounded px-4 py-2 text-white focus:outline-none focus:border-trading-green"
            ></textarea>
          </div>

          <!-- Основные параметры -->
          <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label class="block text-gray-400 text-sm mb-2">Мин. трейдеров *</label>
              <input
                v-model.number="ruleForm.min_traders"
                type="number"
                min="2"
                class="w-full bg-trading-bg border border-trading-border rounded px-4 py-2 text-white focus:outline-none focus:border-trading-green"
              />
            </div>

            <div>
              <label class="block text-gray-400 text-sm mb-2">Окно времени (мин) *</label>
              <input
                v-model.number="ruleForm.window_minutes"
                type="number"
                min="1"
                class="w-full bg-trading-bg border border-trading-border rounded px-4 py-2 text-white focus:outline-none focus:border-trading-green"
              />
            </div>

            <div>
              <label class="block text-gray-400 text-sm mb-2">Приоритет</label>
              <input
                v-model.number="ruleForm.priority"
                type="number"
                class="w-full bg-trading-bg border border-trading-border rounded px-4 py-2 text-white focus:outline-none focus:border-trading-green"
              />
            </div>
          </div>

          <!-- Фильтры -->
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label class="block text-gray-400 text-sm mb-2">Фильтр по тикерам</label>
              <input
                v-model="ruleForm.ticker_filter"
                type="text"
                placeholder="SBER,GAZP или оставьте пустым"
                class="w-full bg-trading-bg border border-trading-border rounded px-4 py-2 text-white focus:outline-none focus:border-trading-green"
              />
              <p class="text-gray-500 text-xs mt-1">Через запятую или пусто для всех</p>
            </div>

            <div>
              <label class="block text-gray-400 text-sm mb-2">Направление</label>
              <select
                v-model="ruleForm.direction_filter"
                class="w-full bg-trading-bg border border-trading-border rounded px-4 py-2 text-white focus:outline-none focus:border-trading-green"
              >
                <option value="">Любое</option>
                <option value="long">LONG</option>
                <option value="short">SHORT</option>
              </select>
            </div>
          </div>

          <!-- Критерии -->
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label class="block text-gray-400 text-sm mb-2">Мин. уверенность сигнала (0-100)</label>
              <input
                v-model.number="ruleForm.min_confidence"
                type="number"
                min="0"
                max="100"
                placeholder="Не проверять"
                class="w-full bg-trading-bg border border-trading-border rounded px-4 py-2 text-white focus:outline-none focus:border-trading-green"
              />
            </div>

            <div>
              <label class="block text-gray-400 text-sm mb-2">Мин. сила консенсуса (0-100)</label>
              <input
                v-model.number="ruleForm.min_strength"
                type="number"
                min="0"
                max="100"
                placeholder="Не проверять"
                class="w-full bg-trading-bg border border-trading-border rounded px-4 py-2 text-white focus:outline-none focus:border-trading-green"
              />
            </div>
          </div>

          <!-- Чекбоксы -->
          <div class="space-y-2">
            <div class="flex items-center">
              <input
                v-model="ruleForm.strict_consensus"
                type="checkbox"
                id="strict-consensus"
                class="w-4 h-4 text-trading-green bg-trading-dark border-trading-border rounded focus:ring-trading-green"
              />
              <label for="strict-consensus" class="ml-2 text-white text-sm">
                Строгий консенсус (все сигналы должны быть в одном направлении)
              </label>
            </div>

            <div class="flex items-center">
              <input
                v-model="ruleForm.is_active"
                type="checkbox"
                id="rule-active"
                class="w-4 h-4 text-trading-green bg-trading-dark border-trading-border rounded focus:ring-trading-green"
              />
              <label for="rule-active" class="ml-2 text-white text-sm">
                Активировать правило сразу после создания
              </label>
            </div>
          </div>

          <!-- Технические индикаторы -->
          <div class="border-t border-trading-border pt-4">
            <h4 class="text-lg font-semibold text-white mb-3">📊 Технические индикаторы (опционально)</h4>

            <!-- RSI -->
            <div class="bg-trading-bg p-3 rounded mb-3">
              <div class="flex items-center mb-2">
                <input
                  v-model="ruleForm.indicator_conditions.rsi.enabled"
                  type="checkbox"
                  id="rsi-enabled"
                  class="w-4 h-4 text-trading-green bg-trading-dark border-trading-border rounded"
                />
                <label for="rsi-enabled" class="ml-2 text-white font-semibold">RSI (Relative Strength Index)</label>
              </div>
              <div v-if="ruleForm.indicator_conditions.rsi.enabled" class="grid grid-cols-2 gap-3 ml-6">
                <div>
                  <label class="block text-gray-400 text-xs mb-1">Мин. RSI</label>
                  <input
                    v-model.number="ruleForm.indicator_conditions.rsi.min"
                    type="number"
                    min="0"
                    max="100"
                    placeholder="0"
                    class="w-full bg-trading-card border border-trading-border rounded px-2 py-1 text-white text-sm"
                  />
                </div>
                <div>
                  <label class="block text-gray-400 text-xs mb-1">Макс. RSI</label>
                  <input
                    v-model.number="ruleForm.indicator_conditions.rsi.max"
                    type="number"
                    min="0"
                    max="100"
                    placeholder="100"
                    class="w-full bg-trading-card border border-trading-border rounded px-2 py-1 text-white text-sm"
                  />
                </div>
              </div>
            </div>

            <!-- MACD -->
            <div class="bg-trading-bg p-3 rounded mb-3">
              <div class="flex items-center mb-2">
                <input
                  v-model="ruleForm.indicator_conditions.macd.enabled"
                  type="checkbox"
                  id="macd-enabled"
                  class="w-4 h-4 text-trading-green bg-trading-dark border-trading-border rounded"
                />
                <label for="macd-enabled" class="ml-2 text-white font-semibold">MACD</label>
              </div>
              <div v-if="ruleForm.indicator_conditions.macd.enabled" class="ml-6">
                <label class="block text-gray-400 text-xs mb-1">Сигнал</label>
                <select
                  v-model="ruleForm.indicator_conditions.macd.signal"
                  class="w-full bg-trading-card border border-trading-border rounded px-2 py-1 text-white text-sm"
                >
                  <option value="">Любой</option>
                  <option value="bullish_crossover">Бычье пересечение</option>
                  <option value="bearish_crossover">Медвежье пересечение</option>
                  <option value="bullish">Бычий</option>
                  <option value="bearish">Медвежий</option>
                </select>
              </div>
            </div>

            <!-- Bollinger Bands -->
            <div class="bg-trading-bg p-3 rounded mb-3">
              <div class="flex items-center mb-2">
                <input
                  v-model="ruleForm.indicator_conditions.bollinger.enabled"
                  type="checkbox"
                  id="bollinger-enabled"
                  class="w-4 h-4 text-trading-green bg-trading-dark border-trading-border rounded"
                />
                <label for="bollinger-enabled" class="ml-2 text-white font-semibold">Bollinger Bands</label>
              </div>
              <div v-if="ruleForm.indicator_conditions.bollinger.enabled" class="ml-6">
                <label class="block text-gray-400 text-xs mb-1">Сигнал</label>
                <select
                  v-model="ruleForm.indicator_conditions.bollinger.signal"
                  class="w-full bg-trading-card border border-trading-border rounded px-2 py-1 text-white text-sm"
                >
                  <option value="">Любой</option>
                  <option value="at_upper_band">У верхней границы</option>
                  <option value="at_lower_band">У нижней границы</option>
                  <option value="within_bands">Внутри полос</option>
                </select>
              </div>
            </div>

            <!-- OBV -->
            <div class="bg-trading-bg p-3 rounded">
              <div class="flex items-center mb-2">
                <input
                  v-model="ruleForm.indicator_conditions.obv.enabled"
                  type="checkbox"
                  id="obv-enabled"
                  class="w-4 h-4 text-trading-green bg-trading-dark border-trading-border rounded"
                />
                <label for="obv-enabled" class="ml-2 text-white font-semibold">OBV (On-Balance Volume)</label>
              </div>
              <div v-if="ruleForm.indicator_conditions.obv.enabled" class="ml-6">
                <label class="block text-gray-400 text-xs mb-1">Сигнал</label>
                <select
                  v-model="ruleForm.indicator_conditions.obv.signal"
                  class="w-full bg-trading-card border border-trading-border rounded px-2 py-1 text-white text-sm"
                >
                  <option value="">Любой</option>
                  <option value="accumulation">Накопление</option>
                  <option value="distribution">Распределение</option>
                  <option value="neutral">Нейтрально</option>
                </select>
              </div>
            </div>
          </div>
        </div>

        <div class="flex gap-3 mt-6">
          <button
            @click="saveRule"
            :disabled="!ruleForm.name || !ruleForm.min_traders || !ruleForm.window_minutes || ruleSaving"
            class="flex-1 px-4 py-2 bg-trading-green text-black rounded font-semibold hover:bg-green-500 disabled:opacity-50 transition-colors"
          >
            {{ ruleSaving ? '⏳ Сохранение...' : (editingRule ? '✓ Сохранить' : '✓ Создать') }}
          </button>
          <button
            @click="closeRuleModal"
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
import { ref, computed, onMounted } from 'vue'
import { tradingAPI } from '../services/api'
import ConsensusBacktest from '../components/ConsensusBacktest.vue'

// Общие состояния
const activeTab = ref('events')

// События консенсуса
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

// Правила
const rules = ref([])
const rulesLoading = ref(false)
const showRuleModal = ref(false)
const editingRule = ref(null)
const ruleSaving = ref(false)
const ruleForm = ref({
  name: '',
  description: '',
  min_traders: 2,
  window_minutes: 10,
  strict_consensus: true,
  ticker_filter: '',
  direction_filter: '',
  min_confidence: null,
  min_strength: null,
  is_active: true,
  priority: 0,
  indicator_conditions: {
    rsi: { enabled: false, min: null, max: null },
    macd: { enabled: false, signal: '' },
    bollinger: { enabled: false, signal: '' },
    obv: { enabled: false, signal: '' }
  }
})

const totalPages = computed(() => {
  return Math.ceil(totalConsensus.value / filters.value.limit)
})

// ===== ФУНКЦИИ ДЛЯ СОБЫТИЙ КОНСЕНСУСА =====

async function loadConsensusEvents() {
  isLoading.value = true
  error.value = null

  try {
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
  // TODO: Открыть модальное окно с деталями консенсуса
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

// ===== ФУНКЦИИ ДЛЯ ПРАВИЛ =====

async function loadRules() {
  rulesLoading.value = true

  try {
    const response = await tradingAPI.getConsensusRules()
    rules.value = response.rules || []
  } catch (err) {
    console.error('❌ Error loading rules:', err)
  } finally {
    rulesLoading.value = false
  }
}

function openRuleModal(rule = null) {
  if (rule) {
    editingRule.value = rule
    ruleForm.value = {
      name: rule.name,
      description: rule.description || '',
      min_traders: rule.min_traders,
      window_minutes: rule.window_minutes,
      strict_consensus: rule.strict_consensus,
      ticker_filter: rule.ticker_filter || '',
      direction_filter: rule.direction_filter || '',
      min_confidence: rule.min_confidence,
      min_strength: rule.min_strength,
      is_active: rule.is_active,
      priority: rule.priority,
      indicator_conditions: rule.indicator_conditions || {
        rsi: { enabled: false, min: null, max: null },
        macd: { enabled: false, signal: '' },
        bollinger: { enabled: false, signal: '' },
        obv: { enabled: false, signal: '' }
      }
    }
  } else {
    editingRule.value = null
    ruleForm.value = {
      name: '',
      description: '',
      min_traders: 2,
      window_minutes: 10,
      strict_consensus: true,
      ticker_filter: '',
      direction_filter: '',
      min_confidence: null,
      min_strength: null,
      is_active: true,
      priority: 0,
      indicator_conditions: {
        rsi: { enabled: false, min: null, max: null },
        macd: { enabled: false, signal: '' },
        bollinger: { enabled: false, signal: '' },
        obv: { enabled: false, signal: '' }
      }
    }
  }
  showRuleModal.value = true
}

function closeRuleModal() {
  showRuleModal.value = false
  editingRule.value = null
}

async function saveRule() {
  if (!ruleForm.value.name || !ruleForm.value.min_traders || !ruleForm.value.window_minutes) {
    return
  }

  ruleSaving.value = true

  try {
    const ruleData = { ...ruleForm.value }

    // Убираем пустые строки для фильтров
    if (!ruleData.ticker_filter) ruleData.ticker_filter = null
    if (!ruleData.direction_filter) ruleData.direction_filter = null
    if (!ruleData.description) ruleData.description = null

    if (editingRule.value) {
      await tradingAPI.updateConsensusRule(editingRule.value.id, ruleData)
    } else {
      await tradingAPI.createConsensusRule(ruleData)
    }

    await loadRules()
    closeRuleModal()
  } catch (err) {
    console.error('❌ Error saving rule:', err)
    alert(`Ошибка: ${err.message}`)
  } finally {
    ruleSaving.value = false
  }
}

async function toggleRule(rule) {
  try {
    await tradingAPI.updateConsensusRule(rule.id, {
      is_active: !rule.is_active
    })
    await loadRules()
  } catch (err) {
    console.error('❌ Error toggling rule:', err)
    alert(`Ошибка: ${err.message}`)
  }
}

async function deleteRule(rule) {
  if (!confirm(`Удалить правило "${rule.name}"?`)) {
    return
  }

  try {
    await tradingAPI.deleteConsensusRule(rule.id)
    await loadRules()
  } catch (err) {
    console.error('❌ Error deleting rule:', err)
    alert(`Ошибка: ${err.message}`)
  }
}

// ===== ИНИЦИАЛИЗАЦИЯ =====

onMounted(() => {
  loadConsensusEvents()
  loadStats()
  loadRules()
})
</script>
