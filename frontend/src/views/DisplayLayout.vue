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
        <router-link
          v-for="(m, i) in modules"
          :key="m.name"
          :to="m.path"
          class="d-nav-it"
          :class="isActive(m.name) ? 'on' : ''"
        >
          <span class="no">{{ String(i + 1).padStart(2, '0') }}</span>
          <component :is="m.icon" :size="14" :stroke-width="1.75" />
          <span>{{ m.label }}</span>
        </router-link>
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
        <div v-if="route.name === 'display-advisor'" class="d-combo" style="position:relative;width:240px;margin-right:12px">
          <input
            v-model="advisorStore.searchText"
            class="d-ipt"
            style="width:100%;font-size:12px;padding:4px 8px"
            placeholder="输入投顾名称、代码或ID搜索…"
            @focus="advisorStore.showDropdown = true"
            @blur="setTimeout(() => advisorStore.showDropdown = false, 150)"
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
import { useRoute } from 'vue-router'
import {
  LayoutDashboard,
  TrendingUp,
  PieChart,
  ArrowLeftRight,
  ShieldCheck,
  LineChart,
} from 'lucide-vue-next'
import { useAdvisorStore } from '../stores/advisor'
import '../styles/display.css'

const route = useRoute()
const advisorStore = useAdvisorStore()
const isAdmin = computed(() => route.path.startsWith('/admin'))

const modules = [
  { name: 'display-overview', label: '总览', path: '/display/overview', icon: LayoutDashboard },
  { name: 'display-advisor', label: '投顾业绩', path: '/display/advisor', icon: TrendingUp },
  { name: 'display-position', label: '持仓分析', path: '/display/position', icon: PieChart },
  { name: 'display-trade', label: '交易分析', path: '/display/trade', icon: ArrowLeftRight },
  { name: 'display-risk', label: '风险控制', path: '/display/risk', icon: ShieldCheck },
  { name: 'display-strategy', label: '策略分析', path: '/display/strategy', icon: LineChart },
]

const titleMap = {
  'display-overview': '总览',
  'display-advisor': '投顾业绩',
  'display-position': '持仓分析',
  'display-trade': '交易分析',
  'display-risk': '风险控制',
  'display-strategy': '策略分析',
}

const currentTitle = computed(() => titleMap[route.name] || '分析展示')

function isActive(name) {
  return route.name === name
}

const now = ref('')
let timer = null
function tick() {
  now.value = new Date().toLocaleString('zh-CN', { hour12: false })
}
onMounted(() => {
  tick()
  timer = setInterval(tick, 1000)
})
onUnmounted(() => clearInterval(timer))

// 进入投顾业绩页时加载投顾列表
watch(() => route.name, (name) => {
  if (name === 'display-advisor' && !advisorStore.advisors.length) {
    advisorStore.fetchAdvisors()
  }
}, { immediate: true })
</script>
