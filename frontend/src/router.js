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
  // 前台分析（公开访问，无需登录）
  {
    path: '/display',
    component: () => import('./views/DisplayLayout.vue'),
    meta: { public: true },
    children: [
      { path: 'overview', name: 'display-overview', component: () => import('./views/display/Overview.vue') },
      { path: 'advisor', name: 'display-advisor', component: () => import('./views/display/AdvisorPerformance.vue') },
      { path: 'sector', name: 'display-sector', component: () => import('./views/display/SectorBoard.vue') },
      { path: 'sector/pnl', name: 'display-sector-pnl', component: () => import('./views/display/SectorPnl.vue') },
      { path: 'sector/advisor-variety', name: 'display-sector-advisor-variety', component: () => import('./views/display/SectorAdvisorVariety.vue') },
      { path: 'sector/contract-kline', name: 'display-sector-contract-kline', component: () => import('./views/display/ContractKline.vue') },
      { path: 'position', name: 'display-position', component: () => import('./views/display/PositionAnalysis.vue') },
      { path: 'position/sector-analysis', name: 'display-position-sector-analysis', component: () => import('./views/display/SectorAnalysis.vue') },
      { path: 'position/sector-detail', name: 'display-position-sector-detail', component: () => import('./views/display/SectorPositionDetail.vue') },
      { path: 'position/sector-overview', name: 'display-position-sector-overview', component: () => import('./views/display/SectorPositionOverview.vue') },
      { path: 'position/variety-advisor-long-short', name: 'display-position-variety-advisor-long-short', component: () => import('./views/display/VarietyAdvisorLongShort.vue') },
      { path: 'trade', name: 'display-trade', component: () => import('./views/display/TradeAnalysis.vue') },
      { path: 'trade/advisor-overview', name: 'display-trade-advisor-overview', component: () => import('./views/display/AdvisorTradeOverview.vue') },
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
