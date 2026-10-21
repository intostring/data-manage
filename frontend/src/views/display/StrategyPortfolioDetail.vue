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
          <div>
            <span class="d-card-t">组合收益率曲线</span>
            <span class="d-card-x" style="margin-left:10px">
              {{ result.metrics.start_date }} ~ {{ result.metrics.end_date }} · {{ result.metrics.daily_count }} 个交易日 · 实线为组合，细线为各成分投顾
            </span>
          </div>
          <label class="spd-check">
            <input type="checkbox" v-model="showMembers" /> 显示成分投顾
          </label>
        </div>
        <div class="d-card-b">
          <div ref="chartRef" style="width:100%;height:480px"></div>
        </div>
      </div>

      <!-- ③ 组合规模与成分明细 -->
      <div class="d-card" style="margin-top:14px">
        <div class="d-card-h">
          <div>
            <span class="d-card-t">组合规模与成分明细</span>
            <span class="d-card-x" style="margin-left:10px">合计规模与各成分投顾明细</span>
          </div>
        </div>
        <div class="d-card-b">
          <div class="spd-scale">
            <div><div class="k">总投资金额</div><div class="v d-mono">{{ fmtMoney(result.scale.cum_investment) }}</div></div>
            <div><div class="k">初始市值</div><div class="v d-mono">{{ fmtMoney(result.scale.mk_bf) }}</div></div>
            <div><div class="k">新增规模</div><div class="v d-mono">{{ fmtMoney(result.scale.new_add) }}</div></div>
            <div><div class="k">成分投顾</div><div class="v d-mono">{{ result.scale.advisor_count }} 个</div></div>
          </div>

          <div class="spd-scroll" style="margin-top:14px">
            <table class="d-table">
              <thead>
                <tr>
                  <th style="text-align:left">投顾名称</th>
                  <th style="text-align:left">代码</th>
                  <th>投资逻辑</th>
                  <th>组合权重</th>
                  <th>最新净值</th>
                  <th>成立以来收益</th>
                  <th>总投资金额</th>
                  <th>新增规模</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="a in result.advisors" :key="a.pid">
                  <td>{{ a.account_name || a.account_code }}</td>
                  <td class="d-mono d-muted">{{ a.account_code }}</td>
                  <td class="d-muted">{{ a.invest_logic || '—' }}</td>
                  <td class="d-mono">{{ a.weight.toFixed(2) }}%</td>
                  <td class="d-mono">{{ a.latest_nav ?? '—' }}</td>
                  <td class="d-mono" :class="fmtColorPct(a.total_return)">{{ fmtPct(a.total_return, 100) }}</td>
                  <td class="d-mono">{{ fmtMoney(a.cum_investment) }}</td>
                  <td class="d-mono">{{ fmtMoney(a.new_add) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div class="d-muted" style="font-size:11px;margin-top:8px">
            口径说明：组合日收益率 = Σ(成分日收益率 × 权重)，成分当日无净值按 0 处理；年化按 252 个交易日，无风险利率取 1.5%；
            风险平价 = 等风险贡献（ERC），均值方差 = 最大夏普切点组合（负权截断）。
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { useRoute } from 'vue-router'
import * as echarts from 'echarts/core'
import { LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent, DataZoomComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import client from '../../api/client'

echarts.use([CanvasRenderer, LineChart, GridComponent, TooltipComponent, LegendComponent, DataZoomComponent])

const route = useRoute()
const recordId = route.params.id

const record = ref({})
const result = ref(null)
const loading = ref(false)
const error = ref('')
const showMembers = ref(true)

const chartRef = ref(null)
let chart = null

const MEMBER_COLORS = ['#4472C4', '#70AD47', '#7F7F7F', '#C4685D', '#8E7CC3', '#33608C', '#BE8A3C', '#6AA9C9']

async function load() {
  loading.value = true
  error.value = ''
  try {
    const { data: r } = await client.get(`/tables/strategy/portfolios/${recordId}/`)
    record.value = r

    const params = new URLSearchParams()
    params.set('pids', r.pids.join(','))
    params.set('model', r.weight_model || 'equal')
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

  const dates = result.value.nav_series.map((p) => p.date)
  const cumReturns = result.value.nav_series.map((p) => p.cum_return)
  const drawdowns = result.value.nav_series.map((p) => p.drawdown)

  const memberSeries = []
  if (showMembers.value) {
    const dateIdx = new Map(dates.map((d, i) => [d, i]))
    result.value.member_series.forEach((ms, i) => {
      const nameMap = new Map(result.value.advisors.map((a) => [a.pid, a]))
      const name = nameMap.get(ms.pid)?.account_name || nameMap.get(ms.pid)?.account_code || `投顾${ms.pid}`
      const arr = new Array(dates.length).fill(null)
      ms.points.forEach((p) => {
        const idx = dateIdx.get(p.date)
        if (idx != null) arr[idx] = p.cum_return
      })
      memberSeries.push({
        name,
        type: 'line',
        xAxisIndex: 0,
        yAxisIndex: 0,
        data: arr,
        lineStyle: { width: 1, color: MEMBER_COLORS[i % MEMBER_COLORS.length], opacity: 0.55 },
        itemStyle: { color: MEMBER_COLORS[i % MEMBER_COLORS.length] },
        symbol: 'none',
        connectNulls: false,
      })
    })
  }

  chart.setOption(
    {
      tooltip: {
        trigger: 'axis',
        backgroundColor: '#FDFCF8',
        borderColor: '#E5E0D2',
        textStyle: { fontSize: 11, color: '#20283A' },
        valueFormatter: (v) => (v == null ? '—' : `${v >= 0 ? '+' : ''}${Number(v).toFixed(2)}%`),
      },
      legend: {
        top: 0,
        type: 'scroll',
        textStyle: { fontSize: 11 },
        data: ['策略组合', '回撤', ...memberSeries.map((s) => s.name)],
      },
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
        ...memberSeries,
        {
          name: '回撤',
          type: 'line',
          xAxisIndex: 1,
          yAxisIndex: 1,
          data: drawdowns,
          lineStyle: { width: 1, color: '#B03A2E' },
          itemStyle: { color: '#B03A2E' },
          areaStyle: { color: 'rgba(176,58,46,0.10)' },
          symbol: 'none',
        },
      ],
    },
    { notMerge: true }
  )
}

watch(showMembers, () => {
  if (result.value) renderChart()
})

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
