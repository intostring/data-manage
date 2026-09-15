<template>
  <div class="advisor-variety-page">
    <section class="d-card">
      <div class="d-card-h">
        <div>
          <span class="d-card-t">投顾品种累计盈亏</span>
          <span class="d-card-x" style="margin-left:10px">
            {{ advisorName }} · {{ varietyName }} · 单投顾累计盈亏
          </span>
        </div>
        <div class="av-query">
          <input v-model="queryAccount" class="d-ipt" placeholder="投顾代码/名称" />
          <input v-model="queryVariety" class="d-ipt" placeholder="品种代码/简称" />
          <button type="button" class="d-btn" @click="applyQuery">查询</button>
        </div>
      </div>
      <div class="d-card-b">
        <div v-if="loading" class="av-empty">加载中...</div>
        <div
          v-else-if="chartRows.length"
          class="av-chart"
          @mousemove="onChartMove"
          @mouseleave="hoverIndex = null"
        >
          <div class="av-chart-meta">
            <strong>{{ fmtMoney(latestPoint?.cumulative_pnl) }}</strong>
            <span>{{ firstDate }} 至 {{ latestDate }}</span>
          </div>
          <svg viewBox="0 0 1000 372" preserveAspectRatio="none" class="av-svg">
            <defs>
              <linearGradient id="advisorVarietyFill" x1="0" x2="0" y1="0" y2="1">
                <stop offset="0%" stop-color="#B03A2E" stop-opacity="0.22" />
                <stop offset="100%" stop-color="#B03A2E" stop-opacity="0.02" />
              </linearGradient>
            </defs>
            <g class="av-grid">
              <line v-for="tick in yTicks" :key="tick.y" x1="56" x2="980" :y1="tick.y" :y2="tick.y" />
            </g>
            <g class="av-axis-labels">
              <text v-for="tick in yTicks" :key="tick.label" x="48" :y="tick.y + 4" text-anchor="end">
                {{ tick.label }}
              </text>
            </g>
            <path v-if="areaPath" :d="areaPath" class="av-area" />
            <path v-if="linePath" :d="linePath" class="av-line" />
            <g class="av-legend" @mousemove.stop>
              <g class="av-legend-item" :class="{ off: !showPosition }" @click="showPosition = !showPosition">
                <rect x="56" y="228" width="10" height="10" class="av-legend-total" />
                <text x="70" y="237" class="av-bar-title">持仓金额</text>
              </g>
              <g class="av-legend-item" :class="{ off: !showNet }" @click="showNet = !showNet">
                <rect x="150" y="228" width="5" height="10" class="av-legend-net-pos" />
                <rect x="156" y="228" width="5" height="10" class="av-legend-net-neg" />
                <text x="166" y="237" class="av-bar-title">单边敞口（轧差）</text>
              </g>
            </g>
            <g class="av-grid">
              <line v-for="tick in barTicks" :key="`bar-${tick.y}`" x1="56" x2="980" :y1="tick.y" :y2="tick.y" />
            </g>
            <g class="av-axis-labels">
              <text v-for="tick in barTicks" :key="`barl-${tick.y}`" x="48" :y="tick.y + 4" text-anchor="end">
                {{ tick.label }}
              </text>
            </g>
            <g v-if="showPosition" class="av-bars">
              <rect
                v-for="point in barPoints"
                :key="`bar-${point.date}`"
                :x="point.x - barWidth"
                :y="point.barY"
                :width="barWidth"
                :height="barZero - point.barY"
              />
            </g>
            <g v-if="showNet" class="av-net-bars">
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
            <line x1="56" x2="980" :y1="barZero" :y2="barZero" class="av-bar-zero" />
            <g v-if="hoverPoint" class="av-hover">
              <line :x1="hoverPoint.x" :x2="hoverPoint.x" y1="18" y2="340" />
              <circle :cx="hoverPoint.x" :cy="hoverPoint.y" r="4.5" />
            </g>
            <text x="56" y="364" class="av-x-label">{{ firstDate }}</text>
            <text x="980" y="364" text-anchor="end" class="av-x-label">{{ latestDate }}</text>
          </svg>
          <div
            v-if="hoverPoint"
            class="av-tooltip"
            :style="{ left: `${hoverPoint.tooltipX}px`, top: `${hoverPoint.tooltipY}px` }"
          >
            <b>{{ hoverPoint.date }}</b>
            <span>累计盈亏 <em :class="hoverPoint.cumulative_pnl >= 0 ? 'd-up' : 'd-dn'">{{ fmtMoney(hoverPoint.cumulative_pnl) }}</em></span>
            <span>当日盈亏 <em :class="hoverPoint.daily_pnl >= 0 ? 'd-up' : 'd-dn'">{{ fmtMoney(hoverPoint.daily_pnl) }}</em></span>
            <span v-if="showPosition">持仓金额 <em>{{ fmtMoney(hoverPoint.position_value) }}</em></span>
            <span v-if="showNet">单边敞口 <em :class="hoverPoint.net_position_value >= 0 ? 'd-up' : 'd-dn'">{{ fmtMoney(hoverPoint.net_position_value) }}</em></span>
          </div>
        </div>
        <div v-else class="av-empty">暂无该投顾品种累计盈亏数据</div>
      </div>
    </section>

    <section class="d-card">
      <div class="d-card-h">
        <div>
          <span class="d-card-t">投顾品种成交记录</span>
          <span class="d-card-x" style="margin-left:10px">{{ advisorName }} · {{ varietyName }} · 按成交时间倒序</span>
        </div>
      </div>
      <div class="av-table-wrap">
        <table class="d-table av-table">
          <thead>
            <tr>
              <th v-for="col in tradeColumns" :key="col.key">{{ col.label }}</th>
            </tr>
          </thead>
          <tbody v-if="loading">
            <tr><td :colspan="tradeColumns.length" class="av-empty-cell">加载中...</td></tr>
          </tbody>
          <tbody v-else-if="tradeRows.length">
            <tr v-for="row in tradeRows" :key="`${row.trade_date}-${row.trade_time}-${row.contract}-${row.trade_amount}`">
              <td class="d-mono">{{ row.trade_date || '—' }}</td>
              <td class="d-mono">{{ row.trade_time || '—' }}</td>
              <td class="d-mono">
                <router-link
                  v-if="row.contract"
                  class="av-contract-link"
                  :to="{ name: 'display-sector-contract-kline', query: { contract: row.contract, account: row.account } }"
                >
                  {{ row.contract }}
                </router-link>
                <span v-else>—</span>
              </td>
              <td>{{ row.side || '—' }}</td>
              <td>{{ row.open_close || '—' }}</td>
              <td class="d-mono">{{ fmtNumber(row.trade_price) }}</td>
              <td class="d-mono">{{ fmtNumber(row.trade_qty) }}</td>
              <td class="d-mono">{{ fmtMoney(row.trade_amount) }}</td>
              <td class="d-mono">{{ fmtMoney(row.fee) }}</td>
              <td class="d-mono">{{ fmtMoney(row.close_profit) }}</td>
              <td class="d-mono">{{ fmtMoney(row.daily_close_profit) }}</td>
            </tr>
          </tbody>
          <tbody v-else>
            <tr><td :colspan="tradeColumns.length" class="av-empty-cell">暂无成交记录</td></tr>
          </tbody>
        </table>
      </div>
      <div v-if="tradeCount" class="av-pagination">
        <div class="av-page-size">
          <span>共 {{ tradeCount }} 条</span>
          <span>每页</span>
          <select v-model.number="tradePageSize" @change="changeTradePage(1)">
            <option :value="10">10 条</option>
            <option :value="20">20 条</option>
            <option :value="50">50 条</option>
          </select>
        </div>
        <div class="av-page-actions">
          <button type="button" :disabled="tradePage === 1" @click="changeTradePage(tradePage - 1)">上一页</button>
          <button
            v-for="page in tradePageNumbers"
            :key="page"
            type="button"
            :class="{ on: tradePage === page }"
            @click="changeTradePage(page)"
          >
            {{ page }}
          </button>
          <button type="button" :disabled="tradePage === totalTradePages" @click="changeTradePage(tradePage + 1)">下一页</button>
        </div>
        <div class="av-page-jump">
          <span>前往</span>
          <input v-model="tradeJumpPage" type="number" min="1" :max="totalTradePages" @keydown.enter="goToTradePage" />
          <span>页</span>
          <button type="button" @click="goToTradePage">go</button>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import client from '../../api/client'

const route = useRoute()
const router = useRouter()
const loading = ref(false)
const account = ref(route.query.account || '250528_HG')
const variety = ref(route.query.variety || 'LH')
const queryAccount = ref(account.value)
const queryVariety = ref(variety.value)
const advisorName = ref(account.value)
const varietyName = ref('生猪')
const latestDate = ref('')
const chartRows = ref([])
const tradeRows = ref([])
const tradeCount = ref(0)
const tradePage = ref(Number(route.query.trade_page || 1))
const tradePageSize = ref(Number(route.query.trade_page_size || 20))
const tradeJumpPage = ref('')
const hoverIndex = ref(null)
const showPosition = ref(true)
const showNet = ref(true)

const chartBox = { width: 1000, left: 56, right: 980, top: 18, bottom: 218 }
const barBox = { top: 244, bottom: 340 }

// 存在负敞口时零轴居中（正负各半空间），否则零轴贴底（全部空间给正值）
const hasNegativeNet = computed(() =>
  showNet.value && chartRows.value.some((row) => Number(row.net_position_value || 0) < 0),
)
const barZero = computed(() =>
  hasNegativeNet.value ? Math.round((barBox.top + barBox.bottom) / 2) : barBox.bottom,
)
const tradeColumns = [
  { key: 'trade_date', label: '成交日期' },
  { key: 'trade_time', label: '成交时间' },
  { key: 'contract', label: '合约' },
  { key: 'side', label: '买卖' },
  { key: 'open_close', label: '开平' },
  { key: 'trade_price', label: '成交价' },
  { key: 'trade_qty', label: '成交量' },
  { key: 'trade_amount', label: '成交额' },
  { key: 'fee', label: '手续费' },
  { key: 'close_profit', label: '平仓盈亏' },
  { key: 'daily_close_profit', label: '逐日平仓盈亏' },
]

const firstDate = computed(() => chartRows.value[0]?.date || '')
const latestPoint = computed(() => chartRows.value[chartRows.value.length - 1] || null)
const totalTradePages = computed(() => Math.max(Math.ceil(tradeCount.value / tradePageSize.value), 1))
const tradePageNumbers = computed(() => {
  const total = totalTradePages.value
  const current = tradePage.value
  const start = Math.max(1, Math.min(current - 2, total - 4))
  const end = Math.min(total, start + 4)
  return Array.from({ length: end - start + 1 }, (_, index) => start + index)
})

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

const linePath = computed(() => chartPoints.value.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`).join(' '))
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
    ticks.push({ y: valueToY(value), label: fmtMoney(value) })
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
  return {
    ...point,
    tooltipX: Math.min(Math.max(point.x + 10, 70), 790),
    tooltipY: point.y < 104 ? point.y + 18 : point.y - 82,
  }
})

function valueToY(value) {
  const { min, max } = yDomain.value
  return chartBox.bottom - ((Number(value || 0) - min) / (max - min)) * (chartBox.bottom - chartBox.top)
}

function barValueToY(value) {
  const spanY = barZero.value - barBox.top
  return barZero.value - (Number(value || 0) / barMax.value) * spanY
}

function onChartMove(event) {
  const rect = event.currentTarget.getBoundingClientRect()
  const x = ((event.clientX - rect.left) / rect.width) * chartBox.width
  const ratio = Math.min(Math.max((x - chartBox.left) / (chartBox.right - chartBox.left), 0), 1)
  hoverIndex.value = Math.round(ratio * (chartRows.value.length - 1))
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

function applyQuery() {
  tradePage.value = 1
  router.push({
    name: 'display-sector-advisor-variety',
    query: { account: queryAccount.value.trim(), variety: queryVariety.value.trim() },
  })
}

function changeTradePage(page) {
  tradePage.value = Math.min(Math.max(page, 1), totalTradePages.value)
  loadData()
}

function goToTradePage() {
  const next = Number(tradeJumpPage.value)
  if (!Number.isFinite(next)) return
  changeTradePage(Math.trunc(next))
  tradeJumpPage.value = ''
}

async function loadData() {
  loading.value = true
  try {
    const { data } = await client.get('/tables/sector/advisor-variety/', {
      params: {
        account: account.value,
        variety: variety.value,
        trade_page: tradePage.value,
        trade_page_size: tradePageSize.value,
      },
    })
    advisorName.value = data.advisor_name || account.value
    varietyName.value = data.variety_name || variety.value
    latestDate.value = data.latest_date || ''
    chartRows.value = data.chart_rows || []
    tradeRows.value = data.trade_rows || []
    tradeCount.value = data.trade_count || 0
    account.value = data.account || account.value
    variety.value = data.variety || variety.value
  } catch (error) {
    console.error('获取投顾品种明细失败', error)
    chartRows.value = []
    tradeRows.value = []
    tradeCount.value = 0
  } finally {
    loading.value = false
  }
}

watch(() => route.query, (query) => {
  account.value = query.account || '250528_HG'
  variety.value = query.variety || 'LH'
  queryAccount.value = account.value
  queryVariety.value = variety.value
  tradePage.value = Number(query.trade_page || 1)
  tradePageSize.value = Number(query.trade_page_size || tradePageSize.value || 20)
  hoverIndex.value = null
  loadData()
}, { immediate: true })

onMounted(() => {
  if (!route.query.account || !route.query.variety) {
    router.replace({ name: 'display-sector-advisor-variety', query: { account: account.value, variety: variety.value } })
  }
})
</script>

<style scoped>
.advisor-variety-page {
  max-width: 1280px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.av-query {
  display: flex;
  align-items: center;
  gap: 8px;
}

.av-query .d-ipt {
  width: 132px;
  font-size: 12px;
}

.av-chart {
  position: relative;
  min-height: 318px;
}

.av-chart-meta {
  display: flex;
  align-items: baseline;
  gap: 10px;
  margin: 0 0 6px 56px;
}

.av-chart-meta strong {
  font-family: var(--mono);
  color: var(--ink);
  font-size: 20px;
}

.av-chart-meta span,
.av-x-label,
.av-axis-labels text {
  fill: var(--muted);
  color: var(--muted);
  font-family: var(--mono);
  font-size: 11px;
}

.av-svg {
  width: 100%;
  height: 372px;
  display: block;
  overflow: visible;
}

.av-bar-title {
  fill: var(--muted);
  font-size: 11px;
  font-family: var(--sans);
}

.av-legend-item {
  cursor: pointer;
  transition: opacity 0.15s ease;
}

.av-legend-item.off {
  opacity: 0.35;
}

.av-legend-total {
  fill: rgba(156, 107, 47, 0.55);
}

.av-legend-net-pos {
  fill: rgba(176, 58, 46, 0.75);
}

.av-legend-net-neg {
  fill: rgba(23, 113, 75, 0.75);
}

.av-bars rect {
  fill: rgba(156, 107, 47, 0.55);
}

.av-bars rect:hover {
  fill: rgba(156, 107, 47, 0.8);
}

.av-net-bars rect.pos {
  fill: rgba(176, 58, 46, 0.75);
}

.av-net-bars rect.neg {
  fill: rgba(23, 113, 75, 0.75);
}

.av-net-bars rect:hover {
  opacity: 0.85;
}

.av-bar-zero {
  stroke: rgba(18, 36, 56, 0.3);
  stroke-width: 1;
  vector-effect: non-scaling-stroke;
}

.av-grid line {
  stroke: rgba(18, 36, 56, 0.1);
  stroke-dasharray: 4 4;
}

.av-area {
  fill: url(#advisorVarietyFill);
}

.av-line {
  fill: none;
  stroke: #B03A2E;
  stroke-width: 2.4;
  vector-effect: non-scaling-stroke;
}

.av-hover line {
  stroke: rgba(18, 36, 56, 0.22);
  stroke-dasharray: 4 4;
  vector-effect: non-scaling-stroke;
}

.av-hover circle {
  fill: #fff;
  stroke: #B03A2E;
  stroke-width: 2;
  vector-effect: non-scaling-stroke;
}

.av-tooltip {
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

.av-tooltip span {
  display: flex;
  justify-content: space-between;
  gap: 14px;
  color: rgba(255, 255, 255, 0.82);
  font-size: 12px;
}

.av-tooltip em {
  font-style: normal;
  color: #fff;
  font-family: var(--mono);
}

.av-empty {
  min-height: 260px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--muted);
}

.av-table-wrap {
  overflow: auto;
  max-height: 520px;
  position: relative;
}

.av-table {
  table-layout: fixed;
  min-width: 1120px;
}

.av-table th,
.av-table td {
  text-align: center;
  white-space: nowrap;
}

.av-table th {
  position: sticky;
  top: 0;
  z-index: 5;
  background: var(--card);
  box-shadow: 0 1px 0 var(--line), 0 8px 10px rgba(245, 242, 234, 0.96);
}

.av-contract-link {
  color: var(--ink);
  text-decoration: none;
}

.av-contract-link:hover {
  color: var(--brass);
}

.av-empty-cell {
  text-align: center;
  color: var(--muted);
  padding: 42px 12px;
}

.av-pagination {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
  gap: 12px;
  padding: 10px 18px 14px;
  border-top: 1px solid var(--line2);
  color: var(--muted);
  font-size: 12px;
}

.av-page-size,
.av-page-jump {
  display: flex;
  align-items: center;
  gap: 8px;
}

.av-page-jump {
  justify-content: flex-end;
}

.av-page-size select,
.av-page-jump input {
  height: 32px;
  border: 1px solid var(--line);
  border-radius: 7px;
  background: var(--card);
  color: var(--ink);
  font-size: 12px;
}

.av-page-size select {
  padding: 0 26px 0 10px;
}

.av-page-jump input {
  width: 64px;
  padding: 0 8px;
  text-align: center;
}

.av-page-actions {
  display: flex;
  align-items: center;
  gap: 6px;
}

.av-page-actions button,
.av-page-jump button {
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

.av-page-actions button:hover:not(:disabled),
.av-page-jump button:hover {
  border-color: var(--brass);
  color: var(--brass);
}

.av-page-actions button.on {
  border-color: var(--navy);
  background: var(--navy);
  color: #F2EDE0;
}

.av-page-actions button:disabled {
  cursor: not-allowed;
  opacity: 0.45;
}

@media (max-width: 900px) {
  .av-pagination {
    grid-template-columns: 1fr;
  }

  .av-page-actions,
  .av-page-jump {
    justify-content: flex-start;
  }
}
</style>
