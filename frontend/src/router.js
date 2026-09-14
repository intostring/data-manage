import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from './stores/auth'

const routes = [
  {
    path: '/login',
    name: 'login',
    component: () => import('./views/Login.vue'),
    meta: { public: true },
  },
  // 默认进入前台分析
  { path: '/', redirect: '/display/overview' },
  // 前台分析
  {
    path: '/display',
    component: () => import('./views/DisplayLayout.vue'),
    children: [
      { path: 'overview', name: 'display-overview', component: () => import('./views/display/Overview.vue') },
      { path: 'advisor', name: 'display-advisor', component: () => import('./views/display/AdvisorPerformance.vue') },
      { path: 'position', name: 'display-position', component: () => import('./views/display/PositionAnalysis.vue') },
      { path: 'trade', name: 'display-trade', component: () => import('./views/display/TradeAnalysis.vue') },
      { path: 'risk', name: 'display-risk', component: () => import('./views/display/RiskControl.vue') },
      { path: 'strategy', name: 'display-strategy', component: () => import('./views/display/StrategyAnalysis.vue') },
      { path: '', redirect: { name: 'display-overview' } },
    ],
  },
  // 后台管理
  {
    path: '/admin',
    component: () => import('./views/AppLayout.vue'),
    children: [
      { path: '', name: 'dashboard', component: () => import('./views/Dashboard.vue') },
      { path: 'table/existing/:key', name: 'existing-table', component: () => import('./views/TableView.vue') },
      { path: 'table/dynamic/:key', name: 'dynamic-table', component: () => import('./views/TableView.vue') },
      { path: 'upload', name: 'upload', component: () => import('./views/UploadTable.vue') },
      { path: 'system/users', name: 'system-users', component: () => import('./views/SystemUsers.vue') },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to) => {
  const auth = useAuthStore()
  if (!to.meta.public && !auth.isAuthenticated) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
  if (to.name === 'login' && auth.isAuthenticated) {
    return { name: 'display-overview' }
  }
})

export default router
