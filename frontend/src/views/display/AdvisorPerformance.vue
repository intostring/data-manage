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
              <span v-if="detail.info.merged" class="d-pill info" :title="(detail.info.account_codes || []).join('、')">
                合并 {{ detail.info.account_count }} 账号
              </span>
              <span v-if="detail.info.is_stop === 0" class="d-pill ok">运行中</span>
              <span v-else class="d-pill gray">已停止</span>
              <!-- 多账号投顾：跳转合并业绩入口 -->
              <button
                v-if="!detail.info.merged && detail.info.mergeable"
                class="ap-merge-btn"
                @click="goMerged"
              >查看合并业绩 →</button>
              <span v-if="detail.info.data_update_date" class="d-muted d-mono" style="margin-left:auto;font-size:11px">
                数据更新至{{ detail.info.data_update_date }}
              </span>
            </div>
            <div class="d-muted d-mono" style="font-size:11px;margin-top:4px">
              <template v-if="detail.info.merged">
                <template v-for="(code, idx) in (detail.info.account_codes || [])" :key="code">
                  <a
                    v-if="detail.info.account_pids?.[code]"
                    class="ap-acct-link"
                    :title="`查看 ${code} 单账号业绩`"
                    @click="goSingle(detail.info.account_pids[code])"
                  >{{ code }}</a>
                  <template v-else>{{ code }}</template>
                  <span v-if="idx < (detail.info.account_codes || []).length - 1">、</span>
                </template>
                <span v-if="detail.info.invest_logic" style="margin-left:10px">投资逻辑: {{ detail.info.invest_logic }}</span>
                <span v-if="detail.info.invest_cate" style="margin-left:10px">投资范围: {{ detail.info.invest_cate }}</span>
              </template>
              <template v-else>
                {{ detail.info.account_code || detail.info.product_name }}
                <span v-if="detail.info.product_name_cn" style="margin-left:10px">所属产品: {{ detail.info.product_name_cn }}</span>
                <span v-if="detail.info.invest_logic" style="margin-left:10px">投资逻辑: {{ detail.info.invest_logic }}</span>
                <span v-if="detail.info.invest_cate" style="margin-left:10px">投资范围: {{ detail.info.invest_cate }}</span>
              </template>
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
              <input type="date" name="start_date" v-model="customStart" class="d-ipt" style="font-size:11px;padding:4px 8px;width:130px" @change="changePeriod" />
              <span class="d-muted">至</span>
              <input type="date" name="end_date" v-model="customEnd" class="d-ipt" style="font-size:11px;padding:4px 8px;width:130px" @change="changePeriod" />
            </div>
          </div>
          <!-- 图例 + 收益率（点击可切换曲线显隐） -->
          <div style="display:flex;align-items:center;gap:16px;margin-bottom:8px;padding:4px 0;margin-left:55px;flex-wrap:wrap">
            <span class="d-leg-i ap-leg-toggle" :class="{ off: !legendOn(advisorLegendName) }" @click="toggleSeries(advisorLegendName)">
              <i class="d-leg-sw" style="background:#9C6B2F"></i>
              <span style="font-size:12px">{{ detail.info.account_name || detail.info.product_name }}</span>
              <span class="d-mono" :style="periodReturn >= 0 ? 'color:#B03A2E;font-size:12px;margin-left:4px' : 'color:#17714B;font-size:12px;margin-left:4px'">{{ periodReturn >= 0 ? '+' : '' }}{{ periodReturn.toFixed(2) }}%</span>
            </span>
            <span class="d-leg-i ap-leg-toggle" :class="{ off: !legendOn('南华商品指数') }" @click="toggleSeries('南华商品指数')">
              <i class="d-leg-sw" style="background:#8A8A8A"></i>
              <span style="font-size:12px">南华商品指数</span>
              <span class="d-mono" :style="benchPeriodReturn >= 0 ? 'color:#B03A2E;font-size:12px;margin-left:4px' : 'color:#17714B;font-size:12px;margin-left:4px'">{{ benchPeriodReturn >= 0 ? '+' : '' }}{{ benchPeriodReturn.toFixed(2) }}%</span>
            </span>
            <span class="d-leg-i ap-leg-toggle" :class="{ off: !legendOn('超额收益') }" @click="toggleSeries('超额收益')">
              <i class="d-leg-sw" style="background:#4472C4"></i>
              <span style="font-size:12px">超额收益</span>
              <span class="d-mono" :style="excessPeriodReturn >= 0 ? 'color:#B03A2E;font-size:12px;margin-left:4px' : 'color:#17714B;font-size:12px;margin-left:4px'">{{ excessPeriodReturn >= 0 ? '+' : '' }}{{ excessPeriodReturn.toFixed(2) }}%</span>
            </span>
          </div>
          <template v-if="(detail.nav_series || []).length">
            <div style="position:relative" @mousemove="updateDomTooltip" @mouseleave="hideChartTooltip">
              <div ref="navChartRef" style="width:100%;height:520px"></div>
              <!-- 回撤区图例（点击可切换，置于「动态回撤」标题下方） -->
              <div style="position:absolute; left:55px; right:170px; top:331px; display:flex; align-items:center; gap:14px; flex-wrap:wrap; zIndex:5">
                <span class="d-leg-i ap-leg-toggle ap-dd-leg" :class="{ off: !legendOn('回撤') }" @click="toggleSeries('回撤')">
                  <i class="d-leg-sw" style="background:#B03A2E"></i>
                  <span>{{ advisorLegendName }}</span>
                </span>
                <span class="d-leg-i ap-leg-toggle ap-dd-leg" :class="{ off: !legendOn('基准回撤') }" @click="toggleSeries('基准回撤')">
                  <i class="d-leg-sw" style="background:#8A8A8A"></i>
                  <span>基准回撤</span>
                </span>
                <span class="d-leg-i ap-leg-toggle ap-dd-leg" :class="{ off: !legendOn('超额回撤') }" @click="toggleSeries('超额回撤')">
                  <i class="d-leg-sw" style="background:#4472C4"></i>
                  <span>超额回撤</span>
                </span>
              </div>
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
                <div style="display:flex;align-items:center;gap:6px;margin-top:2px">
                  <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:#8A8A8A"></span>
                  <span style="color:#666">南华商品指数</span>
                  <span style="font-weight:600;margin-left:12px">{{ tipData.bench >= 0 ? '+' : '' }}{{ tipData.bench.toFixed(2) }}%</span>
                </div>
                <div style="display:flex;align-items:center;gap:6px;margin-top:2px">
                  <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:#4472C4"></span>
                  <span style="color:#666">超额收益</span>
                  <span style="font-weight:600;margin-left:12px;color:#4472C4">{{ tipData.excess >= 0 ? '+' : '' }}{{ tipData.excess.toFixed(2) }}%</span>
                </div>
              </div>
              <div v-if="tipData.show" :style="{ position:'absolute', left: tipData.x+'px', top:'362px', zIndex:99, background:'#FDFCF8', border:'1px solid #E5E0D2', borderRadius:'4px', padding:'6px 10px', fontSize:'11px', boxShadow:'0 2px 8px rgba(0,0,0,0.08)', pointerEvents:'none', whiteSpace:'nowrap' }">
                <div style="color:#999;margin-bottom:2px">{{ tipData.date }}</div>
                <div style="display:flex;align-items:center;gap:6px">
                  <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:#B03A2E"></span>
                  <span style="color:#666">回撤</span>
                  <span style="font-weight:600;margin-left:12px;color:#B03A2E">{{ tipData.dd.toFixed(2) }}%</span>
                </div>
                <div style="display:flex;align-items:center;gap:6px;margin-top:2px">
                  <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:#8A8A8A"></span>
                  <span style="color:#666">基准回撤</span>
                  <span style="font-weight:600;margin-left:12px;color:#8A8A8A">{{ tipData.benchDd.toFixed(2) }}%</span>
                </div>
                <div style="display:flex;align-items:center;gap:6px;margin-top:2px">
                  <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:#4472C4"></span>
                  <span style="color:#666">超额回撤</span>
                  <span style="font-weight:600;margin-left:12px;color:#4472C4">{{ tipData.excessDd.toFixed(2) }}%</span>
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
          <div>
            <span class="d-card-t">区间收益</span>
            <span class="d-card-x" style="margin-left:10px">按月度与年度划分的区间收益率</span>
          </div>
          <div v-if="hasBenchRows" style="display:flex;gap:6px">
            <button class="pr-toggle" :class="{ on: showBench }" @click="showBench = !showBench">基准指数</button>
            <button class="pr-toggle" :class="{ on: showExcess }" @click="showExcess = !showExcess">超额收益</button>
          </div>
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
                  <template v-for="row in periodReturnRows" :key="row.year">
                    <tr>
                      <td class="pr-year">{{ row.year }}</td>
                      <td v-for="m in 12" :key="m" class="d-mono pr-c" :style="cellStyle(row.months[m - 1])">
                        {{ fmtCell(row.months[m - 1]) }}
                      </td>
                      <td class="d-mono pr-year-cell" :style="cellStyle(row.yearReturn)">
                        {{ fmtCell(row.yearReturn) }}
                      </td>
                    </tr>
                    <tr v-if="showBench && benchByYear[row.year]">
                      <td class="pr-sub">基准指数</td>
                      <td
                        v-for="m in 12"
                        :key="m"
                        class="d-mono pr-c pr-c-sub"
                        :style="cellStyle(benchByYear[row.year].months[m - 1])"
                      >{{ fmtCell(benchByYear[row.year].months[m - 1]) }}</td>
                      <td class="d-mono pr-year-cell pr-c-sub" :style="cellStyle(benchByYear[row.year].yearReturn)">
                        {{ fmtCell(benchByYear[row.year].yearReturn) }}
                      </td>
                    </tr>
                    <tr v-if="showExcess && excessByYear[row.year]">
                      <td class="pr-sub">超额收益</td>
                      <td
                        v-for="m in 12"
                        :key="m"
                        class="d-mono pr-c pr-c-sub"
                        :style="cellStyle(excessByYear[row.year].months[m - 1])"
                      >{{ fmtCell(excessByYear[row.year].months[m - 1]) }}</td>
                      <td class="d-mono pr-year-cell pr-c-sub" :style="cellStyle(excessByYear[row.year].yearReturn)">
                        {{ fmtCell(excessByYear[row.year].yearReturn) }}
                      </td>
                    </tr>
                  </template>
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
import { useRoute, useRouter } from 'vue-router'

echarts.use([CanvasRenderer, LineChart, GridComponent, TooltipComponent, LegendComponent, MarkLineComponent, DataZoomComponent, TitleComponent, GraphicComponent])

const route = useRoute()
const router = useRouter()
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
const emptyTipData = () => ({ show: false, panel: '', x: 0, guideX: 0, date: '', ret: 0, dd: 0, bench: 0, excess: 0, benchDd: 0, excessDd: 0 })
const tipData = ref(emptyTipData())
const zoomLabel = ref({ show: false, startDate: '', endDate: '', startX: 55, endX: 55 })
let chartDates = []
let chartCumReturns = []
let chartDrawdowns = []
const chartBenchReturns = ref([])
const chartExcessReturns = ref([])
const chartBenchDrawdowns = ref([])
const chartExcessDrawdowns = ref([])

// 图例显隐状态（点击 DOM 图例切换对应曲线）
const legendSelected = ref({})
const advisorLegendName = computed(() =>
  detail.value?.info?.account_name || detail.value?.info?.product_name || '投顾'
)
function legendOn(name) {
  return legendSelected.value[name] !== false
}
function toggleSeries(name) {
  navChart?.dispatchAction({ type: 'legendToggleSelect', name })
}
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
    bench: chartBenchReturns.value[idx] ?? 0,
    excess: chartExcessReturns.value[idx] ?? 0,
    benchDd: chartBenchDrawdowns.value[idx] ?? 0,
    excessDd: chartExcessDrawdowns.value[idx] ?? 0,
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

// 当前时间段内基准收益率与超额收益率（与图表同口径：区间首日重算）
const benchPeriodReturn = computed(() => {
  const arr = chartBenchReturns.value
  return arr.length ? arr[arr.length - 1] : 0
})
const excessPeriodReturn = computed(() => {
  const arr = chartExcessReturns.value
  return arr.length ? arr[arr.length - 1] : 0
})

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
    // 日收益按其所属日期归入当月/当年（跨年首段归新年度，符合 月收益=月末净值环比 口径）
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

// 区间收益：按月度 / 年度划分（基于完整净值序列，与时间段选择无关）
const periodReturnRows = computed(() => {
  const series = (detail.value?.nav_series || []).filter((s) => s.nav && s.date)
  if (series.length < 2) return []
  const rets = []
  for (let i = 1; i < series.length; i++) {
    rets.push({ date: series[i].date, ret: series[i].nav / series[i - 1].nav - 1 })
  }
  const byYear = prMonthlyByYear(rets)
  return Object.keys(byYear)
    .map(Number)
    .sort((a, b) => a - b)
    .map((y) => ({ year: y, ...byYear[y] }))
})

// 基准指数（NHCI）月度/年度区间收益：日收益由累计收益推算（缺失日沿用前值）
const benchByYear = computed(() => {
  const navSeries = (detail.value?.nav_series || []).filter((s) => s.nav && s.date)
  const benchRaw = new Map((detail.value?.benchmark_series || []).map((p) => [p.date, p.cum_return]))
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

// 超额区间收益 = 投顾区间收益 − 基准区间收益（百分点）
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

// 跳转到同名账号合并业绩页：push 后直接加载，不依赖路由 watch（双保险）
function goMerged() {
  const pid = Number(route.params.pid)
  router.push(`/display/advisor/detail/${pid}?merged=1`).catch(() => {})
  if (pid) loadDetail(pid, true)
}

// 合并模式下点击账号代码 → 进入对应单账号业绩页
function goSingle(pid) {
  router.push(`/display/advisor/detail/${pid}`).catch(() => {})
  loadDetail(pid, false)
}

// 合并模式状态：?merged=1 进入时加载同名多账号合并详情
const mergedMode = ref(false)

async function loadDetail(pid, merge = false) {
  loading.value = true
  detail.value = null
  try {
    const params = { pid }
    if (merge) params.merge = 1
    const { data } = await client.get('/tables/advisor/performance/', { params })
    detail.value = data
    mergedMode.value = !!data?.info?.merged
    loading.value = false
    await nextTick()
    renderCharts()
  } catch (e) {
    console.error('获取投顾详情失败', e)
    loading.value = false
  }
}

// 监听 store 中 selectedPid 变化（顶部搜索切换 → 退出合并模式）
watch(() => advisorStore.selectedPid, (pid) => {
  if (pid) loadDetail(pid, false)
})

// 同路由仅 query 变化（单账号 ↔ 合并切换）时重新加载
watch(() => [route.params.pid, route.query.merged], ([newPid, newMerged]) => {
  if (!newPid) return
  loadDetail(Number(newPid), newMerged === '1')
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

  // 基准指数（NHCI.NH）累计收益：与组合同区间、以区间首日为基准重算
  const fullBench = detail.value?.benchmark_series || []
  const benchMap = new Map(fullBench.map((p) => [p.date, p.cum_return]))
  const benchCumFull = [] // 区间内各日基准全期累计（缺失日沿用前值）
  let lastBench = null
  for (const s of series) {
    const v = benchMap.get(s.date)
    if (v != null) lastBench = v
    benchCumFull.push(lastBench)
  }
  const baseBench = benchCumFull.length ? benchCumFull[0] : 0
  const benchReturns = benchCumFull.map((v) =>
    v == null || baseBench == null ? 0 : ((100 + v) / (100 + baseBench) - 1) * 100
  )
  const excessReturns = series.map((s, i) => s.cum_return - (benchReturns[i] ?? 0))

  // 基准/超额的动态回撤：累计收益相对历史峰值的回落（百分点）
  const drawdownOf = (values) => {
    let peak = 0
    return values.map((v) => {
      peak = Math.max(peak, v)
      return v - peak
    })
  }
  const benchDrawdowns = drawdownOf(benchReturns)
  const excessDrawdowns = drawdownOf(excessReturns)

  const maxDrawdown = drawdowns.length ? Math.min(...drawdowns) : 0

  // 存储数据供自定义 tooltip 使用
  chartDates = dates
  chartCumReturns = cumReturns
  chartDrawdowns = drawdowns
  chartBenchReturns.value = benchReturns
  chartExcessReturns.value = excessReturns
  chartBenchDrawdowns.value = benchDrawdowns
  chartExcessDrawdowns.value = excessDrawdowns
  chartAdvisorName.value = advisorName
  updateZoomLabel(0, 100)

  navChart.setOption({
    tooltip: { show: false },
    legend: {
      show: false,
      data: [advisorName, '南华商品指数', '超额收益', '回撤', '基准回撤', '超额回撤'],
      selected: { ...legendSelected.value },
    },
    axisPointer: {
      link: [{ xAxisIndex: 'all' }],
      label: { show: true, formatter: (p) => p.value, backgroundColor: '#9C6B2F' },
    },
    title: [
      { text: '动态回撤', left: 55, top: 315, textStyle: { fontSize: 12, fontWeight: 'normal', color: '#333' } },
      { text: `截止日期：${dates[dates.length - 1] || '—'}  ·  最大回撤 ${maxDrawdown.toFixed(2)}%`, right: 25, top: 315, textStyle: { fontSize: 11, fontWeight: 'normal', color: '#8F8A79' } },
    ],
    grid: [
      { left: 55, right: 25, top: 15, height: 250 },
      { left: 55, right: 25, top: 362, height: 92 },
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
      { name: advisorName, type: 'line', xAxisIndex: 0, yAxisIndex: 0, data: cumReturns, lineStyle: { width: 1.5, color: '#9C6B2F' }, itemStyle: { color: '#9C6B2F' }, showSymbol: false, z: 5 },
      { name: '南华商品指数', type: 'line', xAxisIndex: 0, yAxisIndex: 0, data: benchReturns, lineStyle: { width: 1.2, color: '#8A8A8A' }, itemStyle: { color: '#8A8A8A' }, showSymbol: false },
      { name: '超额收益', type: 'line', xAxisIndex: 0, yAxisIndex: 0, data: excessReturns, lineStyle: { width: 1.2, color: '#4472C4' }, itemStyle: { color: '#4472C4' }, showSymbol: false, areaStyle: { color: 'rgba(68,114,196,0.06)' } },
      { name: '回撤', type: 'line', xAxisIndex: 1, yAxisIndex: 1, data: drawdowns, lineStyle: { width: 1, color: '#B03A2E' }, itemStyle: { color: '#B03A2E' }, areaStyle: { color: 'rgba(176,58,46,0.10)' }, showSymbol: false },
      { name: '基准回撤', type: 'line', xAxisIndex: 1, yAxisIndex: 1, data: benchDrawdowns, lineStyle: { width: 1, color: '#8A8A8A', type: 'dashed' }, itemStyle: { color: '#8A8A8A' }, showSymbol: false },
      { name: '超额回撤', type: 'line', xAxisIndex: 1, yAxisIndex: 1, data: excessDrawdowns, lineStyle: { width: 1, color: '#4472C4', type: 'dashed' }, itemStyle: { color: '#4472C4' }, showSymbol: false },
    ],
  })

  navChart.off('dataZoom')
  navChart.on('dataZoom', (event) => {
    const payload = event.batch?.[0] || event
    updateZoomLabel(payload.start ?? 0, payload.end ?? 100)
  })

  // 图例切换后同步 DOM 图例的置灰状态
  navChart.off('legendselectchanged')
  navChart.on('legendselectchanged', (event) => {
    legendSelected.value = { ...event.selected }
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
  // 优先使用路由参数 pid（从列表页进入），并同步到全局搜索 store
  const routePid = Number(route.params.pid)
  const wantMerge = route.query.merged === '1'
  if (routePid) {
    if (wantMerge) {
      // 合并模式：不同步 selectedPid，避免触发搜索切换覆盖
      loadDetail(routePid, true)
    } else if (advisorStore.selectedPid !== routePid) {
      advisorStore.selectAdvisor(routePid)
    } else {
      loadDetail(routePid)
    }
  } else if (advisorStore.selectedPid) {
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
/* 多账号投顾「查看合并业绩」入口按钮 */
/* 合并模式下账号代码：点击进入单账号业绩页 */
.ap-acct-link {
  color: #9C6B2F;
  cursor: pointer;
  text-decoration: underline dotted rgba(156, 107, 47, 0.6);
  text-underline-offset: 3px;
}
.ap-acct-link:hover {
  color: #B03A2E;
}
.ap-merge-btn {
  border: 1px solid #E4D5BC;
  background: #F5EDE0;
  color: #9C6B2F;
  font-size: 11px;
  padding: 3px 10px;
  border-radius: 999px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.ap-merge-btn:hover {
  background: #9C6B2F;
  color: #FFFDF8;
}

/* 可点击图例：切换曲线显隐 */
.ap-leg-toggle {
  cursor: pointer;
  user-select: none;
  transition: opacity 0.15s ease;
}

.ap-leg-toggle:hover {
  opacity: 0.75;
}

.ap-leg-toggle.off {
  opacity: 0.35;
}

.ap-leg-toggle.off .d-leg-sw {
  background: #C6C2B4 !important;
}

/* 回撤区图例：与「动态回撤/截止日期」标题同行，字号略小 */
.ap-dd-leg span {
  font-size: 11px;
}

.ap-dd-leg .d-leg-sw {
  width: 8px;
  height: 8px;
}

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

.pr-toggle {
  font-size: 12px;
  padding: 3px 12px;
  border: 1px solid var(--line);
  border-radius: 4px;
  background: transparent;
  color: var(--muted);
  cursor: pointer;
  transition: all 0.15s;
}

.pr-toggle:hover {
  border-color: #9C6B2F;
  color: #9C6B2F;
}

.pr-toggle.on {
  background: #9C6B2F;
  border-color: #9C6B2F;
  color: #FDFCF8;
}

.pr-sub {
  font-size: 11px;
  font-weight: normal;
  color: var(--muted);
  background: var(--soft);
  white-space: nowrap;
}

.pr-c-sub {
  font-size: 11px;
  opacity: 0.88;
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
