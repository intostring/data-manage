<template>
  <div class="sector-pnl-page">
    <section class="d-card">
      <div class="d-card-h">
        <div>
          <span class="d-card-t">品种累计盈亏</span>
          <span class="d-card-x" style="margin-left:10px">{{ selectedVarietyName }} · {{ selectedWindowLabel }} · 各投顾累计盈亏合计</span>
        </div>
        <div class="sector-card-actions">
          <div class="sector-periods">
            <button
              v-for="item in windowOptions"
              :key="item.key"
              type="button"
              :class="{ on: selectedWindow === item.key }"
              @click="selectWindow(item.key)"
            >
              {{ item.label }}
            </button>
          </div>
          <div v-if="selectedWindow === 'custom'" class="sector-custom-range">
            <input v-model="customStartDate" type="date" />
            <span>至</span>
            <input v-model="customEndDate" type="date" />
            <button type="button" @click="applyCustomWindow">查询</button>
          </div>
          <span class="d-card-x">{{ latestDate ? `截止日期：${latestDate}` : '按交易日期汇总' }}</span>
        </div>
      </div>
      <div class="d-card-b">
        <div v-if="loading" class="sector-empty-chart">
          <Layers :size="36" :stroke-width="1.5" class="text-ink-faint" />
          <p>加载中...</p>
        </div>
        <div
          v-else-if="chartRows.length"
          class="sector-line-chart"
          @mousemove="onChartMove"
          @mouseleave="hoverIndex = null"
        >
          <div class="sector-chart-meta">
            <strong>{{ fmtMoney(latestPoint?.cumulative_pnl) }}</strong>
            <span>{{ firstDate }} 至 {{ latestDate }}</span>
          </div>
          <svg viewBox="0 0 1000 372" preserveAspectRatio="none" class="sector-svg">
            <defs>
              <linearGradient id="sectorPnlFill" x1="0" x2="0" y1="0" y2="1">
                <stop offset="0%" stop-color="#B03A2E" stop-opacity="0.22" />
                <stop offset="100%" stop-color="#B03A2E" stop-opacity="0.02" />
              </linearGradient>
            </defs>
            <g class="sector-grid">
              <line v-for="tick in yTicks" :key="tick.y" x1="56" x2="980" :y1="tick.y" :y2="tick.y" />
            </g>
            <g class="sector-axis-labels">
              <text v-for="tick in yTicks" :key="tick.label" x="48" :y="tick.y + 4" text-anchor="end">
                {{ tick.label }}
              </text>
            </g>
            <path v-if="areaPath" :d="areaPath" class="sector-area" />
            <path v-if="linePath" :d="linePath" class="sector-line" />
            <g class="sector-legend" @mousemove.stop>
              <g class="sector-legend-item" :class="{ off: !showPosition }" @click="showPosition = !showPosition">
                <rect x="56" y="228" width="10" height="10" class="sector-legend-total" />
                <text x="70" y="237" class="sector-bar-title">持仓金额</text>
              </g>
              <g class="sector-legend-item" :class="{ off: !showNet }" @click="showNet = !showNet">
                <rect x="150" y="228" width="5" height="10" class="sector-legend-net-pos" />
                <rect x="156" y="228" width="5" height="10" class="sector-legend-net-neg" />
                <text x="166" y="237" class="sector-bar-title">单边敞口（轧差）</text>
              </g>
            </g>
            <g class="sector-grid">
              <line v-for="tick in barTicks" :key="`bar-${tick.y}`" x1="56" x2="980" :y1="tick.y" :y2="tick.y" />
            </g>
            <g class="sector-axis-labels">
              <text v-for="tick in barTicks" :key="`barl-${tick.y}`" x="48" :y="tick.y + 4" text-anchor="end">
                {{ tick.label }}
              </text>
            </g>
            <g v-if="showPosition" class="sector-bars">
              <rect
                v-for="point in barPoints"
                :key="`bar-${point.date}`"
                :x="point.x - barWidth"
                :y="point.barY"
                :width="barWidth"
                :height="barZero - point.barY"
              />
            </g>
            <g v-if="showNet" class="sector-net-bars">
              <rect
                v-for="point in netBarPoints"
                :key="`net-${point.date}`"
                :x="point.x"
                :y="point.barY"
                :width="barWidth"
                :height="point.barH"
                :class="point.up ? 'pos' : 'neg'"
              />
            </g>
            <line x1="56" x2="980" :y1="barZero" :y2="barZero" class="sector-bar-zero" />
            <g v-if="hoverPoint" class="sector-hover">
              <line :x1="hoverPoint.x" :x2="hoverPoint.x" y1="18" y2="340" />
              <circle :cx="hoverPoint.x" :cy="hoverPoint.y" r="4.5" />
            </g>
            <text x="56" y="364" class="sector-x-label">{{ firstDate }}</text>
            <text x="980" y="364" text-anchor="end" class="sector-x-label">{{ latestDate }}</text>
          </svg>
          <div
            v-if="hoverPoint"
            class="sector-tooltip"
            :style="{ left: `${hoverPoint.tooltipX}px`, top: `${hoverPoint.tooltipY}px` }"
          >
            <b>{{ hoverPoint.date }}</b>
            <span>累计盈亏 <em :class="hoverPoint.cumulative_pnl >= 0 ? 'd-up' : 'd-dn'">{{ fmtMoney(hoverPoint.cumulative_pnl) }}</em></span>
            <span>当日盈亏 <em :class="hoverPoint.daily_pnl >= 0 ? 'd-up' : 'd-dn'">{{ fmtMoney(hoverPoint.daily_pnl) }}</em></span>
            <span v-if="showPosition">持仓金额 <em>{{ fmtMoney(hoverPoint.position_value) }}</em></span>
            <span v-if="showNet">单边敞口 <em :class="hoverPoint.net_position_value >= 0 ? 'd-up' : 'd-dn'">{{ fmtMoney(hoverPoint.net_position_value) }}</em></span>
            <span>投顾数量 <em>{{ hoverPoint.advisor_count || 0 }}</em></span>
          </div>
        </div>
        <div v-else class="sector-empty-chart">
          <Layers :size="36" :stroke-width="1.5" class="text-ink-faint" />
          <p>暂无品种累计盈亏数据</p>
        </div>
      </div>
    </section>

    <section class="d-card">
      <div class="d-card-h">
        <div>
          <span class="d-card-t">投顾品种交易概况</span>
          <span class="d-card-x" style="margin-left:10px">{{ selectedVarietyName }} · {{ selectedWindowLabel }} · 按交易品种成交额从高到低排序</span>
        </div>
        <button
          type="button"
          class="sector-filter-btn"
          :class="{ on: onlyHolding }"
          @click="onlyHolding = !onlyHolding"
        >
          当前有持仓
        </button>
      </div>
      <div class="sector-table-wrap">
        <table class="d-table sector-table">
          <thead>
            <tr>
              <th
                v-for="col in columns"
                :key="col.key"
                class="sector-sort-th"
                @click="toggleSort(col.key)"
              >
                <span>{{ col.label }}</span>
                <span class="sector-sort-mark" :class="{ on: sortKey === col.key }">
                  {{ sortKey === col.key ? (sortDir === 'asc' ? '↑' : '↓') : '↕' }}
                </span>
                <button
                  v-if="col.key === 'symbol_name'"
                  type="button"
                  class="sector-col-filter-btn"
                  :class="{ on: varietyFilterActive }"
                  @click.stop="varietyFilterOpen = !varietyFilterOpen"
                >
                  ▾
                </button>
                <div
                  v-if="col.key === 'symbol_name' && varietyFilterOpen"
                  class="sector-col-filter"
                  @click.stop
                >
                  <div class="sector-col-filter-actions">
                    <button type="button" @click="selectAllVarieties">全选</button>
                    <button type="button" @click="clearVarieties">清空</button>
                  </div>
                  <label
                    v-for="item in varietyOptions"
                    :key="item"
                    class="sector-col-filter-item"
                  >
                    <input v-model="selectedVarieties" type="checkbox" :value="item" @change="currentPage = 1">
                    <span>{{ item }}</span>
                  </label>
                </div>
              </th>
            </tr>
          </thead>
          <tbody v-if="loading">
            <tr>
              <td :colspan="columns.length" class="sector-empty-cell">加载中...</td>
            </tr>
          </tbody>
          <tbody v-else-if="pagedRows.length">
            <tr v-for="row in pagedRows" :key="`${row.advisor_code || row.advisor_name}-${row.symbol_code}`">
              <td>
                <router-link
                  class="sector-advisor-link"
                  :to="{
                    name: 'display-sector-advisor-variety',
                    query: { account: row.advisor_code, variety: row.symbol_code },
                  }"
                >
                  <span>{{ row.advisor_name || '—' }}</span>
                  <small v-if="row.advisor_code">（{{ row.advisor_code }}）</small>
                </router-link>
              </td>
              <td>{{ row.symbol_name || '—' }}</td>
              <td class="d-mono">{{ fmtMoney(row.profit_loss) }}</td>
              <td class="d-mono">{{ fmtMoney(row.trade_amount) }}</td>
              <td class="d-mono">{{ fmtPct(row.total_ratio) }}</td>
              <td class="d-mono">{{ fmtPct(row.profit_ratio) }}</td>
              <td class="d-mono">{{ fmtNumber(row.avg_daily_volume) }}</td>
              <td class="d-mono">{{ fmtMoney(row.avg_daily_amount) }}</td>
              <td class="d-mono">{{ fmtPct(row.intraday_trade_ratio) }}</td>
              <td class="d-mono">{{ fmtPct(row.turnover_rate) }}</td>
              <td class="d-mono">{{ fmtPct(row.win_rate) }}</td>
              <td class="d-mono">{{ fmtRatio(row.profit_loss_ratio) }}</td>
              <td class="d-mono">{{ fmtMoney(row.max_profit) }}</td>
              <td class="d-mono">{{ fmtMoney(row.max_loss) }}</td>
              <td class="d-mono">{{ fmtPlainPct(row.margin_return_rate) }}</td>
            </tr>
          </tbody>
          <tbody v-else>
            <tr>
              <td :colspan="columns.length" class="sector-empty-cell">
                {{ onlyHolding ? '暂无当前有持仓的投顾' : '暂无投顾品种交易概况数据' }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-if="filteredRows.length" class="sector-pagination">
        <div class="sector-page-size">
          <span>共 {{ filteredRows.length }} 条</span>
          <span>每页</span>
          <select v-model.number="pageSize" @change="currentPage = 1">
            <option :value="10">10 条</option>
            <option :value="20">20 条</option>
            <option :value="50">50 条</option>
          </select>
        </div>
        <div class="sector-page-actions">
          <button type="button" :disabled="currentPage === 1" @click="currentPage -= 1">上一页</button>
          <button
            v-for="page in pageNumbers"
            :key="page"
            type="button"
            :class="{ on: currentPage === page }"
            @click="currentPage = page"
          >
            {{ page }}
          </button>
          <button type="button" :disabled="currentPage === totalPages" @click="currentPage += 1">下一页</button>
        </div>
        <div class="sector-page-jump">
          <span>前往</span>
          <input v-model="jumpPage" type="number" min="1" :max="totalPages" @keydown.enter="goToPage" />
          <span>页</span>
          <button type="button" @click="goToPage">go</button>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { Layers } from 'lucide-vue-next'
import client from '../../api/client'

const route = useRoute()
const chartRows = ref([])
const detailRows = ref([])
const latestDate = ref('')
const loading = ref(false)
const hoverIndex = ref(null)
const onlyHolding = ref(false)
const showPosition = ref(true)
const showNet = ref(true)
const selectedWindow = ref('std')
const selectedVariety = ref(route.query.variety || 'LH')
const selectedVarietyName = ref('生猪')
const sortKey = ref('trade_amount')
const sortDir = ref('desc')
const currentPage = ref(1)
const pageSize = ref(200)
const jumpPage = ref('')
const varietyFilterOpen = ref(false)
const selectedVarieties = ref([])
const today = new Date()
const oneMonthAgo = new Date(today)
oneMonthAgo.setMonth(oneMonthAgo.getMonth() - 1)
const toDateInput = (date) => `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
const customStartDate = ref(toDateInput(oneMonthAgo))
const customEndDate = ref(toDateInput(today))

const windowOptions = [
  { key: 'ytd', label: '今年以来' },
  { key: '1m', label: '近1月' },
  { key: '3m', label: '近3月' },
  { key: '6m', label: '近6月' },
  { key: '1y', label: '近1年' },
  { key: 'std', label: '成立以来' },
  { key: 'custom', label: '自定义' },
]

const chartBox = {
  width: 1000,
  left: 56,
  right: 980,
  top: 18,
  bottom: 218,
}

const barBox = {
  top: 244,
  bottom: 340,
}

// 存在负敞口时零轴居中（正负各半空间），否则零轴贴底（全部空间给正值）
const hasNegativeNet = computed(() =>
  showNet.value && chartRows.value.some((row) => Number(row.net_position_value || 0) < 0),
)
const barZero = computed(() =>
  hasNegativeNet.value ? Math.round((barBox.top + barBox.bottom) / 2) : barBox.bottom,
)

const columns = [
  { key: 'advisor_name', label: '投顾名称' },
  { key: 'symbol_name', label: '品种简称' },
  { key: 'profit_loss', label: '盈亏金额' },
  { key: 'trade_amount', label: '成交额' },
  { key: 'total_ratio', label: '占总交易比例' },
  { key: 'profit_ratio', label: '占投顾总盈利比例' },
  { key: 'avg_daily_volume', label: '日均成交量' },
  { key: 'avg_daily_amount', label: '日均成交额' },
  { key: 'intraday_trade_ratio', label: '日内交易占比' },
  { key: 'turnover_rate', label: '换手率' },
  { key: 'win_rate', label: '胜率' },
  { key: 'profit_loss_ratio', label: '盈亏比' },
  { key: 'max_profit', label: '最大单笔盈利' },
  { key: 'max_loss', label: '最大单笔亏损' },
  { key: 'margin_return_rate', label: '保证金收益率' },
]

const textSortKeys = new Set(['advisor_name', 'symbol_name'])

const varietyOptions = computed(() => {
  const names = detailRows.value
    .map((row) => row.symbol_name || '—')
    .filter(Boolean)
  return [...new Set(names)].sort((a, b) => String(a).localeCompare(String(b), 'zh-CN'))
})
const varietyFilterActive = computed(() =>
  varietyOptions.value.length > 0 && selectedVarieties.value.length < varietyOptions.value.length
)

const sortedRows = computed(() => {
  const key = sortKey.value
  const dir = sortDir.value === 'asc' ? 1 : -1
  return [...detailRows.value].sort((a, b) => {
    if (textSortKeys.has(key)) {
      const av = key === 'advisor_name' ? formatAdvisorText(a) : String(a[key] || '')
      const bv = key === 'advisor_name' ? formatAdvisorText(b) : String(b[key] || '')
      return av.localeCompare(bv, 'zh-CN') * dir
    }
    const av = Number(a[key] ?? Number.NEGATIVE_INFINITY)
    const bv = Number(b[key] ?? Number.NEGATIVE_INFINITY)
    return (av - bv) * dir
  })
})

const filteredRows = computed(() => {
  const selected = new Set(selectedVarieties.value)
  const byVariety = varietyFilterActive.value
    ? sortedRows.value.filter((row) => selected.has(row.symbol_name || '—'))
    : sortedRows.value
  return onlyHolding.value ? byVariety.filter((row) => row.has_position) : byVariety
})

const totalPages = computed(() => Math.max(Math.ceil(filteredRows.value.length / pageSize.value), 1))
const pagedRows = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  return filteredRows.value.slice(start, start + pageSize.value)
})
const pageNumbers = computed(() => {
  const total = totalPages.value
  const current = currentPage.value
  const start = Math.max(1, Math.min(current - 2, total - 4))
  const end = Math.min(total, start + 4)
  return Array.from({ length: end - start + 1 }, (_, index) => start + index)
})

const firstDate = computed(() => chartRows.value[0]?.date || '')
const latestPoint = computed(() => chartRows.value[chartRows.value.length - 1] || null)
const selectedWindowLabel = computed(() =>
  selectedWindow.value === 'custom'
    ? `${customStartDate.value} 至 ${customEndDate.value}`
    : windowOptions.find((item) => item.key === selectedWindow.value)?.label || '成立以来'
)

const yDomain = computed(() => {
  const values = chartRows.value.map((row) => Number(row.cumulative_pnl || 0))
  const min = Math.min(...values, 0)
  const max = Math.max(...values, 0)
  if (min === max) return { min: min - 1, max: max + 1 }
  const pad = (max - min) * 0.12
  return { min: min - pad, max: max + pad }
})

const chartPoints = computed(() => {
  const rows = chartRows.value
  const count = rows.length
  const spanX = chartBox.right - chartBox.left
  const spanY = chartBox.bottom - chartBox.top
  const { min, max } = yDomain.value
  return rows.map((row, index) => {
    const x = chartBox.left + (count === 1 ? spanX : (index / (count - 1)) * spanX)
    const value = Number(row.cumulative_pnl || 0)
    const y = chartBox.bottom - ((value - min) / (max - min)) * spanY
    return { ...row, x, y }
  })
})

const linePath = computed(() => {
  return chartPoints.value.map((point, index) => `${index === 0 ? 'M' : 'L'} ${point.x} ${point.y}`).join(' ')
})

const areaPath = computed(() => {
  if (!chartPoints.value.length) return ''
  const points = chartPoints.value
  const zeroY = valueToY(0)
  return `${linePath.value} L ${points[points.length - 1].x} ${zeroY} L ${points[0].x} ${zeroY} Z`
})

const yTicks = computed(() => {
  const ticks = []
  const { min, max } = yDomain.value
  for (let i = 0; i < 5; i += 1) {
    const value = min + ((max - min) / 4) * i
    ticks.push({
      y: valueToY(value),
      label: fmtMoney(value),
    })
  }
  return ticks.reverse()
})

const barMax = computed(() => {
  const values = [1]
  if (showPosition.value) {
    values.push(...chartRows.value.map((row) => Number(row.position_value || 0)))
  }
  if (showNet.value) {
    values.push(...chartRows.value.map((row) => Math.abs(Number(row.net_position_value || 0))))
  }
  return Math.max(...values)
})

const barTicks = computed(() => {
  const span = barZero.value - barBox.top
  return [0, 0.5, 1].map((ratio) => ({
    y: barZero.value - span * ratio,
    label: fmtMoney(barMax.value * ratio),
  }))
})

const barPoints = computed(() =>
  chartPoints.value
    .filter((point) => Number(point.position_value || 0) > 0)
    .map((point) => ({
      date: point.date,
      x: point.x,
      barY: barValueToY(point.position_value),
    })),
)

const netBarPoints = computed(() =>
  chartPoints.value
    .filter((point) => Number(point.net_position_value || 0) !== 0)
    .map((point) => {
      const value = Number(point.net_position_value || 0)
      const magnitudeY = barValueToY(Math.abs(value))
      if (value > 0) {
        return { date: point.date, x: point.x, barY: magnitudeY, barH: barZero.value - magnitudeY, up: true }
      }
      const height = Math.min(barZero.value - magnitudeY, barBox.bottom - barZero.value)
      return { date: point.date, x: point.x, barY: barZero.value, barH: height, up: false }
    }),
)

const barWidth = computed(() =>
  Math.max(Math.min(((chartBox.right - chartBox.left) / Math.max(chartPoints.value.length, 1)) * 0.32, 8), 1.2),
)

const hoverPoint = computed(() => {
  if (hoverIndex.value == null) return null
  const point = chartPoints.value[hoverIndex.value]
  if (!point) return null
  const tooltipX = Math.min(Math.max(point.x + 10, 70), 790)
  const tooltipY = point.y < 104 ? point.y + 18 : point.y - 92
  return { ...point, tooltipX, tooltipY }
})

function valueToY(value) {
  const spanY = chartBox.bottom - chartBox.top
  const { min, max } = yDomain.value
  return chartBox.bottom - ((Number(value || 0) - min) / (max - min)) * spanY
}

function barValueToY(value) {
  const spanY = barZero.value - barBox.top
  return barZero.value - (Number(value || 0) / barMax.value) * spanY
}

function onChartMove(event) {
  const rect = event.currentTarget.getBoundingClientRect()
  const x = ((event.clientX - rect.left) / rect.width) * chartBox.width
  const spanX = chartBox.right - chartBox.left
  const count = chartRows.value.length
  if (!count) return
  const ratio = Math.min(Math.max((x - chartBox.left) / spanX, 0), 1)
  hoverIndex.value = Math.round(ratio * (count - 1))
}

function fmtNumber(value) {
  if (value == null || value === '') return '—'
  return Number(value).toLocaleString('zh-CN', { maximumFractionDigits: 2 })
}

function fmtMoney(value) {
  if (value == null || value === '') return '—'
  const n = Number(value)
  if (Math.abs(n) >= 100000000) return `${(n / 100000000).toFixed(2)}亿`
  if (Math.abs(n) >= 10000) return `${(n / 10000).toFixed(2)}万`
  return n.toLocaleString('zh-CN', { maximumFractionDigits: 2 })
}

function fmtPct(value) {
  if (value == null || value === '') return '—'
  return `${(Number(value) * 100).toFixed(2)}%`
}

function fmtPlainPct(value) {
  if (value == null || value === '') return '—'
  return `${Number(value).toFixed(2)}%`
}

function fmtRatio(value) {
  if (value == null || value === '') return '—'
  return Number(value).toFixed(2)
}

function formatAdvisorText(row) {
  const name = row.advisor_name || ''
  return row.advisor_code ? `${name}（${row.advisor_code}）` : name
}

function toggleSort(key) {
  if (sortKey.value === key) {
    sortDir.value = sortDir.value === 'asc' ? 'desc' : 'asc'
  } else {
    sortKey.value = key
    sortDir.value = textSortKeys.has(key) ? 'asc' : 'desc'
  }
  currentPage.value = 1
}

function selectAllVarieties() {
  selectedVarieties.value = [...varietyOptions.value]
  currentPage.value = 1
}

function clearVarieties() {
  selectedVarieties.value = []
  currentPage.value = 1
}

function selectWindow(key) {
  if (selectedWindow.value === key) return
  selectedWindow.value = key
  hoverIndex.value = null
  currentPage.value = 1
  fetchSectorPnl()
}

function applyCustomWindow() {
  if (selectedWindow.value !== 'custom') selectedWindow.value = 'custom'
  hoverIndex.value = null
  currentPage.value = 1
  fetchSectorPnl()
}

function goToPage() {
  const next = Number(jumpPage.value)
  if (!Number.isFinite(next)) return
  currentPage.value = Math.min(Math.max(Math.trunc(next), 1), totalPages.value)
  jumpPage.value = ''
}

async function fetchSectorPnl() {
  loading.value = true
  try {
    const params = { window: selectedWindow.value, variety: selectedVariety.value }
    if (selectedWindow.value === 'custom') {
      params.start_date = customStartDate.value
      params.end_date = customEndDate.value
    }
    const { data } = await client.get('/tables/sector/pnl/', { params })
    chartRows.value = data.chart_rows || []
    detailRows.value = data.detail_rows || []
    latestDate.value = data.latest_date || ''
    selectedVariety.value = data.variety || selectedVariety.value
    selectedVarietyName.value = data.variety_name || chartRows.value[0]?.symbol_name || detailRows.value[0]?.symbol_name || selectedVariety.value
  } catch (error) {
    console.error('获取品种盈亏数据失败', error)
    chartRows.value = []
    detailRows.value = []
    latestDate.value = ''
  } finally {
    loading.value = false
  }
}

onMounted(fetchSectorPnl)

watch(() => route.query.variety, (code) => {
  const next = code || 'LH'
  if (next === selectedVariety.value) return
  selectedVariety.value = next
  hoverIndex.value = null
  onlyHolding.value = false
  currentPage.value = 1
  fetchSectorPnl()
})

watch(onlyHolding, () => {
  currentPage.value = 1
})

watch(varietyOptions, (options) => {
  selectedVarieties.value = [...options]
  currentPage.value = 1
})

watch(totalPages, (total) => {
  if (currentPage.value > total) currentPage.value = total
})
</script>

<style scoped>
.sector-pnl-page {
  max-width: 1280px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.sector-line-chart {
  position: relative;
  min-height: 328px;
  padding-top: 4px;
}

.sector-chart-meta {
  display: flex;
  align-items: baseline;
  gap: 10px;
  margin: 0 0 6px 56px;
}

.sector-chart-meta strong {
  font-family: var(--mono);
  color: var(--ink);
  font-size: 20px;
}

.sector-chart-meta span {
  color: var(--muted);
  font-size: 12px;
}

.sector-svg {
  width: 100%;
  height: 372px;
  display: block;
  overflow: visible;
}

.sector-bar-title {
  fill: var(--muted);
  font-size: 11px;
  font-family: var(--sans);
}

.sector-legend-item {
  cursor: pointer;
  transition: opacity 0.15s ease;
}

.sector-legend-item.off {
  opacity: 0.35;
}

.sector-legend-total {
  fill: rgba(156, 107, 47, 0.55);
}

.sector-legend-net-pos {
  fill: rgba(176, 58, 46, 0.75);
}

.sector-legend-net-neg {
  fill: rgba(23, 113, 75, 0.75);
}

.sector-bars rect {
  fill: rgba(156, 107, 47, 0.55);
}

.sector-bars rect:hover {
  fill: rgba(156, 107, 47, 0.8);
}

.sector-net-bars rect.pos {
  fill: rgba(176, 58, 46, 0.75);
}

.sector-net-bars rect.neg {
  fill: rgba(23, 113, 75, 0.75);
}

.sector-net-bars rect:hover {
  opacity: 0.85;
}

.sector-bar-zero {
  stroke: rgba(18, 36, 56, 0.3);
  stroke-width: 1;
  vector-effect: non-scaling-stroke;
}

.sector-grid line {
  stroke: rgba(18, 36, 56, 0.1);
  stroke-dasharray: 4 4;
}

.sector-axis-labels text,
.sector-x-label {
  fill: var(--muted);
  font-size: 11px;
  font-family: var(--mono);
}

.sector-area {
  fill: url(#sectorPnlFill);
}

.sector-line {
  fill: none;
  stroke: #B03A2E;
  stroke-width: 2.4;
  vector-effect: non-scaling-stroke;
}

.sector-hover line {
  stroke: rgba(18, 36, 56, 0.22);
  stroke-dasharray: 4 4;
  vector-effect: non-scaling-stroke;
}

.sector-hover circle {
  fill: #fff;
  stroke: #B03A2E;
  stroke-width: 2;
  vector-effect: non-scaling-stroke;
}

.sector-tooltip {
  position: absolute;
  z-index: 3;
  min-width: 170px;
  padding: 10px 12px;
  border-radius: 6px;
  background: rgba(33, 42, 52, 0.9);
  color: #fff;
  box-shadow: 0 8px 22px rgba(22, 34, 48, 0.2);
  pointer-events: none;
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.sector-tooltip b {
  font-size: 12px;
}

.sector-tooltip span {
  display: flex;
  justify-content: space-between;
  gap: 14px;
  color: rgba(255, 255, 255, 0.82);
  font-size: 12px;
}

.sector-tooltip em {
  font-style: normal;
  color: #fff;
  font-family: var(--mono);
}

.sector-card-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 14px;
  min-width: 0;
}

.sector-periods {
  display: flex;
  align-items: center;
  border: 1px solid var(--line);
  border-radius: 4px;
  background: #FBF9F3;
  overflow: hidden;
}

.sector-periods button {
  height: 26px;
  padding: 0 12px;
  border: 0;
  border-radius: 0;
  background: none;
  color: var(--muted);
  font-size: 12px;
  font-family: var(--sans);
  cursor: pointer;
  white-space: nowrap;
}

.sector-periods button:hover {
  color: var(--ink);
}

.sector-periods button.on {
  background: var(--navy);
  color: #F2EDE0;
  box-shadow: none;
}

.sector-custom-range {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--muted);
  font-size: 12px;
}

.sector-custom-range input {
  height: 26px;
  width: 130px;
  border: 1px solid var(--line);
  border-radius: 4px;
  background: var(--card);
  color: var(--ink);
  font-family: var(--mono);
  font-size: 11px;
  padding: 0 8px;
}

.sector-custom-range button {
  height: 26px;
  padding: 0 12px;
  border: 1px solid var(--line);
  border-radius: 4px;
  background: var(--card);
  color: var(--muted);
  font-size: 12px;
  cursor: pointer;
}

.sector-custom-range button:hover {
  border-color: var(--brass);
  color: var(--brass);
}

.sector-filter-btn {
  height: 30px;
  padding: 0 12px;
  border: 1px solid var(--line);
  border-radius: 6px;
  background: var(--surface);
  color: var(--muted);
  font-size: 12px;
  cursor: pointer;
  transition: border-color 0.15s ease, color 0.15s ease, background 0.15s ease;
}

.sector-filter-btn:hover {
  border-color: var(--brand);
  color: var(--brand);
}

.sector-filter-btn.on {
  border-color: var(--brand);
  background: rgba(176, 58, 46, 0.08);
  color: var(--brand);
}

.sector-empty-chart {
  min-height: 260px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  align-items: center;
  justify-content: center;
  color: var(--muted);
}

.sector-empty-chart p {
  font-size: 13px;
}

.sector-table-wrap {
  overflow: auto;
  max-height: 460px;
  position: relative;
}

.sector-table {
  table-layout: fixed;
  min-width: 1180px;
}

.sector-table th,
.sector-table td {
  white-space: nowrap;
  text-align: center;
}

.sector-table th:first-child,
.sector-table td:first-child {
  width: 170px;
  max-width: 170px;
}

.sector-advisor-link {
  display: inline-flex;
  align-items: baseline;
  justify-content: center;
  gap: 2px;
  max-width: 100%;
  overflow: hidden;
  vertical-align: middle;
  color: var(--ink);
  text-decoration: none;
}

.sector-advisor-link:hover {
  color: var(--brass);
}

.sector-advisor-link span {
  flex: 0 1 auto;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
}

.sector-advisor-link small {
  flex: 0 1 auto;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  color: var(--muted);
  font-family: var(--mono);
  font-size: 10px;
}

.sector-table th {
  position: sticky;
  top: 0;
  z-index: 5;
  background: var(--card);
  box-shadow: 0 1px 0 var(--line), 0 8px 10px rgba(245, 242, 234, 0.96);
}

.sector-sort-th {
  position: relative;
  cursor: pointer;
  user-select: none;
}

.sector-sort-th span:first-child {
  vertical-align: middle;
}

.sector-sort-mark {
  display: inline-block;
  width: 12px;
  margin-left: 3px;
  color: #C9C2AE;
  font-size: 10px;
  vertical-align: middle;
}

.sector-sort-mark.on {
  color: var(--brass);
}

.sector-col-filter-btn {
  width: 18px;
  height: 18px;
  margin-left: 4px;
  border: 1px solid var(--line);
  border-radius: 3px;
  background: #F7F4EC;
  color: var(--muted);
  font-size: 11px;
  line-height: 1;
  cursor: pointer;
  vertical-align: middle;
}

.sector-col-filter-btn.on {
  border-color: var(--brass);
  color: var(--brass);
  background: rgba(151, 121, 62, 0.12);
}

.sector-col-filter {
  position: absolute;
  top: calc(100% + 4px);
  left: 50%;
  z-index: 30;
  width: 190px;
  max-height: 260px;
  padding: 8px;
  overflow-y: auto;
  transform: translateX(-50%);
  border: 1px solid var(--line);
  border-radius: 4px;
  background: var(--card);
  box-shadow: 0 10px 24px rgba(28, 34, 40, 0.14);
  color: var(--ink);
  text-align: left;
  cursor: default;
}

.sector-col-filter-actions {
  display: flex;
  gap: 6px;
  padding-bottom: 6px;
  margin-bottom: 6px;
  border-bottom: 1px solid var(--line);
}

.sector-col-filter-actions button {
  flex: 1;
  height: 26px;
  border: 1px solid var(--line);
  border-radius: 3px;
  background: #F7F4EC;
  color: var(--ink);
  font-size: 12px;
  cursor: pointer;
}

.sector-col-filter-item {
  display: flex;
  align-items: center;
  gap: 7px;
  height: 28px;
  padding: 0 4px;
  border-radius: 3px;
  color: var(--ink);
  font-size: 12px;
  font-weight: 400;
  cursor: pointer;
}

.sector-col-filter-item:hover {
  background: #F7F4EC;
}

.sector-col-filter-item input {
  margin: 0;
}

.sector-table td:nth-child(n+4) {
  text-align: center;
}

.sector-empty-cell {
  text-align: center;
  color: var(--muted);
  padding: 42px 12px;
}

.sector-pagination {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
  gap: 12px;
  padding: 10px 18px 14px;
  border-top: 1px solid var(--line2);
  color: var(--muted);
  font-size: 12px;
}

.sector-page-size,
.sector-page-jump {
  display: flex;
  align-items: center;
  gap: 8px;
}

.sector-page-jump {
  justify-content: flex-end;
}

.sector-page-size select,
.sector-page-jump input {
  height: 32px;
  border: 1px solid var(--line);
  border-radius: 7px;
  background: var(--card);
  color: var(--ink);
  font-size: 12px;
}

.sector-page-size select {
  padding: 0 26px 0 10px;
}

.sector-page-jump input {
  width: 64px;
  padding: 0 8px;
  text-align: center;
}

.sector-page-actions {
  display: flex;
  align-items: center;
  gap: 6px;
}

.sector-page-actions button,
.sector-page-jump button {
  min-width: 30px;
  height: 32px;
  padding: 0 9px;
  border: 1px solid var(--line);
  border-radius: 7px;
  background: var(--card);
  color: var(--muted);
  font-size: 12px;
  cursor: pointer;
}

.sector-page-actions button:hover:not(:disabled),
.sector-page-jump button:hover {
  border-color: var(--brass);
  color: var(--brass);
}

.sector-page-actions button.on {
  border-color: var(--navy);
  background: var(--navy);
  color: #F2EDE0;
}

.sector-page-actions button:disabled {
  cursor: not-allowed;
  opacity: 0.45;
}

@media (max-width: 900px) {
  .sector-card-actions {
    align-items: flex-end;
    flex-direction: column;
    gap: 8px;
  }

  .sector-periods {
    flex-wrap: wrap;
    justify-content: flex-end;
  }

  .sector-custom-range {
    flex-wrap: wrap;
    justify-content: flex-end;
  }

  .sector-pagination {
    grid-template-columns: 1fr;
  }

  .sector-page-actions,
  .sector-page-jump {
    justify-content: flex-start;
  }
}
</style>
