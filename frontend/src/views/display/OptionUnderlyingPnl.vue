<template>
  <div class="max-w-6xl mx-auto">
    <!-- 品种期权盈亏汇总 -->
    <section class="d-card">
      <div class="d-card-h">
        <div>
          <span class="d-card-t">{{ data.name || data.underlying || '—' }} 期权盈亏</span>
          <span class="d-card-x" style="margin-left:10px">
            {{ data.underlying || '—' }} · 截至 {{ data.trade_date || '—' }} · 以来累计 · 全体投顾合计
          </span>
        </div>
        <router-link class="opu-back" :to="{ name: 'display-sector' }">← 返回盈亏分析</router-link>
      </div>
      <div class="d-card-b">
        <div v-if="loading" class="opu-empty">加载中...</div>
        <div v-else-if="error" class="opu-empty">{{ error }}</div>
        <template v-else>
          <div class="opu-kpis">
            <div>
              <div class="k">权利金净收支</div>
              <div class="v d-mono" :class="(summary.premium ?? 0) >= 0 ? 'd-up' : 'd-dn'">
                {{ fmtSignedMoney(summary.premium) }}
              </div>
            </div>
            <div>
              <div class="k">手续费合计</div>
              <div class="v d-mono">{{ fmtMoney(summary.fee) }}</div>
            </div>
            <div>
              <div class="k">参与投顾</div>
              <div class="v d-mono">{{ summary.advisors ?? '—' }}</div>
            </div>
            <div>
              <div class="k">合约数</div>
              <div class="v d-mono">{{ summary.contracts ?? '—' }}</div>
            </div>
            <div>
              <div class="k">成交笔数</div>
              <div class="v d-mono">{{ (summary.trades ?? 0).toLocaleString() }}</div>
            </div>
          </div>
        </template>
      </div>
    </section>

    <!-- 投顾在该品种期权上的盈亏 -->
    <section class="d-card" style="margin-top:16px">
      <div class="d-card-h">
        <div>
          <span class="d-card-t">投顾期权盈亏明细</span>
          <span class="d-card-x" style="margin-left:10px">
            {{ data.name || data.underlying || '—' }}({{ data.underlying || '—' }}) · 按权利金净收支倒序
          </span>
        </div>
        <span class="d-card-x">权利金净收支口径</span>
      </div>
      <div class="d-card-b">
        <div v-if="loading" class="opu-empty">加载中...</div>
        <div v-else-if="error" class="opu-empty">{{ error }}</div>
        <div v-else-if="!advisors.length" class="opu-empty">该品种暂无投顾期权成交</div>
        <div v-else class="opu-scroll">
          <table class="d-table opu-table">
            <thead>
              <tr>
                <th class="opu-rank-col">排名</th>
                <th>投顾名称</th>
                <th>合约数</th>
                <th>成交笔数</th>
                <th>权利金净收支</th>
                <th>手续费</th>
                <th>交易区间</th>
                <th class="opu-bar-col">占比图示</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(row, idx) in advisors" :key="row.account">
                <td class="opu-rank-col">
                  <span class="opu-rank" :class="`opu-rank-${idx + 1}`">{{ idx + 1 }}</span>
                </td>
                <td>
                  <router-link
                    class="opu-name"
                    :to="{ name: 'display-option-advisor-trades', query: { account: row.account, underlying: data.underlying } }"
                  >{{ row.account_name }}</router-link>
                  <span class="opu-code">{{ row.account }}</span>
                  <span v-if="row.is_stop" class="opu-stop">终止</span>
                </td>
                <td class="d-mono">{{ row.contracts ?? '—' }}</td>
                <td class="d-mono">{{ (row.trades ?? 0).toLocaleString() }}</td>
                <td class="d-mono" :class="(row.premium ?? 0) >= 0 ? 'd-up' : 'd-dn'">
                  {{ fmtSignedMoney(row.premium) }}
                </td>
                <td class="d-mono">{{ fmtMoney(row.fee) }}</td>
                <td class="d-mono opu-range">{{ row.first_date || '—' }} ~ {{ row.last_date || '—' }}</td>
                <td class="opu-bar-col">
                  <div class="opu-bar-track">
                    <div
                      class="opu-bar-fill"
                      :class="row.premium >= 0 ? 'opu-fill-up' : 'opu-fill-dn'"
                      :style="{ width: barWidth(row) }"
                    ></div>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import client from '../../api/client'

const route = useRoute()

const loading = ref(false)
const error = ref('')
const data = ref({})

const summary = computed(() => data.value.summary || {})
const advisors = computed(() => data.value.advisors || [])

const maxAbsPremium = computed(() =>
  Math.max(...advisors.value.map((row) => Math.abs(Number(row.premium) || 0)), 1)
)

function barWidth(row) {
  return `${Math.max((Math.abs(Number(row.premium) || 0) / maxAbsPremium.value) * 100, 1)}%`
}

function fmtMoney(value) {
  if (value == null || value === '') return '—'
  const n = Number(value)
  if (Math.abs(n) >= 100000000) return `${(n / 100000000).toFixed(2)}亿`
  if (Math.abs(n) >= 10000) return `${(n / 10000).toFixed(2)}万`
  return n.toLocaleString('zh-CN', { maximumFractionDigits: 2 })
}

function fmtSignedMoney(value) {
  if (value == null || value === '') return '—'
  const n = Number(value)
  const sign = n > 0 ? '+' : ''
  if (Math.abs(n) >= 100000000) return `${sign}${(n / 100000000).toFixed(2)}亿`
  if (Math.abs(n) >= 10000) return `${sign}${(n / 10000).toFixed(2)}万`
  return `${sign}${n.toLocaleString('zh-CN', { maximumFractionDigits: 2 })}`
}

async function fetchDetail() {
  const underlying = (route.query.underlying || '').trim()
  if (!underlying) {
    error.value = '缺少品种参数'
    data.value = {}
    return
  }
  loading.value = true
  error.value = ''
  try {
    const { data: res } = await client.get('/tables/option/pnl/underlying/', {
      params: { underlying },
    })
    data.value = res || {}
  } catch (e) {
    console.error('获取品种期权盈亏失败', e)
    const detail = e?.response?.data?.detail
    error.value = detail || '获取品种期权盈亏失败'
    data.value = {}
  } finally {
    loading.value = false
  }
}

onMounted(fetchDetail)
watch(() => route.query.underlying, fetchDetail)
</script>

<style scoped>
.opu-empty {
  min-height: 160px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--muted);
}

.opu-back {
  font-size: 12.5px;
  color: var(--muted);
  text-decoration: none;
  transition: color 0.15s ease;
}
.opu-back:hover { color: #4472C4; }

.opu-kpis {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 12px;
}
.opu-kpis .k {
  font-size: 12px;
  color: var(--muted);
  margin-bottom: 4px;
}
.opu-kpis .v {
  font-size: 17px;
  font-weight: 600;
}
@media (max-width: 900px) {
  .opu-kpis { grid-template-columns: repeat(2, 1fr); }
}

.opu-scroll {
  max-height: calc(100vh - 360px);
  min-height: 200px;
  overflow: auto;
  border: 1px solid var(--line);
  border-radius: 4px;
}

.opu-table {
  table-layout: fixed;
  width: 100%;
}
.opu-table thead th {
  position: sticky;
  top: 0;
  z-index: 3;
  background: var(--soft);
}
.opu-table th,
.opu-table td {
  text-align: left;
  padding: 9px 12px;
}
.opu-table th:nth-child(3),
.opu-table td:nth-child(3),
.opu-table th:nth-child(4),
.opu-table td:nth-child(4) {
  width: 84px;
}
.opu-table th:nth-child(5),
.opu-table td:nth-child(5) {
  width: 130px;
}
.opu-table th:nth-child(6),
.opu-table td:nth-child(6) {
  width: 96px;
}
.opu-table th:nth-child(7),
.opu-table td:nth-child(7) {
  width: 190px;
}

.opu-rank-col { width: 60px; }
.opu-rank {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  border-radius: 4px;
  font-family: var(--mono);
  font-size: 12px;
  background: var(--soft);
  color: var(--muted);
}
.opu-rank-1 { background: #B03A2E; color: #FDFCF8; }
.opu-rank-2 { background: #C4685D; color: #FDFCF8; }
.opu-rank-3 { background: #D89A92; color: #FDFCF8; }

.opu-name {
  color: var(--ink);
  text-decoration: none;
  border-bottom: 1px dashed transparent;
  transition: all 0.15s ease;
}
.opu-name:hover {
  color: #4472C4;
  border-bottom-color: #4472C4;
}

.opu-code {
  margin-left: 6px;
  font-family: var(--mono);
  font-size: 10.5px;
  color: var(--muted);
}

.opu-stop {
  display: inline-block;
  margin-left: 6px;
  padding: 1px 6px;
  border-radius: 3px;
  font-size: 10.5px;
  background: var(--soft);
  color: var(--dn);
  border: 1px solid var(--line);
}

.opu-range {
  font-size: 11.5px;
  color: var(--muted);
}

.opu-bar-track {
  height: 12px;
  background: var(--soft);
  border-radius: 2px;
  overflow: hidden;
}
.opu-bar-fill { height: 100%; border-radius: 2px; }
.opu-fill-up { background: var(--up); }
.opu-fill-dn { background: var(--dn); }
</style>
