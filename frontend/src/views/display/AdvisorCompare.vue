<template>
  <div class="d-anim max-w-6xl mx-auto">
    <!-- 页头 + 全局对比区间 -->
    <div class="d-page-head" style="align-items:center;gap:12px;flex-wrap:wrap">
      <div>
        <h1>投顾对比</h1>
        <div class="sub">选择 2~10 位投顾，对比累计收益、回撤与风险收益指标（同名多账户合并口径）</div>
      </div>
      <div class="ac-gp">
        <span class="ac-gp-label">对比区间</span>
        <div class="d-seg">
          <button
            v-for="p in periods"
            :key="p.key"
            :class="selectedPeriod === p.key ? 'on' : ''"
            @click="selectedPeriod = p.key"
          >{{ p.label }}</button>
        </div>
        <div v-if="selectedPeriod === 'custom'" style="display:flex;align-items:center;gap:6px">
          <input
            v-model="customStart"
            type="date"
            name="compare_start_date"
            class="d-ipt"
            style="font-size:11px;padding:4px 8px;width:130px"
          />
          <span class="d-muted">至</span>
          <input
            v-model="customEnd"
            type="date"
            name="compare_end_date"
            class="d-ipt"
            style="font-size:11px;padding:4px 8px;width:130px"
          />
        </div>
      </div>
    </div>

    <!-- ① 投顾选择器 -->
    <div class="d-card" style="margin-bottom:14px">
      <div class="d-card-h">
        <span class="d-card-t">选择投顾</span>
        <span class="d-card-x">最多 10 位 · 支持名称 / 账号 / pid 搜索</span>
      </div>
      <div class="d-card-b ac-picker">
        <div class="ac-search-wrap">
          <input
            v-model="searchText"
            class="ac-search"
            type="text"
            placeholder="搜索并添加投顾…"
            @focus="showDropdown = true"
            @input="onSearch"
            @keydown="onKeydown"
          />
          <div v-if="showDropdown && filteredCandidates.length" class="ac-dropdown">
            <div
              v-for="(c, i) in filteredCandidates"
              :key="c.pid"
              class="ac-opt"
              :class="{ hover: i === hoverIdx, picked: isPicked(c.pid) }"
              @click="addAdvisor(c)"
              @mouseenter="hoverIdx = i"
            >
              <span>{{ c.account_name || c.product_name }}</span>
              <span class="d-muted d-mono ac-opt-x">
                {{ c.account_code }}<template v-if="c.account_count > 1"> · {{ c.account_count }}账户</template>
                <template v-if="isPicked(c.pid)"> · 已选</template>
              </span>
            </div>
          </div>
        </div>
        <div class="ac-chips">
          <span v-if="!selected.length" class="d-muted" style="font-size:12px">尚未选择，从上方搜索添加投顾开始对比</span>
          <span
            v-for="(s, i) in selected"
            :key="s.pid"
            class="ac-chip"
            :style="{ borderColor: palette[i], background: `${palette[i]}12` }"
          >
            <span class="ac-dot" :style="{ background: palette[i] }"></span>
            {{ s.name }}
            <span v-if="s.loading" class="d-muted d-mono" style="font-size:10px">加载中…</span>
            <span class="ac-chip-x" @click="removeAdvisor(s.pid)">×</span>
          </span>
        </div>
      </div>
    </div>

    <!-- 加载中 -->
    <div v-if="anyLoading" class="d-card" style="display:flex;align-items:center;justify-content:center;height:220px">
      <span class="d-muted">加载投顾业绩数据…</span>
    </div>

    <!-- 已选不足提示 -->
    <div
      v-else-if="selected.length && selected.length < 2"
      class="d-card"
      style="display:flex;align-items:center;justify-content:center;height:220px"
    >
      <span class="d-muted">再添加 1 位投顾即可开始对比</span>
    </div>

    <!-- 对比内容 -->
    <template v-else-if="selected.length >= 2">
      <!-- ② 曲线对比 -->
      <div class="d-card">
        <div class="d-card-h">
          <span class="d-card-t">累计收益率与回撤对比</span>
          <label class="ac-bench-toggle">
            <input v-model="showBench" type="checkbox" @change="renderChart" />
            叠加南华商品指数
          </label>
        </div>
        <div class="d-card-b" style="padding-bottom:8px">
          <!-- 区间收益摘要 -->
          <div class="ac-psum">
            <span v-for="(item, i) in windowSummary" :key="item.pid" class="ac-psum-item">
              <span class="ac-dot" :style="{ background: palette[i % palette.length] }"></span>
              <span class="ac-psum-name">{{ item.name }}</span>
              <span class="d-mono ac-psum-ret" :class="item.ret >= 0 ? 'ac-up' : 'ac-dn'">{{ fmtSigned(item.ret) }}%</span>
              <span class="d-muted d-mono ac-psum-dd">回撤 {{ fmtSigned(item.dd) }}%</span>
            </span>
          </div>
          <div ref="chartRef" style="height:480px"></div>
          <div class="d-muted d-mono" style="font-size:10.5px;text-align:right;margin-top:2px">
            {{ selectedPeriod === 'aligned' && alignedStartDate
              ? `注：起点对齐——对比自全部所选投顾的首个共同数据日 ${alignedStartDate} 起`
              : '注：所选区间内各曲线以区间首日重基准；成立晚于区间起点的投顾从其首个数据日起算' }}
          </div>
        </div>
      </div>

      <!-- ③ 区间收益对比 -->
      <div class="d-card" style="margin-top:14px">
        <div class="d-card-h">
          <div>
            <span class="d-card-t">区间收益对比</span>
            <span class="d-card-x" style="margin-left:10px">口径：{{ currentPeriodLabel }} · 月收益 = 月内净值环比连乘</span>
          </div>
        </div>
        <div class="d-card-b">
          <template v-if="returnYears.length">
            <div class="acp-scroll">
              <table class="acp-table">
                <thead>
                  <tr>
                    <th>年份</th>
                    <th style="width:120px">投顾</th>
                    <th v-for="m in 12" :key="m">{{ m }}月</th>
                    <th>全年</th>
                  </tr>
                </thead>
                <tbody>
                  <template v-for="year in returnYears" :key="year">
                    <tr v-for="(s, i) in selected" :key="`${year}-${s.pid}`">
                      <td v-if="i === 0" :rowspan="selected.length" class="acp-year">{{ year }}</td>
                      <td class="acp-label">
                        <span class="ac-dot" :style="{ background: palette[i % palette.length] }"></span>
                        {{ s.name }}
                      </td>
                      <td
                        v-for="m in 12"
                        :key="m"
                        class="d-mono acp-c"
                        :style="cellStyle(monthCell(s, year, m))"
                      >{{ fmtCell(monthCell(s, year, m)) }}</td>
                      <td class="d-mono acp-c acp-year-cell" :style="cellStyle(yearCell(s, year))">
                        {{ fmtCell(yearCell(s, year)) }}
                      </td>
                    </tr>
                  </template>
                </tbody>
              </table>
            </div>
            <!-- 图例 -->
            <div class="acp-legend">
              <span v-for="bucket in legendBuckets" :key="bucket.label" class="acp-leg-item">
                <i :style="{ background: bucket.color }"></i>
                {{ bucket.label }}
              </span>
            </div>
          </template>
          <div v-else style="display:flex;align-items:center;justify-content:center;height:160px">
            <span class="d-muted">所选投顾暂无净值数据</span>
          </div>
        </div>
      </div>

      <!-- ④ 指标与信息对比 -->
      <div class="d-card" style="margin-top:14px">
        <div class="d-card-h">
          <div>
            <span class="d-card-t">风险收益指标对比</span>
            <span class="d-card-x" style="margin-left:10px">口径：{{ currentPeriodLabel }}</span>
          </div>
        </div>
        <div class="d-card-b" style="padding:0">
          <table class="ac-table">
            <thead>
              <tr>
                <th class="ac-th-label">指标</th>
                <th v-for="(s, i) in selected" :key="s.pid" class="ac-th-col">
                  <span class="ac-dot" :style="{ background: palette[i] }"></span>
                  <router-link class="ac-col-link" :to="`/display/advisor/detail/${s.pid}?merged=1`">{{ s.name }}</router-link>
                </th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in metricRows" :key="row.key">
                <td class="ac-td-label">
                  {{ row.label }}
                  <span v-if="row.key === 'total_return'" class="d-muted" style="font-size:10px">（区间）</span>
                </td>
                <td
                  v-for="(s, i) in selected"
                  :key="s.pid"
                  class="ac-td-val"
                  :class="valueClass(row, s)"
                  :style="{ borderLeft: i > 0 ? '1px solid var(--line2)' : '' }"
                >{{ cellValue(row, s) }}</td>
              </tr>
              <tr class="ac-tr-gap"><td :colspan="selected.length + 1"></td></tr>
              <tr v-for="row in infoRows" :key="row.key">
                <td class="ac-td-label ac-td-info">{{ row.label }}</td>
                <td
                  v-for="(s, i) in selected"
                  :key="s.pid"
                  class="ac-td-val ac-td-info"
                  :style="{ borderLeft: i > 0 ? '1px solid var(--line2)' : '' }"
                >
                  <template v-if="row.key === 'is_stop'">
                    <span v-if="infoOf(s).is_stop === 0" class="d-pill ok">运行中</span>
                    <span v-else class="d-pill gray">已停止</span>
                  </template>
                  <template v-else>{{ infoCell(row, s) }}</template>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </template>

    <!-- 未选择 -->
    <div v-else class="d-card" style="display:flex;align-items:center;justify-content:center;height:320px">
      <span class="d-muted">从上方搜索并添加 2~10 位投顾，开始对比分析</span>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import * as echarts from 'echarts/core'
import { LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent, DataZoomComponent, TitleComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import client from '../../api/client'

echarts.use([CanvasRenderer, LineChart, GridComponent, TooltipComponent, LegendComponent, DataZoomComponent, TitleComponent])

const route = useRoute()
const router = useRouter()

// 对比投顾配色（与主题色协调的 10 色调色板）
const palette = [
  '#9C6B2F', '#33608C', '#B03A2E', '#17714B', '#7A4A8C',
  '#B07A1F', '#3E7CB1', '#8C3A5C', '#4F6D4A', '#5C6B7A',
]
const MAX_PICK = 10

const candidates = ref([])      // 候选列表（merge=1 合并口径）
const searchText = ref('')
const showDropdown = ref(false)
const hoverIdx = ref(-1)

const selected = ref([])        // [{pid, name, loading}]
const details = ref({})         // pid -> 详情 {info, indicators, risk_table, nav_series, benchmark_series}
const showBench = ref(true)

const chartRef = ref(null)
let chart = null

// ---------- 全局对比时间区间（驱动曲线图 / 区间收益 / 风险指标） ----------
const periods = [
  { key: 'ytd', label: '今年以来' },
  { key: '1m', label: '近1月' },
  { key: '3m', label: '近3月' },
  { key: '6m', label: '近6月' },
  { key: '1y', label: '近1年' },
  { key: 'since', label: '成立以来' },
  { key: 'aligned', label: '起点对齐' },
  { key: 'custom', label: '自定义' },
]
const selectedPeriod = ref('since')

// 自定义日期（默认近一年）
const today = new Date()
const oneYearAgo = new Date(today)
oneYearAgo.setFullYear(oneYearAgo.getFullYear() - 1)
const fmtDate = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
const customStart = ref(fmtDate(oneYearAgo))
const customEnd = ref(fmtDate(today))

// 起点对齐：全部所选投顾序列的首个共同数据日（各首日的最大值，即交集起点）
const alignedStartDate = computed(() => {
  const firsts = []
  for (const s of selected.value) {
    const series = details.value[s.pid]?.nav_series
    if (series?.length) firsts.push(series[0].date)
  }
  return firsts.length ? firsts.sort()[firsts.length - 1] : null
})

// 按所选时间段过滤序列（与业绩详情页同口径）
function filterByPeriod(series) {
  if (!series || !series.length || selectedPeriod.value === 'since') return series || []
  if (selectedPeriod.value === 'aligned') {
    const start = alignedStartDate.value
    if (!start) return []
    return (series || []).filter((x) => x.date >= start)
  }
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
    default: return series || []
  }
  return (series || []).filter((x) => new Date(x.date) >= startDate)
}

// 过滤 + 区间内重基准：累计收益/回撤均以区间首日重新计算（%）
function windowSeries(navSeries) {
  const arr = filterByPeriod(navSeries)
  if (!arr.length) return []
  const base = arr[0].nav
  let peak = arr[0].nav
  return arr.map((p) => {
    peak = Math.max(peak, p.nav)
    return {
      date: p.date,
      cum: base ? (p.nav / base - 1) * 100 : 0,
      dd: peak ? (p.nav / peak - 1) * 100 : 0,
    }
  })
}

// 区间收益摘要：各投顾所选区间总收益与区间最大回撤
const windowSummary = computed(() =>
  selected.value.map((s) => {
    const d = details.value[s.pid]
    const arr = d ? filterByPeriod(d.nav_series || []) : []
    if (arr.length < 2) return { pid: s.pid, name: s.name, ret: null, dd: null }
    const base = arr[0].nav
    let peak = arr[0].nav
    let maxDd = 0
    for (const p of arr) {
      peak = Math.max(peak, p.nav)
      maxDd = Math.min(maxDd, p.nav / peak - 1)
    }
    return {
      pid: s.pid,
      name: s.name,
      ret: (arr[arr.length - 1].nav / base - 1) * 100,
      dd: maxDd * 100,
    }
  }),
)

function fmtSigned(v) {
  if (v == null || !Number.isFinite(v)) return '—'
  return (v >= 0 ? '+' : '') + v.toFixed(2)
}

const anyLoading = computed(() => selected.value.some((s) => s.loading))

// ---------- 选择器 ----------
const filteredCandidates = computed(() => {
  const q = searchText.value.trim().toLowerCase()
  const list = q
    ? candidates.value.filter((c) =>
        [c.account_name, c.product_name, c.account_code, String(c.pid)]
          .some((f) => (f || '').toLowerCase().includes(q)))
    : candidates.value
  return list.slice(0, 30)
})

function isPicked(pid) {
  return selected.value.some((s) => s.pid === pid)
}

function onSearch() {
  hoverIdx.value = -1
  showDropdown.value = true
}

function onKeydown(e) {
  const list = filteredCandidates.value
  if (!list.length) return
  if (e.key === 'ArrowDown') {
    e.preventDefault()
    hoverIdx.value = Math.min(hoverIdx.value + 1, list.length - 1)
  } else if (e.key === 'ArrowUp') {
    e.preventDefault()
    hoverIdx.value = Math.max(hoverIdx.value - 1, 0)
  } else if (e.key === 'Enter') {
    e.preventDefault()
    addAdvisor(list[Math.max(hoverIdx.value, 0)])
  } else if (e.key === 'Escape') {
    showDropdown.value = false
  }
}

function addAdvisor(c) {
  if (isPicked(c.pid)) return
  if (selected.value.length >= MAX_PICK) return
  selected.value.push({ pid: c.pid, name: c.account_name || c.product_name, loading: true })
  searchText.value = ''
  showDropdown.value = false
  loadDetail(c.pid)
  syncQuery()
}

function removeAdvisor(pid) {
  selected.value = selected.value.filter((s) => s.pid !== pid)
  syncQuery()
  nextTick(() => { if (selected.value.length >= 2) renderChart() })
}

function syncQuery() {
  router.replace({
    query: {
      ...route.query,
      pids: selected.value.length ? selected.value.map((s) => s.pid).join(',') : undefined,
    },
  })
}

// ---------- 数据加载 ----------
async function loadDetail(pid) {
  try {
    const { data } = await client.get('/tables/advisor/performance/', { params: { pid, merge: 1 } })
    details.value = { ...details.value, [pid]: data }
  } catch (e) {
    console.error('获取投顾详情失败', e)
    details.value = { ...details.value, [pid]: null }
  } finally {
    const s = selected.value.find((x) => x.pid === pid)
    if (s) s.loading = false
    nextTick(() => { if (selected.value.length >= 2 && !anyLoading.value) renderChart() })
  }
}

// ---------- 图表 ----------
function round2(v) {
  return Math.round(v * 100) / 100
}

function benchSeriesOf() {
  // 取序列最长的投顾的基准指数（同一指数，只是对齐日期不同）
  let best = null
  for (const s of selected.value) {
    const d = details.value[s.pid]
    const len = d?.benchmark_series?.length || 0
    if (len > (best?.len || 0)) best = { len, series: d.benchmark_series }
  }
  return best?.series || []
}

// 基准指数在所选区间内重基准（缺失日沿用前值），返回 [[date, cum%]]
function windowBenchSeries() {
  const arr = filterByPeriod(benchSeriesOf())
  if (!arr.length) return []
  const out = []
  let first = null
  for (const p of arr) {
    if (p.cum_return == null) continue
    if (first === null) first = p.cum_return
    out.push([p.date, round2(((100 + p.cum_return) / (100 + first) - 1) * 100)])
  }
  return out
}

function renderChart() {
  if (!chartRef.value || selected.value.length < 2) return
  if (chart && chart.getDom() !== chartRef.value) {
    chart.dispose()
    chart = null
  }
  chart = chart || echarts.init(chartRef.value)

  const lineSeries = []
  const legendData = []
  selected.value.forEach((s, i) => {
    const d = details.value[s.pid]
    const win = d ? windowSeries(d.nav_series) : []
    if (!win.length) return
    const color = palette[i % palette.length]
    legendData.push(s.name)
    lineSeries.push({
      name: s.name,
      type: 'line',
      xAxisIndex: 0,
      yAxisIndex: 0,
      data: win.map((p) => [p.date, round2(p.cum)]),
      lineStyle: { width: 1.6, color },
      itemStyle: { color },
      showSymbol: false,
      z: 5,
      emphasis: { focus: 'series' },
    })
    lineSeries.push({
      name: `${s.name}·回撤`,
      type: 'line',
      xAxisIndex: 1,
      yAxisIndex: 1,
      data: win.map((p) => [p.date, round2(p.dd)]),
      lineStyle: { width: 1, color },
      itemStyle: { color },
      showSymbol: false,
      areaStyle: { color: `${color}1A` },
    })
  })
  if (showBench.value) {
    const bench = windowBenchSeries()
    if (bench.length) {
      legendData.push('南华商品指数')
      lineSeries.push({
        name: '南华商品指数',
        type: 'line',
        xAxisIndex: 0,
        yAxisIndex: 0,
        data: bench,
        lineStyle: { width: 1.1, color: '#8A8A8A', type: 'dashed' },
        itemStyle: { color: '#8A8A8A' },
        showSymbol: false,
      })
    }
  }

  const tooltipBase = {
    trigger: 'axis',
    backgroundColor: '#FDFCF8',
    borderColor: '#E5E0D2',
    textStyle: { color: '#20283A', fontSize: 11, fontFamily: 'IBM Plex Mono, Menlo, monospace' },
  }

  chart.setOption(
    {
      tooltip: { ...tooltipBase, valueFormatter: (v) => (v == null ? '—' : `${Number(v).toFixed(2)}%`) },
      legend: {
        top: 0,
        data: legendData,
        textStyle: { fontSize: 11, color: '#20283A' },
        inactiveColor: '#C9C2AE',
      },
      axisPointer: { link: [{ xAxisIndex: 'all' }] },
      title: {
        text: '动态回撤',
        left: 55,
        top: 330,
        textStyle: { fontSize: 12, fontWeight: 'normal', color: '#333' },
      },
      grid: [
        { left: 55, right: 25, top: 30, height: 265 },
        { left: 55, right: 25, top: 355, height: 90 },
      ],
      xAxis: [
        { type: 'time', gridIndex: 0, axisLabel: { show: false }, axisLine: { lineStyle: { color: '#E5E0D2' } } },
        { type: 'time', gridIndex: 1, axisLabel: { fontSize: 10, color: '#8F8A79', hideOverlap: true }, axisLine: { lineStyle: { color: '#E5E0D2' } }, splitLine: { show: false } },
      ],
      yAxis: [
        { type: 'value', gridIndex: 0, scale: true, axisLabel: { fontSize: 10, formatter: '{value}%' }, splitLine: { lineStyle: { color: '#EFEAE0' } } },
        { type: 'value', gridIndex: 1, max: 0, axisLabel: { fontSize: 10, formatter: '{value}%' }, splitLine: { lineStyle: { color: '#EFEAE0' } } },
      ],
      dataZoom: [
        { type: 'inside', xAxisIndex: [0, 1] },
        { type: 'slider', xAxisIndex: [0, 1], top: 290, height: 18, borderColor: '#E5E0D2', fillerColor: 'rgba(156,107,47,0.08)', handleStyle: { color: '#9C6B2F' }, textStyle: { fontSize: 10 } },
      ],
      series: lineSeries,
    },
    { notMerge: true },
  )
}

function handleResize() {
  chart?.resize()
}

// 时间区间变化 → 重绘曲线图（摘要条/热力表/指标表均为响应式自动更新）
watch([selectedPeriod, customStart, customEnd], () => renderChart())

// 当前区间显示名（自定义显示具体起止，起点对齐显示共同起点）
const currentPeriodLabel = computed(() => {
  if (selectedPeriod.value === 'custom') return `${customStart.value || '…'} ~ ${customEnd.value || '…'}`
  if (selectedPeriod.value === 'aligned') {
    return alignedStartDate.value ? `起点对齐（自${alignedStartDate.value}）` : '起点对齐'
  }
  return periods.find((p) => p.key === selectedPeriod.value)?.label || ''
})

// ---------- 指标对比表（按全局区间现算） ----------
// 基准指数日收益 {date: r}：由累计收益序列差分（缺失日沿用前值，与后端口径一致）
function benchDailyRets(benchSeries) {
  const rets = {}
  let prev = null
  for (const p of benchSeries || []) {
    if (p.cum_return == null) continue
    if (prev !== null) rets[p.date] = (100 + p.cum_return) / (100 + prev) - 1
    prev = p.cum_return
  }
  return rets
}

// 区间风险指标：与后端 _nav_window_metrics 同公式（小数口径，无风险利率 1.5%，252 日年化）
function windowMetrics(navArr, benchRets) {
  const empty = Object.fromEntries(
    ['annual_yield', 'annual_volatility', 'max_drawdown', 'sharpe_ratio', 'kama_ratio', 'info_ratio', 'alpha', 'beta']
      .map((k) => [k, null]),
  )
  if (!navArr || navArr.length < 2) return empty

  const rets = []
  for (let i = 1; i < navArr.length; i++) rets.push(navArr[i].nav / navArr[i - 1].nav - 1)
  const n = rets.length
  const total = navArr[n].nav / navArr[0].nav - 1
  const annualYield = Math.pow(1 + total, 252 / n) - 1
  const mean = rets.reduce((a, b) => a + b, 0) / n
  const sampleVar = n >= 2 ? rets.reduce((a, b) => a + (b - mean) ** 2, 0) / (n - 1) : null
  const annualVol = sampleVar != null ? Math.sqrt(sampleVar) * Math.sqrt(252) : null
  let peak = navArr[0].nav
  let maxDd = 0
  for (const p of navArr) {
    peak = Math.max(peak, p.nav)
    maxDd = Math.min(maxDd, p.nav / peak - 1)
  }
  const sharpe = annualVol ? (annualYield - 0.015) / annualVol : null
  const kama = maxDd < 0 ? annualYield / Math.abs(maxDd) : null

  let infoRatio = null
  let alpha = null
  let beta = null
  if (benchRets) {
    const pr = []
    const br = []
    for (let i = 1; i < navArr.length; i++) {
      const b = benchRets[navArr[i].date]
      if (b != null) {
        pr.push(navArr[i].nav / navArr[i - 1].nav - 1)
        br.push(b)
      }
    }
    if (pr.length >= 3) {
      const mp = pr.reduce((a, b) => a + b, 0) / pr.length
      const mb = br.reduce((a, b) => a + b, 0) / br.length
      const m = pr.length
      const varB = br.reduce((a, b) => a + (b - mb) ** 2, 0) / m
      const covPB = pr.reduce((a, v, i) => a + (v - mp) * (br[i] - mb), 0) / m
      if (varB > 0) {
        beta = covPB / varB
        const annP = Math.pow(1 + mp, 252) - 1
        const annB = Math.pow(1 + mb, 252) - 1
        alpha = (annP - 0.015) - beta * (annB - 0.015)
      }
      const excess = pr.map((v, i) => v - br[i])
      const me = excess.reduce((a, b) => a + b, 0) / excess.length
      const teVar = excess.reduce((a, b) => a + (b - me) ** 2, 0) / excess.length
      const te = Math.sqrt(teVar) * Math.sqrt(252)
      if (te > 0) infoRatio = (me * 252) / te
    }
  }

  return {
    annual_yield: annualYield,
    annual_volatility: annualVol,
    max_drawdown: maxDd,
    sharpe_ratio: sharpe,
    kama_ratio: kama,
    info_ratio: infoRatio,
    alpha,
    beta,
  }
}

// 各投顾在当前区间的指标 {pid: metrics}
const windowMetricsByPid = computed(() => {
  const map = {}
  for (const s of selected.value) {
    const d = details.value[s.pid]
    if (!d) {
      map[s.pid] = null
      continue
    }
    map[s.pid] = windowMetrics(filterByPeriod(d.nav_series || []), benchDailyRets(d.benchmark_series))
  }
  return map
})

const metricRows = [
  { key: 'total_return', label: '总收益', kind: 'pct' },
  { key: 'annual_yield', label: '年化收益', kind: 'pct' },
  { key: 'annual_volatility', label: '年化波动', kind: 'pct' },
  { key: 'max_drawdown', label: '最大回撤', kind: 'pct' },
  { key: 'sharpe_ratio', label: '夏普比率', kind: 'ratio' },
  { key: 'kama_ratio', label: '卡玛比率', kind: 'ratio' },
  { key: 'info_ratio', label: '信息比率', kind: 'ratio' },
  { key: 'alpha', label: 'Alpha', kind: 'pct' },
  { key: 'beta', label: 'Beta', kind: 'ratio' },
]
const infoRows = [
  { key: 'is_stop', label: '运行状态' },
  { key: 'invest_logic', label: '投资逻辑' },
  { key: 'invest_cate', label: '投资范围' },
  { key: 'account_count', label: '账户数' },
  { key: 'cum_investment', label: '累计投资' },
  { key: 'data_update_date', label: '数据更新至' },
]

function infoOf(s) {
  return details.value[s.pid]?.info || {}
}

function metricValue(row, s) {
  if (row.key === 'total_return') {
    const item = windowSummary.value.find((x) => x.pid === s.pid)
    return item?.ret == null ? null : item.ret / 100
  }
  return windowMetricsByPid.value[s.pid]?.[row.key] ?? null
}

function cellValue(row, s) {
  const v = metricValue(row, s)
  if (v == null) return '—'
  if (row.kind === 'pct') return `${(v * 100).toFixed(2)}%`
  return Number(v).toFixed(2)
}

// 每行最优值高亮：收益/比率类取最大，回撤/波动取绝对值最小
function valueClass(row, s) {
  const v = metricValue(row, s)
  if (v == null || selected.value.length < 2) return ''
  const vals = selected.value.map((x) => metricValue(row, x)).filter((x) => x != null)
  if (vals.length < 2) return ''
  const lowerBetter = row.key === 'max_drawdown' || row.key === 'annual_volatility'
  const best = lowerBetter
    ? vals.reduce((a, b) => (Math.abs(a) <= Math.abs(b) ? a : b))
    : Math.max(...vals)
  return v === best ? 'ac-best' : ''
}

function fmtMoney(v) {
  if (v == null || v === '') return '—'
  const n = Number(v)
  if (Math.abs(n) >= 100000000) return `${(n / 100000000).toFixed(2)}亿`
  if (Math.abs(n) >= 10000) return `${(n / 10000).toFixed(0)}万`
  return n.toLocaleString('zh-CN', { maximumFractionDigits: 0 })
}

// ---------- 区间收益（月度 / 年度，与业绩详情页同口径） ----------
// 净值序列 → {年份: {months(12), yearReturn}}，月收益 = 月内净值环比连乘，单位 %
function monthlyReturnsByYear(navSeries) {
  const series = (navSeries || []).filter((s) => s.nav && s.date)
  if (series.length < 2) return {}
  const yearMap = new Map()
  const push = (year) => {
    let row = yearMap.get(year)
    if (!row) {
      row = { year, months: Array(12).fill(null), yearReturn: 0 }
      yearMap.set(year, row)
    }
    return row
  }
  for (let i = 1; i < series.length; i++) {
    const ret = series[i].nav / series[i - 1].nav - 1
    const y = Number(series[i].date.slice(0, 4))
    const m = Number(series[i].date.slice(5, 7))
    const row = push(y)
    row.months[m - 1] = (1 + (row.months[m - 1] ?? 0)) * (1 + ret) - 1
    row.yearReturn = (1 + row.yearReturn) * (1 + ret) - 1
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

const periodReturns = computed(() => {
  const map = {}
  for (const s of selected.value) {
    const d = details.value[s.pid]
    map[s.pid] = d ? monthlyReturnsByYear(filterByPeriod(d.nav_series || [])) : {}
  }
  return map
})

const returnYears = computed(() => {
  const ys = new Set()
  for (const by of Object.values(periodReturns.value)) {
    Object.keys(by).forEach((y) => ys.add(Number(y)))
  }
  // 年份倒序：最新年份在前
  return [...ys].sort((a, b) => b - a)
})

function monthCell(s, year, m) {
  return periodReturns.value[s.pid]?.[year]?.months[m - 1] ?? null
}

function yearCell(s, year) {
  return periodReturns.value[s.pid]?.[year]?.yearReturn ?? null
}

// 热力色阶（与业绩详情页区间收益一致）
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

function infoCell(row, s) {
  const info = infoOf(s)
  const v = info[row.key]
  if (row.key === 'cum_investment') return fmtMoney(v)
  if (v == null || v === '') return '—'
  return String(v)
}

// ---------- 初始化 ----------
async function fetchCandidates() {
  try {
    const { data } = await client.get('/tables/advisor/performance/', { params: { merge: 1 } })
    candidates.value = data
  } catch (e) {
    console.error('获取投顾列表失败', e)
  }
}

onMounted(async () => {
  await fetchCandidates()
  // 从 URL pids 恢复已选投顾
  const pids = String(route.query.pids || '')
    .split(',')
    .map((x) => Number(x))
    .filter((x) => Number.isFinite(x) && x > 0)
    .slice(0, MAX_PICK)
  for (const pid of pids) {
    const c = candidates.value.find((x) => x.pid === pid)
    if (c) addAdvisor(c)
  }
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  chart?.dispose()
})
</script>

<style scoped>
/* ---------- 选择器 ---------- */
.ac-picker { display: flex; flex-direction: column; gap: 12px; }
.ac-search-wrap { position: relative; }
.ac-search {
  width: 100%;
  border: 1px solid var(--line);
  background: var(--card);
  border-radius: 4px;
  padding: 8px 12px;
  font-size: 13px;
  font-family: var(--sans);
  color: var(--ink);
  outline: none;
}
.ac-search:focus { border-color: #C9C2AE; }
.ac-dropdown {
  position: absolute;
  top: calc(100% + 4px);
  left: 0; right: 0;
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: 4px;
  box-shadow: 0 8px 24px rgba(32, 40, 58, 0.10);
  max-height: 264px;
  overflow-y: auto;
  z-index: 30;
}
.ac-opt {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 12px;
  padding: 8px 12px;
  font-size: 12.5px;
  cursor: pointer;
}
.ac-opt.hover { background: var(--soft); }
.ac-opt.picked { color: var(--muted); cursor: default; }
.ac-opt-x { font-size: 10.5px; white-space: nowrap; }

.ac-chips { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }
.ac-chip {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  border: 1px solid;
  border-radius: 999px;
  padding: 4px 8px 4px 12px;
  font-size: 12.5px;
}
.ac-chip-x {
  cursor: pointer;
  color: var(--muted);
  font-size: 14px;
  line-height: 1;
  padding: 0 4px;
  border-radius: 50%;
}
.ac-chip-x:hover { color: var(--up); background: rgba(176, 58, 46, 0.08); }
.ac-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; display: inline-block; }

.ac-bench-toggle {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 11.5px;
  color: var(--muted);
  cursor: pointer;
  user-select: none;
}
.ac-bench-toggle input { accent-color: #9C6B2F; }

/* ---------- 对比表 ---------- */
.ac-table { width: 100%; border-collapse: collapse; }
.ac-table th { padding: 11px 16px; border-bottom: 1px solid var(--line); text-align: right; font-weight: 600; }
.ac-table td { padding: 7px 16px; }
.ac-th-label, .ac-td-label { text-align: left; }
.ac-th-label { font-size: 11px; color: var(--muted); letter-spacing: 0.05em; }
.ac-th-col { display: table-cell; white-space: nowrap; }
.ac-col-link { color: var(--ink); text-decoration: none; border-bottom: 1px dotted rgba(156, 107, 47, 0.5); }
.ac-col-link:hover { color: #9C6B2F; }
.ac-td-label { font-size: 12px; color: var(--ink); }
.ac-td-val {
  text-align: right;
  font-family: var(--mono);
  font-size: 12.5px;
  white-space: nowrap;
}
.ac-td-val.ac-best { color: #17714B; font-weight: 600; }
.ac-td-info { color: var(--muted); font-size: 11.5px; }
.ac-td-info.ac-td-val { font-size: 11.5px; }
.ac-tr-gap td { padding: 0; height: 10px; border-bottom: 1px solid var(--line2); }
.ac-table tbody tr:not(.ac-tr-gap):hover { background: rgba(239, 235, 223, 0.4); }

/* ---------- 区间收益热力表 ---------- */
.acp-scroll { overflow-x: auto; }
.acp-table { width: 100%; table-layout: fixed; border-collapse: collapse; }
.acp-table th,
.acp-table td { text-align: center; padding: 7px 4px; font-size: 12px; border: 1px solid var(--line); }
.acp-table th { color: var(--muted); font-weight: 500; font-size: 10.5px; letter-spacing: 0.08em; white-space: nowrap; }
.acp-table th:first-child,
.acp-table td:first-child { width: 58px; }
.acp-table th:last-child,
.acp-table td:last-child { width: 90px; }
.acp-year { font-weight: 600; background: var(--soft); font-family: var(--mono); }
.acp-label { white-space: nowrap; text-align: left; padding-left: 10px; font-size: 11.5px; }
.acp-c { text-align: center; }
.acp-year-cell { font-weight: 600; }
.acp-legend { display: flex; align-items: center; gap: 14px; margin-top: 10px; flex-wrap: wrap; }
.acp-leg-item { display: inline-flex; align-items: center; gap: 5px; font-size: 11px; color: var(--muted); }
.acp-leg-item i { width: 22px; height: 10px; border-radius: 2px; display: inline-block; }

/* ---------- 页头全局区间选择 ---------- */
.ac-gp {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.ac-gp-label {
  font-size: 11px;
  color: var(--muted);
  letter-spacing: 0.08em;
}

/* ---------- 区间收益摘要 ---------- */
.ac-psum {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
  margin-bottom: 8px;
  padding: 4px 0;
}
.ac-psum-item {
  display: inline-flex;
  align-items: baseline;
  gap: 6px;
  white-space: nowrap;
}
.ac-psum-item .ac-dot { align-self: center; }
.ac-psum-name { font-size: 12px; }
.ac-psum-ret { font-size: 12.5px; font-weight: 600; }
.ac-psum-dd { font-size: 10.5px; }
.ac-up { color: #B03A2E; }
.ac-dn { color: #17714B; }
</style>
