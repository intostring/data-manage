<template>
  <div class="d-root">
    <!-- 深墨蓝侧栏 -->
    <aside class="d-side">
      <div class="d-brand">
        <div class="d-brand-mark">
          <div class="d-mark">M</div>
          <div>
            <div class="d-brand-t">MOM分析平台</div>
            <div class="d-brand-s">MOM · ANALYSIS</div>
          </div>
        </div>
      </div>

      <nav class="d-nav">
        <div class="d-nav-g">分析模块</div>
        <template v-for="(m, i) in modules" :key="m.name">
          <router-link
            :to="m.path"
            class="d-nav-it"
            :class="isActive(m.name) || isChildActive(m) ? 'on' : ''"
          >
            <span class="no">{{ String(i + 1).padStart(2, '0') }}</span>
            <component :is="m.icon" :size="14" :stroke-width="1.75" />
            <span>{{ m.label }}</span>
          </router-link>
          <div v-if="m.children?.length" class="d-nav-sub">
            <router-link
              v-for="child in m.children"
              :key="child.name"
              :to="child.path"
              class="d-nav-sub-it"
              :class="isActive(child.name) ? 'on' : ''"
            >
              {{ child.label }}
            </router-link>
          </div>
        </template>
      </nav>

      <div class="d-side-foot">
        <router-link to="/admin">
          <ArrowLeftRight :size="14" :stroke-width="1.75" />
          <span>返回后台管理</span>
        </router-link>
      </div>
    </aside>

    <!-- 主区 -->
    <div class="d-main">
      <header class="d-top">
        <div class="d-crumb">
          <b>MOM分析平台</b>
          <span class="sep">/</span>
          <span>{{ currentTitle }}</span>
        </div>
        <div class="d-spacer"></div>
        <!-- 投顾搜索框（仅投顾业绩页显示） -->
        <div
          v-if="route.name === 'display-advisor'"
          ref="advisorComboRef"
          class="d-combo"
          style="position:relative;width:240px;margin-right:12px"
        >
          <input
            v-model="advisorStore.searchText"
            class="d-ipt"
            style="width:100%;font-size:12px;padding:4px 8px"
            placeholder="输入投顾名称、代码或ID搜索…"
            @focus="advisorStore.showDropdown = true"
            @input="advisorStore.onSearch()"
            @keydown.down="advisorStore.hoverNext"
            @keydown.up="advisorStore.hoverPrev"
            @keydown.enter="advisorStore.confirmHover"
          />
          <div v-if="advisorStore.shouldShowDropdown && advisorStore.displayAdvisors.length" class="d-combo-list">
            <div
              v-for="(a, i) in advisorStore.displayAdvisors"
              :key="a.pid"
              class="d-combo-it"
              :class="advisorStore.hoverIdx === i ? 'on' : ''"
              @mousedown.prevent="advisorStore.selectAdvisor(a.pid)"
              @mouseenter="advisorStore.hoverIdx = i"
            >
              <span style="font-size:12.5px">{{ a.account_name || a.product_name }}</span>
              <span class="d-muted d-mono" style="font-size:10px;margin-left:6px">{{ a.account_code || a.product_name }}</span>
            </div>
          </div>
        </div>
        <!-- 品种搜索框（仅品种盈亏页显示） -->
        <div
          v-if="route.name === 'display-sector-pnl'"
          ref="varietyComboRef"
          class="d-combo"
          style="position:relative;width:220px;margin-right:12px"
        >
          <input
            v-model="varietySearchText"
            class="d-ipt"
            style="width:100%;font-size:12px;padding:4px 8px"
            placeholder="输入品种代码或简称搜索…"
            @input="onVarietyInput"
            @keydown.down.prevent="hoverVarietyNext"
            @keydown.up.prevent="hoverVarietyPrev"
            @keydown.enter.prevent="confirmVarietyHover"
          />
          <div v-if="showVarietyDropdown && varietyResults.length" class="d-combo-list">
            <div
              v-for="(v, i) in varietyResults"
              :key="v.code"
              class="d-combo-it"
              :class="varietyHoverIdx === i ? 'on' : ''"
              @mousedown.prevent="selectVariety(v)"
              @mouseenter="varietyHoverIdx = i"
            >
              <span style="font-size:12.5px">{{ v.name }}</span>
              <span class="d-muted d-mono" style="font-size:10px;margin-left:6px">{{ v.code }}</span>
            </div>
          </div>
        </div>
        <span class="d-mtime">{{ now }}</span>
        <div class="d-seg">
          <router-link to="/display/overview" :class="!isAdmin ? 'on' : ''">前台分析</router-link>
          <router-link to="/admin" :class="isAdmin ? 'on' : ''">后台管理</router-link>
        </div>
      </header>

      <main class="d-content">
        <router-view />
      </main>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  LayoutDashboard,
  TrendingUp,
  Layers,
  PieChart,
  ArrowLeftRight,
  ShieldCheck,
  LineChart,
} from 'lucide-vue-next'
import { useAdvisorStore } from '../stores/advisor'
import client from '../api/client'
import '../styles/display.css'

const route = useRoute()
const router = useRouter()
const advisorStore = useAdvisorStore()
const isAdmin = computed(() => route.path.startsWith('/admin'))
const advisorComboRef = ref(null)
const varietyComboRef = ref(null)
const varietySearchText = ref('')
const varietyResults = ref([])
const showVarietyDropdown = ref(false)
const varietyHoverIdx = ref(-1)
let varietySearchTimer = null

const modules = [
  { name: 'display-overview', label: '总览', path: '/display/overview', icon: LayoutDashboard },
  { name: 'display-advisor', label: '投顾业绩', path: '/display/advisor', icon: TrendingUp },
  {
    name: 'display-sector',
    label: '盈亏分析',
    path: '/display/sector',
    icon: Layers,
    children: [
      { name: 'display-sector-pnl', label: '品种盈亏', path: '/display/sector/pnl' },
      { name: 'display-sector-advisor-variety', label: '品种投顾明细', path: '/display/sector/advisor-variety' },
    ],
  },
  {
    name: 'display-position',
    label: '持仓分析',
    path: '/display/position',
    icon: PieChart,
    children: [
      { name: 'display-position-sector-analysis', label: '板块分析', path: '/display/position/sector-analysis' },
      { name: 'display-position-sector-detail', label: '板块持仓明细', path: '/display/position/sector-detail' },
      { name: 'display-position-sector-overview', label: '板块持仓概览', path: '/display/position/sector-overview' },
      { name: 'display-position-variety-advisor-long-short', label: '品种投顾多空', path: '/display/position/variety-advisor-long-short' },
    ],
  },
  {
    name: 'display-trade',
    label: '交易分析',
    path: '/display/trade',
    icon: ArrowLeftRight,
    children: [
      { name: 'display-trade-advisor-overview', label: '投顾交易概况', path: '/display/trade/advisor-overview' },
      { name: 'display-sector-contract-kline', label: '合约K线', path: '/display/sector/contract-kline' },
    ],
  },
  { name: 'display-risk', label: '风险控制', path: '/display/risk', icon: ShieldCheck },
  { name: 'display-strategy', label: '策略分析', path: '/display/strategy', icon: LineChart },
]

const titleMap = {
  'display-overview': '总览',
  'display-advisor': '投顾业绩',
  'display-sector': '盈亏分析',
  'display-sector-pnl': '品种盈亏',
  'display-sector-advisor-variety': '品种投顾明细',
  'display-sector-contract-kline': '合约K线',
  'display-position': '持仓分析',
  'display-position-sector-analysis': '板块分析',
  'display-position-sector-detail': '板块持仓明细',
  'display-position-sector-overview': '板块持仓概览',
  'display-position-variety-advisor-long-short': '品种投顾多空',
  'display-trade': '交易分析',
  'display-trade-advisor-overview': '投顾交易概况',
  'display-risk': '风险控制',
  'display-strategy': '策略分析',
}

const currentTitle = computed(() => titleMap[route.name] || '分析展示')

function isActive(name) {
  return route.name === name
}

function isChildActive(module) {
  return module.children?.some((child) => child.name === route.name)
}

const now = ref('')
let timer = null
function tick() {
  now.value = new Date().toLocaleString('zh-CN', { hour12: false })
}

function closeAdvisorDropdown() {
  advisorStore.showDropdown = false
  advisorStore.hoverIdx = -1
}

function closeVarietyDropdown() {
  showVarietyDropdown.value = false
  varietyHoverIdx.value = -1
}

function onDocumentPointerDown(event) {
  const advisorCombo = advisorComboRef.value
  const varietyCombo = varietyComboRef.value
  if (advisorCombo && advisorCombo.contains(event.target)) return
  if (varietyCombo && varietyCombo.contains(event.target)) return
  closeAdvisorDropdown()
  closeVarietyDropdown()
}

async function fetchVarieties(openDropdown = false, syncCurrent = false) {
  const keyword = varietySearchText.value.trim()
  if (openDropdown && !keyword) {
    closeVarietyDropdown()
    varietyResults.value = []
    return
  }
  if (openDropdown) showVarietyDropdown.value = true
  try {
    const { data } = await client.get('/tables/sector/varieties/', {
      params: { q: keyword, limit: 20 },
    })
    varietyResults.value = data.results || []
    varietyHoverIdx.value = varietyResults.value.length ? 0 : -1
    if (syncCurrent) syncVarietySearchText()
  } catch (error) {
    console.error('获取品种列表失败', error)
    varietyResults.value = []
    varietyHoverIdx.value = -1
  }
}

function onVarietyInput() {
  if (varietySearchTimer) clearTimeout(varietySearchTimer)
  varietySearchTimer = setTimeout(() => {
    fetchVarieties(true)
  }, 250)
}

function hoverVarietyNext() {
  if (!varietyResults.value.length) return
  varietyHoverIdx.value = (varietyHoverIdx.value + 1) % varietyResults.value.length
}

function hoverVarietyPrev() {
  if (!varietyResults.value.length) return
  varietyHoverIdx.value = (varietyHoverIdx.value - 1 + varietyResults.value.length) % varietyResults.value.length
}

function confirmVarietyHover() {
  const item = varietyResults.value[varietyHoverIdx.value]
  if (item) selectVariety(item)
}

function selectVariety(item) {
  varietySearchText.value = ''
  varietyResults.value = []
  closeVarietyDropdown()
  router.push({
    name: 'display-sector-pnl',
    query: { ...route.query, variety: item.code },
  })
}

function syncVarietySearchText() {
  if (route.name === 'display-sector-pnl') varietySearchText.value = ''
}

onMounted(() => {
  tick()
  timer = setInterval(tick, 1000)
  document.addEventListener('pointerdown', onDocumentPointerDown)
})
onUnmounted(() => {
  clearInterval(timer)
  if (varietySearchTimer) clearTimeout(varietySearchTimer)
  document.removeEventListener('pointerdown', onDocumentPointerDown)
})

// 进入投顾业绩页时加载投顾列表
watch(() => route.name, (name) => {
  closeAdvisorDropdown()
  closeVarietyDropdown()
  if (name === 'display-advisor' && !advisorStore.advisors.length) {
    advisorStore.fetchAdvisors()
  }
}, { immediate: true })

watch(() => route.query.variety, () => {
  if (route.name !== 'display-sector-pnl') return
  syncVarietySearchText()
}, { immediate: true })
</script>
