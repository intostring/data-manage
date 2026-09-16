<template>
  <div class="max-w-6xl mx-auto">
    <div class="mb-5">
      <h2 class="text-lg font-semibold text-ink">盈亏分析</h2>
      <p class="text-sm text-ink-muted mt-1">品种表现、板块分布与投顾配置观察</p>
    </div>

    <section class="d-card">
      <div class="d-card-h">
        <div>
          <span class="d-card-t">品种盈亏排行</span>
          <span class="d-card-x" style="margin-left:10px">截至 {{ data.trade_date || '—' }} · 以来累计 · 全体投顾合计</span>
        </div>
        <span class="d-card-x">参与品种 {{ data.variety_count ?? '—' }}</span>
      </div>
      <div class="d-card-b">
        <div v-if="loading" class="pnr-empty">加载中...</div>
        <div v-else-if="error" class="pnr-empty">{{ error }}</div>
        <template v-else>
          <div class="pnr-tabs">
            <button
              class="pnr-tab"
              :class="{ on: tab === 'profit', up: true }"
              @click="tab = 'profit'"
            >盈利品种</button>
            <button
              class="pnr-tab"
              :class="{ on: tab === 'loss', dn: true }"
              @click="tab = 'loss'"
            >亏损品种</button>
          </div>

          <div class="pnr-scroll">
            <table class="d-table pnr-table">
              <thead>
                <tr>
                  <th class="pnr-rank-col">排名</th>
                  <th>品种名称</th>
                  <th>累计盈亏</th>
                  <th class="pnr-bar-col">占比图示</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in activeRows" :key="row.code">
                  <td class="pnr-rank-col">
                    <span class="pnr-rank" :class="`pnr-rank-${row.rank}`">{{ row.rank }}</span>
                  </td>
                  <td>
                    <router-link
                      class="pnr-name"
                      :to="{ name: 'display-sector-pnl', query: { variety: row.code } }"
                    >{{ row.name }}</router-link>
                    <span class="pnr-code">{{ row.code }}</span>
                  </td>
                  <td class="d-mono" :class="tab === 'profit' ? 'd-up' : 'd-dn'">
                    {{ fmtSignedMoney(row.value) }}
                  </td>
                  <td class="pnr-bar-col">
                    <div class="pnr-bar-track">
                      <div
                        class="pnr-bar-fill"
                        :class="tab === 'profit' ? 'pnr-fill-up' : 'pnr-fill-dn'"
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
const data = ref({})
const tab = ref('profit')

const activeRows = computed(() =>
  tab.value === 'profit' ? data.value.profit_list || [] : data.value.loss_list || []
)

// 条形长度按当前选项卡内的绝对值最大值归一
const activeMax = computed(() =>
  Math.max(...activeRows.value.map((row) => Math.abs(Number(row.value) || 0)), 1)
)

function barWidth(row) {
  return `${Math.max((Math.abs(Number(row.value) || 0) / activeMax.value) * 100, 1)}%`
}

function fmtSignedMoney(value) {
  if (value == null || value === '') return '—'
  const n = Number(value)
  const sign = n > 0 ? '+' : ''
  if (Math.abs(n) >= 100000000) return `${sign}${(n / 100000000).toFixed(2)}亿`
  if (Math.abs(n) >= 10000) return `${sign}${(n / 10000).toFixed(2)}万`
  return `${sign}${n.toLocaleString('zh-CN', { maximumFractionDigits: 2 })}`
}

async function fetchRanking() {
  loading.value = true
  error.value = ''
  try {
    const { data: res } = await client.get('/tables/sector/pnl-ranking/')
    data.value = res || {}
  } catch (e) {
    console.error('获取品种盈亏排行失败', e)
    error.value = '获取品种盈亏排行失败'
    data.value = {}
  } finally {
    loading.value = false
  }
}

onMounted(fetchRanking)
</script>

<style scoped>
.pnr-empty {
  min-height: 200px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--muted);
}

.pnr-tabs {
  display: flex;
  gap: 6px;
  margin-bottom: 14px;
  border-bottom: 1px solid var(--line);
  padding-bottom: 0;
}

.pnr-tab {
  border: 1px solid var(--line);
  border-bottom: none;
  background: var(--soft);
  color: var(--muted);
  font-size: 13px;
  font-weight: 500;
  padding: 7px 22px;
  border-radius: 5px 5px 0 0;
  cursor: pointer;
  transition: all 0.15s ease;
  position: relative;
  top: 1px;
}

.pnr-tab.up.on {
  background: var(--card);
  color: var(--up);
  border-color: var(--line);
  border-bottom: 1px solid var(--card);
}

.pnr-tab.dn.on {
  background: var(--card);
  color: var(--dn);
  border-color: var(--line);
  border-bottom: 1px solid var(--card);
}

.pnr-scroll {
  max-height: calc(100vh - 320px);
  min-height: 200px;
  overflow: auto;
  border: 1px solid var(--line);
  border-radius: 4px;
}

.pnr-table thead th {
  position: sticky;
  top: 0;
  z-index: 3;
  background: var(--soft);
}

.pnr-table th,
.pnr-table td {
  text-align: left;
  padding: 9px 12px;
}

.pnr-table td:nth-child(3) {
  text-align: right;
}

.pnr-table th:nth-child(3) {
  text-align: right;
}

.pnr-rank-col {
  width: 64px;
}

.pnr-rank {
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

.pnr-rank-1 { background: #B03A2E; color: #FDFCF8; }
.pnr-rank-2 { background: #C4685D; color: #FDFCF8; }
.pnr-rank-3 { background: #D89A92; color: #FDFCF8; }

.pnr-name {
  color: var(--ink);
  text-decoration: none;
  border-bottom: 1px dashed transparent;
  transition: all 0.15s ease;
}

.pnr-name:hover {
  color: #4472C4;
  border-bottom-color: #4472C4;
}

.pnr-code {
  margin-left: 6px;
  font-family: var(--mono);
  font-size: 10.5px;
  color: var(--muted);
}

.pnr-bar-col {
  width: 34%;
}

.pnr-bar-track {
  height: 12px;
  background: var(--soft);
  border-radius: 2px;
  overflow: hidden;
}

.pnr-bar-fill {
  height: 100%;
  border-radius: 2px;
}

.pnr-fill-up { background: var(--up); }
.pnr-fill-dn { background: var(--dn); }
</style>
