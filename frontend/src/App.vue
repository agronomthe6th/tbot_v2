<!-- frontend/src/App.vue -->
<template>
  <div id="app" class="app-container">
    <!-- Глобальная навигация -->
    <nav v-if="showNavigation" class="app-navigation">
      <div class="nav-content">
        <router-link to="/" class="nav-brand">
          📊 Trader Tracker
        </router-link>
        
        <div class="nav-links hidden md:flex">
          <router-link to="/" class="nav-link">
            🏠 Дашборд
          </router-link>
          <router-link to="/signals-chart" class="nav-link">
            📈 График сигналов
          </router-link>
          <router-link to="/traders" class="nav-link">
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
            to="/traders" 
            @click="isMobileMenuOpen = false"
            class="mobile-menu-link"
          >
            👥 Трейдеры
          </router-link>
        </div>
      </div>
    </nav>

    <!-- Основной контент -->
    <div class="app-main" :class="{ 'with-navigation': showNavigation }">
      <router-view v-slot="{ Component }">
        <transition name="page" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </div>

    <!-- Глобальные модальные окна и уведомления -->
    <div id="modals"></div>
    <div id="notifications"></div>

    <!-- Глобальный индикатор загрузки (если понадобится) -->
    <div v-if="isGlobalLoading" class="global-loading">
      <div class="loading-spinner"></div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'

// Реактивные данные
const route = useRoute()
const showNavigation = ref(true) // Включаем навигацию
const isMobileMenuOpen = ref(false)
const isGlobalLoading = ref(false)

// Закрываем мобильное меню при смене роута
watch(() => route.path, () => {
  isMobileMenuOpen.value = false
})

// Lifecycle
onMounted(() => {
  console.log('🚀 Trader Tracker App started')
  
  // Проверяем поддержку современных браузерных API
  checkBrowserSupport()
  
  // Инициализируем приложение
  initializeApp()
})

function checkBrowserSupport() {
  const features = {
    'WebSocket': typeof WebSocket !== 'undefined',
    'localStorage': typeof Storage !== 'undefined',
    'ResizeObserver': typeof ResizeObserver !== 'undefined',
    'IntersectionObserver': typeof IntersectionObserver !== 'undefined',
    'Fetch': typeof fetch !== 'undefined'
  }
  
  const unsupported = Object.entries(features)
    .filter(([_, supported]) => !supported)
    .map(([feature]) => feature)
  
  if (unsupported.length > 0) {
    console.warn('⚠️ Unsupported browser features:', unsupported)
    // Показываем уведомление пользователю
    showBrowserWarning(unsupported)
  } else {
    console.log('✅ All browser features supported')
  }
}

function showBrowserWarning(unsupportedFeatures) {
  // Простое уведомление о несовместимости
  const message = `Ваш браузер не поддерживает некоторые функции: ${unsupportedFeatures.join(', ')}. Рекомендуем обновить браузер.`
  console.warn(message)
  
  // Можно добавить более красивое уведомление позже
  if (unsupportedFeatures.includes('Fetch')) {
    alert('Ваш браузер устарел. Пожалуйста, обновите его для корректной работы приложения.')
  }
}

async function initializeApp() {
  try {
    // Здесь можно добавить глобальную инициализацию
    // Например, проверка авторизации, загрузка настроек и т.д.
    
    console.log('✅ App initialized successfully')
  } catch (error) {
    console.error('❌ App initialization failed:', error)
  }
}

// Глобальные методы для управления загрузкой
function showGlobalLoading() {
  isGlobalLoading.value = true
}

function hideGlobalLoading() {
  isGlobalLoading.value = false
}

// Экспортируем методы для использования в других компонентах
defineExpose({
  showGlobalLoading,
  hideGlobalLoading
})
</script>

<style scoped>
.app-container {
  @apply min-h-screen bg-trading-bg text-white;
}

/* === НАВИГАЦИЯ === */
.app-navigation {
  @apply bg-trading-card border-b border-trading-border sticky top-0 z-50;
}

.nav-content {
  @apply max-w-7xl mx-auto px-4 flex items-center justify-between h-16;
}

.nav-brand {
  @apply text-xl font-bold text-white hover:text-trading-green transition-colors;
  @apply no-underline;
}

.nav-links {
  @apply flex items-center space-x-6;
}

.nav-link {
  @apply text-gray-300 hover:text-white transition-colors;
  @apply no-underline font-medium px-3 py-2 rounded;
}

.nav-link:hover {
  @apply bg-trading-bg bg-opacity-50;
}

.nav-link.router-link-active {
  @apply text-trading-green bg-trading-green bg-opacity-10;
}

/* Мобильное меню */
.mobile-menu-btn {
  @apply text-gray-300 hover:text-white focus:outline-none focus:text-white;
  @apply p-2 rounded transition-colors;
}

.mobile-menu-btn:hover {
  @apply bg-trading-bg bg-opacity-50;
}

.mobile-menu {
  @apply border-t border-trading-border bg-trading-card;
}

.mobile-menu-content {
  @apply max-w-7xl mx-auto px-4 py-4 flex flex-col space-y-3;
}

.mobile-menu-link {
  @apply block text-gray-300 hover:text-white transition-colors;
  @apply no-underline font-medium px-3 py-2 rounded;
}

.mobile-menu-link:hover {
  @apply bg-trading-bg bg-opacity-50;
}

.mobile-menu-link.router-link-active {
  @apply text-trading-green bg-trading-green bg-opacity-10;
}

/* === ОСНОВНОЙ КОНТЕНТ === */
.app-main {
  @apply flex-1;
}

.app-main.with-navigation {
  /* Контент с навигацией */
  @apply pt-0;
}

/* === ГЛОБАЛЬНАЯ ЗАГРУЗКА === */
.global-loading {
  @apply fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50;
}

.loading-spinner {
  @apply animate-spin rounded-full h-12 w-12 border-b-2 border-trading-green;
}

/* === АНИМАЦИИ === */
.page-enter-active,
.page-leave-active {
  transition: all 0.3s cubic-bezier(0.55, 0, 0.1, 1);
}

.page-enter-from {
  opacity: 0;
  transform: translate(30px, 0);
}

.page-leave-to {
  opacity: 0;
  transform: translate(-30px, 0);
}

/* Анимация появления мобильного меню */
.mobile-menu {
  animation: slideDown 0.3s ease-out;
}

@keyframes slideDown {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>

<style>
/* === ГЛОБАЛЬНЫЕ СТИЛИ === */

/* Базовые стили для ссылок */
a {
  text-decoration: none;
}

/* Убираем синие outline'ы в Firefox */
button::-moz-focus-inner {
  border: 0;
}

/* Кастомные скроллбары */
::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

::-webkit-scrollbar-track {
  background: #1a1a1a;
}

::-webkit-scrollbar-thumb {
  background: #404040;
  border-radius: 4px;
}

::-webkit-scrollbar-thumb:hover {
  background: #555555;
}

/* Стили для фокуса */
.router-link-active {
  color: #00d4aa !important;
}

/* Скрываем автозаполнение в Chrome */
input:-webkit-autofill,
input:-webkit-autofill:hover,
input:-webkit-autofill:focus,
input:-webkit-autofill:active {
  -webkit-box-shadow: 0 0 0 30px #1a1a1a inset !important;
  -webkit-text-fill-color: white !important;
}

/* Стили для выделения текста */
::selection {
  background-color: #00d4aa;
  color: #000000;
}

::-moz-selection {
  background-color: #00d4aa;
  color: #000000;
}

/* Базовые стили для форм */
input, textarea, select {
  @apply bg-trading-card border border-trading-border text-white;
  @apply focus:outline-none focus:border-trading-green transition-colors;
}

input::placeholder,
textarea::placeholder {
  @apply text-gray-400;
}

/* Кнопки */
.btn-primary {
  @apply bg-trading-green text-black font-medium px-4 py-2 rounded;
  @apply hover:bg-opacity-80 transition-colors;
}

.btn-secondary {
  @apply bg-trading-card border border-trading-border text-white font-medium px-4 py-2 rounded;
  @apply hover:border-gray-500 transition-colors;
}

.btn-danger {
  @apply bg-trading-red text-white font-medium px-4 py-2 rounded;
  @apply hover:bg-opacity-80 transition-colors;
}

/* Утилиты для текста */
.text-success {
  @apply text-trading-green;
}

.text-danger {
  @apply text-trading-red;
}

.text-warning {
  @apply text-trading-yellow;
}

/* Анимации для элементов */
.fade-in {
  animation: fadeIn 0.5s ease-in;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.slide-up {
  animation: slideUp 0.3s ease-out;
}

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* Отзывчивость */
@media (max-width: 768px) {
  .app-main {
    @apply px-2;
  }
}

/* Высокий DPI */
@media (-webkit-min-device-pixel-ratio: 2), (min-resolution: 192dpi) {
  /* Улучшенная четкость для retina дисплеев */
  .loading-spinner {
    @apply border-2;
  }
}

/* Печать */
@media print {
  .app-navigation,
  .mobile-menu,
  .global-loading {
    display: none !important;
  }
  
  .app-main {
    @apply p-0;
  }
}

/* Темы для пользователей с ограниченными возможностями */
@media (prefers-reduced-motion: reduce) {
  .page-enter-active,
  .page-leave-active,
  .loading-spinner,
  .fade-in,
  .slide-up {
    animation: none !important;
    transition: none !important;
  }
}

@media (prefers-high-contrast: high) {
  .nav-link,
  .mobile-menu-link {
    @apply border border-transparent;
  }
  
  .nav-link:focus,
  .mobile-menu-link:focus {
    @apply border-white;
  }
}
</style>