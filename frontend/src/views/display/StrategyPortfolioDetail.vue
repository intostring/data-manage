<template>
  <div class="d-anim max-w-6xl mx-auto">
    <!-- ① 组合头部 -->
    <div class="d-card" style="margin-bottom:14px">
      <div class="d-card-h">
        <div>
          <span class="d-card-t">{{ record.name || '组合分析' }}</span>
          <span class="d-pill info" style="margin-left:10px">{{ record.weight_model_label || '—' }}</span>
          <span class="d-card-x" style="margin-left:10px">{{ record.note }}</span>
        </div>
        <div style="display:flex;gap:8px">
          <router-link class="d-btn" to="/display/strategy/portfolio">返回列表</router-link>
          <router-link class="d-btn" :to="`/display/strategy/portfolio/create?id=${recordId}`">编辑组合</router-link>
        </div>
      </div>

      <div class="d-card-b" style="padding-top:4px">
        <div v-if="loading" style="display:flex;align-items:center;justify-content:center;height:120px">
          <span class="d-muted">组合计算中…</span>
        </div>
        <div v-else-if="error" style="display:flex;align-items:center;justify-content:center;height:120px">
          <span style="color:var(--up)">{{ error }}</span>
        </div>
        <template v-else-if="result">
          <div v-if="result.weight_note" class="d-muted" style="font-size:12px;margin-bottom:8px">
            ⚠ {{ result.weight_note }}
          </div>
          <div class="d-kpis">
            <div><div class="k">总收益</div><div class="v" :class="fmtColorPct(m.total_return)">{{ fmtPct(m.total_return) }}</div></div>
            <div><div class="k">年化收益</div><div class="v" :class="fmtColorPct(m.annual_yield)">{{ fmtPct(m.annual_yield) }}</div></div>
            <div><div class="k">夏普比率</div><div class="v">{{ fmtNum(m.sharpe_ratio) }}</div></div>
            <div><div class="k">卡玛比率</div><div class="v">{{ fmtNum(m.calmar_ratio) }}</div></div>
            <div><div class="k">最大回撤</div><div class="v d-dn">{{ fmtPct(m.max_drawdown) }}</div></div>
            <div><div class="k">年化波动率</div><div class="v">{{ fmtPct(m.annual_volatility) }}</div></div>
            <div><div class="k">成分投顾</div><div class="v">{{ result.scale.advisor_count }}</div></div>
          </div>
        </template>
      </div>
    </div>

    <template v-if="result">
      <!-- ② 收益率曲线 -->
      <div class="d-card">
        <div class="d-card-h">
          <span class="d-card-t">组合收益率曲线</span>
          <span class="d-card-x" style="margin-left:10px">
            {{ result.metrics.start_date }} ~ {{ result.metrics.end_date }} · {{ result.metrics.daily_count }} 个交易日
          </span>
        </div>
        <div class="d-card-b">
          <!-- 时间段选择器 -->
          <div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap;margin-bottom:8px">
            <div class="d-seg">
              <button v-for="p in periods" :key="p.key" :class="selectedPeriod === p.key ? 'on' : ''" @click="selectedPeriod = p.key; changePeriod()">{{ p.label }}</button>
            </div>
            <div v-if="selectedPeriod === 'custom'" style="display:flex;align-items:center;gap:6px">
              <input type="date" v-model="customStart" class="d-ipt" style="font-size:11px;padding:4px 8px;width:130px" @change="changePeriod" />
              <span class="d-muted">至</span>
              <input type="date" v-model="customEnd" class="d-ipt" style="font-size:11px;padding:4px 8px;width:130px" @change="changePeriod" />
            </div>
          </div>
          <!-- 图例条：曲线显隐 + 区间收益 -->
          <div style="display:flex;align-items:center;gap:16px;margin-bottom:8px;flex-wrap:wrap">
            <span class="d-leg-i spd-leg" :class="{ off: !legendOn('策略组合') }" @click="toggleSeries('策略组合')">
              <i class="d-leg-sw" style="background:#9C6B2F"></i>
              <span style="font-size:12px">策略组合</span>
              <span class="d-mono spd-leg-ret" :class="portPeriodReturn >= 0 ? 'd-up' : 'd-dn'">{{ fmtSigned(portPeriodReturn) }}</span>
            </span>
            <span class="d-leg-i spd-leg" :class="{ off: !legendOn('南华商品指数') }" @click="toggleSeries('南华商品指数')">
              <i class="d-leg-sw" style="background:#8A8A8A"></i>
              <span style="font-size:12px">南华商品指数</span>
              <span class="d-mono spd-leg-ret" :class="benchPeriodReturn >= 0 ? 'd-up' : 'd-dn'">{{ fmtSigned(benchPeriodReturn) }}</span>
            </span>
            <span class="d-leg-i spd-leg" :class="{ off: !legendOn('超额收益') }" @click="toggleSeries('超额收益')">
              <i class="d-leg-sw" style="background:#4472C4"></i>
              <span style="font-size:12px">超额收益</span>
              <span class="d-mono spd-leg-ret" :class="excessPeriodReturn >= 0 ? 'd-up' : 'd-dn'">{{ fmtSigned(excessPeriodReturn) }}</span>
            </span>
          </div>
          <div ref="chartRef" style="width:100%;height:480px"></div>
        </div>
      </div>

      <!-- ③ 区间收益（月度 / 年度） -->
      <div class="d-card" style="margin-top:14px">
        <div class="d-card-h">
          <div>
            <span class="d-card-t">区间收益</span>
            <span class="d-card-x" style="margin-left:10px">按月度与年度划分的区间收益率</span>
          </div>
          <div v-if="hasBenchRows" style="display:flex;gap:6px">
            <button class="spd-pr-toggle" :class="{ on: showBench }" @click="showBench = !showBench">基准指数</button>
            <button class="spd-pr-toggle" :class="{ on: showExcess }" @click="showExcess = !showExcess">超额收益</button>
          </div>
        </div>
        <div class="d-card-b">
          <template v-if="periodReturnRows.length">
            <div class="spd-pr-scroll">
              <table class="d-table spd-pr-table">
                <thead>
                  <tr>
                    <th>年份</th>
                    <th v-for="mm in 12" :key="mm">{{ mm }}月</th>
                    <th>全年</th>
                  </tr>
                </thead>
                <tbody>
                  <template v-for="row in periodReturnRows" :key="row.year">
                    <tr>
                      <td class="spd-pr-year">{{ row.year }}</td>
                      <td v-for="mm in 12" :key="mm" class="d-mono spd-pr-c" :style="prCellStyle(row.months[mm - 1])">
                        {{ prFmtCell(row.months[mm - 1]) }}
                      </td>
                      <td class="d-mono spd-pr-year-cell" :style="prCellStyle(row.yearReturn)">
                        {{ prFmtCell(row.yearReturn) }}
                      </td>
                    </tr>
                    <tr v-if="showBench && benchByYear[row.year]">
                      <td class="spd-pr-sub">基准指数</td>
                      <td
                        v-for="mm in 12"
                        :key="mm"
                        class="d-mono spd-pr-c spd-pr-c-sub"
                        :style="prCellStyle(benchByYear[row.year].months[mm - 1])"
                      >{{ prFmtCell(benchByYear[row.year].months[mm - 1]) }}</td>
                      <td class="d-mono spd-pr-year-cell spd-pr-c-sub" :style="prCellStyle(benchByYear[row.year].yearReturn)">
                        {{ prFmtCell(benchByYear[row.year].yearReturn) }}
                      </td>
                    </tr>
                    <tr v-if="showExcess && excessByYear[row.year]">
                      <td class="spd-pr-sub">超额收益</td>
                      <td
                        v-for="mm in 12"
                        :key="mm"
                        class="d-mono spd-pr-c spd-pr-c-sub"
                        :style="prCellStyle(excessByYear[row.year].months[mm - 1])"
                      >{{ prFmtCell(excessByYear[row.year].months[mm - 1]) }}</td>
                      <td class="d-mono spd-pr-year-cell spd-pr-c-sub" :style="prCellStyle(excessByYear[row.year].yearReturn)">
                        {{ prFmtCell(excessByYear[row.year].yearReturn) }}
                      </td>
                    </tr>
                  </template>
                </tbody>
              </table>
            </div>
            <!-- 图例 -->
            <div class="spd-pr-legend">
              <span v-for="bucket in prLegendBuckets" :key="bucket.label" class="spd-pr-leg-item">
                <i :style="{ background: bucket.color }"></i>
                {{ bucket.label }}
              </span>
            </div>
          </template>
          <div v-else style="display:flex;align-items:center;justify-content:center;height:160px">
            <span class="d-muted">该组合暂无净值数据</span>
          </div>
        </div>
      </div>

      <!-- ④ 组合规模与成分明细 -->
      <div class="d-card" style="margin-top:14px">
        <div class="d-card-h">
          <div>
            <span class="d-card-t">组合规模与成分明细</span>
            <span class="d-card-x" style="margin-left:10px">合计规模与各成分投顾明细</span>
          </div>
        </div>
        <div class="d-card-b">
          <div class="spd-scale">
            <div><div class="k">组合累计总投入</div><div class="v d-mono">{{ fmtMoney(result.scale.cum_investment) }}</div></div>
            <div><div class="k">最新市值</div><div class="v d-mono">{{ fmtMoney(result.scale.latest_mv) }}</div></div>
            <div>
              <div class="k">累计盈亏</div>
              <div class="v d-mono" :class="fmtColorPct(result.scale.total_pnl)">
                {{ result.scale.total_pnl != null ? (result.scale.total_pnl >= 0 ? '+' : '') + fmtMoney(result.scale.total_pnl) : '—' }}
              </div>
            </div>
            <div><div class="k">成分投顾</div><div class="v d-mono">{{ result.scale.advisor_count }} 个</div></div>
          </div>

          <div class="spd-scroll" style="margin-top:14px">
            <table class="d-table">
              <thead>
                <tr>
                  <th style="text-align:left">投顾名称</th>
                  <th style="text-align:left">账号代码</th>
                  <th>起始日期</th>
                  <th>截至日期</th>
                  <th style="text-align:right">累计投入</th>
                  <th style="text-align:right">累计盈亏</th>
                  <th>投资逻辑</th>
                  <th>组合权重</th>
                  <th>最新净值</th>
                  <th>累计收益</th>
                  <th>最新市值</th>
                </tr>
              </thead>
              <tbody>
                <template v-for="a in result.advisors" :key="a.pid">
                  <tr v-for="(acc, ai) in accountRowsOf(a)" :key="a.pid + '-' + acc.code" :class="{ 'spd-sub-row': ai > 0 }">
                    <td>{{ ai === 0 ? (a.account_name || a.account_code) : '' }}</td>
                    <td class="d-mono">
                      <a
                        v-if="acc.pid"
                        class="spd-acct-link"
                        :title="`查看 ${acc.code} 业绩`"
                        @click.stop="goAdvisor(acc.pid)"
                      >{{ acc.code }}</a>
                      <span v-else class="d-muted">{{ acc.code }}</span>
                    </td>
                    <td class="d-mono d-muted">{{ acc.start_date || '—' }}</td>
                    <td class="d-mono d-muted">{{ acc.end_date || '—' }}</td>
                    <td class="d-mono" style="text-align:right">{{ fmtMoney(acc.cum_investment) }}</td>
                    <td class="d-mono" style="text-align:right" :class="fmtColorPct(acc.pnl)">{{ fmtMoney(acc.pnl) }}</td>
                    <td v-if="ai === 0" :rowspan="accountRowsOf(a).length" class="d-muted">{{ a.invest_logic || '—' }}</td>
                    <td v-if="ai === 0" :rowspan="accountRowsOf(a).length" class="d-mono">{{ a.weight != null ? a.weight.toFixed(2) + '%' : '—' }}</td>
                    <td v-if="ai === 0" :rowspan="accountRowsOf(a).length" class="d-mono">{{ a.latest_nav ?? '—' }}</td>
                    <td v-if="ai === 0" :rowspan="accountRowsOf(a).length" class="d-mono" :class="fmtColorPct(a.total_return)">{{ fmtPct(a.total_return) }}</td>
                    <td v-if="ai === 0" :rowspan="accountRowsOf(a).length" class="d-mono">{{ fmtMoney(a.latest_mv) }}</td>
                  </tr>
                </template>
              </tbody>
            </table>
          </div>
          <div class="d-muted" style="font-size:11px;margin-top:8px">
            口径说明：成分净值由 rh_funds 每日结算权益 + 出入金份额法现算（同名多账户合并）；
            组合日收益率 = Σ(成分日收益率 × 权重)，成分当日无净值按 0 处理；年化按 252 个交易日，无风险利率取 1.5%；
            风险平价 = 等风险贡献（ERC），均值方差 = 最大夏普切点组合（负权截断）。
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import * as echarts from 'echarts/core'
import { LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent, DataZoomComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import client from '../../api/client'

echarts.use([CanvasRenderer, LineChart, GridComponent, TooltipComponent, LegendComponent, DataZoomComponent])

const route = useRoute()
const router = useRouter()
const recordId = route.params.id

const record = ref({})
const result = ref(null)
const loading = ref(false)
const error = ref('')

const chartRef = ref(null)
let chart = null

// 时间段选择（与投顾业绩页一致）
const periods = [
  { key: 'ytd', label: '今年以来' },
  { key: '1m', label: '近1月' },
  { key: '3m', label: '近3月' },
  { key: '6m', label: '近6月' },
  { key: '1y', label: '近1年' },
  { key: 'since', label: '成立以来' },
  { key: 'custom', label: '自定义' },
]
const selectedPeriod = ref('since')
const today = new Date()
const oneYearAgo = new Date(today)
oneYearAgo.setFullYear(oneYearAgo.getFullYear() - 1)
const fmtDate = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
const customStart = ref(fmtDate(oneYearAgo))
const customEnd = ref(fmtDate(today))

// 图例显隐 + 区间收益
const legendSelected = ref({})
function legendOn(name) {
  return legendSelected.value[name] !== false
}
function toggleSeries(name) {
  chart?.dispatchAction({ type: 'legendToggleSelect', name })
  legendSelected.value[name] = !legendOn(name)
}
const portPeriodReturn = ref(0)
const benchPeriodReturn = ref(0)
const excessPeriodReturn = ref(0)

function changePeriod() {
  if (result.value) renderChart()
}

function fmtSigned(v) {
  return (v >= 0 ? '+' : '') + v.toFixed(2) + '%'
}

// 成分代码列表（无 codes 时退回拼接串）
function codeListOf(a) {
  return a.account_codes?.length ? a.account_codes : [a.account_code]
}

// 成分明细行：账号级（每账号一行：累计投入/累计盈亏）
function accountRowsOf(a) {
  if (a.accounts?.length) {
    return a.accounts
  }
  return codeListOf(a).map((code) => ({
    code,
    pid: a.account_pids?.[code],
    cum_investment: a.cum_investment,
    pnl: null,
  }))
}

// 点击代码 → 对应投顾业绩页
function goAdvisor(pid) {
  router.push(`/display/advisor/detail/${pid}`)
}

// 按时间段过滤序列
function filterByPeriod(series) {
  const last = series[series.length - 1]
  const endDate = selectedPeriod.value === 'custom' ? new Date(customEnd.value) : new Date(last?.date || today)
  if (selectedPeriod.value === 'since') return series
  let startDate = null
  const now = endDate
  if (selectedPeriod.value === 'ytd') startDate = new Date(now.getFullYear(), 0, 1)
  if (selectedPeriod.value === 'custom') startDate = new Date(customStart.value)
  if (selectedPeriod.value === '1m') { startDate = new Date(now); startDate.setMonth(startDate.getMonth() - 1) }
  if (selectedPeriod.value === '3m') { startDate = new Date(now); startDate.setMonth(startDate.getMonth() - 3) }
  if (selectedPeriod.value === '6m') { startDate = new Date(now); startDate.setMonth(startDate.getMonth() - 6) }
  if (selectedPeriod.value === '1y') { startDate = new Date(now); startDate.setFullYear(startDate.getFullYear() - 1) }
  if (!startDate) return series
  return series.filter((s) => new Date(s.date) >= startDate && new Date(s.date) <= endDate)
}

// 日收益序列 → {年份: {months, yearReturn}}（月收益 = 月末净值环比连乘，单位 %）
function prMonthlyByYear(rets) {
  const yearMap = new Map()
  const push = (year) => {
    let row = yearMap.get(year)
    if (!row) {
      row = { year, months: Array(12).fill(null), yearReturn: 0 }
      yearMap.set(year, row)
    }
    return row
  }
  for (const item of rets) {
    const y = Number(item.date.slice(0, 4))
    const m = Number(item.date.slice(5, 7))
    const row = push(y)
    row.months[m - 1] = (1 + (row.months[m - 1] ?? 0)) * (1 + item.ret) - 1
    row.yearReturn = (1 + row.yearReturn) * (1 + item.ret) - 1
  }
  const out = {}
  for (const row of yearMap.values()) {
    out[row.year] = {
      months: row.months.map((v) => (v == null ? null : Math.round(v * 10000) / 100)),
      yearReturn: Math.round(row.yearReturn * 10000) / 100,
    }
  }
  return out
}

// 区间收益：按月度 / 年度划分（基于完整净值序列，与时间段选择无关，口径同投顾业绩页）
const periodReturnRows = computed(() => {
  const series = (result.value?.nav_series || []).filter((s) => s.nav && s.date)
  if (series.length < 2) return []
  const rets = []
  for (let i = 1; i < series.length; i++) {
    rets.push({ date: series[i].date, ret: series[i].nav / series[i - 1].nav - 1 })
  }
  const byYear = prMonthlyByYear(rets)
  return Object.keys(byYear)
    .map(Number)
    .sort((a, b) => b - a)
    .map((y) => ({ year: y, ...byYear[y] }))
})

// 基准指数（NHCI）月度/年度区间收益：日收益由累计收益推算（缺失日沿用前值）
const benchByYear = computed(() => {
  const navSeries = (result.value?.nav_series || []).filter((s) => s.nav && s.date)
  const benchRaw = new Map((result.value?.benchmark_series || []).map((p) => [p.date, p.cum_return]))
  if (navSeries.length < 2 || !benchRaw.size) return {}
  let lastCum = null
  const cums = []
  for (const s of navSeries) {
    const v = benchRaw.get(s.date)
    if (v != null) lastCum = v
    cums.push({ date: s.date, cum: lastCum })
  }
  const rets = []
  for (let i = 1; i < cums.length; i++) {
    const a = cums[i - 1].cum
    const b = cums[i].cum
    if (a == null || b == null) continue
    rets.push({ date: cums[i].date, ret: (100 + b) / (100 + a) - 1 })
  }
  return prMonthlyByYear(rets)
})

// 超额区间收益 = 组合区间收益 − 基准区间收益（百分点）
const excessByYear = computed(() => {
  const out = {}
  for (const row of periodReturnRows.value) {
    const b = benchByYear.value[row.year]
    if (!b) continue
    out[row.year] = {
      months: row.months.map((v, i) =>
        v == null || b.months[i] == null ? null : Math.round((v - b.months[i]) * 100) / 100
      ),
      yearReturn: Math.round((row.yearReturn - b.yearReturn) * 100) / 100,
    }
  }
  return out
})

const hasBenchRows = computed(() => Object.keys(benchByYear.value).length > 0)
const showBench = ref(false)
const showExcess = ref(false)

// 图例分档（正收益暖色 / 负收益绿色，与站点涨跌配色一致）
const prLegendBuckets = [
  { label: '≥10%', color: '#7A2E26' },
  { label: '5%~10%', color: '#B03A2E' },
  { label: '0%~5%', color: '#E2B4AE' },
  { label: '-5%~0%', color: '#BCD9C9' },
  { label: '-10%~-5%', color: '#5C9C7B' },
  { label: '≤-10%', color: '#17714B' },
]

function prBucketOf(v) {
  if (v == null) return null
  if (v >= 10) return prLegendBuckets[0]
  if (v >= 5) return prLegendBuckets[1]
  if (v > 0) return prLegendBuckets[2]
  if (v > -5) return prLegendBuckets[3]
  if (v > -10) return prLegendBuckets[4]
  return prLegendBuckets[5]
}

function prCellStyle(v) {
  const b = prBucketOf(v)
  if (!b) return null
  const dark = v >= 10 || v <= -10
  return { background: b.color, color: dark ? '#FDFCF8' : null }
}

function prFmtCell(v) {
  if (v == null) return ''
  return (v > 0 ? '+' : '') + v.toFixed(2)
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const { data: r } = await client.get(`/tables/strategy/portfolios/${recordId}/`)
    record.value = r

    const params = new URLSearchParams()
    params.set('pids', r.pids.join(','))
    params.set('model', r.weight_model || 'equal')
    params.set('equity', 'settle')
    if (r.weight_model === 'custom' && Array.isArray(r.weights) && r.weights.length) {
      params.set('weights', r.weights.join(','))
    }
    const { data } = await client.get(`/tables/strategy/portfolio/?${params.toString()}`)
    result.value = data
    await nextTick()
    renderChart()
  } catch (e) {
    console.error('加载组合分析失败', e)
    error.value = e.response?.data?.detail || '加载组合失败'
  } finally {
    loading.value = false
  }
}

function renderChart() {
  if (!chartRef.value || !result.value) return
  chart = chart || echarts.init(chartRef.value)

  // 区间序列：首日重算累计收益与回撤（与投顾业绩页同口径）
  const raw = filterByPeriod(result.value.nav_series || [])
  const baseNav = raw.length ? raw[0].nav : 1
  let peak = baseNav
  const dates = []
  const cumReturns = []
  const drawdowns = []
  for (const s of raw) {
    const cum = baseNav ? (s.nav / baseNav - 1) * 100 : 0
    if (s.nav > peak) peak = s.nav
    dates.push(s.date)
    cumReturns.push(Math.round(cum * 100) / 100)
    drawdowns.push(Math.round((s.nav / peak - 1) * 10000) / 100)
  }

  // 基准（NHCI）累计收益：区间首日重算，缺失日沿用前值
  const benchMap = new Map((result.value.benchmark_series || []).map((p) => [p.date, p.cum_return]))
  const benchCumFull = []
  let lastBench = null
  for (const s of raw) {
    const v = benchMap.get(s.date)
    if (v != null) lastBench = v
    benchCumFull.push(lastBench)
  }
  const baseBench = benchCumFull.length && benchCumFull[0] != null ? benchCumFull[0] : 0
  const benchReturns = benchCumFull.map((v) =>
    v == null ? 0 : Math.round(((100 + v) / (100 + baseBench) - 1) * 10000) / 100
  )
  const excessReturns = cumReturns.map((v, i) => Math.round((v - (benchReturns[i] ?? 0)) * 100) / 100)

  // 回撤（相对区间内峰值回落，百分点）
  const drawdownOf = (values) => {
    let pk = 0
    return values.map((v) => {
      pk = Math.max(pk, v)
      return Math.round((v - pk) * 100) / 100
    })
  }
  const benchDrawdowns = drawdownOf(benchReturns)
  const excessDrawdowns = drawdownOf(excessReturns)

  portPeriodReturn.value = cumReturns.length ? cumReturns[cumReturns.length - 1] : 0
  benchPeriodReturn.value = benchReturns.length ? benchReturns[benchReturns.length - 1] : 0
  excessPeriodReturn.value = excessReturns.length ? excessReturns[excessReturns.length - 1] : 0

  chart.setOption(
    {
      tooltip: {
        trigger: 'axis',
        backgroundColor: '#FDFCF8',
        borderColor: '#E5E0D2',
        textStyle: { fontSize: 11, color: '#20283A' },
        valueFormatter: (v) => (v == null ? '—' : `${v >= 0 ? '+' : ''}${Number(v).toFixed(2)}%`),
      },
      legend: { show: false },
      title: [
        { text: '动态回撤', left: 55, top: 315, textStyle: { fontSize: 12, fontWeight: 'normal', color: '#333' } },
        { text: `截止：${dates[dates.length - 1] || '—'}`, right: 25, top: 315, textStyle: { fontSize: 11, fontWeight: 'normal', color: '#8F8A79' } },
      ],
      grid: [
        { left: 55, right: 25, top: 30, height: 250 },
        { left: 55, right: 25, top: 350, height: 100 },
      ],
      xAxis: [
        { type: 'category', gridIndex: 0, data: dates, axisLabel: { show: false }, axisLine: { lineStyle: { color: '#E5E0D2' } } },
        { type: 'category', gridIndex: 1, data: dates, axisLabel: { fontSize: 10 }, axisLine: { lineStyle: { color: '#E5E0D2' } } },
      ],
      yAxis: [
        { type: 'value', gridIndex: 0, scale: true, axisLabel: { fontSize: 10, formatter: '{value}%' }, splitLine: { lineStyle: { color: '#EFEAE0' } } },
        { type: 'value', gridIndex: 1, max: 0, axisLabel: { fontSize: 10, formatter: '{value}%' }, splitLine: { lineStyle: { color: '#EFEAE0' } } },
      ],
      dataZoom: [
        { type: 'inside', xAxisIndex: [0, 1], start: 0, end: 100 },
        { type: 'slider', xAxisIndex: [0, 1], top: 280, height: 18, start: 0, end: 100, borderColor: '#E5E0D2', fillerColor: 'rgba(156,107,47,0.08)', handleStyle: { color: '#9C6B2F' }, textStyle: { fontSize: 10 } },
      ],
      series: [
        {
          name: '策略组合',
          type: 'line',
          xAxisIndex: 0,
          yAxisIndex: 0,
          data: cumReturns,
          lineStyle: { width: 2, color: '#9C6B2F' },
          itemStyle: { color: '#9C6B2F' },
          symbol: 'none',
          z: 10,
        },
        {
          name: '南华商品指数',
          type: 'line',
          xAxisIndex: 0,
          yAxisIndex: 0,
          data: benchReturns,
          lineStyle: { width: 1, color: '#8A8A8A', type: 'dashed' },
          itemStyle: { color: '#8A8A8A' },
          symbol: 'none',
        },
        {
          name: '超额收益',
          type: 'line',
          xAxisIndex: 0,
          yAxisIndex: 0,
          data: excessReturns,
          lineStyle: { width: 1, color: '#4472C4' },
          itemStyle: { color: '#4472C4' },
          symbol: 'none',
        },
        {
          name: '组合回撤',
          type: 'line',
          xAxisIndex: 1,
          yAxisIndex: 1,
          data: drawdowns,
          lineStyle: { width: 1, color: '#B03A2E' },
          itemStyle: { color: '#B03A2E' },
          areaStyle: { color: 'rgba(176,58,46,0.10)' },
          symbol: 'none',
        },
        {
          name: '基准回撤',
          type: 'line',
          xAxisIndex: 1,
          yAxisIndex: 1,
          data: benchDrawdowns,
          lineStyle: { width: 1, color: '#8A8A8A', type: 'dashed' },
          itemStyle: { color: '#8A8A8A' },
          symbol: 'none',
        },
        {
          name: '超额回撤',
          type: 'line',
          xAxisIndex: 1,
          yAxisIndex: 1,
          data: excessDrawdowns,
          lineStyle: { width: 1, color: '#4472C4' },
          itemStyle: { color: '#4472C4' },
          symbol: 'none',
        },
      ],
    },
    { notMerge: true }
  )
}

function handleResize() {
  chart?.resize()
}

const m = computed(() => result.value?.metrics || {})

function fmtPct(v, times = 1) {
  if (v == null) return '—'
  return (v >= 0 ? '+' : '') + (v * times * 100).toFixed(2) + '%'
}
function fmtNum(v) {
  if (v == null) return '—'
  return Number(v).toFixed(2)
}
function fmtColorPct(v) {
  if (v == null) return ''
  return v >= 0 ? 'd-up' : 'd-dn'
}
function fmtMoney(v) {
  if (v == null || v === '') return '—'
  const n = Number(v)
  if (Math.abs(n) >= 100000000) return `${(n / 100000000).toFixed(2)}亿`
  if (Math.abs(n) >= 10000) return `${(n / 10000).toFixed(2)}万`
  return n.toLocaleString('zh-CN', { maximumFractionDigits: 2 })
}

onMounted(() => {
  window.addEventListener('resize', handleResize)
  load()
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  chart?.dispose()
})
</script>

<style scoped>
.spd-sub-row td {
  background: #FBF9F3;
}
.spd-acct-link {
  color: #9C6B2F;
  cursor: pointer;
  font-size: 12px;
  text-decoration: underline dotted rgba(156, 107, 47, 0.6);
  text-underline-offset: 3px;
}
.spd-acct-link:hover {
  color: #B03A2E;
}
.spd-leg {
  cursor: pointer;
  user-select: none;
}
.spd-leg.off {
  opacity: 0.4;
}
.spd-leg-ret {
  font-size: 12px;
  margin-left: 4px;
}

.spd-check {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 12px;
  color: var(--muted);
  cursor: pointer;
}

.spd-scroll {
  overflow-x: auto;
}

.spd-pr-scroll {
  overflow-x: auto;
}

.spd-pr-table {
  width: 100%;
  table-layout: fixed;
  border-collapse: collapse;
}

.spd-pr-table th,
.spd-pr-table td {
  text-align: center;
  padding: 8px 4px;
  font-size: 12px;
  border: 1px solid var(--line);
}

.spd-pr-table th:first-child,
.spd-pr-table td:first-child {
  width: 64px;
}

.spd-pr-table th:last-child,
.spd-pr-table td:last-child {
  width: 90px;
}

.spd-pr-toggle {
  font-size: 12px;
  padding: 3px 12px;
  border: 1px solid var(--line);
  border-radius: 4px;
  background: transparent;
  color: var(--muted);
  cursor: pointer;
  transition: all 0.15s;
}

.spd-pr-toggle:hover {
  border-color: #9C6B2F;
  color: #9C6B2F;
}

.spd-pr-toggle.on {
  background: #9C6B2F;
  border-color: #9C6B2F;
  color: #FDFCF8;
}

.spd-pr-sub {
  font-size: 11px;
  font-weight: normal;
  color: var(--muted);
  background: var(--soft);
  white-space: nowrap;
}

.spd-pr-c-sub {
  font-size: 11px;
  opacity: 0.88;
}

.spd-pr-year {
  font-weight: 600;
  background: var(--soft);
}

.spd-pr-year-cell {
  font-weight: 600;
}

.spd-pr-legend {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-top: 10px;
  flex-wrap: wrap;
}

.spd-pr-leg-item {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 11px;
  color: var(--muted);
}

.spd-pr-leg-item i {
  width: 22px;
  height: 10px;
  border-radius: 2px;
  display: inline-block;
}

.spd-scale {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}

.spd-scale .k {
  font-size: 12px;
  color: var(--muted);
  margin-bottom: 4px;
}

.spd-scale .v {
  font-size: 16px;
  font-weight: 600;
}
</style>
