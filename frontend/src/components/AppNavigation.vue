<!-- frontend/src/components/AppNavigation.vue - ОБНОВЛЕННАЯ ВЕРСИЯ -->
<template>
  <nav class="bg-trading-card border-b border-trading-border">
    <div class="max-w-7xl mx-auto px-4">
      <div class="flex items-center justify-between h-16">
        <div class="flex items-center">
          <router-link to="/" class="flex items-center gap-2 text-xl font-bold text-white hover:text-trading-green transition-colors">
            📊 Trader Tracker
          </router-link>
        </div>

        <div class="hidden md:flex items-center space-x-6">
          <router-link 
            to="/" 
            :class="$route.name === 'Dashboard' ? 'text-trading-green' : 'text-gray-300 hover:text-white'"
            class="transition-colors"
          >
            🏠 Дашборд
          </router-link>

          <router-link 
            to="/data-management" 
            :class="$route.name === 'DataManagement' ? 'text-trading-green' : 'text-gray-300 hover:text-white'"
            class="transition-colors"
          >
            📊 Управление
          </router-link>

          <router-link 
            to="/signals" 
            :class="$route.name === 'AllSignals' ? 'text-trading-green' : 'text-gray-300 hover:text-white'"
            class="transition-colors"
          >
            🎯 Все сигналы
          </router-link>
          
          <router-link 
            to="/consensus" 
            :class="$route.name === 'Consensus' ? 'text-trading-green bg-trading-bg' : 'text-gray-300 hover:text-white hover:bg-trading-bg'"
            class="px-3 py-2 rounded-md text-sm font-medium transition-colors"
          >
            🔥 Консенсус
          </router-link>

          <router-link 
            to="/signals-chart" 
            :class="$route.name === 'SignalsChart' ? 'text-trading-green' : 'text-gray-300 hover:text-white'"
            class="transition-colors"
          >
            📈 График сигналов
          </router-link>
          
          <router-link 
            to="/clean-chart" 
            :class="$route.name === 'CleanChart' ? 'text-trading-green' : 'text-gray-300 hover:text-white'"
            class="transition-colors"
          >
            📊 Чистый график
          </router-link>
          
          <router-link 
            to="/traders" 
            :class="$route.name === 'TraderProfile' || $route.name === 'TradersOverview' ? 'text-trading-green' : 'text-gray-300 hover:text-white'"
            class="transition-colors"
          >
            👥 Трейдеры
          </router-link>
          
          <router-link 
            to="/patterns" 
            :class="$route.name === 'PatternsManager' ? 'text-trading-green' : 'text-gray-300 hover:text-white'"
            class="transition-colors"
          >
            🎯 Паттерны
          </router-link>

          <router-link 
            to="/diagnostics" 
            :class="$route.name === 'DataDiagnostics' ? 'text-trading-green' : 'text-gray-300 hover:text-white'"
            class="transition-colors"
          >
            🔍 Диагностика
          </router-link>
        </div>

        <!-- Мобильное меню -->
        <div class="md:hidden">
          <button 
            @click="isMobileMenuOpen = !isMobileMenuOpen"
            class="text-gray-300 hover:text-white focus:outline-none focus:text-white transition-colors"
          >
            <svg class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>
        </div>
      </div>

      <!-- Мобильное меню -->
      <div v-if="isMobileMenuOpen" class="md:hidden">
        <div class="px-2 pt-2 pb-3 space-y-1 sm:px-3 border-t border-trading-border">
          <router-link 
            to="/" 
            @click="isMobileMenuOpen = false"
            :class="$route.name === 'Dashboard' ? 'text-trading-green bg-trading-bg' : 'text-gray-300 hover:text-white hover:bg-trading-bg'"
            class="block px-3 py-2 rounded-md text-base font-medium transition-colors"
          >
            🏠 Дашборд
          </router-link>
          
          <router-link 
            to="/signals" 
            @click="isMobileMenuOpen = false"
            :class="$route.name === 'AllSignals' ? 'text-trading-green bg-trading-bg' : 'text-gray-300 hover:text-white hover:bg-trading-bg'"
            class="block px-3 py-2 rounded-md text-base font-medium transition-colors"
          >
            🎯 Все сигналы
          </router-link>
          
          <router-link 
            to="/signals-chart" 
            @click="isMobileMenuOpen = false"
            :class="$route.name === 'SignalsChart' ? 'text-trading-green bg-trading-bg' : 'text-gray-300 hover:text-white hover:bg-trading-bg'"
            class="block px-3 py-2 rounded-md text-base font-medium transition-colors"
          >
            📈 График сигналов
          </router-link>

          <router-link 
            to="/clean-chart" 
            @click="isMobileMenuOpen = false"
            :class="$route.name === 'CleanChart' ? 'text-trading-green bg-trading-bg' : 'text-gray-300 hover:text-white hover:bg-trading-bg'"
            class="block px-3 py-2 rounded-md text-base font-medium transition-colors"
          >
            📊 Чистый график
          </router-link>
          
          <router-link 
            to="/traders" 
            @click="isMobileMenuOpen = false"
            :class="$route.name === 'TraderProfile' || $route.name === 'TradersOverview' ? 'text-trading-green bg-trading-bg' : 'text-gray-300 hover:text-white hover:bg-trading-bg'"
            class="block px-3 py-2 rounded-md text-base font-medium transition-colors"
          >
            👥 Трейдеры
          </router-link>

          <router-link 
            to="/diagnostics" 
            @click="isMobileMenuOpen = false"
            :class="$route.name === 'DataDiagnostics' ? 'text-trading-green bg-trading-bg' : 'text-gray-300 hover:text-white hover:bg-trading-bg'"
            class="block px-3 py-2 rounded-md text-base font-medium transition-colors"
          >
            🔍 Диагностика
          </router-link>

        </div>
      </div>
    </div>
  </nav>
</template>

<script setup>
import { ref } from 'vue'

const isMobileMenuOpen = ref(false)
</script>

<style scoped>
.router-link-active {
  color: var(--trading-green);
}
</style>