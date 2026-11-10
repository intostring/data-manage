<template>
  <div class="d-anim max-w-6xl mx-auto">
    <!-- 页头 -->
    <div class="d-page-head">
      <div>
        <h1>期权盈亏总览</h1>
        <div class="sub">全体投顾期权交易的权利金净收支，按标的品种聚合，点击标的下钻盈亏与投顾成交明细</div>
      </div>
      <span class="d-card-x">权利金净收支口径</span>
    </div>

    <!-- 期权盈亏汇总 -->
    <section class="d-card">
      <div class="d-card-h">
        <div>
          <span class="d-card-t">期权盈亏</span>
          <span class="d-card-x" style="margin-left:10px">截至 {{ optionData.trade_date || '—' }} · 以来累计 · 全体投顾合计</span>
        </div>
        <span class="d-card-x">{{ optionData.source === 'summary' ? '汇总表' : '实时聚合' }}</span>
      </div>
      <div class="d-card-b">
        <div v-if="loading" class="oa-empty">加载中...</div>
        <div v-else-if="error" class="oa-empty">{{ error }}</div>
        <template v-else>
          <div class="oa-kpis">
            <div>
              <div class="k">权利金净收支</div>
              <div class="v d-mono" :class="(optTotal.premium ?? 0) >= 0 ? 'd-up' : 'd-dn'">
                {{ fmtSignedMoney(optTotal.premium) }}
              </div>
            </div>
            <div>
              <div class="k">手续费合计</div>
              <div class="v d-mono">{{ fmtMoney(optTotal.fee) }}</div>
            </div>
            <div>
              <div class="k">参与投顾</div>
              <div class="v d-mono">{{ optTotal.advisors ?? '—' }}</div>
            </div>
            <div>
              <div class="k">期权标的</div>
              <div class="v d-mono">{{ optTotal.underlying_count ?? '—' }}</div>
            </div>
            <div>
              <div class="k">合约数</div>
              <div class="v d-mono">{{ optTotal.contracts ?? '—' }}</div>
            </div>
            <div>
              <div class="k">成交笔数</div>
              <div class="v d-mono">{{ (optTotal.trades ?? 0).toLocaleString() }}</div>
            </div>
          </div>

          <div class="oa-scroll">
            <table class="d-table oa-table">
              <thead>
                <tr>
                  <th class="oa-rank-col">排名</th>
                  <th>标的品种</th>
                  <th>合约数</th>
                  <th>成交笔数</th>
                  <th>权利金净收支</th>
                  <th>手续费</th>
                  <th class="oa-bar-col">占比图示</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(row, idx) in optionRows" :key="row.underlying">
                  <td class="oa-rank-col">
                    <span class="oa-rank" :class="`oa-rank-${idx + 1}`">{{ idx + 1 }}</span>
                  </td>
                  <td>
                    <router-link
                      class="oa-name"
                      :to="{ name: 'display-option-underlying', query: { underlying: row.underlying } }"
                    >{{ row.name }}</router-link>
                    <span class="oa-code">{{ row.underlying }}</span>
                  </td>
                  <td class="d-mono">{{ row.contracts ?? '—' }}</td>
                  <td class="d-mono">{{ (row.trades ?? 0).toLocaleString() }}</td>
                  <td class="d-mono" :class="(row.premium ?? 0) >= 0 ? 'd-up' : 'd-dn'">
                    {{ fmtSignedMoney(row.premium) }}
                  </td>
                  <td class="d-mono">{{ fmtMoney(row.fee) }}</td>
                  <td class="oa-bar-col">
                    <div class="oa-bar-track">
                      <div
                        class="oa-bar-fill"
                        :class="row.premium >= 0 ? 'oa-fill-up' : 'oa-fill-dn'"
                        :style="{ width: barWidth(row) }"
                      ></div>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </template>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import client from '../../api/client'

const loading = ref(false)
const error = ref('')
const optionData = ref({})

const optTotal = computed(() => optionData.value.total || {})
const optionRows = computed(() => optionData.value.rows || [])

const optMax = computed(() =>
  Math.max(...optionRows.value.map((row) => Math.abs(Number(row.premium) || 0)), 1)
)

function barWidth(row) {
  return `${Math.max((Math.abs(Number(row.premium) || 0) / optMax.value) * 100, 1)}%`
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

async function fetchOptions() {
  loading.value = true
  error.value = ''
  try {
    const { data: res } = await client.get('/tables/option/pnl/')
    optionData.value = res || {}
  } catch (e) {
    console.error('获取期权盈亏失败', e)
    error.value = '获取期权盈亏失败'
    optionData.value = {}
  } finally {
    loading.value = false
  }
}

onMounted(fetchOptions)
</script>

<style scoped>
.oa-empty {
  min-height: 200px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--muted);
}

.oa-kpis {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 12px;
  margin-bottom: 14px;
}
.oa-kpis .k {
  font-size: 12px;
  color: var(--muted);
  margin-bottom: 4px;
}
.oa-kpis .v {
  font-size: 16px;
  font-weight: 600;
}
@media (max-width: 900px) {
  .oa-kpis { grid-template-columns: repeat(3, 1fr); }
}

.oa-scroll {
  max-height: calc(100vh - 360px);
  min-height: 200px;
  overflow: auto;
  border: 1px solid var(--line);
  border-radius: 4px;
}

.oa-table {
  table-layout: fixed;
  width: 100%;
}
.oa-table thead th {
  position: sticky;
  top: 0;
  z-index: 3;
  background: var(--soft);
}
.oa-table th,
.oa-table td {
  text-align: left;
  padding: 9px 12px;
}
.oa-table th:nth-child(3),
.oa-table td:nth-child(3),
.oa-table th:nth-child(4),
.oa-table td:nth-child(4) {
  width: 90px;
}
.oa-table th:nth-child(5),
.oa-table td:nth-child(5) {
  width: 130px;
}
.oa-table th:nth-child(6),
.oa-table td:nth-child(6) {
  width: 100px;
}

.oa-rank-col {
  width: 64px;
}
.oa-rank {
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
.oa-rank-1 { background: #B03A2E; color: #FDFCF8; }
.oa-rank-2 { background: #C4685D; color: #FDFCF8; }
.oa-rank-3 { background: #D89A92; color: #FDFCF8; }

.oa-name {
  color: var(--ink);
  text-decoration: none;
  border-bottom: 1px dashed transparent;
  transition: all 0.15s ease;
}
.oa-name:hover {
  color: #4472C4;
  border-bottom-color: #4472C4;
}
.oa-code {
  margin-left: 6px;
  font-family: var(--mono);
  font-size: 10.5px;
  color: var(--muted);
}

.oa-bar-track {
  height: 12px;
  background: var(--soft);
  border-radius: 2px;
  overflow: hidden;
}
.oa-bar-fill {
  height: 100%;
  border-radius: 2px;
}
.oa-fill-up { background: var(--up); }
.oa-fill-dn { background: var(--dn); }
</style>
