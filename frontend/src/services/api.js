// frontend/src/services/api.js - ПОЛНОСТЬЮ ОБНОВЛЕННАЯ ВЕРСИЯ
import axios from 'axios'

// Базовая конфигурация API
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  }
})

// Интерцептор для обработки ошибок
api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', {
      url: error.config?.url,
      method: error.config?.method,
      status: error.response?.status,
      data: error.response?.data
    })
    return Promise.reject(error)
  }
)

export const tradingAPI = {
  // ===== 📊 СВЕЧИ И РЫНОЧНЫЕ ДАННЫЕ =====
  
  /**
   * Получение свечных данных - ТОЛЬКО ЧТЕНИЕ, без авто-загрузки
   * @param {string} ticker - Тикер инструмента
   * @param {number} days - Количество дней
   */
  async getCandles(ticker, days = 30) {
    try {
      const response = await api.get(`/api/candles/${ticker}`, {
        params: { days } // ✅ Убрали limit
      })
      return response.data
    } catch (error) {
      if (error.response?.status === 404) {
        throw new Error(`No candle data available for ${ticker}. Use smart load to load historical data first.`)
      }
      throw new Error(`Failed to get candles for ${ticker}: ${error.response?.data?.detail || error.message}`)
    }
  },

  /**
   * Получение текущей цены инструмента
   * @param {string} ticker - Тикер инструмента
   */
  async getCurrentPrice(ticker) {
    try {
      const response = await api.get(`/api/market/${ticker}/price`)
      return response.data
    } catch (error) {
      // Не критичная ошибка - можем работать без текущей цены
      console.warn(`Failed to get current price for ${ticker}:`, error.message)
      return null
    }
  },

  // ===== 🎯 СИГНАЛЫ =====
  
  /**
   * Получение сигналов по тикеру
   * @param {string} ticker - Тикер инструмента
   * @param {number} days - Количество дней
   * @param {number} limit - Максимальное количество сигналов
   */
  async getSignalsByTicker(ticker, days = 365, limit = 100) {
    try {
      const response = await api.get(`/api/signals/ticker/${ticker}`, {
        params: { days, limit }
      })
      return response.data
    } catch (error) {
      throw new Error(`Failed to get signals for ${ticker}: ${error.response?.data?.detail || error.message}`)
    }
  },

  async getTraders() {
    try {
      const response = await api.get('/api/traders');
      return response.data;  // Возвращаем массив трейдеров
    } catch (error) {
      console.error('Error fetching traders:', error);
      throw error;  // Чтобы ошибка обрабатывалась в компоненте
    }
  },

  async getTraderStats(traderId) {
    try {
      const response = await api.get(`/api/traders/${traderId}`);
      return response.data;  // Возвращаем объект статистики
    } catch (error) {
      console.error(`Error fetching trader stats for ${traderId}:`, error);
      throw error;
    }
  },

  getTraderSignals: async (traderId, params = {}) => {
    try {
      const ticker = params.ticker || null;
      const limit = params.limit || 100;
      const queryParams = {};
      if (ticker) queryParams.ticker = ticker;
      if (limit) queryParams.limit = limit;

      const response = await api.get(`/api/traders/${traderId}/signals`, { params: queryParams });
      return response.data;  // Возвращаем массив сигналов
    } catch (error) {
      console.error(`Error fetching signals for trader ${traderId}:`, error);
      throw error;
    }
  },

  /**
   * Получение всех сигналов с фильтрацией
   * @param {number} days - Количество дней
   * @param {number} limit - Максимальное количество сигналов
   * @param {string} ticker - Фильтр по тикеру (опционально)
   */
  async getAllSignals(days = 30, limit = 100, ticker = null) {
    try {
      const params = { days, limit }
      if (ticker) params.ticker = ticker
      
      const response = await api.get('/api/signals', { params })
      return response.data
    } catch (error) {
      throw new Error(`Failed to get signals: ${error.response?.data?.detail || error.message}`)
    }
  },

  /**
   * Получение сигналов по конкретному трейдеру
   * @param {string} trader - Имя трейдера
   * @param {number} days - Количество дней
   * @param {number} limit - Максимальное количество сигналов
   */
  async getSignalsByTrader(trader, days = 30, limit = 100) {
    try {
      const response = await api.get(`/api/signals/trader/${trader}`, {
        params: { days, limit }
      })
      return response.data
    } catch (error) {
      throw new Error(`Failed to get signals for trader ${trader}: ${error.response?.data?.detail || error.message}`)
    }
  },

  // ===== 📈 ТИКЕРЫ И ИНСТРУМЕНТЫ =====
  
  /**
   * Получение списка доступных тикеров
   */
  async getTickers() {
    try {
      const response = await api.get('/api/tickers')
      return response.data
    } catch (error) {
      throw new Error(`Failed to get tickers: ${error.response?.data?.detail || error.message}`)
    }
  },

  /**
   * Поиск инструментов по названию или тикеру
   * @param {string} query - Поисковой запрос
   */
  async searchInstruments(query) {
    try {
      const response = await api.get('/api/instruments/search', {
        params: { q: query }
      })
      return response.data
    } catch (error) {
      throw new Error(`Failed to search instruments: ${error.response?.data?.detail || error.message}`)
    }
  },

  // ===== 🔄 УМНАЯ ЗАГРУЗКА ДАННЫХ =====
  
  /**
   * Умная загрузка данных для конкретного тикера
   * @param {string} ticker - Тикер инструмента
   * @param {number} days - Количество дней для загрузки
   * @param {boolean} force - Принудительная загрузка
   */
  async smartLoadData(ticker, days = 365, force = false) {
    try {
      const params = { days }
      if (force) params.force = true
      
      const response = await api.post(`/api/data/smart-load/${ticker}`, null, { params })
      return response.data
    } catch (error) {
      throw new Error(`Failed to smart load data for ${ticker}: ${error.response?.data?.detail || error.message}`)
    }
  },

  /**
   * Массовая умная загрузка для всех тикеров с сигналами
   */
  async bulkSmartLoad() {
    try {
      const response = await api.post('/api/data/bulk-smart-load')
      return response.data
    } catch (error) {
      throw new Error(`Failed to perform bulk smart load: ${error.response?.data?.detail || error.message}`)
    }
  },

  /**
   * Умный метод получения свечей с автозагрузкой при необходимости
   * @param {string} ticker - Тикер инструмента
   * @param {number} days - Количество дней
   * @param {boolean} forceLoad - Принудительная загрузка данных
   */
  async getCandlesWithSmartLoad(ticker, days = 30, forceLoad = false) {
    try {
      // Если принудительная загрузка - сначала загружаем данные
      if (forceLoad) {
        console.log(`🔄 Force loading data for ${ticker}...`)
        await this.smartLoadData(ticker, Math.max(days, 365), true)
      }

      // Пытаемся получить данные из БД
      try {
        return await this.getCandles(ticker, days)
      } catch (error) {
        // Если данных нет и не было принудительной загрузки - пытаемся загрузить
        if (error.message.includes('No candle data available') && !forceLoad) {
          console.log(`🔥 No data found for ${ticker}, attempting smart load...`)
          
          await this.smartLoadData(ticker, Math.max(days, 365), true)
          
          // Повторяем запрос после загрузки
          return await this.getCandles(ticker, days)
        }
        
        throw error
      }
    } catch (error) {
      throw new Error(`Failed to get candles with smart load for ${ticker}: ${error.message}`)
    }
  },

  // ===== 📊 ПОКРЫТИЕ ДАННЫХ =====
  
  /**
   * Проверка покрытия данных для тикера
   * @param {string} ticker - Тикер инструмента
   * @param {number} days - Количество дней для проверки
   */
  async getDataCoverage(ticker, days = 30) {
    try {
      const response = await api.get(`/api/data/coverage/${ticker}`, {
        params: { days }
      })
      return response.data
    } catch (error) {
      throw new Error(`Failed to get data coverage for ${ticker}: ${error.response?.data?.detail || error.message}`)
    }
  },

  // ===== 📈 СТАТИСТИКА =====
  
  /**
   * Получение общей статистики системы
   */
  async getStatistics() {
    try {
      const response = await api.get('/api/statistics')
      return response.data
    } catch (error) {
      throw new Error(`Failed to get statistics: ${error.response?.data?.detail || error.message}`)
    }
  },

  // ===== 🛠️ УПРАВЛЕНИЕ ДАННЫМИ =====
  
  /**
   * Получение статуса парсинга сообщений
   */
  async getParsingStatus() {
    try {
      const response = await api.get('/api/messages/parsing-status')
      return response.data
    } catch (error) {
      throw new Error(`Failed to get parsing status: ${error.response?.data?.detail || error.message}`)
    }
  },

  /**
   * Запуск парсинга сообщений
   * @param {number} limit - Лимит сообщений для обработки
   */
  async startMessageParsing(limit = null) {
    try {
      const params = limit ? { limit } : {}
      const response = await api.post('/api/messages/parse', null, { params })
      return response.data
    } catch (error) {
      throw new Error(`Failed to start message parsing: ${error.response?.data?.detail || error.message}`)
    }
  }
}

export default tradingAPI