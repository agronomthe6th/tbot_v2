import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  }
})

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
  get: async (url, config = {}) => {
    const response = await api.get(url, config)
    return response
  },

  post: async (url, data = {}, config = {}) => {
    const response = await api.post(url, data, config)
    return response
  },

  put: async (url, data = {}, config = {}) => {
    const response = await api.put(url, data, config)
    return response
  },

  patch: async (url, data = {}, config = {}) => {
    const response = await api.patch(url, data, config)
    return response
  },

  delete: async (url, config = {}) => {
    const response = await api.delete(url, config)
    return response
  },

  async getSignals(options = {}) {
    try {
      const {
        ticker,
        author,
        trader_id,
        direction = 'all',
        status = 'all',
        hours_back,
        days_back,
        limit = 50,
        offset = 0,
        order_by = 'timestamp',
        order_dir = 'desc',
        include_stats = false
      } = options

      console.log('🌐 API: Universal getSignals called with:', options)

      const params = {
        limit,
        offset,
        order_by,
        order_dir,
        direction,
        status,
        include_stats
      }

      if (ticker) params.ticker = ticker
      if (author) params.author = author
      if (trader_id) params.trader_id = trader_id
      if (hours_back) params.hours_back = hours_back
      if (days_back) params.days_back = days_back

      const response = await api.get('/api/signals', { params })

      console.log('✅ API: Universal signals response:', {
        count: response.data.count,
        has_stats: !!response.data.stats
      })
      
      return response.data
    } catch (error) {
      console.error('❌ API: Signals error:', error.response?.data)
      throw new Error(error.response?.data?.detail || 'Failed to fetch signals')
    }
  },

  async getSignal(signal_id) {
    try {
      console.log(`🌐 API: Getting signal ${signal_id}`)
      
      const response = await api.get(`/api/signals/${signal_id}`)
      
      console.log('✅ API: Signal response:', response.data)
      return response.data
    } catch (error) {
      console.error(`❌ API: Signal error for ${signal_id}:`, error.response?.data)
      throw new Error(error.response?.data?.detail || `Failed to fetch signal ${signal_id}`)
    }
  },

  async updateSignal(signal_id, update_data) {
    try {
      console.log(`🌐 API: Updating signal ${signal_id}`)
      
      const response = await api.patch(`/api/signals/${signal_id}`, update_data)
      
      console.log('✅ API: Signal updated:', response.data)
      return response.data
    } catch (error) {
      console.error(`❌ API: Update signal error for ${signal_id}:`, error.response?.data)
      throw new Error(error.response?.data?.detail || 'Failed to update signal')
    }
  },

  async getSignalsStats(options = {}) {
    try {
      const {
        ticker,
        author,
        trader_id,
        direction = 'all',
        status = 'all',
        hours_back,
        days_back
      } = options

      console.log('🌐 API: Getting signals stats with:', options)

      const params = { direction, status }
      
      if (ticker) params.ticker = ticker
      if (author) params.author = author
      if (trader_id) params.trader_id = trader_id
      if (hours_back) params.hours_back = hours_back
      if (days_back) params.days_back = days_back

      const response = await api.get('/api/signals/stats', { params })
      
      console.log('✅ API: Signals stats response:', response.data)
      return response.data
    } catch (error) {
      console.error('❌ API: Signals stats error:', error.response?.data)
      throw new Error(error.response?.data?.detail || 'Failed to fetch signals statistics')
    }
  },

  async getTraders(options = {}) {
    try {
      const {
        days_back = 30,
        min_signals = 1,
        include_stats = true,
        limit = 100,
        offset = 0
      } = options

      console.log('🌐 API: Getting traders with options:', options)

      const params = {
        days_back,
        min_signals,
        include_stats,
        limit,
        offset
      }

      const response = await api.get('/api/traders', { params })

      console.log('✅ API: Traders response:', {
        count: response.data.count,
        has_stats: include_stats
      })
      
      return response.data.traders || response.data
    } catch (error) {
      console.error('❌ API: Traders error:', error.response?.data)
      throw new Error(error.response?.data?.detail || 'Failed to fetch traders')
    }
  },

  async getTraderDetails(trader_id) {
    try {
      console.log(`🌐 API: Getting trader details for ${trader_id}`)
      
      const response = await api.get(`/api/traders/${trader_id}`)
      
      console.log('✅ API: Trader details response:', response.data)
      return response.data
    } catch (error) {
      console.error(`❌ API: Trader details error for ${trader_id}:`, error.response?.data)
      throw new Error(error.response?.data?.detail || `Failed to fetch trader ${trader_id}`)
    }
  },

  async getTraderStats(trader_id, days_back = 30) {
    try {
      console.log(`🌐 API: Getting trader stats for ${trader_id}, ${days_back} days`)
      
      const response = await api.get(`/api/traders/${trader_id}/stats`, {
        params: { days_back }
      })
      
      console.log('✅ API: Trader stats response:', response.data)
      return response.data
    } catch (error) {
      console.error(`❌ API: Trader stats error for ${trader_id}:`, error.response?.data)
      throw new Error(error.response?.data?.detail || `Failed to fetch stats for trader ${trader_id}`)
    }
  },

  async getPatterns(category = null, active_only = false) {
    try {
      console.log('🌐 API: Getting patterns')
      
      const params = {}
      if (category) params.category = category
      if (active_only) params.active_only = true
      
      const response = await api.get('/api/patterns', { params })
      
      console.log('✅ API: Patterns response:', {
        count: response.data.count
      })
      
      return response.data
    } catch (error) {
      console.error('❌ API: Patterns error:', error.response?.data)
      throw new Error(error.response?.data?.detail || 'Failed to fetch patterns')
    }
  },

  async getPattern(pattern_id) {
    try {
      console.log(`🌐 API: Getting pattern ${pattern_id}`)
      
      const response = await api.get(`/api/patterns/${pattern_id}`)
      
      console.log('✅ API: Pattern response:', response.data)
      return response.data
    } catch (error) {
      console.error(`❌ API: Pattern error for ${pattern_id}:`, error.response?.data)
      throw new Error(error.response?.data?.detail || `Failed to fetch pattern ${pattern_id}`)
    }
  },

  async createPattern(pattern_data) {
    try {
      console.log('🌐 API: Creating pattern:', pattern_data.name)
      
      const response = await api.post('/api/patterns', pattern_data)
      
      console.log('✅ API: Pattern created:', response.data)
      return response.data
    } catch (error) {
      console.error('❌ API: Create pattern error:', error.response?.data)
      throw new Error(error.response?.data?.detail || 'Failed to create pattern')
    }
  },

  async updatePattern(pattern_id, pattern_data) {
    try {
      console.log(`🌐 API: Updating pattern ${pattern_id}`)
      
      const response = await api.put(`/api/patterns/${pattern_id}`, pattern_data)
      
      console.log('✅ API: Pattern updated:', response.data)
      return response.data
    } catch (error) {
      console.error(`❌ API: Update pattern error for ${pattern_id}:`, error.response?.data)
      throw new Error(error.response?.data?.detail || 'Failed to update pattern')
    }
  },

  async deletePattern(pattern_id) {
    try {
      console.log(`🌐 API: Deleting pattern ${pattern_id}`)
      
      const response = await api.delete(`/api/patterns/${pattern_id}`)
      
      console.log('✅ API: Pattern deleted:', response.data)
      return response.data
    } catch (error) {
      console.error(`❌ API: Delete pattern error for ${pattern_id}:`, error.response?.data)
      throw new Error(error.response?.data?.detail || 'Failed to delete pattern')
    }
  },

  async togglePattern(pattern_id) {
    try {
      console.log(`🌐 API: Toggling pattern ${pattern_id}`)
      
      const response = await api.patch(`/api/patterns/${pattern_id}/toggle`)
      
      console.log('✅ API: Pattern toggled:', response.data)
      return response.data
    } catch (error) {
      console.error(`❌ API: Toggle pattern error for ${pattern_id}:`, error.response?.data)
      throw new Error(error.response?.data?.detail || 'Failed to toggle pattern')
    }
  },

  async testPattern(test_data) {
    try {
      console.log('🌐 API: Testing pattern')
      
      const response = await api.post('/api/patterns/test', test_data)
      
      console.log('✅ API: Pattern test result:', response.data)
      return response.data
    } catch (error) {
      console.error('❌ API: Test pattern error:', error.response?.data)
      throw new Error(error.response?.data?.detail || 'Failed to test pattern')
    }
  },

  async getAvailableTickers(with_stats = true) {
    try {
      console.log('🌐 API: Getting available tickers')
      
      const response = await api.get('/api/tickers', {
        params: { with_stats }
      })
      
      console.log('✅ API: Tickers response:', {
        count: response.data.count || response.data.tickers?.length || response.data.length
      })
      
      return response.data.tickers || response.data
    } catch (error) {
      console.error('❌ API: Tickers error:', error.response?.data)
      throw new Error(error.response?.data?.detail || 'Failed to fetch available tickers')
    }
  },

  async getCandles(ticker, days = 30) {
    try {
      console.log(`🌐 API: Getting candles for ${ticker}, ${days} days`)
      
      const response = await api.get(`/api/candles/${ticker}`, {
        params: { days }
      })
      
      console.log('✅ API: Candles response:', {
        ticker: response.data.ticker,
        count: response.data.count,
        period_days: response.data.period_days
      })
      
      return response.data
    } catch (error) {
      console.error(`❌ API: Candles error for ${ticker}:`, error.response?.data)
      if (error.response?.status === 404) {
        throw new Error(`No candle data available for ${ticker}. Try loading historical data first.`)
      }
      throw new Error(error.response?.data?.detail || `Failed to fetch candles for ${ticker}`)
    }
  },

  async getCurrentPrice(ticker) {
    try {
      console.log(`🌐 API: Getting current price for ${ticker}`)
      
      const response = await api.get(`/api/price/${ticker}`)
      
      console.log(`✅ API: Price response for ${ticker}:`, response.data)
      return response.data
    } catch (error) {
      console.error(`❌ API: Price error for ${ticker}:`, error.response?.data)
      throw new Error(error.response?.data?.detail || `Failed to fetch price for ${ticker}`)
    }
  },

  async getStats(options = {}) {
    try {
      const {
        days_back = 30
      } = options

      console.log('🌐 API: Getting stats', { days_back })

      const params = { days_back }

      const response = await api.get('/api/stats', { params })

      console.log('✅ API: Stats response:', response.data)
      return response.data
    } catch (error) {
      console.error('❌ API: Stats error:', error.response?.data)
      throw new Error(error.response?.data?.detail || 'Failed to fetch stats')
    }
  },

  async getHealth() {
    try {
      console.log('🌐 API: Checking health')
      
      const response = await api.get('/health')
      
      console.log('✅ API: Health response:', response.data)
      return response.data
    } catch (error) {
      console.error('❌ API: Health check error:', error.response?.data)
      throw new Error(error.response?.data?.detail || 'Health check failed')
    }
  },

  async loadHistoricalData(ticker, options = {}) {
    try {
      const {
        days_back = 365,
        force_reload = false
      } = options

      console.log(`🌐 API: Loading historical data for ${ticker}`, { days_back, force_reload })

      const params = {
        days_back,
        force_reload
      }

      const response = await api.post(`/api/data/load/${ticker}`, null, { params })

      console.log(`✅ API: Historical data loaded for ${ticker}:`, response.data)
      return response.data
    } catch (error) {
      console.error(`❌ API: Load historical data error for ${ticker}:`, error.response?.data)
      throw new Error(error.response?.data?.detail || `Failed to load historical data for ${ticker}`)
    }
  },

  async checkDataCoverage(ticker, days_back = 30) {
    try {
      console.log(`🌐 API: Checking data coverage for ${ticker}`, { days_back })

      const params = { days_back }

      const response = await api.get(`/api/data/coverage/${ticker}`, { params })

      console.log(`✅ API: Data coverage for ${ticker}:`, response.data)
      return response.data
    } catch (error) {
      console.error(`❌ API: Data coverage error for ${ticker}:`, error.response?.data)
      throw new Error(error.response?.data?.detail || `Failed to check data coverage for ${ticker}`)
    }
  },

  async getSystemStatistics() {
    try {
      console.log('🌐 API: Getting system statistics')
      
      const response = await api.get('/api/statistics')
      
      console.log('✅ API: System statistics response:', response.data)
      return response.data
    } catch (error) {
      console.error('❌ API: System statistics error:', error.response?.data)
      throw new Error(error.response?.data?.detail || 'Failed to get system statistics')
    }
  },

  async getSignalsByTicker(ticker, days = 30, limit = 50) {
    console.warn('⚠️ getSignalsByTicker is deprecated. Use getSignals({ ticker }) instead.')
    
    const result = await this.getSignals({
      ticker,
      days_back: days,
      limit
    })
    
    return {
      signals: result.signals || result,
      count: result.count || result.length
    }
  },

  async getTraderSignals(trader, options = {}) {
    console.warn('⚠️ getTraderSignals is deprecated. Use getSignals({ author }) instead.')
    
    const { days = 90, limit = 50, ticker = null } = options
    
    const result = await this.getSignals({
      author: trader,
      ticker,
      days_back: days,
      limit
    })
    
    return result.signals || result
  },

  async getRecentSignals(hours = 24, limit = 50) {
    console.warn('⚠️ getRecentSignals is deprecated. Use getSignals({ hours_back }) instead.')
    
    const result = await this.getSignals({
      hours_back: hours,
      limit
    })
    
    return result
  },

  async getActiveSignals() {
    console.warn('⚠️ getActiveSignals is deprecated. Use getSignals({ status: "active" }) instead.')
    
    const result = await this.getSignals({
      status: 'active'
    })
    
    return result
  },

  async debugSignalsData() {
    try {
      console.log('🌐 API: Getting debug signals info')
      
      const response = await api.get('/api/debug/signals')
      
      console.log('✅ API: Debug signals response:', response.data)
      return response.data
    } catch (error) {
      console.warn('API: Debug signals failed:', error)
      return null
    }
  },

  async debugMessagesData(limit = 10) {
    try {
      console.log('🌐 API: Getting debug messages info')
      
      const response = await api.get('/api/debug/messages', {
        params: { limit }
      })
      
      console.log('✅ API: Debug messages response:', response.data)
      return response.data
    } catch (error) {
      console.warn('API: Debug messages failed:', error)
      return null
    }
  },

  async healthCheck() {
    try {
      const response = await api.get('/api/health')
      return response.data
    } catch (error) {
      throw new Error('API health check failed')
    }
  }
}

export default tradingAPI