<!-- frontend/src/views/TradingDashboard.vue - ОБНОВЛЕННАЯ ВЕРСИЯ -->
<template>
  <div class="min-h-screen bg-trading-bg text-white">
    <div class="max-w-7xl mx-auto p-4">
      
      <!-- Заголовок -->
      <div class="mb-8">
        <h1 class="text-3xl font-bold mb-2">📊 Торговый Терминал</h1>
        <p class="text-gray-400">Анализ торговых сигналов и мониторинг результатов</p>
      </div>

      <!-- Быстрые ссылки -->
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <!-- График с сигналами -->
        <router-link 
          to="/signals-chart"
          class="bg-trading-card rounded-lg border border-trading-border p-6 hover:border-trading-green transition-colors cursor-pointer group"
        >
          <div class="text-4xl mb-4 group-hover:scale-110 transition-transform">📈</div>
          <h3 class="text-xl font-semibold mb-2">График с сигналами</h3>
          <p class="text-gray-400">Просматривайте торговые сигналы на графике свечей</p>
        </router-link>

        <!-- Чистый график -->
        <router-link 
          to="/clean-chart"
          class="bg-trading-card rounded-lg border border-trading-border p-6 hover:border-trading-green transition-colors cursor-pointer group"
        >
          <div class="text-4xl mb-4 group-hover:scale-110 transition-transform">📊</div>
          <h3 class="text-xl font-semibold mb-2">Чистый график</h3>
          <p class="text-gray-400">График свечей без торговых сигналов</p>
        </router-link>

        <!-- Трейдеры -->
        <router-link 
          to="/traders"
          class="bg-trading-card rounded-lg border border-trading-border p-6 hover:border-trading-green transition-colors cursor-pointer group"
        >
          <div class="text-4xl mb-4 group-hover:scale-110 transition-transform">👥</div>
          <h3 class="text-xl font-semibold mb-2">Трейдеры</h3>
          <p class="text-gray-400">Анализ эффективности трейдеров и их сигналов</p>
        </router-link>

        <!-- Статистика -->
        <div class="bg-trading-card rounded-lg border border-trading-border p-6">
          <div class="text-4xl mb-4">📊</div>
          <h3 class="text-xl font-semibold mb-2">Статистика</h3>
          <p class="text-gray-400">Общая статистика системы и производительность</p>
        </div>
      </div>

      <!-- Дополнительная информация -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <!-- Быстрый доступ -->
        <div class="bg-trading-card rounded-lg border border-trading-border p-6">
          <h3 class="text-xl font-semibold mb-4">🚀 Быстрый старт</h3>
          <div class="space-y-3">
            <div class="flex items-center justify-between p-3 bg-trading-bg border border-trading-border rounded">
              <div>
                <div class="font-semibold">График с сигналами</div>
                <div class="text-sm text-gray-400">Анализ сигналов на графике</div>
              </div>
              <router-link 
                to="/signals-chart" 
                class="px-3 py-1 bg-trading-green text-black rounded hover:bg-opacity-80 transition-colors text-sm"
              >
                Открыть
              </router-link>
            </div>
            
            <div class="flex items-center justify-between p-3 bg-trading-bg border border-trading-border rounded">
              <div>
                <div class="font-semibold">Чистый график</div>
                <div class="text-sm text-gray-400">Только свечи без сигналов</div>
              </div>
              <router-link 
                to="/clean-chart" 
                class="px-3 py-1 bg-trading-green text-black rounded hover:bg-opacity-80 transition-colors text-sm"
              >
                Открыть
              </router-link>
            </div>
            
            <div class="flex items-center justify-between p-3 bg-trading-bg border border-trading-border rounded">
              <div>
                <div class="font-semibold">Трейдеры</div>
                <div class="text-sm text-gray-400">Анализ эффективности</div>
              </div>
              <router-link 
                to="/traders" 
                class="px-3 py-1 bg-trading-green text-black rounded hover:bg-opacity-80 transition-colors text-sm"
              >
                Открыть
              </router-link>
            </div>
          </div>
        </div>

        <!-- Система -->
        <div class="bg-trading-card rounded-lg border border-trading-border p-6">
          <h3 class="text-xl font-semibold mb-4">⚙️ Система</h3>
          <div class="space-y-4">
            <div class="flex justify-between items-center">
              <span class="text-gray-400">Статус системы</span>
              <span class="text-trading-green">🟢 Активна</span>
            </div>
            
            <div class="flex justify-between items-center">
              <span class="text-gray-400">База данных</span>
              <span class="text-trading-green">🟢 Подключена</span>
            </div>
            
            <div class="flex justify-between items-center">
              <span class="text-gray-400">API Tinkoff</span>
              <span class="text-trading-green">🟢 Работает</span>
            </div>
            
            <div class="flex justify-between items-center">
              <span class="text-gray-400">Парсинг сигналов</span>
              <span class="text-trading-green">🟢 Активен</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Футер с информацией -->
      <div class="mt-12 text-center text-gray-500 text-sm">
        <p>Trader Tracker v2.0 - Система анализа торговых сигналов</p>
        <p class="mt-1">Разработано для автоматизации торговых решений</p>
      </div>
    </div>
  </div>
</template>

<script setup>
// Логика компонента (если нужна)
</script>