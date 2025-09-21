// frontend/src/stores/tradingStore.js - ОБНОВЛЕННАЯ ВЕРСИЯ
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { tradingAPI } from '../services/api.js'

export const useTradingStore = defineStore('trading', () => {
  // ===== 🎯 ОСНОВНОЕ СОСТОЯНИЕ =====
  const selectedTicker = ref('SBER')
  const candlesData = ref([])
  const signalsData = ref([])
  const availableTickers = ref([])
  const currentPrice = ref(null)
  
  // ⚙️ Настройки временных рамок
  const chartDays = ref(30)
  const signalsDays = ref(365)
  const autoLoadEnabled = ref(true) // Включить умную авто-загрузку
  
  // 📄 Загрузочные состояния
  const isLoadingCandles = ref(false)
  const isLoadingSignals = ref(false)
  const isLoadingTickers = ref(false)
  const isAutoLoading = ref(false)
  
  // ❌ Ошибки
  const candlesError = ref(null)
  const signalsError = ref(null)
  const tickersError = ref(null)
  
  // 📊 Статус данных
  const dataCoverage = ref(null)
  const lastAutoLoadTime = ref(null)
  
  // ===== 💫 ВЫЧИСЛЯЕМЫЕ СВОЙСТВА =====
  
  const formattedCandles = computed(() => {
    return candlesData.value.map(candle => ({
      time: new Date(candle.time).getTime() / 1000,
      open: candle.open,
      high: candle.high,
      low: candle.low,
      close: candle.close,
      volume: candle.volume
    }))
  })
  
  const hasData = computed(() => candlesData.value.length > 0)
  
  const isLoading = computed(() => 
    isLoadingCandles.value || isLoadingSignals.value || isAutoLoading.value
  )
  
  const dataQuality = computed(() => {
    if (!dataCoverage.value) return null
    
    const coverage = dataCoverage.value.coverage
    if (coverage.coverage_percentage >= 90) return 'excellent'
    if (coverage.coverage_percentage >= 70) return 'good'
    if (coverage.coverage_percentage >= 50) return 'fair'
    return 'poor'
  })
  
  // ===== 📋 МЕТОДЫ ЗАГРУЗКИ ТИКЕРОВ =====
  
  async function loadTickers() {
    isLoadingTickers.value = true
    tickersError.value = null
    
    try {
      const response = await tradingAPI.getTickers()
      availableTickers.value = response.sort((a, b) => b.signal_count - a.signal_count)
      console.log('📊 Loaded tickers:', availableTickers.value.length)
    } catch (error) {
      tickersError.value = error.message
      console.error('❌ Error loading tickers:', error)
    } finally {
      isLoadingTickers.value = false
    }
  }
  
  // ===== 🕯️ МЕТОДЫ ЗАГРУЗКИ СВЕЧЕЙ =====
  
  async function loadCandles(ticker = selectedTicker.value, days = chartDays.value, forceLoad = false) {
    isLoadingCandles.value = true
    candlesError.value = null
    
    try {
      console.log(`📈 Loading candles for ${ticker} (${days} days)${forceLoad ? ' [FORCE]' : ''}...`)
      
      let response
      
      if (autoLoadEnabled.value || forceLoad) {
        // Используем умную загрузку с авто-загрузкой при необходимости
        response = await tradingAPI.getCandlesWithSmartLoad(ticker, days, forceLoad)
      } else {
        // Только чтение из БД
        response = await tradingAPI.getCandles(ticker, days)
      }
      
      if (response.candles && response.candles.length > 0) {
        candlesData.value = response.candles
        console.log(`✅ Loaded ${response.candles.length} candles for ${ticker}`)
        
        // Обновляем покрытие данных после загрузки
        if (autoLoadEnabled.value) {
          await checkDataCoverage(ticker)
        }
      } else {
        candlesData.value = []
        candlesError.value = `No candle data available for ${ticker}.`
      }
      
    } catch (error) {
      console.error('❌ Error loading candles:', error)
      candlesError.value = error.message
      candlesData.value = []
    } finally {
      isLoadingCandles.value = false
    }
  }
  
  // ===== 🎯 МЕТОДЫ ЗАГРУЗКИ СИГНАЛОВ =====
  
  async function loadSignals(ticker = selectedTicker.value, days = signalsDays.value) {
    isLoadingSignals.value = true
    signalsError.value = null
    
    try {
      console.log(`🎯 Loading signals for ${ticker} (${days} days)...`)
      
      const response = await tradingAPI.getSignalsByTicker(ticker, days)
      
      if (response.signals) {
        signalsData.value = response.signals
        console.log(`✅ Loaded ${response.signals.length} signals for ${ticker}`)
      } else {
        signalsData.value = []
      }
      
    } catch (error) {
      console.error('❌ Error loading signals:', error)
      signalsError.value = error.message
      signalsData.value = []
    } finally {
      isLoadingSignals.value = false
    }
  }
  
  // ===== 💰 ЗАГРУЗКА ТЕКУЩЕЙ ЦЕНЫ =====
  
  async function loadCurrentPrice(ticker = selectedTicker.value) {
    try {
      const priceData = await tradingAPI.getCurrentPrice(ticker)
      if (priceData) {
        currentPrice.value = priceData.price
        console.log(`💰 Current price for ${ticker}: ${priceData.price}`)
      }
    } catch (error) {
      console.warn('⚠️ Failed to load current price:', error.message)
    }
  }
  
  // ===== 📊 ПРОВЕРКА ПОКРЫТИЯ ДАННЫХ =====
  
  async function checkDataCoverage(ticker = selectedTicker.value) {
    try {
      // ✅ ИСПРАВЛЕНО: используем getDataCoverage вместо checkDataCoverage
      const coverage = await tradingAPI.getDataCoverage(ticker, Math.max(chartDays.value, signalsDays.value))
      dataCoverage.value = coverage
      return coverage
    } catch (error) {
      console.warn('⚠️ Failed to check data coverage:', error.message)
      return null
    }
  }
  
  // ===== 🔄 УПРАВЛЕНИЕ СОСТОЯНИЕМ =====
  
  async function setTicker(ticker) {
    const isActuallyChanging = ticker !== selectedTicker.value
    const hasNoData = candlesData.value.length === 0
    
    if (!isActuallyChanging && !hasNoData) return
    
    console.log(`🔄 ${isActuallyChanging ? 'Switching to' : 'Loading data for'} ticker: ${ticker}`)
    selectedTicker.value = ticker
    
    // Сбрасываем данные
    candlesData.value = []
    signalsData.value = []
    dataCoverage.value = null
    currentPrice.value = null
 
    if (isActuallyChanging) {
      candlesData.value = []
      signalsData.value = []
      dataCoverage.value = null
      currentPrice.value = null
    }

    await Promise.all([
        loadCandles(ticker, chartDays.value),
        loadSignals(ticker, signalsDays.value), 
        loadCurrentPrice(ticker)
      ])
  }
  
  async function setChartDays(days) {
    chartDays.value = days
    await loadCandles(selectedTicker.value, days)
  }
  
  async function setSignalsDays(days) {
    signalsDays.value = days
    await loadSignals(selectedTicker.value, days)
  }
  
  function setAutoLoadEnabled(enabled) {
    autoLoadEnabled.value = enabled
    console.log(`🔧 Auto-load ${enabled ? 'enabled' : 'disabled'}`)
    
    if (enabled) {
      checkDataCoverage()
    }
  }
  
  function clearErrors() {
    candlesError.value = null
    signalsError.value = null
    tickersError.value = null
  }
  
  // ===== 🛠️ УТИЛИТЫ ДЛЯ УПРАВЛЕНИЯ ДАННЫМИ =====
  
  /**
   * Принудительная перезагрузка всех данных
   */
  async function forceReloadData() {
    console.log('🔄 Force reloading all data...')
    clearErrors()
    
    await Promise.all([
      loadCandles(selectedTicker.value, chartDays.value, true), // force=true
      loadSignals(selectedTicker.value, signalsDays.value),
      loadCurrentPrice(selectedTicker.value)
    ])
  }
  
  /**
   * Явная загрузка данных для тикера
   */
  async function manualLoadData(ticker = selectedTicker.value, maxDays = 365) {
    isAutoLoading.value = true
    
    try {
      console.log(`🔄 Manual smart load for ${ticker}...`)
      
      const result = await tradingAPI.smartLoadData(ticker, maxDays, true)
      console.log('✅ Manual load completed:', result)
      
      // Обновляем свечи после загрузки
      await loadCandles(ticker, chartDays.value, false)
      
      lastAutoLoadTime.value = new Date()
      return result
    } catch (error) {
      console.error('❌ Manual load failed:', error)
      throw error
    } finally {
      isAutoLoading.value = false
    }
  }
  
  /**
   * Оптимизация временных рамок на основе доступных данных
   */
  async function optimizeTimeframes() {
    const coverage = await checkDataCoverage()
    if (!coverage) return
    
    const availableDays = coverage.coverage.period_days
    
    // Автоматически подстраиваем временные рамки под доступные данные
    if (chartDays.value > availableDays) {
      console.log(`📅 Optimizing chart days from ${chartDays.value} to ${availableDays}`)
      chartDays.value = Math.min(availableDays, 90)
      await loadCandles()
    }
  }
  
  /**
   * Массовая загрузка недостающих данных
   */
  async function bulkLoadMissingData() {
    isAutoLoading.value = true
    
    try {
      console.log('🚀 Starting bulk smart load...')
      const result = await tradingAPI.bulkSmartLoad()
      console.log('✅ Bulk load completed:', result)
      
      // Обновляем данные для текущего тикера
      await forceReloadData()
      
      lastAutoLoadTime.value = new Date()
      return result
    } catch (error) {
      console.error('❌ Bulk load failed:', error)
      throw error
    } finally {
      isAutoLoading.value = false
    }
  }
  
  
async function initialize() {
  console.log('🚀 Initializing Trading Store...')
  
  try {
    await loadTickers()
    
    const currentTicker = selectedTicker.value || 'SBER'
    console.log('🎯 Initializing with ticker:', currentTicker)
    
    await setTicker(currentTicker)
  } catch (error) {
    console.error('⌐ Initialization error:', error)
  }
}
  
  // ===== 📤 ЭКСПОРТ =====
  
  return {
    // 🎯 Основное состояние
    selectedTicker,
    candlesData,
    signalsData,
    availableTickers,
    currentPrice,
    chartDays,
    signalsDays,
    autoLoadEnabled,
    dataCoverage,
    lastAutoLoadTime,
    
    // 📄 Загрузочные состояния
    isLoadingCandles,
    isLoadingSignals,
    isLoadingTickers,
    isAutoLoading,
    
    // ❌ Ошибки
    candlesError,
    signalsError,
    tickersError,
    
    // 💫 Вычисляемые свойства
    formattedCandles,
    hasData,
    isLoading,
    dataQuality,
    
    // 📋 Основные действия
    loadTickers,
    loadCandles,
    loadSignals,
    loadCurrentPrice,
    setTicker,
    setChartDays,
    setSignalsDays,
    setAutoLoadEnabled,
    clearErrors,
    
    // 🛠️ Управление данными
    checkDataCoverage,
    forceReloadData,
    manualLoadData,
    optimizeTimeframes,
    bulkLoadMissingData,
    
    // 🚀 Инициализация
    initialize
  }
})