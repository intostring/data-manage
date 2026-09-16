<template>
  <div class="ato-page">
    <div class="mb-5">
      <h2 class="text-lg font-semibold text-ink">投顾交易概况</h2>
      <p class="text-sm text-ink-muted mt-1">主观投顾 × 品种交易矩阵，按板块大类/子类分组，展示保证金占比</p>
    </div>

    <section class="d-card">
      <div class="d-card-h">
        <div>
          <span class="d-card-t">交易品种矩阵</span>
          <span class="d-card-x" style="margin-left:10px">截至 {{ data.trade_date || '—' }} · {{ advisorCount }} 位主观投顾 · {{ varietyCount }} 个品种</span>
        </div>
        <div class="ato-tools">
          <div class="ato-seg">
            <button
              v-for="w in windowOptions"
              :key="w.key"
              :class="{ on: window === w.key }"
              @click="selectWindow(w.key)"
            >{{ w.label }}</button>
          </div>
        </div>
      </div>

      <div class="d-card-b ato-card-b">
        <div v-if="loading" class="ato-empty">加载中...</div>
        <div v-else-if="error" class="ato-empty">{{ error }}</div>
        <div v-else class="ato-scroll">
          <table class="ato-table">
            <thead>
              <tr>
                <th class="ato-fix ato-fix-1" rowspan="4">投顾</th>
                <th class="ato-fix ato-fix-2" rowspan="4">起始时间</th>
                <th class="ato-fix ato-fix-3" rowspan="4">板块数</th>
                <th class="ato-fix ato-fix-4" rowspan="4">品种数</th>
                <th
                  v-for="g in headerL1"
                  :key="`l1-${g.name}`"
                  :colspan="g.colSpan"
                  class="ato-l1"
                >{{ g.name }}</th>
              </tr>
              <tr>
                <th
                  v-for="g in headerL2"
                  :key="`l2-${g.name}`"
                  :colspan="g.colSpan"
                  class="ato-l2"
                >{{ g.name }}</th>
              </tr>
              <tr>
                <th v-for="col in columns" :key="`c-${col.key}`" class="ato-code">{{ col.code }}</th>
              </tr>
              <tr>
                <th v-for="col in columns" :key="`n-${col.key}`" :class="['ato-name', col.agg ? 'ato-agg' : '']">{{ col.name }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in rows" :key="row.account_id">
                <td class="ato-fix ato-fix-1 ato-advisor">{{ row.advisor_name }}</td>
                <td class="ato-fix ato-fix-2 ato-mono">{{ row.start_time }}</td>
                <td class="ato-fix ato-fix-3 ato-mono">{{ row.sector_count }}</td>
                <td class="ato-fix ato-fix-4 ato-mono">{{ row.variety_count }}</td>
                <td
                  v-for="col in columns"
                  :key="`${row.account_id}-${col.key}`"
                  :class="['ato-cell', col.agg ? 'ato-agg' : '']"
                  :style="cellStyle(row.values[col.key], col)"
                  :title="cellTitle(row, col)"
                >
                  {{ fmtCell(row.values[col.key]) }}
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
import { computed, onMounted, ref } from 'vue'
import client from '../../api/client'

const loading = ref(false)
const error = ref('')
const data = ref({})
const mode = ref('margin_share')
const window = ref('std')

const windowOptions = [
  { key: 'day', label: '当天' },
  { key: '1m', label: '近一月' },
  { key: '3m', label: '近一季' },
  { key: '1y', label: '近一年' },
  { key: 'std', label: '成立以来' },
]

const columns = computed(() => data.value.columns || [])
const rows = computed(() => data.value.rows || [])
const advisorCount = computed(() => data.value.advisor_count ?? rows.value.length)
const varietyCount = computed(() => data.value.variety_count ?? 0)

const isShare = computed(() => mode.value === 'turnover_share' || mode.value === 'margin_share')

// 4 行表头：大类分组
const headerL1 = computed(() => {
  const groups = []
  let current = null
  for (const col of columns.value) {
    if (!current || current.name !== col.l1) {
      current = { name: col.l1, colSpan: 1 }
      groups.push(current)
    } else {
      current.colSpan++
    }
  }
  return groups
})

// 4 行表头：子类分组
const headerL2 = computed(() => {
  const groups = []
  let current = null
  for (const col of columns.value) {
    const name = col.l2 || col.name
    if (!current || current.name !== name) {
      current = { name, colSpan: 1 }
      groups.push(current)
    } else {
      current.colSpan++
    }
  }
  return groups
})

// 金额模式下，用全部品种列的最大值归一化热力色
const maxValue = computed(() => {
  let max = 1
  for (const row of rows.value) {
    for (const col of columns.value) {
      if (col.agg) continue
      const v = Number(row.values[col.key] || 0)
      if (v > max) max = v
    }
  }
  return max
})

function cellStyle(value, col) {
  const v = Number(value || 0)
  if (v <= 0) return {}
  const ratio = isShare.value ? Math.min(v, 1) : Math.min(v / maxValue.value, 1)
  const alpha = 0.06 + ratio * 0.82
  return {
    background: col.agg ? `rgba(156, 107, 47, ${alpha})` : `rgba(68, 114, 196, ${alpha})`,
  }
}

function cellTitle(row, col) {
  return `${row.advisor_name} · ${col.name}：${fmtCell(row.values[col.key])}`
}

function fmtCell(value) {
  if (value == null || value === '') return ''
  const v = Number(value)
  if (isShare.value) {
    return v > 0 ? `${(v * 100).toFixed(1)}%` : ''
  }
  return fmtMoney(v)
}

function fmtMoney(value) {
  if (value == null || value === '') return ''
  const n = Number(value)
  if (Math.abs(n) >= 100000000) return `${(n / 100000000).toFixed(2)}亿`
  if (Math.abs(n) >= 10000) return `${(n / 10000).toFixed(1)}万`
  return n.toLocaleString('zh-CN', { maximumFractionDigits: 0 })
}

function selectWindow(key) {
  if (window.value === key) return
  window.value = key
  fetchData()
}

async function fetchData() {
  loading.value = true
  error.value = ''
  try {
    const { data: res } = await client.get('/tables/trade/advisor-overview/', {
      params: { mode: mode.value, window: window.value },
    })
    data.value = res || {}
  } catch (e) {
    console.error('获取投顾交易概况失败', e)
    error.value = '获取投顾交易概况失败'
    data.value = {}
  } finally {
    loading.value = false
  }
}

onMounted(fetchData)
</script>

<style scoped>
.ato-page {
  max-width: 100%;
}

.ato-tools {
  display: flex;
  align-items: center;
  gap: 12px;
}

.ato-seg {
  display: flex;
  border: 1px solid var(--line);
  border-radius: 4px;
  background: #FBF9F3;
  overflow: hidden;
}

.ato-seg button {
  height: 26px;
  padding: 0 12px;
  border: 0;
  background: none;
  color: var(--muted);
  font-size: 12px;
  cursor: pointer;
  white-space: nowrap;
}

.ato-seg button:hover {
  color: var(--ink);
}

.ato-seg button.on {
  background: var(--navy);
  color: #F2EDE0;
}

.ato-card-b {
  padding: 0;
}

.ato-empty {
  min-height: 200px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--muted);
}

.ato-scroll {
  max-height: calc(100vh - 220px);
  overflow: auto;
  border-radius: 0 0 6px 6px;
}

.ato-table {
  border-collapse: separate;
  border-spacing: 0;
  font-size: 12px;
  table-layout: fixed;
  min-width: 100%;
}

.ato-table th,
.ato-table td {
  border-right: 1px solid var(--line2);
  border-bottom: 1px solid var(--line2);
  text-align: center;
  white-space: nowrap;
  padding: 5px 8px;
  min-width: 46px;
}

.ato-table thead th {
  position: sticky;
  top: 0;
  z-index: 3;
  background: var(--soft);
  color: var(--ink);
  font-weight: 600;
}

.ato-table thead tr:nth-child(1) th.ato-l1 {
  top: 0;
  z-index: 3;
  background: #5B9BD5;
  color: #fff;
}

.ato-table thead tr:nth-child(2) th.ato-l2 {
  top: 27px;
  z-index: 2;
  background: #D6E4F0;
  color: #2C4A6E;
}

.ato-table thead tr:nth-child(3) th.ato-code {
  top: 54px;
  z-index: 1;
  background: #EDF2F8;
  font-family: var(--mono);
  font-size: 11px;
}

.ato-table thead tr:nth-child(4) th.ato-name {
  top: 81px;
  z-index: 1;
  background: var(--soft);
  font-weight: 500;
}

.ato-table thead th.ato-agg {
  background: #F5EFD8;
}

/* 固定前 4 列 */
.ato-fix {
  position: sticky;
  z-index: 4;
  background: var(--card);
  text-align: left;
}

.ato-fix-1 { left: 0; min-width: 76px; }
.ato-fix-2 { left: 76px; min-width: 88px; }
.ato-fix-3 { left: 164px; min-width: 52px; }
.ato-fix-4 { left: 216px; min-width: 52px; }

.ato-table thead .ato-fix {
  z-index: 6;
  background: var(--soft);
}

.ato-advisor {
  font-weight: 600;
  text-align: left;
}

.ato-mono {
  font-family: var(--mono);
}

.ato-cell {
  color: var(--ink);
}

.ato-cell.ato-agg {
  font-weight: 600;
}

.ato-table tbody tr:hover td {
  background-color: #F8F4E9;
}

.ato-table tbody tr:hover td.ato-fix {
  background: #F8F4E9;
}
</style>
