// frontend/src/router/index.js - ОБНОВЛЕННАЯ ВЕРСИЯ
import { createRouter, createWebHistory } from 'vue-router'
import TradingDashboard from '../views/TradingDashboard.vue'
import SignalsChart from '../views/SignalsChart.vue'
import CleanChart from '../views/CleanChart.vue'
import TraderProfile from '../views/TraderProfile.vue'

const routes = [
  {
    path: '/',
    name: 'Dashboard',
    component: TradingDashboard,
    meta: { title: '📊 Торговый Терминал' }
  },
  {
    path: '/signals-chart/:ticker?',
    name: 'SignalsChart',
    component: SignalsChart,
    meta: { title: '📈 График с сигналами' }
  },
  {
    path: '/clean-chart/:ticker?',
    name: 'CleanChart',
    component: CleanChart,
    meta: { title: '📊 Чистый график' }
  },
  {
    path: '/trader/:id',
    name: 'TraderProfile',
    component: TraderProfile,
    meta: { title: '👤 Профиль трейдера' }
  },
  {
    path: '/traders',
    name: 'TradersOverview',
    component: TraderProfile, // Можно использовать тот же компонент без ID для списка
    meta: { title: '👥 Трейдеры' }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to) => {
  document.title = to.meta.title || 'Trader Tracker'
})

export default router