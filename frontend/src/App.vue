<!-- frontend/src/App.vue - ИСПОЛЬЗОВАНИЕ КОМПОНЕНТА НАВИГАЦИИ -->
<template>
  <div id="app" class="app-container">
    <!-- Используем компонент навигации -->
    <AppNavigation v-if="showNavigation" />

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

    <!-- Глобальный индикатор загрузки -->
    <div v-if="isGlobalLoading" class="global-loading">
      <div class="loading-spinner"></div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import AppNavigation from './components/AppNavigation.vue'  // ✅ ИМПОРТИРУЕМ КОМПОНЕНТ

// Реактивные данные
const route = useRoute()
const showNavigation = ref(true)
const isGlobalLoading = ref(false)

// Lifecycle
onMounted(() => {
  console.log('🚀 Trader Tracker App started')
  checkBrowserSupport()
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
    showBrowserWarning(unsupported)
  } else {
    console.log('✅ All browser features supported')
  }
}

function showBrowserWarning(unsupportedFeatures) {
  const message = `Ваш браузер не поддерживает некоторые функции: ${unsupportedFeatures.join(', ')}. Рекомендуем обновить браузер.`
  console.warn(message)
  
  if (unsupportedFeatures.includes('Fetch')) {
    alert('Ваш браузер устарел. Пожалуйста, обновите его для корректной работы приложения.')
  }
}

async function initializeApp() {
  try {
    console.log('✅ App initialized successfully')
  } catch (error) {
    console.error('❌ App initialization failed:', error)
  }
}

function showGlobalLoading() {
  isGlobalLoading.value = true
}

function hideGlobalLoading() {
  isGlobalLoading.value = false
}

defineExpose({
  showGlobalLoading,
  hideGlobalLoading
})
</script>