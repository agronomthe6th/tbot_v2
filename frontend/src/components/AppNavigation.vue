<!-- frontend/src/components/AppNavigation.vue -->
<template>
  <nav class="bg-trading-card border-b border-trading-border">
    <div class="max-w-7xl mx-auto px-4">
      <div class="flex items-center justify-between h-16">
        <!-- Логотип/Название -->
        <div class="flex items-center">
          <router-link to="/" class="flex items-center gap-2 text-xl font-bold text-white hover:text-trading-green transition-colors">
            📊 Trader Tracker
          </router-link>
        </div>

        <!-- Основная навигация -->
        <div class="hidden md:flex items-center space-x-6">
          <router-link 
            to="/" 
            :class="$route.name === 'Dashboard' ? 'text-trading-green' : 'text-gray-300 hover:text-white'"
            class="transition-colors"
          >
            🏠 Дашборд
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
        </div>

        <!-- Мобильное меню -->
        <div class="md:hidden">
          <button 
            @click="isMobileMenuOpen = !isMobileMenuOpen"
            class="mobile-menu-btn"
          >
            <svg class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>
        </div>
      </div>

      <!-- Мобильное меню -->
      <div v-if="isMobileMenuOpen" class="mobile-menu md:hidden">
        <div class="mobile-menu-content">
          <router-link 
            to="/" 
            @click="isMobileMenuOpen = false"
            class="mobile-menu-link"
          >
            🏠 Дашборд
          </router-link>
          
          <router-link 
            to="/signals-chart" 
            @click="isMobileMenuOpen = false"
            class="mobile-menu-link"
          >
            📈 График сигналов
          </router-link>
          
          <router-link 
            to="/clean-chart" 
            @click="isMobileMenuOpen = false"
            class="mobile-menu-link"
          >
            📊 Чистый график
          </router-link>
          
          <router-link 
            to="/traders" 
            @click="isMobileMenuOpen = false"
            class="mobile-menu-link"
          >
            👥 Трейдеры
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
.mobile-menu-btn {
  @apply text-gray-300 hover:text-white p-2 rounded transition-colors;
}

.mobile-menu {
  @apply border-t border-trading-border;
}

.mobile-menu-content {
  @apply py-2 space-y-1;
}

.mobile-menu-link {
  @apply block px-4 py-2 text-gray-300 hover:text-white hover:bg-trading-bg transition-colors;
}
</style>