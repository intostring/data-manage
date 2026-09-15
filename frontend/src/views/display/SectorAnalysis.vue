<template>
  <div class="max-w-6xl mx-auto">
    <div class="mb-5">
      <h2 class="text-lg font-semibold text-ink">板块分析</h2>
      <p class="text-sm text-ink-muted mt-1">板块表现、轮动与投顾板块配置观察</p>
    </div>

    <section class="d-card">
      <div class="d-card-h">
        <div>
          <span class="d-card-t">板块风险概况</span>
          <span class="d-card-x" style="margin-left:10px">截至 {{ snapshot.trade_date || '—' }} · 全体投顾合计</span>
        </div>
      </div>
      <div class="d-card-b">
        <div v-if="loading" class="sb-empty">加载中...</div>
        <div v-else-if="error" class="sb-empty">{{ error }}</div>
        <div v-else class="d-kpis sb-kpis">
          <div>
            <div class="k">总资产</div>
            <div class="v">{{ fmtMoney(snapshot.asset_total) }}</div>
          </div>
          <div>
            <div class="k">保证金</div>
            <div class="v">{{ fmtMoney(snapshot.margin) }}</div>
          </div>
          <div>
            <div class="k">仓位率</div>
            <div class="v">{{ fmtRatioPct(snapshot.pos_rate) }}</div>
          </div>
          <div>
            <div class="k">品种保证金</div>
            <div class="v">{{ fmtMoney(snapshot.variety_margin) }}</div>
          </div>
          <div>
            <div class="k">品种风险度</div>
            <div class="v">{{ fmtPct(snapshot.variety_risk_degree) }}</div>
          </div>
          <div>
            <div class="k">板块保证金</div>
            <div class="v">{{ fmtMoney(snapshot.bk_margin) }}</div>
          </div>
          <div>
            <div class="k">板块风险度</div>
            <div class="v">{{ fmtPct(snapshot.bk_risk_degree) }}</div>
          </div>
        </div>
      </div>
    </section>

    <section class="d-card">
      <div class="d-card-h">
        <div>
          <span class="d-card-t">板块保证金</span>
          <span class="d-card-x" style="margin-left:10px">截至 {{ marginData.trade_date || '—' }} · 保证金占比按总资产</span>
        </div>
      </div>
      <div class="d-card-b">
        <div v-if="marginLoading" class="sb-empty">加载中...</div>
        <div v-else-if="marginError" class="sb-empty">{{ marginError }}</div>
        <div v-else>
          <div class="sb2-charts">
            <div class="sb2-chart-col">
              <div class="sb2-chart-title">保证金</div>
              <div class="sb2-bars">
                <div v-for="row in marginRows" :key="row.name" class="sb2-bar-row" :title="`${row.name} ${fmtMoney(row.value)}`">
                  <span class="sb2-bar-name">{{ row.name }}</span>
                  <div class="sb2-bar-track">
                    <div class="sb2-bar-fill" :style="{ width: barWidth(marginMax, row), background: rowColor(marginRows, row) }"></div>
                  </div>
                  <span class="sb2-bar-val">{{ fmtMoney(row.value) }}</span>
                </div>
              </div>
            </div>
            <div class="sb2-chart-col">
              <div class="sb2-chart-title">
                保证金占比
                <span class="sb2-pie-total">总资产 {{ fmtMoney(marginData.asset_total) }}</span>
              </div>
              <div ref="pieRef" class="sb2-pie-echart"></div>
            </div>
          </div>
          <div class="sb2-table-wrap">
            <table class="d-table sb2-table-t">
              <tbody>
                <tr>
                  <th>板块名称</th>
                  <td v-for="row in marginRows" :key="`n-${row.name}`" class="sb2-name">
                    <i :style="{ background: rowColor(marginRows, row) }"></i>{{ row.name }}
                  </td>
                </tr>
                <tr>
                  <th>保证金</th>
                  <td v-for="row in marginRows" :key="`m-${row.name}`" class="d-mono">{{ fmtMoney(row.value) }}</td>
                </tr>
                <tr>
                  <th>占比</th>
                  <td v-for="row in marginRows" :key="`s-${row.name}`" class="d-mono">{{ fmtShare(marginData, row.value) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </section>

    <section class="d-card">
      <div class="d-card-h">
        <div>
          <span class="d-card-t">品种保证金（前30）</span>
          <span class="d-card-x" style="margin-left:10px">截至 {{ varietyData.trade_date || '—' }} · 保证金占比按总资产</span>
        </div>
      </div>
      <div class="d-card-b">
        <div v-if="varietyLoading" class="sb-empty">加载中...</div>
        <div v-else-if="varietyError" class="sb-empty">{{ varietyError }}</div>
        <div v-else>
          <div class="sb2-charts">
            <div class="sb2-chart-col">
              <div class="sb2-chart-title">保证金</div>
              <div class="sb2-bars">
                <div v-for="row in varietyRows" :key="row.name" class="sb2-bar-row" :title="`${row.name} ${fmtMoney(row.value)}`">
                  <span class="sb2-bar-name">{{ row.name }}</span>
                  <div class="sb2-bar-track">
                    <div class="sb2-bar-fill" :style="{ width: barWidth(varietyMax, row), background: rowColor(varietyRows, row) }"></div>
                  </div>
                  <span class="sb2-bar-val">{{ fmtMoney(row.value) }}</span>
                </div>
              </div>
            </div>
            <div class="sb2-chart-col">
              <div class="sb2-chart-title">
                保证金占比
                <span class="sb2-pie-total">总资产 {{ fmtMoney(varietyData.asset_total) }}</span>
              </div>
              <div ref="varietyPieRef" class="sb2-pie-echart sb2-pie-echart-lg"></div>
            </div>
          </div>
          <div class="sb2-table-wrap">
            <table class="d-table sb2-table-t">
              <tbody>
                <tr>
                  <th>品种名称</th>
                  <td v-for="row in varietyRows" :key="`vn-${row.name}`" class="sb2-name">
                    <i :style="{ background: rowColor(varietyRows, row) }"></i>{{ row.name }}
                  </td>
                </tr>
                <tr>
                  <th>保证金</th>
                  <td v-for="row in varietyRows" :key="`vm-${row.name}`" class="d-mono">{{ fmtMoney(row.value) }}</td>
                </tr>
                <tr>
                  <th>占比</th>
                  <td v-for="row in varietyRows" :key="`vs-${row.name}`" class="d-mono">{{ fmtShare(varietyData, row.value) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import * as echarts from 'echarts/core'
import { PieChart } from 'echarts/charts'
import { LegendComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import client from '../../api/client'

echarts.use([CanvasRenderer, PieChart, LegendComponent, TooltipComponent])

const loading = ref(false)
const error = ref('')
const snapshot = ref({})

const marginLoading = ref(false)
const marginError = ref('')
const marginData = ref({})

// Excel 调色板风格配色，按数据顺序（占比降序）分配
const sbExcelPalette = [
  '#4472C4', '#C5504B', '#70AD47', '#5B4B8A', '#2E8B8B', '#ED7D31',
  '#5B9BD5', '#E07A70', '#A9D18E', '#B4A7D6', '#76C3B8', '#F8CBAD',
  '#C5E0B4', '#F4B7C7', '#FFE699', '#D6E3F3', '#E2EFDA', '#FDE9D9', '#EDEDED',
]

const marginRows = computed(() => marginData.value.rows || [])
const marginMax = computed(() => Math.max(...marginRows.value.map((row) => row.value), 1))

const varietyLoading = ref(false)
const varietyError = ref('')
const varietyData = ref({})

const varietyRows = computed(() => varietyData.value.rows || [])
const varietyMax = computed(() => Math.max(...varietyRows.value.map((row) => row.value), 1))

function rowColor(rows, row) {
  const index = rows.findIndex((item) => item.name === row.name)
  return sbExcelPalette[(index >= 0 ? index : 0) % sbExcelPalette.length]
}

function barWidth(max, row) {
  return `${Math.max((row.value / max) * 100, 0.4)}%`
}

// ---------- 保证金占比饼图（ECharts，通用） ----------
const pieRef = ref(null)
const varietyPieRef = ref(null)
const pieHolder = { current: null }
const varietyPieHolder = { current: null }

function pieOption(rows, total) {
  return {
    color: sbExcelPalette,
    tooltip: {
      trigger: 'item',
      backgroundColor: 'rgba(32, 40, 58, 0.94)',
      borderWidth: 0,
      padding: [6, 10],
      textStyle: { color: '#FDFCF8', fontSize: 12 },
      formatter: (p) => {
        const share = total ? ((p.value / total) * 100).toFixed(2) : '—'
        return `${p.name}<br/>保证金：${fmtMoney(p.value)}<br/>占比：${share}%`
      },
    },
    legend: {
      orient: 'vertical',
      right: 0,
      top: 12,
      icon: 'rect',
      itemWidth: 9,
      itemHeight: 9,
      itemGap: 3,
      textStyle: { fontSize: 11, color: '#20283A' },
      formatter: (name) => {
        const row = rows.find((r) => r.name === name)
        if (!row) return name
        const share = total ? ((row.value / total) * 100).toFixed(2) : '—'
        return `${name}  ${share}%`
      },
    },
    series: [
      {
        name: '保证金占比',
        type: 'pie',
        radius: '58%',
        center: ['33%', '58%'],
        avoidLabelOverlap: true,
        minAngle: 0.5,
        label: {
          show: true,
          formatter: '{b}\n{d}%',
          fontSize: 10,
          lineHeight: 13,
          color: '#20283A',
        },
        labelLine: { length: 10, length2: 8, lineStyle: { color: '#8F8A79' } },
        emphasis: { scaleSize: 3 },
        data: rows.map((row) => ({ name: row.name, value: row.value })),
      },
    ],
  }
}

function renderPie(container, holder, rows, total) {
  if (!container) return
  if (!holder.current) holder.current = echarts.init(container)
  holder.current.setOption(pieOption(rows, total))
}

watch(marginRows, async () => {
  // 等待 v-else 分支渲染完成（pieRef 挂载）后再初始化图表
  await nextTick()
  renderPie(pieRef.value, pieHolder, marginRows.value, marginData.value.asset_total || 0)
}, { deep: true })

watch(varietyRows, async () => {
  await nextTick()
  renderPie(varietyPieRef.value, varietyPieHolder, varietyRows.value, varietyData.value.asset_total || 0)
}, { deep: true })

function fmtMoney(value) {
  if (value == null || value === '') return '—'
  const n = Number(value)
  if (Math.abs(n) >= 100000000) return `${(n / 100000000).toFixed(2)}亿`
  if (Math.abs(n) >= 10000) return `${(n / 10000).toFixed(2)}万`
  return n.toLocaleString('zh-CN', { maximumFractionDigits: 2 })
}

// 0-1 区间的小数转为百分比
function fmtRatioPct(value) {
  if (value == null || value === '') return '—'
  return `${(Number(value) * 100).toFixed(2)}%`
}

// 已是百分比值，直接附加百分号
function fmtPct(value) {
  if (value == null || value === '') return '—'
  return `${Number(value).toFixed(2)}%`
}

// 占总资产比例
function fmtShare(data, value) {
  const total = data && data.asset_total
  if (!total || value == null) return '—'
  return `${((Number(value) / total) * 100).toFixed(2)}%`
}

async function fetchSnapshot() {
  loading.value = true
  error.value = ''
  try {
    const { data } = await client.get('/tables/sector/bk-latest/')
    snapshot.value = data || {}
  } catch (e) {
    console.error('获取板块风险概况失败', e)
    error.value = '获取板块风险概况失败'
    snapshot.value = {}
  } finally {
    loading.value = false
  }
}

async function fetchMargin() {
  marginLoading.value = true
  marginError.value = ''
  try {
    const { data } = await client.get('/tables/sector/bk-margin/')
    marginData.value = data || {}
  } catch (e) {
    console.error('获取板块总保证金失败', e)
    marginError.value = '获取板块总保证金失败'
    marginData.value = {}
  } finally {
    marginLoading.value = false
  }
}

async function fetchVariety() {
  varietyLoading.value = true
  varietyError.value = ''
  try {
    const { data } = await client.get('/tables/variety/top-margin/')
    varietyData.value = data || {}
  } catch (e) {
    console.error('获取品种保证金前30失败', e)
    varietyError.value = '获取品种保证金前30失败'
    varietyData.value = {}
  } finally {
    varietyLoading.value = false
  }
}

onMounted(() => {
  fetchSnapshot()
  fetchMargin()
  fetchVariety()
})

onUnmounted(() => {
  if (pieHolder.current) {
    pieHolder.current.dispose()
    pieHolder.current = null
  }
  if (varietyPieHolder.current) {
    varietyPieHolder.current.dispose()
    varietyPieHolder.current = null
  }
})
</script>

<style scoped>
.sb-kpis {
  grid-template-columns: repeat(7, 1fr);
}

.sb-empty {
  min-height: 120px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--muted);
}

.sb2-charts {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
  align-items: start;
  margin-bottom: 16px;
}

.sb2-chart-col {
  min-width: 0;
}

.sb2-chart-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 12px;
  font-weight: 600;
  color: var(--ink);
  margin-bottom: 8px;
  padding-bottom: 6px;
  border-bottom: 1px solid var(--line);
}

.sb2-pie-total {
  font-size: 11px;
  font-weight: 400;
  color: var(--muted);
  font-family: var(--mono);
}

.sb2-table-wrap {
  overflow-x: auto;
}

.sb2-table-t {
  width: 100%;
  table-layout: auto;
}

.sb2-table-t th,
.sb2-table-t td {
  padding: 6px 8px;
  text-align: center;
  white-space: nowrap;
}

.sb2-table-t th {
  position: sticky;
  left: 0;
  z-index: 5;
  background: var(--card);
  box-shadow: 1px 0 0 var(--line);
  color: var(--muted);
  font-weight: 500;
  font-size: 12px;
}

.sb2-table-t td.sb2-name i {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 2px;
  margin-right: 4px;
  vertical-align: middle;
}

.sb2-table-t tr:not(:last-child) th,
.sb2-table-t tr:not(:last-child) td {
  border-bottom: 1px solid var(--line);
}

.sb2-bars {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.sb2-bar-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.sb2-bar-name {
  flex: 0 0 72px;
  font-size: 11px;
  color: var(--ink);
  text-align: right;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sb2-bar-track {
  flex: 1 1 auto;
  height: 12px;
  background: var(--soft);
  border-radius: 2px;
  overflow: hidden;
}

.sb2-bar-fill {
  height: 100%;
  border-radius: 2px;
}

.sb2-bar-val {
  flex: 0 0 auto;
  font-family: var(--mono);
  font-size: 11px;
  color: var(--muted);
}

.sb2-pie-echart {
  width: 100%;
  height: 420px;
}

/* 品种饼图 30 项图例，加高避免滚动 */
.sb2-pie-echart-lg {
  height: 640px;
}

@media (max-width: 1100px) {
  .sb2-charts {
    grid-template-columns: 1fr;
  }
}
</style>
