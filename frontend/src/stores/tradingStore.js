// frontend/src/stores/tradingStore.js - ИСПРАВЛЕННАЯ ВЕРСИЯ
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
  
  // ⚙️ Настройки временных рамок - УВЕЛИЧЕННЫЕ ДЕФОЛТЫ
  const chartDays = ref(30)
  const signalsDays = ref(30)
  const autoLoadEnabled = ref(true)
  
  // 🔄 Загрузочные состояния
  const isLoadingCandles = ref(false)
  const isLoadingSignals = ref(false)
  const isLoadingTickers = ref(false)
  const isAutoLoading = ref(false)
  
  // ❌ Ошибки
  const candlesError = ref(null)
  const signalsError = ref(null)
  const tickersError = ref(null)
  
  // 📊 Опции периодов для UI - РАСШИРЕННЫЕ
  const chartPeriodOptions = ref([
    { value: 7, label: '7 дней', description: 'Неделя' },
    { value: 30, label: '30 дней', description: 'Месяц' },
    { value: 90, label: '90 дней', description: 'Квартал' },
    { value: 180, label: '180 дней', description: 'Полгода' },
    { value: 365, label: '365 дней', description: 'Год' },
  ])
  
  // ===== 📈 COMPUTED ГЕТТЕРЫ =====
  
  const isLoading = computed(() => 
    isLoadingCandles.value || isLoadingSignals.value || isLoadingTickers.value || isAutoLoading.value
  )
  
  const formattedCandles = computed(() => {
    if (!candlesData.value || !Array.isArray(candlesData.value)) {
      return []
    }
    
    console.log('📊 Store: Formatting candles, sample data:', candlesData.value.slice(0, 2))
    
    return candlesData.value.map(candle => {
      // Обрабатываем разные возможные форматы времени из API
      let timeValue
      
      if (candle.time !== undefined) {
        timeValue = candle.time
      } else if (candle.timestamp !== undefined) {
        timeValue = candle.timestamp  
      } else if (candle.datetime !== undefined) {
        timeValue = candle.datetime
      } else if (candle.date !== undefined) {
        timeValue = candle.date
      } else {
        console.warn('⚠️ No time field found in candle from API:', Object.keys(candle))
        timeValue = Date.now() / 1000 // fallback
      }
      
      // Конвертируем в Unix timestamp если это строка
      if (typeof timeValue === 'string') {
        timeValue = Math.floor(new Date(timeValue).getTime() / 1000)
      }
      
      const formatted = {
        time: timeValue,
        open: parseFloat(candle.open || candle.o || 0),
        high: parseFloat(candle.high || candle.h || 0),
        low: parseFloat(candle.low || candle.l || 0),
        close: parseFloat(candle.close || candle.c || 0),
        volume: candle.volume || candle.v || 0
      }
      
      // Валидация данных
      const isValid = formatted.open > 0 && formatted.high > 0 && 
                     formatted.low > 0 && formatted.close > 0 && 
                     !isNaN(formatted.time)
      
      if (!isValid) {
        console.warn('⚠️ Invalid candle data:', { original: candle, formatted })
      }
      
      return formatted
    }).filter(candle => 
      // Оставляем только валидные свечи
      candle.open > 0 && candle.high > 0 && candle.low > 0 && candle.close > 0 && !isNaN(candle.time)
    ).sort((a, b) => a.time - b.time) // Сортируем по времени
  })
  
  const currentPeriodInfo = computed(() => {
    const option = chartPeriodOptions.value.find(opt => opt.value === chartDays.value)
    return option || { value: chartDays.value, label: `${chartDays.value} дней`, description: 'Кастомный' }
  })
  
  // ===== 🔧 ОСНОВНЫЕ ДЕЙСТВИЯ =====
  
  /**
   * Загрузка свечных данных
   */
  async function loadCandles(ticker = selectedTicker.value, days = chartDays.value, force = false) {
    if (isLoadingCandles.value && !force) {
      console.log('⏳ Candles already loading, skipping...')
      return
    }
    
    isLoadingCandles.value = true
    candlesError.value = null
    
    try {
      console.log(`📊 Loading candles: ${ticker}, ${days} days`)
      
      const response = await tradingAPI.getCandles(ticker, days)
      
      console.log('🔍 RAW Candles API Response:', response) // DEBUG
      
      if (response && response.candles) {
        console.log(`📊 API returned ${response.candles.length} candles`)
        
        // DEBUG: анализируем структуру первой свечи
        if (response.candles.length > 0) {
          const firstCandle = response.candles[0]
          console.log('🔍 First candle structure:', {
            candle: firstCandle,
            keys: Object.keys(firstCandle),
            timeField: firstCandle.time || firstCandle.timestamp || firstCandle.datetime || 'NO_TIME',
            timeType: typeof (firstCandle.time || firstCandle.timestamp || firstCandle.datetime)
          })
          
          // Проверяем наличие обязательных полей
          const requiredFields = ['open', 'high', 'low', 'close']
          const missingFields = requiredFields.filter(field => 
            firstCandle[field] === undefined && firstCandle[field.charAt(0)] === undefined
          )
          
          if (missingFields.length > 0) {
            console.warn('⚠️ Missing required fields:', missingFields)
          }
        }
        
        candlesData.value = response.candles
        
        // Обновляем текущую цену из последней свечи
        if (response.candles.length > 0) {
          const sortedCandles = [...response.candles].sort((a, b) => {
            const timeA = a.time || a.timestamp || a.datetime
            const timeB = b.time || b.timestamp || b.datetime
            
            if (typeof timeA === 'string' && typeof timeB === 'string') {
              return new Date(timeA).getTime() - new Date(timeB).getTime()
            }
            return timeA - timeB
          })
          
          const lastCandle = sortedCandles[sortedCandles.length - 1]
          currentPrice.value = lastCandle.close || lastCandle.c
          
          console.log(`💰 Updated current price: ${currentPrice.value}`)
        }
        
        console.log(`✅ Loaded ${response.candles.length} candles for ${ticker}`)
      } else {
        console.warn('⚠️ No candles data in response:', response)
        throw new Error('No candles data in response')
      }
      
    } catch (error) {
      console.error('❌ Error loading candles:', error)
      console.error('❌ Error details:', error.response?.data)
      candlesError.value = error.message || 'Ошибка загрузки свечных данных'
      candlesData.value = []
    } finally {
      isLoadingCandles.value = false
    }
  }
  
  /**
   * Загрузка сигналов
   */
  async function loadSignals(ticker = selectedTicker.value, days = signalsDays.value, force = false) {
    if (isLoadingSignals.value && !force) {
      console.log('⏳ Signals already loading, skipping...')
      return
    }
    
    isLoadingSignals.value = true
    signalsError.value = null
    
    try {
      console.log(`🎯 Loading signals: ${ticker}, ${days} days`)
      
      const response = await tradingAPI.getSignalsByTicker(ticker, days)
      
      console.log('🔍 RAW API Response:', response) // DEBUG: смотрим что приходит с API
      
      if (response && Array.isArray(response.signals)) {
        signalsData.value = response.signals
        console.log(`✅ Loaded ${response.signals.length} signals for ${ticker}`)
        
        // DEBUG: детальный анализ первых сигналов
        if (response.signals.length > 0) {
          console.log('🔍 DETAILED signals analysis:')
          response.signals.slice(0, 3).forEach((signal, index) => {
            console.log(`Signal ${index + 1}:`, {
              id: signal.id,
              direction: signal.direction,
              author: signal.author,
              trader: signal.trader, // проверяем разные поля
              timestamp: signal.timestamp,
              ticker: signal.ticker,
              ALL_FIELDS: Object.keys(signal), // смотрим все доступные поля
              FULL_SIGNAL: signal // полный объект сигнала
            })
          })
        }
      } else if (response && Array.isArray(response)) {
        // Иногда API возвращает массив напрямую
        signalsData.value = response
        console.log(`✅ Loaded ${response.length} signals directly`)
        
        // DEBUG: анализ прямого массива
        if (response.length > 0) {
          console.log('🔍 DIRECT array signals analysis:')
          response.slice(0, 3).forEach((signal, index) => {
            console.log(`Direct Signal ${index + 1}:`, {
              author: signal.author,
              trader: signal.trader,
              ALL_FIELDS: Object.keys(signal),
              FULL_SIGNAL: signal
            })
          })
        }
      } else {
        signalsData.value = []
        console.log('ℹ️ No signals found for', ticker)
        console.log('🔍 Response structure:', response) // DEBUG: структура ответа
      }
      
    } catch (error) {
      console.error('❌ Error loading signals:', error)
      console.error('❌ Error details:', error.response?.data) // DEBUG: детали ошибки
      signalsError.value = error.message || 'Ошибка загрузки сигналов'
      signalsData.value = []
    } finally {
      isLoadingSignals.value = false
    }
  }
  
  /**
   * Загрузка доступных тикеров
   */
  async function loadTickers() {
    if (isLoadingTickers.value) return
    
    isLoadingTickers.value = true
    tickersError.value = null
    
    try {
      console.log('📋 Loading available tickers...')
      
      const response = await tradingAPI.getAvailableTickers()
      
      if (Array.isArray(response)) {
        availableTickers.value = response
        console.log(`✅ Loaded ${response.length} tickers`)
      } else {
        availableTickers.value = []
        console.log('⚠️ No tickers received')
      }
      
    } catch (error) {
      console.error('❌ Error loading tickers:', error)
      tickersError.value = error.message || 'Ошибка загрузки списка тикеров'
      availableTickers.value = []
    } finally {
      isLoadingTickers.value = false
    }
  }
  
  /**
   * Загрузка всех данных для тикера
   */
  async function loadAllData(ticker = selectedTicker.value, force = false) {
    if (isAutoLoading.value && !force) return
    
    isAutoLoading.value = true
    
    try {
      console.log(`🚀 Loading all data for ${ticker}`)
      
      // Загружаем параллельно свечи и сигналы
      await Promise.allSettled([
        loadCandles(ticker, chartDays.value, force),
        loadSignals(ticker, signalsDays.value, force)
      ])
      
      console.log(`✅ All data loaded for ${ticker}`)
      
    } finally {
      isAutoLoading.value = false
    }
  }
  
  // ===== 🎛️ УПРАВЛЕНИЕ ПЕРИОДАМИ - НОВЫЕ МЕТОДЫ =====
  
  /**
   * Установить количество дней для графика
   */
  function setChartDays(days) {
    console.log(`📅 Setting chart days: ${days}`)
    chartDays.value = days
    // Автоматически загружаем данные если включена автозагрузка
    if (autoLoadEnabled.value) {
      loadAllData(selectedTicker.value, true)
    }
  }

  /**
   * Установить количество дней для сигналов  
   */
  function setSignalsDays(days) {
    console.log(`🎯 Setting signals days: ${days}`)
    signalsDays.value = days
    if (autoLoadEnabled.value) {
      loadSignals(selectedTicker.value, days, true)
    }
  }

  /**
   * Установить автозагрузку
   */
  function setAutoLoadEnabled(enabled) {
    console.log(`⚙️ Setting auto load: ${enabled}`)
    autoLoadEnabled.value = enabled
  }
  
  /**
   * Установить стандартный вид (180 дней)
   */
  function setStandardView() {
    console.log('📅 Setting standard view (180 days)')
    chartDays.value = 180
    signalsDays.value = 180
    loadAllData(selectedTicker.value, true)
  }
  
  /**
   * Установить годовой вид (365 дней)
   */
  function setYearView() {
    console.log('📅 Setting year view (365 days)')
    chartDays.value = 365
    signalsDays.value = 365
    loadAllData(selectedTicker.value, true)
  }
  
  /**
   * Установить кастомный период
   */
  function setCustomPeriod(days) {
    console.log(`📅 Setting custom period: ${days} days`)
    chartDays.value = days
    signalsDays.value = days
    loadAllData(selectedTicker.value, true)
  }
  
  // ===== 🧹 ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ =====
  
  function clearErrors() {
    candlesError.value = null
    signalsError.value = null
    tickersError.value = null
  }
  
  function clearData() {
    candlesData.value = []
    signalsData.value = []
    currentPrice.value = null
    clearErrors()
  }
  
  /**
   * Смена активного тикера
   */
  async function setSelectedTicker(ticker) {
    if (selectedTicker.value === ticker) return
    
    console.log(`🔄 Changing ticker: ${selectedTicker.value} -> ${ticker}`)
    
    selectedTicker.value = ticker
    clearData()
    
    if (autoLoadEnabled.value) {
      await loadAllData(ticker)
    }
  }

  /**
   * Алиас для setSelectedTicker для обратной совместимости
   */
  async function setTicker(ticker) {
    console.log(`🔄 setTicker called (alias for setSelectedTicker): ${ticker}`)
    return await setSelectedTicker(ticker)
  }
  
  /**
   * Принудительное обновление данных
   */
  async function refreshData() {
    console.log('🔄 Force refreshing data...')
    clearErrors()
    await loadAllData(selectedTicker.value, true)
  }
  
  // ===== 🛠️ ДОПОЛНИТЕЛЬНЫЕ МЕТОДЫ ДИАГНОСТИКИ =====
  
  /**
   * Проверка покрытия данных
   */
  async function checkDataCoverage(ticker = selectedTicker.value) {
    try {
      const response = await tradingAPI.checkDataCoverage(ticker, chartDays.value)
      console.log('📊 Data coverage check:', response)
      return response
    } catch (error) {
      console.error('❌ Error checking data coverage:', error)
      return null
    }
  }
  
  /**
   * Принудительная перезагрузка данных
   */
  async function forceReloadData(ticker = selectedTicker.value) {
    try {
      console.log(`🔄 Force reloading data for ${ticker}...`)
      
      // Пытаемся использовать API для принудительной загрузки
      const response = await tradingAPI.smartLoadData(ticker)
      console.log('🔄 Force reload API response:', response)
      
      // После успешной загрузки обновляем данные
      await refreshData()
      return response
    } catch (error) {
      console.error('❌ Force reload API failed, falling back to regular refresh:', error)
      
      // Если API не работает, делаем обычное обновление
      await refreshData()
      return { success: false, fallback: true, error: error.message }
    }
  }
  
  /**
   * Ручная загрузка данных
   */
  async function manualLoadData(ticker, days = 180) {
    try {
      const response = await tradingAPI.manualLoadData(ticker, days)
      console.log('📥 Manual load response:', response)
      await refreshData()
      return response
    } catch (error) {
      console.error('❌ Error manual loading data:', error)
      return null
    }
  }
  
  /**
   * Оптимизация временных рамок
   */
  function optimizeTimeframes() {
    // Если сигналов мало, уменьшаем период
    if (signalsData.value.length < 5 && signalsDays.value > 30) {
      console.log('📉 Few signals, optimizing timeframe')
      setCustomPeriod(Math.max(30, signalsDays.value / 2))
    }
  }
  
  /**
   * Массовая загрузка недостающих данных
   */
  async function bulkLoadMissingData() {
    try {
      const response = await tradingAPI.bulkLoadMissingData()
      console.log('📦 Bulk load response:', response)
      return response
    } catch (error) {
      console.error('❌ Error bulk loading data:', error)
      return null
    }
  }
  
  // ===== 🚀 ИНИЦИАЛИЗАЦИЯ =====
  
  /**
   * Инициализация store
   */
  async function initialize() {
    console.log('🚀 Initializing trading store...')
    
    try {
      // Загружаем список тикеров
      await loadTickers()
      
      // Загружаем данные для дефолтного тикера
      if (autoLoadEnabled.value) {
        await loadAllData()
      }
      
      console.log('✅ Trading store initialized')
    } catch (error) {
      console.error('❌ Error initializing trading store:', error)
    }
  }
  
  // ===== 📤 ЭКСПОРТ =====
  
  return {
    // 📊 Состояние
    selectedTicker,
    candlesData,
    signalsData,
    availableTickers,
    currentPrice,
    
    // ⚙️ Настройки
    chartDays,
    signalsDays,
    autoLoadEnabled,
    chartPeriodOptions,
    
    // 🔄 Загрузочные состояния
    isLoading,
    isLoadingCandles,
    isLoadingSignals,
    isLoadingTickers,
    isAutoLoading,
    
    // ❌ Ошибки
    candlesError,
    signalsError,
    tickersError,
    
    // 📈 Computed
    formattedCandles,
    currentPeriodInfo,
    
    // 🔧 Основные действия
    loadCandles,
    loadSignals,
    loadTickers,
    loadAllData,
    setSelectedTicker,
    setTicker, // ✅ ДОБАВЛЕНО: алиас для совместимости
    refreshData,
    
    // 🧹 Вспомогательные
    clearErrors,
    clearData,
    
    // 🎛️ Управление периодами и настройками
    setChartDays,
    setSignalsDays, 
    setAutoLoadEnabled,
    setStandardView,
    setYearView,
    setCustomPeriod,
    
    // 🛠️ Диагностика и управление данными
    checkDataCoverage,
    forceReloadData,
    manualLoadData,
    optimizeTimeframes,
    bulkLoadMissingData,
    
    // 🚀 Инициализация
    initialize
  }
})