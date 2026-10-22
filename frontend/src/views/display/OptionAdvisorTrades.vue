<template>
  <div class="max-w-6xl mx-auto">
    <!-- 投顾×品种 期权成交汇总 -->
    <section class="d-card">
      <div class="d-card-h">
        <div>
          <span class="d-card-t">{{ data.advisor_name || '—' }} · {{ data.underlying_name || data.underlying || '—' }} 期权成交</span>
          <span class="d-card-x" style="margin-left:10px">
            {{ data.account || '—' }}({{ data.underlying || '—' }}) · {{ summary.first_date || '—' }} ~ {{ summary.last_date || '—' }} · 权利金净收支口径
          </span>
        </div>
        <router-link
          class="oat-back"
          :to="{ name: 'display-option-underlying', query: { underlying: data.underlying } }"
        >← 返回{{ data.underlying_name || data.underlying || '' }}期权盈亏</router-link>
      </div>
      <div class="d-card-b">
        <div v-if="loading" class="oat-empty">加载中...</div>
        <div v-else-if="error" class="oat-empty">{{ error }}</div>
        <template v-else>
          <div class="oat-kpis">
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

    <!-- 成交明细 -->
    <section class="d-card" style="margin-top:16px">
      <div class="d-card-h">
        <div>
          <span class="d-card-t">期权成交明细</span>
          <span class="d-card-x" style="margin-left:10px">按成交时间倒序</span>
        </div>
      </div>
      <div class="d-card-b" style="padding-top:0">
        <div class="oat-table-wrap">
          <table class="d-table oat-table">
            <thead>
              <tr>
                <th>成交日期</th>
                <th>成交时间</th>
                <th>合约代码</th>
                <th>买卖</th>
                <th>开平</th>
                <th>成交价</th>
                <th>手数</th>
                <th>成交额</th>
                <th>权利金收支</th>
                <th>手续费</th>
              </tr>
            </thead>
            <tbody v-if="loading">
              <tr><td colspan="10" class="oat-empty-cell">加载中...</td></tr>
            </tbody>
            <tbody v-else-if="error">
              <tr><td colspan="10" class="oat-empty-cell">{{ error }}</td></tr>
            </tbody>
            <tbody v-else-if="rows.length">
              <tr v-for="(row, idx) in rows" :key="idx">
                <td class="d-mono">{{ row.trade_date || '—' }}</td>
                <td class="d-mono">{{ row.trade_time || '—' }}</td>
                <td class="d-mono">{{ row.contract || '—' }}</td>
                <td :class="isBuy(row.side) ? 'd-up' : 'd-dn'">{{ row.side || '—' }}</td>
                <td>{{ row.open_close || '—' }}</td>
                <td class="d-mono">{{ fmtNumber(row.trade_price) }}</td>
                <td class="d-mono">{{ fmtNumber(row.trade_qty) }}</td>
                <td class="d-mono">{{ fmtMoney(row.trade_amount) }}</td>
                <td
                  class="d-mono"
                  :class="(row.premium_income_expense ?? 0) >= 0 ? 'd-up' : 'd-dn'"
                >{{ fmtSignedMoney(row.premium_income_expense) }}</td>
                <td class="d-mono">{{ fmtMoney(row.fee) }}</td>
              </tr>
            </tbody>
            <tbody v-else>
              <tr><td colspan="10" class="oat-empty-cell">暂无成交明细</td></tr>
            </tbody>
          </table>
        </div>

        <div v-if="total" class="oat-pagination">
          <div class="oat-page-size">
            <span>共 {{ total.toLocaleString() }} 条</span>
            <span>每页</span>
            <select v-model.number="pageSize" @change="changePage(1)">
              <option :value="10">10 条</option>
              <option :value="20">20 条</option>
              <option :value="50">50 条</option>
            </select>
          </div>
          <div class="oat-page-actions">
            <button type="button" :disabled="page === 1" @click="changePage(page - 1)">上一页</button>
            <button
              v-for="p in pageNumbers"
              :key="p"
              type="button"
              :class="{ on: page === p }"
              @click="changePage(p)"
            >{{ p }}</button>
            <button type="button" :disabled="page === totalPages" @click="changePage(page + 1)">下一页</button>
          </div>
          <div class="oat-page-jump">
            <span>前往</span>
            <input v-model="jumpPage" name="jump_page" type="number" min="1" :max="totalPages" @keydown.enter="goToPage" />
            <span>页</span>
            <button type="button" @click="goToPage">go</button>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import client from '../../api/client'

const route = useRoute()
const router = useRouter()

const loading = ref(false)
const error = ref('')
const data = ref({})
const rows = ref([])
const total = ref(0)
const page = ref(Number(route.query.page || 1))
const pageSize = ref(Number(route.query.page_size || 20))
const jumpPage = ref('')

const summary = computed(() => data.value.summary || {})
const totalPages = computed(() => Math.max(Math.ceil(total.value / pageSize.value), 1))
const pageNumbers = computed(() => {
  const total2 = totalPages.value
  const current = page.value
  const start = Math.max(1, Math.min(current - 2, total2 - 4))
  const end = Math.min(total2, start + 4)
  return Array.from({ length: end - start + 1 }, (_, i) => start + i)
})

function isBuy(side) {
  return String(side || '').includes('买')
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

function fmtSignedMoney(value) {
  if (value == null || value === '') return '—'
  const n = Number(value)
  const sign = n > 0 ? '+' : ''
  if (Math.abs(n) >= 100000000) return `${sign}${(n / 100000000).toFixed(2)}亿`
  if (Math.abs(n) >= 10000) return `${sign}${(n / 10000).toFixed(2)}万`
  return `${sign}${n.toLocaleString('zh-CN', { maximumFractionDigits: 2 })}`
}

async function fetchData() {
  const account = (route.query.account || '').trim()
  const underlying = (route.query.underlying || '').trim()
  if (!account || !underlying) {
    error.value = '缺少投顾或品种参数'
    data.value = {}
    rows.value = []
    total.value = 0
    return
  }
  loading.value = true
  error.value = ''
  try {
    const { data: res } = await client.get('/tables/option/trades/', {
      params: { account, underlying, page: page.value, page_size: pageSize.value },
    })
    data.value = res || {}
    rows.value = res.rows || []
    total.value = res.total || 0
  } catch (e) {
    console.error('获取期权成交记录失败', e)
    const detail = e?.response?.data?.detail
    error.value = detail || '获取期权成交记录失败'
    data.value = {}
    rows.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

function changePage(next) {
  page.value = Math.min(Math.max(next, 1), totalPages.value)
  router.replace({
    name: 'display-option-advisor-trades',
    query: {
      ...route.query,
      page: page.value,
      page_size: pageSize.value,
    },
  })
  fetchData()
}

function goToPage() {
  const next = Number(jumpPage.value)
  if (!Number.isFinite(next)) return
  changePage(Math.trunc(next))
  jumpPage.value = ''
}

onMounted(fetchData)
watch(
  () => [route.query.account, route.query.underlying],
  ([nextAccount, nextUnderlying], [prevAccount, prevUnderlying]) => {
    // 数组 watch source 会被强制触发，须自行判断投顾/品种是否真的变化；
    // 翻页（仅 page query 变化）不重置页码，由 changePage 直接拉取
    if (nextAccount === prevAccount && nextUnderlying === prevUnderlying) return
    page.value = 1
    fetchData()
  },
)
</script>

<style scoped>
.oat-empty {
  min-height: 160px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--muted);
}

.oat-back {
  font-size: 12.5px;
  color: var(--muted);
  text-decoration: none;
  transition: color 0.15s ease;
}
.oat-back:hover { color: #4472C4; }

.oat-kpis {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}
.oat-kpis .k {
  font-size: 12px;
  color: var(--muted);
  margin-bottom: 4px;
}
.oat-kpis .v {
  font-size: 17px;
  font-weight: 600;
}
@media (max-width: 900px) {
  .oat-kpis { grid-template-columns: repeat(2, 1fr); }
}

.oat-table-wrap {
  overflow: auto;
  max-height: calc(100vh - 420px);
  min-height: 200px;
  border: 1px solid var(--line);
  border-radius: 4px;
}

.oat-table {
  table-layout: fixed;
  width: 100%;
  min-width: 900px;
}
.oat-table thead th {
  position: sticky;
  top: 0;
  z-index: 3;
  background: var(--soft);
}
.oat-table th,
.oat-table td {
  text-align: left;
  padding: 8px 12px;
  white-space: nowrap;
}
.oat-table th:nth-child(3),
.oat-table td:nth-child(3) {
  width: 150px;
}
.oat-table th:nth-child(6),
.oat-table td:nth-child(6),
.oat-table th:nth-child(7),
.oat-table td:nth-child(7),
.oat-table th:nth-child(10),
.oat-table td:nth-child(10) {
  width: 90px;
}
.oat-table th:nth-child(8),
.oat-table td:nth-child(8),
.oat-table th:nth-child(9),
.oat-table td:nth-child(9) {
  width: 110px;
}

.oat-empty-cell {
  text-align: center;
  color: var(--muted);
  padding: 42px 12px;
}

.oat-pagination {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
  gap: 12px;
  padding-top: 12px;
  color: var(--muted);
  font-size: 12px;
}

.oat-page-size,
.oat-page-jump {
  display: flex;
  align-items: center;
  gap: 8px;
}
.oat-page-jump { justify-content: flex-end; }

.oat-page-size select,
.oat-page-jump input {
  height: 30px;
  border: 1px solid var(--line);
  border-radius: 7px;
  background: var(--card);
  color: var(--ink);
  font-size: 12px;
}
.oat-page-size select { padding: 0 24px 0 10px; }
.oat-page-jump input {
  width: 60px;
  padding: 0 8px;
  text-align: center;
}

.oat-page-actions {
  display: flex;
  align-items: center;
  gap: 6px;
}
.oat-page-actions button,
.oat-page-jump button {
  min-width: 30px;
  height: 30px;
  padding: 0 9px;
  border: 1px solid var(--line);
  border-radius: 7px;
  background: var(--card);
  color: var(--muted);
  font-size: 12px;
  cursor: pointer;
}
.oat-page-actions button:hover:not(:disabled),
.oat-page-jump button:hover {
  border-color: var(--brass);
  color: var(--brass);
}
.oat-page-actions button.on {
  border-color: var(--navy);
  background: var(--navy);
  color: #F2EDE0;
}
.oat-page-actions button:disabled {
  cursor: not-allowed;
  opacity: 0.45;
}

@media (max-width: 900px) {
  .oat-pagination { grid-template-columns: 1fr; }
  .oat-page-actions,
  .oat-page-jump { justify-content: flex-start; }
}
</style>
