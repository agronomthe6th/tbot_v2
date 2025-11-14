<template>
  <div class="consensus-backtest">
    <!-- Форма запуска бэктеста -->
    <div class="bg-trading-card p-6 rounded-lg border border-trading-border mb-6">
      <h3 class="text-xl font-bold mb-4">🧪 Запустить бэктест</h3>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
        <!-- Выбор правила -->
        <div>
          <label class="block text-sm text-gray-400 mb-2">Правило консенсуса *</label>
          <select
            v-model="backtestForm.rule_id"
            class="w-full bg-trading-bg border border-trading-border rounded px-3 py-2 text-white"
            required
          >
            <option value="">Выберите правило</option>
            <option v-for="rule in rules" :key="rule.id" :value="rule.id">
              {{ rule.name }}
            </option>
          </select>
        </div>

        <!-- Тикеры -->
        <div>
          <label class="block text-sm text-gray-400 mb-2">Тикеры (через запятую)</label>
          <input
            v-model="backtestForm.tickers_str"
            type="text"
            placeholder="SBER,GAZP,LKOH или оставьте пустым для всех"
            class="w-full bg-trading-bg border border-trading-border rounded px-3 py-2 text-white"
          />
        </div>

        <!-- Период -->
        <div>
          <label class="block text-sm text-gray-400 mb-2">Начало периода *</label>
          <input
            v-model="backtestForm.start_date"
            type="date"
            class="w-full bg-trading-bg border border-trading-border rounded px-3 py-2 text-white"
            required
          />
        </div>

        <div>
          <label class="block text-sm text-gray-400 mb-2">Конец периода *</label>
          <input
            v-model="backtestForm.end_date"
            type="date"
            class="w-full bg-trading-bg border border-trading-border rounded px-3 py-2 text-white"
            required
          />
        </div>

        <!-- Параметры торговли -->
        <div>
          <label class="block text-sm text-gray-400 mb-2">Take Profit (%)</label>
          <input
            v-model.number="backtestForm.take_profit_pct"
            type="number"
            step="0.1"
            min="0"
            class="w-full bg-trading-bg border border-trading-border rounded px-3 py-2 text-white"
          />
        </div>

        <div>
          <label class="block text-sm text-gray-400 mb-2">Stop Loss (%)</label>
          <input
            v-model.number="backtestForm.stop_loss_pct"
            type="number"
            step="0.1"
            min="0"
            class="w-full bg-trading-bg border border-trading-border rounded px-3 py-2 text-white"
          />
        </div>

        <div>
          <label class="block text-sm text-gray-400 mb-2">Время удержания (часы)</label>
          <input
            v-model.number="backtestForm.holding_hours"
            type="number"
            min="1"
            class="w-full bg-trading-bg border border-trading-border rounded px-3 py-2 text-white"
          />
        </div>

        <!-- Параметры капитала -->
        <div>
          <label class="block text-sm text-gray-400 mb-2">Начальный капитал (₽)</label>
          <input
            v-model.number="backtestForm.initial_capital"
            type="number"
            min="1000"
            step="1000"
            class="w-full bg-trading-bg border border-trading-border rounded px-3 py-2 text-white"
          />
        </div>

        <div>
          <label class="block text-sm text-gray-400 mb-2">Размер позиции (% от капитала)</label>
          <input
            v-model.number="backtestForm.position_size_pct"
            type="number"
            min="1"
            max="100"
            step="1"
            class="w-full bg-trading-bg border border-trading-border rounded px-3 py-2 text-white"
          />
        </div>
      </div>

      <div class="flex gap-2">
        <button
          @click="runBacktest"
          :disabled="isRunning || !backtestForm.rule_id"
          class="px-6 py-3 bg-trading-green text-black rounded-lg hover:bg-green-500 transition-colors disabled:opacity-50"
        >
          {{ isRunning ? '⏳ Выполняется...' : '🚀 Запустить бэктест' }}
        </button>
      </div>
    </div>

    <!-- Результаты бэктеста -->
    <div v-if="currentResult" class="bg-trading-card p-6 rounded-lg border border-trading-border mb-6">
      <h3 class="text-xl font-bold mb-4">📊 Результаты бэктеста</h3>

      <!-- Статистика -->
      <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <div class="bg-trading-bg p-4 rounded border border-trading-border">
          <div class="text-gray-400 text-sm mb-1">Найдено консенсусов</div>
          <div class="text-2xl font-bold">{{ currentResult.stats.total_consensus_found || 0 }}</div>
        </div>

        <div class="bg-trading-bg p-4 rounded border border-trading-border">
          <div class="text-gray-400 text-sm mb-1">Win Rate</div>
          <div class="text-2xl font-bold text-trading-green">
            {{ currentResult.stats.win_rate?.toFixed(1) || 0 }}%
          </div>
        </div>

        <div class="bg-trading-bg p-4 rounded border border-trading-border">
          <div class="text-gray-400 text-sm mb-1">Доходность</div>
          <div
            class="text-2xl font-bold"
            :class="currentResult.stats.total_return_pct >= 0 ? 'text-trading-green' : 'text-trading-red'"
          >
            {{ currentResult.stats.total_return_pct?.toFixed(2) || 0 }}%
          </div>
          <div v-if="currentResult.stats.total_profit_abs" class="text-sm text-gray-400 mt-1">
            {{ currentResult.stats.total_profit_abs?.toFixed(0) }} ₽
          </div>
        </div>

        <div class="bg-trading-bg p-4 rounded border border-trading-border">
          <div class="text-gray-400 text-sm mb-1">Прибыльных / Убыточных</div>
          <div class="text-2xl font-bold">
            {{ currentResult.stats.profitable_count || 0 }} / {{ currentResult.stats.loss_count || 0 }}
          </div>
        </div>

        <div class="bg-trading-bg p-4 rounded border border-trading-border">
          <div class="text-gray-400 text-sm mb-1">Средняя прибыль</div>
          <div class="text-lg font-bold text-trading-green">
            {{ currentResult.stats.avg_profit_pct?.toFixed(2) || 0 }}%
          </div>
        </div>

        <div class="bg-trading-bg p-4 rounded border border-trading-border">
          <div class="text-gray-400 text-sm mb-1">Средний убыток</div>
          <div class="text-lg font-bold text-trading-red">
            {{ currentResult.stats.avg_loss_pct?.toFixed(2) || 0 }}%
          </div>
        </div>

        <div class="bg-trading-bg p-4 rounded border border-trading-border">
          <div class="text-gray-400 text-sm mb-1">Макс. прибыль</div>
          <div class="text-lg font-bold text-trading-green">
            {{ currentResult.stats.max_profit_pct?.toFixed(2) || 0 }}%
          </div>
        </div>

        <div class="bg-trading-bg p-4 rounded border border-trading-border">
          <div class="text-gray-400 text-sm mb-1">Макс. убыток</div>
          <div class="text-lg font-bold text-trading-red">
            {{ currentResult.stats.max_loss_pct?.toFixed(2) || 0 }}%
          </div>
        </div>
      </div>

      <!-- По тикерам -->
      <div v-if="currentResult.stats.by_ticker && Object.keys(currentResult.stats.by_ticker).length > 0" class="mb-6">
        <h4 class="text-lg font-semibold mb-3">📈 По тикерам</h4>
        <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
          <div
            v-for="(data, ticker) in currentResult.stats.by_ticker"
            :key="ticker"
            class="bg-trading-bg p-3 rounded border border-trading-border"
          >
            <div class="font-bold mb-1">{{ ticker }}</div>
            <div class="text-sm text-gray-400">
              Сделок: {{ data.count }} ({{ data.profitable }} прибыльных)
            </div>
            <div
              class="text-sm font-semibold"
              :class="data.total_pnl >= 0 ? 'text-trading-green' : 'text-trading-red'"
            >
              P&L: {{ data.total_pnl?.toFixed(2) }}%
            </div>
          </div>
        </div>
      </div>

      <!-- Детали сделок -->
      <div v-if="currentResult.results && currentResult.results.length > 0">
        <h4 class="text-lg font-semibold mb-3">📋 Детали сделок ({{ currentResult.results.length }})</h4>
        <div class="overflow-auto max-h-96">
          <table class="w-full text-sm">
            <thead class="bg-trading-bg sticky top-0">
              <tr>
                <th class="px-3 py-2 text-left">Тикер</th>
                <th class="px-3 py-2 text-left">Направление</th>
                <th class="px-3 py-2 text-left">Вход</th>
                <th class="px-3 py-2 text-left">Выход</th>
                <th class="px-3 py-2 text-right">P&L %</th>
                <th class="px-3 py-2 text-right">P&L ₽</th>
                <th class="px-3 py-2 text-left">Причина выхода</th>
                <th class="px-3 py-2 text-center">Трейдеров</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="(result, idx) in currentResult.results"
                :key="idx"
                class="border-t border-trading-border hover:bg-trading-bg/50"
              >
                <td class="px-3 py-2 font-semibold">{{ result.ticker }}</td>
                <td class="px-3 py-2">
                  <span
                    :class="result.direction === 'long' ? 'text-trading-green' : 'text-trading-red'"
                  >
                    {{ result.direction.toUpperCase() }}
                  </span>
                </td>
                <td class="px-3 py-2">{{ result.entry_price?.toFixed(2) }}</td>
                <td class="px-3 py-2">{{ result.exit_price?.toFixed(2) }}</td>
                <td
                  class="px-3 py-2 text-right font-semibold"
                  :class="result.pnl_pct >= 0 ? 'text-trading-green' : 'text-trading-red'"
                >
                  {{ result.pnl_pct >= 0 ? '+' : '' }}{{ result.pnl_pct?.toFixed(2) }}%
                </td>
                <td
                  class="px-3 py-2 text-right font-semibold"
                  :class="result.profit_abs >= 0 ? 'text-trading-green' : 'text-trading-red'"
                >
                  {{ result.profit_abs >= 0 ? '+' : '' }}{{ result.profit_abs?.toFixed(0) }}
                </td>
                <td class="px-3 py-2">
                  <span
                    class="px-2 py-1 rounded text-xs"
                    :class="{
                      'bg-green-900 text-green-300': result.exit_reason === 'take_profit',
                      'bg-red-900 text-red-300': result.exit_reason === 'stop_loss',
                      'bg-gray-700 text-gray-300': result.exit_reason === 'timeout'
                    }"
                  >
                    {{ result.exit_reason }}
                  </span>
                </td>
                <td class="px-3 py-2 text-center">{{ result.traders_count }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- История бэктестов -->
    <div v-if="selectedRuleId" class="bg-trading-card p-6 rounded-lg border border-trading-border">
      <h3 class="text-xl font-bold mb-4">📜 История бэктестов</h3>
      <div v-if="backtestHistory.length === 0" class="text-gray-400 text-center py-4">
        Нет сохраненных бэктестов
      </div>
      <div v-else class="space-y-3">
        <div
          v-for="bt in backtestHistory"
          :key="bt.id"
          @click="loadBacktestResult(bt.id)"
          class="bg-trading-bg p-4 rounded border border-trading-border hover:border-trading-green cursor-pointer transition-colors"
        >
          <div class="flex items-center justify-between mb-2">
            <div class="font-semibold">
              {{ new Date(bt.start_date).toLocaleDateString() }} - {{ new Date(bt.end_date).toLocaleDateString() }}
            </div>
            <div
              class="text-sm font-semibold"
              :class="bt.win_rate >= 50 ? 'text-trading-green' : 'text-trading-red'"
            >
              Win Rate: {{ bt.win_rate?.toFixed(1) }}%
            </div>
          </div>
          <div class="text-sm text-gray-400">
            Консенсусов: {{ bt.total_consensus_found }} |
            Доходность: <span :class="bt.total_return_pct >= 0 ? 'text-trading-green' : 'text-trading-red'">
              {{ bt.total_return_pct?.toFixed(2) }}%
            </span>
          </div>
        </div>
      </div>
    </div>

    <!-- Ошибки -->
    <div v-if="error" class="bg-red-900/20 border border-red-900 text-red-400 p-4 rounded-lg mb-4">
      {{ error }}
    </div>
  </div>
</template>

<script>
import axios from 'axios'

export default {
  name: 'ConsensusBacktest',
  props: {
    rules: {
      type: Array,
      default: () => []
    }
  },
  data() {
    return {
      backtestForm: {
        rule_id: '',
        start_date: this.getDefaultStartDate(),
        end_date: this.getDefaultEndDate(),
        tickers_str: '',
        take_profit_pct: 5.0,
        stop_loss_pct: 3.0,
        holding_hours: 24,
        initial_capital: 100000.0,
        position_size_pct: 10.0
      },
      isRunning: false,
      currentResult: null,
      backtestHistory: [],
      selectedRuleId: null,
      error: null
    }
  },
  watch: {
    'backtestForm.rule_id'(newRuleId) {
      if (newRuleId) {
        this.selectedRuleId = newRuleId
        this.loadBacktestHistory(newRuleId)
      }
    }
  },
  methods: {
    getDefaultStartDate() {
      const date = new Date()
      date.setDate(date.getDate() - 30)
      return date.toISOString().split('T')[0]
    },
    getDefaultEndDate() {
      return new Date().toISOString().split('T')[0]
    },
    async runBacktest() {
      if (!this.backtestForm.rule_id) {
        this.error = 'Выберите правило консенсуса'
        return
      }

      this.isRunning = true
      this.error = null

      try {
        const payload = {
          rule_id: this.backtestForm.rule_id,
          start_date: new Date(this.backtestForm.start_date).toISOString(),
          end_date: new Date(this.backtestForm.end_date).toISOString(),
          take_profit_pct: this.backtestForm.take_profit_pct,
          stop_loss_pct: this.backtestForm.stop_loss_pct,
          holding_hours: this.backtestForm.holding_hours,
          initial_capital: this.backtestForm.initial_capital,
          position_size_pct: this.backtestForm.position_size_pct
        }

        if (this.backtestForm.tickers_str.trim()) {
          payload.tickers = this.backtestForm.tickers_str.split(',').map(t => t.trim().toUpperCase())
        }

        const response = await axios.post('/api/consensus/backtest', payload)
        this.currentResult = response.data
        await this.loadBacktestHistory(this.backtestForm.rule_id)
      } catch (err) {
        console.error('Backtest error:', err)
        this.error = err.response?.data?.detail || 'Ошибка при выполнении бэктеста'
      } finally {
        this.isRunning = false
      }
    },
    async loadBacktestResult(backtestId) {
      try {
        const response = await axios.get(`/api/consensus/backtest/${backtestId}`)
        this.currentResult = response.data
      } catch (err) {
        console.error('Error loading backtest:', err)
        this.error = 'Ошибка при загрузке результатов'
      }
    },
    async loadBacktestHistory(ruleId) {
      try {
        const response = await axios.get(`/api/consensus/backtest/rule/${ruleId}`)
        this.backtestHistory = response.data.backtests || []
      } catch (err) {
        console.error('Error loading backtest history:', err)
      }
    }
  }
}
</script>

<style scoped>
/* Используем существующие tailwind классы */
</style>
