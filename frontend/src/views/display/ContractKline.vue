<template>
  <div class="contract-kline-page">
    <section class="d-card">
      <div class="d-card-h">
        <div>
          <span class="d-card-t">合约K线图</span>
          <span class="d-card-x" style="margin-left:10px">{{ advisorLabel }} · {{ tsCode }} · {{ selectedWindowLabel }}</span>
        </div>
        <div class="ck-head-actions">
          <div class="ck-periods">
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
          <div class="ck-query">
            <input v-model="queryContract" class="d-ipt" placeholder="合约代码" @keydown.enter="applyQuery" />
            <input v-model="queryAccount" class="d-ipt" placeholder="投顾代码" @keydown.enter="applyQuery" />
            <button type="button" class="d-btn" @click="applyQuery">查询</button>
          </div>
        </div>
      </div>
      <div v-if="selectedWindow === 'custom'" class="ck-custom-row">
        <input v-model="customStartDate" type="date" />
        <span>至</span>
        <input v-model="customEndDate" type="date" />
        <button type="button" @click="applyCustomWindow">查询</button>
      </div>
      <div class="d-card-b">
        <div v-if="loading" class="ck-empty">加载中...</div>
        <div
          v-else-if="rows.length"
          class="ck-chart"
          @mousemove="onChartMove"
          @mouseleave="hoverIndex = null"
        >
          <div class="ck-meta">
            <strong>{{ fmtNumber(latestPoint?.close) }}</strong>
            <span>{{ firstDate }} 至 {{ lastDate }} · {{ rows.length }} 根K线</span>
          </div>
          <svg viewBox="0 0 1000 420" preserveAspectRatio="none" class="ck-svg">
            <g class="ck-grid">
              <line v-for="tick in priceTicks" :key="tick.y" x1="58" x2="980" :y1="tick.y" :y2="tick.y" />
            </g>
            <g class="ck-axis-labels">
              <text v-for="tick in priceTicks" :key="tick.label" x="50" :y="tick.y + 4" text-anchor="end">{{ tick.label }}</text>
            </g>
            <g>
              <g v-for="candle in candles" :key="candle.date">
                <line
                  :x1="candle.x"
                  :x2="candle.x"
                  :y1="candle.highY"
                  :y2="candle.lowY"
                  :class="candle.up ? 'ck-up-stroke' : 'ck-dn-stroke'"
                />
                <rect
                  :x="candle.x - candleWidth / 2"
                  :y="Math.min(candle.openY, candle.closeY)"
                  :width="candleWidth"
                  :height="Math.max(Math.abs(candle.openY - candle.closeY), 1)"
                  :class="candle.up ? 'ck-up-fill' : 'ck-dn-fill'"
                />
                <rect
                  :x="candle.x - candleWidth / 2"
                  :y="volumeY(candle.vol)"
                  :width="candleWidth"
                  :height="390 - volumeY(candle.vol)"
                  :class="candle.up ? 'ck-up-vol' : 'ck-dn-vol'"
                />
              </g>
            </g>
            <g class="ck-markers">
              <g
                v-for="marker in tradeMarkers"
                :key="`${marker.date}-${marker.side}-${marker.open_close}`"
                class="ck-marker"
                :transform="`translate(${marker.x}, ${marker.y})`"
              >
                <circle r="6" :class="marker.sideClass" />
                <text y="-9" text-anchor="middle">{{ marker.label }}</text>
                <title>{{ marker.title }}</title>
              </g>
            </g>
            <g v-if="hoverPoint" class="ck-hover">
              <line :x1="hoverPoint.x" :x2="hoverPoint.x" y1="18" y2="390" />
            </g>
            <text x="58" y="414" class="ck-x-label">{{ firstDate }}</text>
            <text x="980" y="414" text-anchor="end" class="ck-x-label">{{ lastDate }}</text>
          </svg>
          <div class="ck-range" @mousemove.stop @mousedown.stop>
            <div class="ck-range-labels">
              <span>{{ sliderStartDate }}</span>
              <span>{{ sliderEndDate }}</span>
            </div>
            <div class="ck-range-track">
              <div class="ck-range-fill" :style="rangeFillStyle"></div>
              <input
                v-model.number="sliderStart"
                type="range"
                :min="0"
                :max="sliderMax"
                :disabled="sliderMax <= 0"
                @input="handleSliderStart"
              />
              <input
                v-model.number="sliderEnd"
                type="range"
                :min="0"
                :max="sliderMax"
                :disabled="sliderMax <= 0"
                @input="handleSliderEnd"
              />
            </div>
          </div>
          <div
            v-if="hoverPoint"
            class="ck-tooltip"
            :style="{ left: `${hoverPoint.tooltipX}px`, top: `${hoverPoint.tooltipY}px` }"
          >
            <b>{{ hoverPoint.date }}</b>
            <span>开 <em>{{ fmtNumber(hoverPoint.open) }}</em></span>
            <span>高 <em>{{ fmtNumber(hoverPoint.high) }}</em></span>
            <span>低 <em>{{ fmtNumber(hoverPoint.low) }}</em></span>
            <span>收 <em>{{ fmtNumber(hoverPoint.close) }}</em></span>
            <span>成交量 <em>{{ fmtNumber(hoverPoint.vol) }}</em></span>
            <span>持仓量 <em>{{ fmtNumber(hoverPoint.oi) }}</em></span>
          </div>
        </div>
        <div v-else class="ck-empty">暂无该合约K线数据</div>
      </div>
    </section>

    <section class="d-card ck-trades-card">
      <div class="d-card-h">
        <div>
          <span class="d-card-t">合约成交明细</span>
          <span class="d-card-x" style="margin-left:10px">{{ advisorLabel }} · {{ tsCode }} · 按成交时间倒序</span>
        </div>
      </div>
      <div class="ck-table-wrap">
        <table class="d-table ck-table">
          <thead>
            <tr>
              <th v-for="col in tradeColumns" :key="col.key">{{ col.label }}</th>
            </tr>
          </thead>
          <tbody v-if="loading">
            <tr><td :colspan="tradeColumns.length" class="ck-empty-cell">加载中...</td></tr>
          </tbody>
          <tbody v-else-if="tradeRows.length">
            <tr v-for="row in tradeRows" :key="`${row.trade_date}-${row.trade_time}-${row.account}-${row.trade_amount}`">
              <td class="d-mono">{{ row.trade_date || '—' }}</td>
              <td class="d-mono">{{ row.trade_time || '—' }}</td>
              <td>{{ formatAdvisor(row) }}</td>
              <td>{{ row.side || '—' }}</td>
              <td>{{ row.open_close || '—' }}</td>
              <td class="d-mono">{{ fmtNumber(row.trade_price) }}</td>
              <td class="d-mono">{{ fmtNumber(row.trade_qty) }}</td>
              <td class="d-mono">{{ fmtMoney(row.trade_amount) }}</td>
              <td class="d-mono">{{ fmtMoney(row.fee) }}</td>
              <td class="d-mono">{{ fmtMoney(row.close_profit) }}</td>
              <td class="d-mono">{{ fmtMoney(row.daily_position_profit) }}</td>
            </tr>
          </tbody>
          <tbody v-else>
            <tr><td :colspan="tradeColumns.length" class="ck-empty-cell">暂无该投顾成交明细</td></tr>
          </tbody>
        </table>
      </div>
      <div v-if="tradeCount" class="ck-pagination">
        <div class="ck-page-size">
          <span>共 {{ tradeCount }} 条</span>
          <span>每页</span>
          <select v-model.number="tradePageSize" @change="changeTradePage(1)">
            <option :value="10">10 条</option>
            <option :value="20">20 条</option>
            <option :value="50">50 条</option>
          </select>
        </div>
        <div class="ck-page-actions">
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
        <div class="ck-page-jump">
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
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import client from '../../api/client'

const route = useRoute()
const router = useRouter()
const loading = ref(false)
const contract = ref(route.query.contract || 'lh2611')
const account = ref(route.query.account || '250528_HG')
const selectedWindow = ref(route.query.window || '6m')
const queryContract = ref(contract.value)
const queryAccount = ref(account.value)
const tsCode = ref(contract.value.toUpperCase())
const advisorLabel = ref(account.value)
const latestDate = ref('')
const allRows = ref([])
const markerRows = ref([])
const positionRows = ref([])
const positionCount = ref(0)
const tradePage = ref(Number(route.query.trade_page || 1))
const tradePageSize = ref(Number(route.query.trade_page_size || 20))
const tradeJumpPage = ref('')
const hoverIndex = ref(null)
const today = new Date()
const sixMonthsAgo = new Date(today)
sixMonthsAgo.setMonth(sixMonthsAgo.getMonth() - 6)
const toDateInput = (date) => `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
const customStartDate = ref(route.query.start_date || toDateInput(sixMonthsAgo))
const customEndDate = ref(route.query.end_date || toDateInput(today))
const sliderStart = ref(0)
const sliderEnd = ref(0)

const box = { width: 1000, left: 58, right: 980, top: 18, priceBottom: 300, volTop: 326, volBottom: 390 }
const windowOptions = [
  { key: '1m', label: '近1月' },
  { key: '3m', label: '近3月' },
  { key: '6m', label: '近6月' },
  { key: '1y', label: '近1年' },
  { key: 'all', label: '全部' },
  { key: 'custom', label: '自定义' },
]
const positionColumns = [
  { key: 'trade_date', label: '持仓日期' },
  { key: 'advisor_name', label: '投顾名称' },
  { key: 'contract', label: '合约' },
  { key: 'side', label: '买卖' },
  { key: 'hedge_flag', label: '投保' },
  { key: 'position_qty', label: '持仓量' },
  { key: 'open_date', label: '开仓日期' },
  { key: 'open_time', label: '开仓时间' },
  { key: 'open_price', label: '开仓价' },
  { key: 'settlement_price', label: '结算价' },
  { key: 'margin', label: '保证金' },
  { key: 'market_value', label: '持仓市值' },
  { key: 'daily_position_profit', label: '逐日持盈' },
  { key: 'position_profit', label: '逐笔持盈' },
]
const firstDate = computed(() => rows.value[0]?.date || '')
const lastDate = computed(() => rows.value[rows.value.length - 1]?.date || '')
const latestPoint = computed(() => rows.value[rows.value.length - 1] || null)
const selectedWindowLabel = computed(() =>
  selectedWindow.value === 'custom'
    ? `${customStartDate.value} 至 ${customEndDate.value}`
    : windowOptions.find((item) => item.key === selectedWindow.value)?.label || '近6月'
)
const totalPositionPages = computed(() => Math.max(Math.ceil(positionCount.value / tradePageSize.value), 1))
const tradePageNumbers = computed(() => {
  const total = totalPositionPages.value
  const current = tradePage.value
  const start = Math.max(1, Math.min(current - 2, total - 4))
  const end = Math.min(total, start + 4)
  return Array.from({ length: end - start + 1 }, (_, index) => start + index)
})
const candleWidth = computed(() => Math.max(Math.min((box.right - box.left) / Math.max(rows.value.length, 1) * 0.58, 8), 2))
const sliderMax = computed(() => Math.max(allRows.value.length - 1, 0))
const rows = computed(() => {
  if (!allRows.value.length) return []
  const start = Math.min(Math.max(sliderStart.value, 0), sliderMax.value)
  const end = Math.min(Math.max(sliderEnd.value, start), sliderMax.value)
  return allRows.value.slice(start, end + 1)
})
const sliderStartDate = computed(() => allRows.value[sliderStart.value]?.date || '')
const sliderEndDate = computed(() => allRows.value[sliderEnd.value]?.date || '')
const rangeFillStyle = computed(() => {
  const max = sliderMax.value || 1
  const start = (sliderStart.value / max) * 100
  const end = (sliderEnd.value / max) * 100
  return { left: `${start}%`, width: `${Math.max(end - start, 0)}%` }
})

const priceDomain = computed(() => {
  const lows = rows.value.map((row) => Number(row.low || 0))
  const highs = rows.value.map((row) => Number(row.high || 0))
  const min = Math.min(...lows)
  const max = Math.max(...highs)
  const pad = (max - min || 1) * 0.08
  return { min: min - pad, max: max + pad }
})

const maxVol = computed(() => Math.max(...rows.value.map((row) => Number(row.vol || 0)), 1))

const candles = computed(() => {
  const spanX = box.right - box.left
  const count = rows.value.length
  return rows.value.map((row, index) => {
    const x = box.left + (count === 1 ? spanX : (index / (count - 1)) * spanX)
    const open = Number(row.open || 0)
    const close = Number(row.close || 0)
    return {
      ...row,
      x,
      open,
      close,
      high: Number(row.high || 0),
      low: Number(row.low || 0),
      vol: Number(row.vol || 0),
      openY: priceY(open),
      closeY: priceY(close),
      highY: priceY(Number(row.high || 0)),
      lowY: priceY(Number(row.low || 0)),
      up: close >= open,
    }
  })
})

const tradeMarkers = computed(() => {
  const candleByDate = new Map(candles.value.map((candle) => [candle.date, candle]))
  const groupIndexByDate = new Map()
  return markerRows.value
    .map((row) => {
      const candle = candleByDate.get(row.date)
      if (!candle) return null
      const used = groupIndexByDate.get(row.date) || 0
      groupIndexByDate.set(row.date, used + 1)
      const price = Number(row.avg_price || candle.close || 0)
      const offset = (used % 2 === 0 ? -1 : 1) * (8 + Math.floor(used / 2) * 12)
      const side = row.side || '—'
      const openClose = row.open_close || '—'
      return {
        ...row,
        x: candle.x,
        y: Math.min(Math.max(priceY(price) + offset, box.top + 12), box.priceBottom - 12),
        label: `${side}${openClose}`.slice(0, 4),
        sideClass: isBuySide(side) ? 'buy' : 'sell',
        title: `${row.date} ${side}${openClose} · ${row.trade_count || 0}笔 · ${fmtNumber(row.trade_qty)}手 · 均价${fmtNumber(row.avg_price)}`,
      }
    })
    .filter(Boolean)
})

const priceTicks = computed(() => {
  const ticks = []
  const { min, max } = priceDomain.value
  for (let i = 0; i < 5; i += 1) {
    const value = min + ((max - min) / 4) * i
    ticks.push({ y: priceY(value), label: fmtNumber(value) })
  }
  return ticks.reverse()
})

const hoverPoint = computed(() => {
  if (hoverIndex.value == null) return null
  const point = candles.value[hoverIndex.value]
  if (!point) return null
  return {
    ...point,
    tooltipX: Math.min(Math.max(point.x + 10, 70), 800),
    tooltipY: point.highY < 120 ? point.highY + 16 : point.highY - 96,
  }
})

function priceY(value) {
  const { min, max } = priceDomain.value
  return box.priceBottom - ((Number(value || 0) - min) / (max - min)) * (box.priceBottom - box.top)
}

function volumeY(value) {
  return box.volBottom - (Number(value || 0) / maxVol.value) * (box.volBottom - box.volTop)
}

function onChartMove(event) {
  const rect = event.currentTarget.getBoundingClientRect()
  const x = ((event.clientX - rect.left) / rect.width) * box.width
  const ratio = Math.min(Math.max((x - box.left) / (box.right - box.left), 0), 1)
  hoverIndex.value = Math.round(ratio * (rows.value.length - 1))
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

function formatAdvisor(row) {
  const name = row.advisor_name || row.account || '—'
  return row.account ? `${name}（${row.account}）` : name
}

function isBuySide(side) {
  return String(side || '').includes('买') || String(side || '').toLowerCase() === 'buy'
}

function handleSliderStart() {
  if (sliderStart.value > sliderEnd.value) sliderEnd.value = sliderStart.value
  hoverIndex.value = null
}

function handleSliderEnd() {
  if (sliderEnd.value < sliderStart.value) sliderStart.value = sliderEnd.value
  hoverIndex.value = null
}

function resetSlider(nextRows) {
  sliderStart.value = 0
  sliderEnd.value = Math.max((nextRows?.length || 1) - 1, 0)
}

function applyQuery() {
  tradePage.value = 1
  router.push({
    name: 'display-sector-contract-kline',
    query: buildRouteQuery({ contract: queryContract.value.trim(), account: queryAccount.value.trim(), trade_page: 1 }),
  })
}

function buildRouteQuery(overrides = {}) {
  const query = {
    contract: contract.value,
    account: account.value,
    window: selectedWindow.value,
    ...overrides,
  }
  if (query.window === 'custom') {
    query.start_date = customStartDate.value
    query.end_date = customEndDate.value
  }
  return query
}

function selectWindow(key) {
  selectedWindow.value = key
  hoverIndex.value = null
  tradePage.value = 1
  router.push({ name: 'display-sector-contract-kline', query: buildRouteQuery({ window: key, trade_page: 1 }) })
}

function applyCustomWindow() {
  selectedWindow.value = 'custom'
  hoverIndex.value = null
  router.push({ name: 'display-sector-contract-kline', query: buildRouteQuery({ window: 'custom', trade_page: 1 }) })
}

function changeTradePage(page) {
  tradePage.value = Math.min(Math.max(page, 1), totalPositionPages.value)
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
    const { data } = await client.get('/tables/sector/contract-kline/', {
      params: {
        contract: contract.value,
        account: account.value,
        window: selectedWindow.value,
        start_date: selectedWindow.value === 'custom' ? customStartDate.value : undefined,
        end_date: selectedWindow.value === 'custom' ? customEndDate.value : undefined,
        trade_page: tradePage.value,
        trade_page_size: tradePageSize.value,
      },
    })
    tsCode.value = data.ts_code || contract.value.toUpperCase()
    latestDate.value = data.latest_date || ''
    allRows.value = data.rows || []
    resetSlider(allRows.value)
    markerRows.value = data.marker_rows || []
    positionRows.value = data.position_rows || []
    positionCount.value = data.position_count || 0
    advisorLabel.value = positionRows.value[0] ? formatAdvisor(positionRows.value[0]) : (account.value || data.account || '—')
  } catch (error) {
    console.error('获取合约K线失败', error)
    allRows.value = []
    resetSlider([])
    markerRows.value = []
    positionRows.value = []
    positionCount.value = 0
    latestDate.value = ''
  } finally {
    loading.value = false
  }
}

watch(() => [route.query.contract, route.query.account, route.query.window, route.query.start_date, route.query.end_date], ([nextContract, nextAccount, nextWindow, nextStart, nextEnd]) => {
  contract.value = nextContract || 'lh2611'
  account.value = nextAccount || '250528_HG'
  selectedWindow.value = nextWindow || '6m'
  if (nextStart) customStartDate.value = nextStart
  if (nextEnd) customEndDate.value = nextEnd
  queryContract.value = contract.value
  queryAccount.value = account.value
  tradePage.value = Number(route.query.trade_page || 1)
  tradePageSize.value = Number(route.query.trade_page_size || tradePageSize.value || 20)
  hoverIndex.value = null
  loadData()
}, { immediate: true })
</script>

<style scoped>
.contract-kline-page {
  max-width: 1280px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.ck-head-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 12px;
  min-width: 0;
}

.ck-periods {
  display: flex;
  align-items: center;
  border: 1px solid var(--line);
  border-radius: 4px;
  background: #FBF9F3;
  overflow: hidden;
}

.ck-periods button {
  height: 26px;
  padding: 0 12px;
  border: 0;
  background: none;
  color: var(--muted);
  font-size: 12px;
  font-family: var(--sans);
  cursor: pointer;
  white-space: nowrap;
}

.ck-periods button:hover {
  color: var(--ink);
}

.ck-periods button.on {
  background: var(--navy);
  color: #F2EDE0;
}

.ck-query {
  display: flex;
  align-items: center;
  gap: 8px;
}

.ck-query .d-ipt {
  width: 140px;
  font-size: 12px;
}

.ck-custom-row {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 6px;
  padding: 0 18px 12px;
  color: var(--muted);
  font-size: 12px;
}

.ck-custom-row input {
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

.ck-custom-row button {
  height: 26px;
  padding: 0 12px;
  border: 1px solid var(--line);
  border-radius: 4px;
  background: var(--card);
  color: var(--muted);
  font-size: 12px;
  cursor: pointer;
}

.ck-custom-row button:hover {
  border-color: var(--brass);
  color: var(--brass);
}

.ck-chart {
  position: relative;
  min-height: 460px;
}

.ck-meta {
  display: flex;
  align-items: baseline;
  gap: 10px;
  margin: 0 0 6px 58px;
}

.ck-meta strong {
  font-family: var(--mono);
  color: var(--ink);
  font-size: 20px;
}

.ck-meta span,
.ck-x-label,
.ck-axis-labels text {
  fill: var(--muted);
  color: var(--muted);
  font-family: var(--mono);
  font-size: 11px;
}

.ck-svg {
  width: 100%;
  height: 420px;
  display: block;
  overflow: visible;
}

.ck-range {
  position: relative;
  margin: -4px 20px 12px 58px;
  padding-right: 18px;
}

.ck-range-labels {
  display: flex;
  justify-content: space-between;
  margin-bottom: 5px;
  color: var(--muted);
  font-family: var(--mono);
  font-size: 11px;
}

.ck-range-track {
  position: relative;
  height: 18px;
}

.ck-range-track::before,
.ck-range-fill {
  content: '';
  position: absolute;
  left: 0;
  right: 0;
  top: 7px;
  height: 4px;
  border-radius: 999px;
}

.ck-range-track::before {
  background: rgba(18, 36, 56, 0.1);
}

.ck-range-fill {
  right: auto;
  background: rgba(35, 85, 80, 0.28);
}

.ck-range input[type='range'] {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 18px;
  margin: 0;
  appearance: none;
  background: transparent;
  pointer-events: none;
}

.ck-range input[type='range']::-webkit-slider-thumb {
  width: 12px;
  height: 18px;
  border: 1px solid var(--navy);
  border-radius: 4px;
  background: var(--card);
  box-shadow: 0 1px 4px rgba(18, 36, 56, 0.18);
  appearance: none;
  cursor: ew-resize;
  pointer-events: auto;
}

.ck-range input[type='range']::-moz-range-thumb {
  width: 12px;
  height: 18px;
  border: 1px solid var(--navy);
  border-radius: 4px;
  background: var(--card);
  box-shadow: 0 1px 4px rgba(18, 36, 56, 0.18);
  cursor: ew-resize;
  pointer-events: auto;
}

.ck-range input[type='range']::-webkit-slider-runnable-track {
  height: 18px;
  background: transparent;
}

.ck-range input[type='range']::-moz-range-track {
  height: 18px;
  background: transparent;
}

.ck-grid line {
  stroke: rgba(18, 36, 56, 0.1);
  stroke-dasharray: 4 4;
}

.ck-up-stroke,
.ck-up-fill {
  stroke: #B03A2E;
  fill: #B03A2E;
  vector-effect: non-scaling-stroke;
}

.ck-dn-stroke,
.ck-dn-fill {
  stroke: #17714B;
  fill: #17714B;
  vector-effect: non-scaling-stroke;
}

.ck-up-vol {
  fill: rgba(176, 58, 46, 0.22);
}

.ck-dn-vol {
  fill: rgba(23, 113, 75, 0.22);
}

.ck-marker circle {
  stroke: #FBF9F3;
  stroke-width: 2;
  vector-effect: non-scaling-stroke;
}

.ck-marker circle.buy {
  fill: #B03A2E;
}

.ck-marker circle.sell {
  fill: #17714B;
}

.ck-marker text {
  fill: var(--ink);
  font-family: var(--sans);
  font-size: 10px;
  font-weight: 600;
  paint-order: stroke;
  stroke: #FBF9F3;
  stroke-width: 3px;
  stroke-linejoin: round;
  pointer-events: none;
}

.ck-hover line {
  stroke: rgba(18, 36, 56, 0.22);
  stroke-dasharray: 4 4;
  vector-effect: non-scaling-stroke;
}

.ck-tooltip {
  position: absolute;
  z-index: 3;
  min-width: 160px;
  padding: 10px 12px;
  border-radius: 6px;
  background: rgba(33, 42, 52, 0.9);
  color: #fff;
  box-shadow: 0 8px 22px rgba(22, 34, 48, 0.2);
  pointer-events: none;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.ck-tooltip span {
  display: flex;
  justify-content: space-between;
  gap: 14px;
  color: rgba(255, 255, 255, 0.82);
  font-size: 12px;
}

.ck-tooltip em {
  font-style: normal;
  color: #fff;
  font-family: var(--mono);
}

.ck-empty {
  min-height: 360px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--muted);
}

.ck-table-wrap {
  overflow: auto;
  max-height: 520px;
  position: relative;
}

.ck-table {
  table-layout: fixed;
  min-width: 1120px;
}

.ck-table th,
.ck-table td {
  text-align: center;
  white-space: nowrap;
}

.ck-table th {
  position: sticky;
  top: 0;
  z-index: 5;
  background: var(--card);
  box-shadow: 0 1px 0 var(--line), 0 8px 10px rgba(245, 242, 234, 0.96);
}

.ck-empty-cell {
  text-align: center;
  color: var(--muted);
  padding: 42px 12px;
}

.ck-pagination {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
  gap: 12px;
  padding: 10px 18px 14px;
  border-top: 1px solid var(--line2);
  color: var(--muted);
  font-size: 12px;
}

.ck-page-size,
.ck-page-jump {
  display: flex;
  align-items: center;
  gap: 8px;
}

.ck-page-jump {
  justify-content: flex-end;
}

.ck-page-size select,
.ck-page-jump input {
  height: 32px;
  border: 1px solid var(--line);
  border-radius: 7px;
  background: var(--card);
  color: var(--ink);
  font-size: 12px;
}

.ck-page-size select {
  padding: 0 26px 0 10px;
}

.ck-page-jump input {
  width: 64px;
  padding: 0 8px;
  text-align: center;
}

.ck-page-actions {
  display: flex;
  align-items: center;
  gap: 6px;
}

.ck-page-actions button,
.ck-page-jump button {
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

.ck-page-actions button:hover:not(:disabled),
.ck-page-jump button:hover {
  border-color: var(--brass);
  color: var(--brass);
}

.ck-page-actions button.on {
  border-color: var(--navy);
  background: var(--navy);
  color: #F2EDE0;
}

.ck-page-actions button:disabled {
  cursor: not-allowed;
  opacity: 0.45;
}

@media (max-width: 900px) {
  .ck-pagination {
    grid-template-columns: 1fr;
  }

  .ck-page-actions,
  .ck-page-jump {
    justify-content: flex-start;
  }
}
</style>
