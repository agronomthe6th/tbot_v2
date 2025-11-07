// frontend/src/router/index.js - ОБНОВЛЕННАЯ ВЕРСИЯ с новой страницей
import { createRouter, createWebHistory } from 'vue-router'
import TradingDashboard from '../views/TradingDashboard.vue'
import SignalsChart from '../views/SignalsChart.vue'
import CleanChart from '../views/CleanChart.vue'
import TraderProfile from '../views/TraderProfile.vue'
import AllSignals from '../views/AllSignals.vue'
import DataDiagnostics from '../views/DataDiagnostics.vue'
import PatternsManager from '../views/PatternsManager.vue'
import ConsensusPage from '../views/ConsensusPage.vue'

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
  path: '/data-management',
  name: 'DataManagement',
  component: () => import('../views/DataManagement.vue'),
  meta: { title: '📊 Управление данными' }
  },
  {
    path: '/patterns',
    name: 'PatternsManager',
    component: PatternsManager,
    meta: { title: '🎯 Управление паттернами' }
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
  },
  {
    path: '/consensus',
    name: 'Consensus',
    component: ConsensusPage,
    meta: { title: '🔥 Консенсус Трейдеров' }
  },
  {
    path: '/signals',
    name: 'AllSignals',
    component: AllSignals,
    meta: { title: '🎯 Все сигналы' }
  },
  {
    path: '/diagnostics',
    name: 'DataDiagnostics',
    component: DataDiagnostics,
    meta: { title: '🔍 Диагностика данных' }
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