<template>
  <div class="d-anim max-w-6xl mx-auto">
    <!-- 加载中 -->
    <div v-if="loading" class="d-card" style="display:flex;align-items:center;justify-content:center;height:320px">
      <span class="d-muted">加载中…</span>
    </div>

    <!-- 未选中 -->
    <div v-else-if="!detail" class="d-card" style="display:flex;align-items:center;justify-content:center;height:320px">
      <span class="d-muted">请从上方选择投顾</span>
    </div>

    <!-- 详情内容 -->
    <template v-else>
      <!-- ① 档案与核心指标（吸顶固定） -->
      <div class="d-card ap-sticky" style="margin-bottom:14px">
        <div class="d-card-b">
          <div>
            <div style="display:flex;align-items:center;gap:10px">
              <span class="d-card-t" style="font-size:17px">{{ detail.info.account_name || detail.info.product_name }}</span>
              <span v-if="detail.info.is_stop === 0" class="d-pill ok">运行中</span>
              <span v-else class="d-pill gray">已停止</span>
              <span v-if="detail.info.data_update_date" class="d-muted d-mono" style="margin-left:auto;font-size:11px">
                数据更新至{{ detail.info.data_update_date }}
              </span>
            </div>
            <div class="d-muted d-mono" style="font-size:11px;margin-top:4px">
              {{ detail.info.account_code || detail.info.product_name }}
              <span v-if="detail.info.product_name_cn" style="margin-left:10px">所属产品: {{ detail.info.product_name_cn }}</span>
              <span v-if="detail.info.invest_logic" style="margin-left:10px">投资逻辑: {{ detail.info.invest_logic }}</span>
              <span v-if="detail.info.invest_cate" style="margin-left:10px">投资范围: {{ detail.info.invest_cate }}</span>
            </div>
          </div>
          <!-- KPI 通栏 -->
          <div class="d-kpis">
            <div><div class="k">总收益</div><div class="v" :class="fmtColorPct(detail.indicators.total_return)">{{ fmtPct(detail.indicators.total_return) }}</div></div>
            <div><div class="k">年化收益</div><div class="v" :class="fmtColorPct(detail.indicators.annual_yield)">{{ fmtPct(detail.indicators.annual_yield) }}</div></div>
            <div><div class="k">夏普</div><div class="v">{{ fmtNum(detail.indicators.sharpe_ratio) }}</div></div>
            <div><div class="k">卡玛</div><div class="v">{{ fmtNum(detail.indicators.kama_ratio) }}</div></div>
            <div><div class="k">信息比率</div><div class="v">{{ fmtNum(detail.indicators.info_ratio) }}</div></div>
            <div><div class="k">最大回撤</div><div class="v" :class="fmtColorPct(detail.indicators.max_drawdown)">{{ fmtPct(detail.indicators.max_drawdown) }}</div></div>
            <div><div class="k">波动率</div><div class="v">{{ fmtPct(detail.indicators.annual_volatility) }}</div></div>
            <div><div class="k">Alpha</div><div class="v">{{ fmtNum(detail.indicators.alpha) }}</div></div>
            <div><div class="k">Beta</div><div class="v">{{ fmtNum(detail.indicators.beta) }}</div></div>
          </div>
        </div>
      </div>

      <!-- ② 收益率走势图 -->
      <div class="d-card">
        <div class="d-card-h">
          <span class="d-card-t">收益率走势图</span>
        </div>
        <div class="d-card-b" style="padding-bottom:10px">
          <!-- 时间段选择器 -->
          <div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap;margin-bottom:6px;margin-left:55px">
            <div class="d-seg">
              <button v-for="p in periods" :key="p.key" :class="selectedPeriod === p.key ? 'on' : ''" @click="selectedPeriod = p.key; changePeriod()">{{ p.label }}</button>
            </div>
            <div v-if="selectedPeriod === 'custom'" style="display:flex;align-items:center;gap:6px">
              <input type="date" v-model="customStart" class="d-ipt" style="font-size:11px;padding:4px 8px;width:130px" @change="changePeriod" />
              <span class="d-muted">至</span>
              <input type="date" v-model="customEnd" class="d-ipt" style="font-size:11px;padding:4px 8px;width:130px" @change="changePeriod" />
            </div>
          </div>
          <!-- 图例 + 收益率 -->
          <div style="display:flex;align-items:center;gap:16px;margin-bottom:8px;padding:4px 0;margin-left:55px">
            <span class="d-leg-i">
              <i class="d-leg-sw" style="background:#9C6B2F"></i>
              <span style="font-size:12px">{{ detail.info.account_name || detail.info.product_name }}</span>
              <span class="d-mono" :style="periodReturn >= 0 ? 'color:#B03A2E;font-size:12px;margin-left:4px' : 'color:#17714B;font-size:12px;margin-left:4px'">{{ periodReturn >= 0 ? '+' : '' }}{{ periodReturn.toFixed(2) }}%</span>
            </span>
          </div>
          <template v-if="(detail.nav_series || []).length">
            <div style="position:relative" @mousemove="updateDomTooltip" @mouseleave="hideChartTooltip">
              <div ref="navChartRef" style="width:100%;height:520px"></div>
              <div
                v-if="zoomLabel.show"
                :style="{ position:'absolute', left: zoomLabel.startX+'px', top:'263px', transform:'translateX(0)', zIndex:99, color:'#8F8A79', fontSize:'10px', fontFamily:'var(--mono)', pointerEvents:'none', whiteSpace:'nowrap' }"
              >
                {{ zoomLabel.startDate }}
              </div>
              <div
                v-if="zoomLabel.show"
                :style="{ position:'absolute', left: zoomLabel.endX+'px', top:'263px', transform:'translateX(-100%)', zIndex:99, color:'#8F8A79', fontSize:'10px', fontFamily:'var(--mono)', pointerEvents:'none', whiteSpace:'nowrap' }"
              >
                {{ zoomLabel.endDate }}
              </div>
              <!-- 自定义 tooltip：同一日期点，上方显示收益率，下方显示动态回撤 -->
              <div v-if="tipData.show" :style="{ position:'absolute', left: tipData.guideX+'px', top:'15px', height:'435px', zIndex:98, borderLeft:'1px dashed #B8B09C', pointerEvents:'none' }"></div>
              <div v-if="tipData.show" :style="{ position:'absolute', left: tipData.x+'px', top:'10px', zIndex:99, background:'#FDFCF8', border:'1px solid #E5E0D2', borderRadius:'4px', padding:'6px 10px', fontSize:'11px', boxShadow:'0 2px 8px rgba(0,0,0,0.08)', pointerEvents:'none', whiteSpace:'nowrap' }">
                <div style="color:#999;margin-bottom:2px">{{ firstChartDate }} 至 {{ tipData.date }}</div>
                <div style="display:flex;align-items:center;gap:6px">
                  <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:#9C6B2F"></span>
                  <span style="color:#666">{{ chartAdvisorName }}</span>
                  <span style="font-weight:600;margin-left:12px">{{ tipData.ret >= 0 ? '+' : '' }}{{ tipData.ret.toFixed(2) }}%</span>
                </div>
              </div>
              <div v-if="tipData.show" :style="{ position:'absolute', left: tipData.x+'px', top:'350px', zIndex:99, background:'#FDFCF8', border:'1px solid #E5E0D2', borderRadius:'4px', padding:'6px 10px', fontSize:'11px', boxShadow:'0 2px 8px rgba(0,0,0,0.08)', pointerEvents:'none', whiteSpace:'nowrap' }">
                <div style="color:#999;margin-bottom:2px">{{ tipData.date }}</div>
                <div style="display:flex;align-items:center;gap:6px">
                  <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:#B03A2E"></span>
                  <span style="color:#666">回撤</span>
                  <span style="font-weight:600;margin-left:12px;color:#B03A2E">{{ tipData.dd.toFixed(2) }}%</span>
                </div>
              </div>
            </div>
          </template>
          <div v-else style="display:flex;align-items:center;justify-content:center;height:480px">
            <span class="d-muted">该投顾暂无净值数据</span>
          </div>
        </div>
      </div>

      <!-- ③ 区间收益（月度 / 年度） -->
      <div class="d-card" style="margin-top:14px">
        <div class="d-card-h">
          <span class="d-card-t">区间收益</span>
          <span class="d-card-x">按月度与年度划分的区间收益率</span>
        </div>
        <div class="d-card-b">
          <template v-if="periodReturnRows.length">
            <div class="pr-scroll">
              <table class="d-table pr-table">
                <thead>
                  <tr>
                    <th>年份</th>
                    <th v-for="m in 12" :key="m">{{ m }}月</th>
                    <th>全年</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="row in periodReturnRows" :key="row.year">
                    <td class="pr-year">{{ row.year }}</td>
                    <td v-for="m in 12" :key="m" class="d-mono pr-c" :style="cellStyle(row.months[m - 1])">
                      {{ fmtCell(row.months[m - 1]) }}
                    </td>
                    <td class="d-mono pr-year-cell" :style="cellStyle(row.yearReturn)">
                      {{ fmtCell(row.yearReturn) }}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
            <!-- 图例 -->
            <div class="pr-legend">
              <template v-for="bucket in legendBuckets" :key="bucket.label">
                <span class="pr-leg-item">
                  <i :style="{ background: bucket.color }"></i>
                  {{ bucket.label }}
                </span>
              </template>
            </div>
          </template>
          <div v-else style="display:flex;align-items:center;justify-content:center;height:160px">
            <span class="d-muted">该投顾暂无净值数据</span>
          </div>
        </div>
      </div>

      <!-- ④ 风险收益指标 -->
      <div class="d-card" style="margin-top:14px">
        <div class="d-card-h">
          <span class="d-card-t">风险收益指标</span>
          <span class="d-card-x">近1年 / 近2年 / 近3年 / 成立以来</span>
        </div>
        <div class="d-card-b">
          <div class="ri-scroll">
            <table class="d-table ri-table">
              <thead>
                <tr>
                  <th style="text-align:left">指标</th>
                  <th>近1年</th>
                  <th>近2年</th>
                  <th>近3年</th>
                  <th>成立以来</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="m in riskMetricDefs" :key="m.key">
                  <td style="text-align:left">{{ m.label }}</td>
                  <td
                    v-for="p in riskPeriods"
                    :key="p"
                    class="d-mono"
                    :class="cellTone(m.key, p)"
                  >{{ fmtRisk(m.key, p) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import * as echarts from 'echarts/core'
import { LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent, MarkLineComponent, DataZoomComponent, TitleComponent, GraphicComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import client from '../../api/client'
import { useAdvisorStore } from '../../stores/advisor'

echarts.use([CanvasRenderer, LineChart, GridComponent, TooltipComponent, LegendComponent, MarkLineComponent, DataZoomComponent, TitleComponent, GraphicComponent])

const advisorStore = useAdvisorStore()
const detail = ref(null)
const loading = ref(false)

// 时间段
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

// 自定义日期（默认近一年）
const today = new Date()
const oneYearAgo = new Date(today)
oneYearAgo.setFullYear(oneYearAgo.getFullYear() - 1)
const fmt = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
const customStart = ref(fmt(oneYearAgo))
const customEnd = ref(fmt(today))

const navChartRef = ref(null)
let navChart = null

// 自定义 tooltip 数据
const emptyTipData = () => ({ show: false, panel: '', x: 0, guideX: 0, date: '', ret: 0, dd: 0 })
const tipData = ref(emptyTipData())
const zoomLabel = ref({ show: false, startDate: '', endDate: '', startX: 55, endX: 55 })
let chartDates = []
let chartCumReturns = []
let chartDrawdowns = []
const chartAdvisorName = ref('')
const firstChartDate = computed(() => chartDates[0] || '')

function isInChartHoverArea(event) {
  const y = event.offsetY
  if (y >= 15 && y <= 265) {
    return true
  } else if (y >= 350 && y <= 450) {
    return true
  }
  return false
}

function getTooltipIndexByOffset(offsetX) {
  const left = 55
  const right = 25
  const width = navChartRef.value?.clientWidth || 0
  const plotWidth = width - left - right
  if (!chartDates.length || plotWidth <= 0 || offsetX < left || offsetX > width - right) return -1
  const ratio = (offsetX - left) / plotWidth
  return Math.min(Math.max(Math.round(ratio * (chartDates.length - 1)), 0), chartDates.length - 1)
}

function updateDomTooltip(event) {
  if (!navChart || !navChartRef.value) return
  const rect = event.currentTarget.getBoundingClientRect()
  const offsetX = event.clientX - rect.left
  const offsetY = event.clientY - rect.top
  if (!isInChartHoverArea({ offsetY })) {
    tipData.value = emptyTipData()
    return
  }

  const idx = getTooltipIndexByOffset(offsetX)
  updateTooltipByIndex(idx)
}

function updateTooltipByIndex(idx) {
  if (idx < 0) {
    tipData.value = emptyTipData()
    return
  }

  const point = navChart.convertToPixel({ xAxisIndex: 0 }, chartDates[idx])
  const chartWidth = navChartRef.value?.clientWidth || 0
  const x = Math.min(Math.max(point + 12, 55), Math.max(chartWidth - 220, 55))
  tipData.value = {
    show: true,
    panel: 'both',
    x,
    guideX: point,
    date: chartDates[idx],
    ret: chartCumReturns[idx],
    dd: chartDrawdowns[idx],
  }
}

function hideChartTooltip() {
  tipData.value = emptyTipData()
}

function updateZoomLabel(start = 0, end = 100) {
  if (!chartDates.length || !navChartRef.value) {
    zoomLabel.value = { show: false, startDate: '', endDate: '', startX: 55, endX: 55 }
    return
  }
  const left = 55
  const right = 25
  const width = navChartRef.value.clientWidth || 0
  const plotWidth = Math.max(width - left - right, 0)
  const startRatio = Math.min(Math.max(Number(start) / 100, 0), 1)
  const endRatio = Math.min(Math.max(Number(end) / 100, 0), 1)
  const last = chartDates.length - 1
  const startIdx = Math.min(Math.max(Math.round(startRatio * last), 0), last)
  const endIdx = Math.min(Math.max(Math.round(endRatio * last), 0), last)
  zoomLabel.value = {
    show: true,
    startDate: chartDates[startIdx],
    endDate: chartDates[endIdx],
    startX: left + plotWidth * startRatio + 4,
    endX: left + plotWidth * endRatio - 4,
  }
}

// 根据时间段过滤净值序列
function filterByPeriod(series) {
  if (!series || !series.length || selectedPeriod.value === 'since') return series
  if (selectedPeriod.value === 'custom') {
    const s = customStart.value ? new Date(customStart.value) : null
    const e = customEnd.value ? new Date(customEnd.value) : null
    return series.filter((d) => {
      const dt = new Date(d.date)
      if (s && dt < s) return false
      if (e && dt > e) return false
      return true
    })
  }
  const now = new Date()
  let startDate
  switch (selectedPeriod.value) {
    case 'ytd': startDate = new Date(now.getFullYear(), 0, 1); break
    case '1m': startDate = new Date(now); startDate.setMonth(startDate.getMonth() - 1); break
    case '3m': startDate = new Date(now); startDate.setMonth(startDate.getMonth() - 3); break
    case '6m': startDate = new Date(now); startDate.setMonth(startDate.getMonth() - 6); break
    case '1y': startDate = new Date(now); startDate.setFullYear(startDate.getFullYear() - 1); break
    default: return series
  }
  return series.filter((s) => new Date(s.date) >= startDate)
}

function changePeriod() {
  hideChartTooltip()
  if (navChart) renderCharts()
}

// 当前时间段内收益率
const periodReturn = computed(() => {
  if (!detail.value?.nav_series) return 0
  const series = recalcSeries(filterByPeriod(detail.value.nav_series))
  if (!series.length) return 0
  return series[series.length - 1].cum_return
})

// 区间收益：按月度 / 年度划分（基于完整净值序列，与时间段选择无关）
const periodReturnRows = computed(() => {
  const series = (detail.value?.nav_series || []).filter((s) => s.nav && s.date)
  if (series.length < 2) return []
  const rets = []
  for (let i = 1; i < series.length; i++) {
    rets.push({
      date: series[i].date,
      ret: series[i].nav / series[i - 1].nav - 1,
    })
  }
  // 起始月的上月末基准
  const first = series[0]
  const yearMap = new Map()
  const push = (year) => {
    let row = yearMap.get(year)
    if (!row) {
      row = { year, months: Array(12).fill(null), yearReturn: 0 }
      yearMap.set(year, row)
    }
    return row
  }
  let prevYear = Number(first.date.slice(0, 4))
  for (const item of rets) {
    const y = Number(item.date.slice(0, 4))
    const m = Number(item.date.slice(5, 7))
    const row = push(y)
    // 日收益按其所属日期归入当月/当年（跨年首段归新年度，符合 月收益=月末净值环比 口径）
    row.months[m - 1] = (1 + (row.months[m - 1] ?? 0)) * (1 + item.ret) - 1
    row.yearReturn = (1 + row.yearReturn) * (1 + item.ret) - 1
    prevYear = y
  }
  const rows = [...yearMap.values()].sort((a, b) => a.year - b.year)
  for (const row of rows) {
    row.months = row.months.map((v) => (v == null ? null : Math.round(v * 10000) / 100))
    row.yearReturn = Math.round(row.yearReturn * 10000) / 100
  }
  return rows
})

// 图例分档（正收益暖色 / 负收益绿色，与站点涨跌配色一致）
const legendBuckets = [
  { label: '≥10%', color: '#7A2E26' },
  { label: '5%~10%', color: '#B03A2E' },
  { label: '0%~5%', color: '#E2B4AE' },
  { label: '-5%~0%', color: '#BCD9C9' },
  { label: '-10%~-5%', color: '#5C9C7B' },
  { label: '≤-10%', color: '#17714B' },
]

function bucketOf(v) {
  if (v == null) return null
  if (v >= 10) return legendBuckets[0]
  if (v >= 5) return legendBuckets[1]
  if (v > 0) return legendBuckets[2]
  if (v > -5) return legendBuckets[3]
  if (v > -10) return legendBuckets[4]
  return legendBuckets[5]
}

function cellStyle(v) {
  const b = bucketOf(v)
  if (!b) return null
  const dark = v >= 10 || v <= -10
  return { background: b.color, color: dark ? '#FDFCF8' : null }
}

function fmtCell(v) {
  if (v == null) return ''
  return (v > 0 ? '+' : '') + v.toFixed(2)
}

// 风险收益指标表
const riskPeriods = ['1y', '2y', '3y', 'since']
const riskMetricDefs = [
  { key: 'annual_yield', label: '年化收益率', kind: 'pct' },
  { key: 'annual_volatility', label: '年化波动率', kind: 'pct' },
  { key: 'max_drawdown', label: '最大回撤', kind: 'pct' },
  { key: 'sharpe_ratio', label: '夏普比率', kind: 'num' },
  { key: 'kama_ratio', label: '卡玛比率', kind: 'num' },
  { key: 'info_ratio', label: '信息比率', kind: 'num' },
  { key: 'alpha', label: 'Alpha', kind: 'num' },
  { key: 'beta', label: 'Beta', kind: 'num' },
]

function riskValue(metric, period) {
  return detail.value?.risk_table?.[metric]?.[period]
}

function fmtRisk(metric, period) {
  const v = riskValue(metric, period)
  if (v == null) return '—'
  const def = riskMetricDefs.find((m) => m.key === metric)
  if (def?.kind === 'pct') return (v > 0 ? '+' : '') + (v * 100).toFixed(2) + '%'
  return Number(v).toFixed(2)
}

// 收益类与回撤类按正负着色
function cellTone(metric, period) {
  const v = riskValue(metric, period)
  if (v == null) return ''
  const def = riskMetricDefs.find((m) => m.key === metric)
  if (!def) return ''
  if (metric === 'beta') return ''
  return v >= 0 ? 'd-up' : 'd-dn'
}

// 以区间起始日为基准重新计算累计收益和回撤
function recalcSeries(series) {
  if (!series.length) return []
  const baseNav = series[0].nav
  if (!baseNav) {
    const baseCum = series[0].cum_return
    return series.map((s) => ({ ...s, cum_return: s.cum_return - baseCum, drawdown: 0 }))
  }
  let peak = baseNav
  return series.map((s) => {
    const cumReturn = (s.nav / baseNav - 1) * 100
    if (s.nav > peak) peak = s.nav
    const drawdown = (s.nav / peak - 1) * 100
    return { ...s, cum_return: cumReturn, drawdown }
  })
}

function fmtPct(v) {
  if (v == null) return '—'
  return (v >= 0 ? '+' : '') + (v * 100).toFixed(2) + '%'
}
function fmtNum(v) {
  if (v == null) return '—'
  return Number(v).toFixed(2)
}
function fmtColorPct(v) {
  if (v == null) return ''
  return v >= 0 ? 'd-up' : 'd-dn'
}

async function loadDetail(pid) {
  loading.value = true
  detail.value = null
  try {
    const { data } = await client.get('/tables/advisor/performance/', { params: { pid } })
    detail.value = data
    loading.value = false
    await nextTick()
    renderCharts()
  } catch (e) {
    console.error('获取投顾详情失败', e)
    loading.value = false
  }
}

// 监听 store 中 selectedPid 变化
watch(() => advisorStore.selectedPid, (pid) => {
  if (pid) loadDetail(pid)
})

function renderCharts() {
  if (!navChartRef.value) return
  if (navChart && navChart.getDom() !== navChartRef.value) {
    navChart.dispose()
    navChart = null
  }
  navChart = navChart || echarts.init(navChartRef.value)

  const rawSeries = filterByPeriod(detail.value?.nav_series || [])
  const series = recalcSeries(rawSeries)
  const dates = series.map((s) => s.date)
  const cumReturns = series.map((s) => s.cum_return)
  const drawdowns = series.map((s) => s.drawdown)
  const advisorName = detail.value?.info?.account_name || detail.value?.info?.product_name || '投顾'

  const maxDrawdown = drawdowns.length ? Math.min(...drawdowns) : 0

  // 存储数据供自定义 tooltip 使用
  chartDates = dates
  chartCumReturns = cumReturns
  chartDrawdowns = drawdowns
  chartAdvisorName.value = advisorName
  updateZoomLabel(0, 100)

  navChart.setOption({
    tooltip: { show: false },
    axisPointer: {
      link: [{ xAxisIndex: 'all' }],
      label: { show: true, formatter: (p) => p.value, backgroundColor: '#9C6B2F' },
    },
    title: [
      { text: '动态回撤', left: 55, top: 315, textStyle: { fontSize: 12, fontWeight: 'normal', color: '#333' } },
      { text: `截止日期：${dates[dates.length - 1] || '—'}`, right: 25, top: 315, textStyle: { fontSize: 11, fontWeight: 'normal', color: '#8F8A79' } },
    ],
    grid: [
      { left: 55, right: 25, top: 15, height: 250 },
      { left: 55, right: 25, top: 350, height: 100 },
    ],
    xAxis: [
      { type: 'category', gridIndex: 0, data: dates, axisLabel: { show: false }, axisLine: { lineStyle: { color: '#E5E0D2' } } },
      { type: 'category', gridIndex: 1, data: dates, axisLabel: { show: false }, axisLine: { lineStyle: { color: '#E5E0D2' } } },
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
      { name: advisorName, type: 'line', xAxisIndex: 0, yAxisIndex: 0, data: cumReturns, lineStyle: { width: 1.5, color: '#9C6B2F' }, itemStyle: { color: '#9C6B2F' }, showSymbol: false },
      { name: '回撤', type: 'line', xAxisIndex: 1, yAxisIndex: 1, data: drawdowns, lineStyle: { width: 1, color: '#B03A2E' }, itemStyle: { color: '#B03A2E' }, areaStyle: { color: 'rgba(176,58,46,0.10)' }, showSymbol: false },
    ],
    graphic: [
      {
        type: 'text', left: 120, top: 318,
        style: { text: `${advisorName}    最大回撤: ${maxDrawdown.toFixed(2)}%`, font: '12px sans-serif', fill: '#999' },
      },
    ],
  })

  navChart.off('dataZoom')
  navChart.on('dataZoom', (event) => {
    const payload = event.batch?.[0] || event
    updateZoomLabel(payload.start ?? 0, payload.end ?? 100)
  })

  // 鼠标离开时隐藏
  navChartRef.value.onmouseleave = hideChartTooltip
}

function handleResize() {
  navChart?.resize()
  const { startX, endX } = zoomLabel.value
  if (zoomLabel.value.show && startX != null && endX != null) {
    const option = navChart?.getOption()
    const slider = option?.dataZoom?.find((z) => z.type === 'slider') || option?.dataZoom?.[1]
    updateZoomLabel(slider?.start ?? 0, slider?.end ?? 100)
  }
}

onMounted(async () => {
  if (!advisorStore.advisors.length) {
    await advisorStore.fetchAdvisors()
  }
  if (advisorStore.selectedPid) {
    loadDetail(advisorStore.selectedPid)
  }
  window.addEventListener('resize', handleResize)
})
onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  navChart?.dispose()
})
</script>

<style scoped>
/* 档案与核心指标卡片吸顶：滚动查看下方图表/表格时保持可见 */
.ap-sticky {
  position: sticky;
  top: 0;
  z-index: 6;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.pr-scroll {
  overflow-x: auto;
}

.pr-table {
  width: 100%;
  table-layout: fixed;
  border-collapse: collapse;
}

.pr-table th,
.pr-table td {
  text-align: center;
  padding: 8px 4px;
  font-size: 12px;
  border: 1px solid var(--line);
}

.pr-table th:first-child,
.pr-table td:first-child {
  width: 64px;
}

.pr-table th:last-child,
.pr-table td:last-child {
  width: 90px;
}

.pr-year {
  font-weight: 600;
  background: var(--soft);
}

.pr-c {
  text-align: center;
}

.pr-year-cell {
  font-weight: 600;
}

.pr-legend {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-top: 10px;
  flex-wrap: wrap;
}

.pr-leg-item {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 11px;
  color: var(--muted);
}

.pr-leg-item i {
  width: 22px;
  height: 10px;
  border-radius: 2px;
  display: inline-block;
}

.ri-scroll {
  overflow-x: auto;
}

.ri-table {
  width: 100%;
}

.ri-table th,
.ri-table td {
  padding: 9px 12px;
}

.ri-table th:not(:first-child),
.ri-table td:not(:first-child) {
  text-align: right;
}

.ri-table thead th {
  position: sticky;
  top: 0;
  background: var(--soft);
}

.ri-table tbody tr:nth-child(odd) {
  background: color-mix(in srgb, var(--soft) 40%, transparent);
}
</style>
