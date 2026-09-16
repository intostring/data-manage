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
        <template v-else>
          <!-- Excel 式筛选栏 -->
          <div class="ato-filter">
            <input v-model.trim="searchText" class="ato-ipt" placeholder="筛选投顾名称…" />
            <div class="ato-fitem">
              <span class="ato-flab">品种数 ≥</span>
              <input v-model.number="minVariety" type="number" min="0" class="ato-ipt ato-ipt-n" />
            </div>
            <select v-model="sectorFilter" class="ato-ipt">
              <option value="">全部板块</option>
              <option v-for="s in sectorOptions" :key="s" :value="s">{{ s }}</option>
            </select>
            <label class="ato-chk"><input type="checkbox" v-model="hideEmpty" />仅显示有交易的品种列</label>
            <button v-if="isFiltered" class="ato-clear" @click="resetFilter">重置</button>
            <span class="ato-fcount">{{ displayRows.length }} 位投顾 · {{ displayColumns.length }} 列</span>
          </div>

          <!-- 左右双表：左侧固定列整体 sticky，杜绝列间缝隙 -->
          <div class="ato-scroll">
            <div class="ato-grid">
              <div class="ato-left">
                <table class="ato-tbl">
                  <colgroup>
                    <col style="width: 96px" />
                    <col style="width: 94px" />
                    <col style="width: 54px" />
                    <col style="width: 54px" />
                  </colgroup>
                  <thead>
                    <tr>
                      <th class="ato-sort" @click="sortBy('advisor')">
                        投顾<i class="ato-arrow" :class="sortClass('advisor')">{{ sortArrow('advisor') }}</i>
                      </th>
                      <th class="ato-sort" @click="sortBy('start')">
                        起始时间<i class="ato-arrow" :class="sortClass('start')">{{ sortArrow('start') }}</i>
                      </th>
                      <th class="ato-sort" @click="sortBy('sector')">
                        板块数<i class="ato-arrow" :class="sortClass('sector')">{{ sortArrow('sector') }}</i>
                      </th>
                      <th class="ato-sort" @click="sortBy('variety')">
                        品种数<i class="ato-arrow" :class="sortClass('variety')">{{ sortArrow('variety') }}</i>
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr
                      v-for="(row, i) in displayRows"
                      :key="row.account_id"
                      :class="{ 'ato-hover': hoverRow === i }"
                      @mouseenter="hoverRow = i"
                      @mouseleave="hoverRow = -1"
                    >
                      <td class="ato-advisor" :title="row.advisor_name">{{ row.advisor_name }}</td>
                      <td class="ato-mono">{{ row.start_time }}</td>
                      <td class="ato-mono">{{ row.sector_count }}</td>
                      <td class="ato-mono">{{ row.variety_count }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>

              <table class="ato-tbl ato-main">
                <colgroup>
                  <col v-for="col in displayColumns" :key="`col-${col.key}`" style="width: 62px" />
                </colgroup>
                <thead>
                  <tr>
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
                    <th
                      v-for="col in displayColumns"
                      :key="`c-${col.key}`"
                      class="ato-code ato-sort"
                      :title="col.code"
                      @click="sortBy(col.key)"
                    >{{ col.code }}<i class="ato-arrow" :class="sortClass(col.key)">{{ sortArrow(col.key) }}</i></th>
                  </tr>
                  <tr>
                    <th
                      v-for="col in displayColumns"
                      :key="`n-${col.key}`"
                      :class="['ato-name', 'ato-sort', col.agg ? 'ato-agg' : '']"
                      :title="col.name"
                      @click="sortBy(col.key)"
                    >{{ col.agg ? '小计' : col.name }}</th>
                  </tr>
                </thead>
                <tbody>
                  <tr
                    v-for="(row, i) in displayRows"
                    :key="row.account_id"
                    :class="{ 'ato-hover': hoverRow === i }"
                    @mouseenter="hoverRow = i"
                    @mouseleave="hoverRow = -1"
                  >
                    <td
                      v-for="col in displayColumns"
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

// ---- Excel 式筛选 / 排序 ----
const searchText = ref('')
const minVariety = ref(0)
const sectorFilter = ref('')
const hideEmpty = ref(false)
const sortKey = ref('variety')
const sortDir = ref('desc')
const hoverRow = ref(-1)

const sectorOptions = computed(() =>
  [...new Set(columns.value.map((c) => c.l1).filter(Boolean))]
)

// 行筛选：投顾名称 + 最小品种数
const filteredRows = computed(() => {
  let list = rows.value
  if (searchText.value) {
    const q = searchText.value.toLowerCase()
    list = list.filter((r) => (r.advisor_name || '').toLowerCase().includes(q))
  }
  if (minVariety.value > 0) {
    list = list.filter((r) => (r.variety_count || 0) >= minVariety.value)
  }
  return list
})

// 列筛选：板块 + 隐藏无交易品种列（含对应合计列）
const displayColumns = computed(() => {
  let cols = columns.value
  if (sectorFilter.value) {
    cols = cols.filter((c) => c.l1 === sectorFilter.value)
  }
  if (hideEmpty.value) {
    const active = new Set()
    for (const r of filteredRows.value) {
      for (const c of cols) {
        if (!c.agg && Number(r.values[c.key] || 0) > 0) active.add(c.key)
      }
    }
    const activeCodes = new Set(
      cols.filter((c) => !c.agg && active.has(c.key)).map((c) => c.code)
    )
    cols = cols.filter((c) =>
      !c.agg ? active.has(c.key) : (c.members || []).some((m) => activeCodes.has(m))
    )
  }
  return cols
})

// 排序：固定 4 列或任意品种列（含合计列）
const displayRows = computed(() => {
  const key = sortKey.value
  const dir = sortDir.value === 'desc' ? -1 : 1
  const list = [...filteredRows.value]
  if (key === 'advisor') {
    list.sort((a, b) => dir * (a.advisor_name || '').localeCompare(b.advisor_name || '', 'zh'))
  } else if (key === 'start') {
    list.sort((a, b) => dir * (a.start_time || '').localeCompare(b.start_time || ''))
  } else if (key === 'sector' || key === 'variety') {
    const field = `${key}_count`
    list.sort((a, b) => dir * ((a[field] || 0) - (b[field] || 0)))
  } else {
    list.sort((a, b) => dir * (Number(a.values[key] || 0) - Number(b.values[key] || 0)))
  }
  return list
})

const isFiltered = computed(() =>
  !!searchText.value || minVariety.value > 0 || !!sectorFilter.value || hideEmpty.value
)

function resetFilter() {
  searchText.value = ''
  minVariety.value = 0
  sectorFilter.value = ''
  hideEmpty.value = false
}

function sortBy(key) {
  if (sortKey.value === key) {
    sortDir.value = sortDir.value === 'desc' ? 'asc' : 'desc'
  } else {
    sortKey.value = key
    sortDir.value = key === 'advisor' || key === 'start' ? 'asc' : 'desc'
  }
}

function sortArrow(key) {
  if (sortKey.value !== key) return '↕'
  return sortDir.value === 'desc' ? '↓' : '↑'
}

function sortClass(key) {
  return sortKey.value === key ? 'on' : ''
}

const isShare = computed(() => mode.value === 'turnover_share' || mode.value === 'margin_share')

// 4 行表头：大类分组
const headerL1 = computed(() => {
  const groups = []
  let current = null
  for (const col of displayColumns.value) {
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
  for (const col of displayColumns.value) {
    const name = col.l2 || (col.agg ? '小计' : col.name)
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

/* Excel 式筛选栏 */
.ato-filter {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  padding: 10px 14px;
  border-bottom: 1px solid var(--line);
  background: #FBF9F3;
  border-radius: 6px 6px 0 0;
}

.ato-ipt {
  height: 28px;
  padding: 0 8px;
  border: 1px solid var(--line);
  border-radius: 4px;
  background: var(--card);
  font-size: 12px;
  color: var(--ink);
  outline: none;
}

.ato-ipt:focus {
  border-color: var(--navy);
}

.ato-ipt-n {
  width: 64px;
}

.ato-fitem {
  display: flex;
  align-items: center;
  gap: 5px;
}

.ato-flab {
  font-size: 12px;
  color: var(--muted);
  white-space: nowrap;
}

.ato-chk {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 12px;
  color: var(--muted);
  cursor: pointer;
  white-space: nowrap;
}

.ato-clear {
  height: 26px;
  padding: 0 10px;
  border: 1px solid var(--line);
  border-radius: 4px;
  background: var(--card);
  color: var(--muted);
  font-size: 12px;
  cursor: pointer;
}

.ato-clear:hover {
  color: var(--ink);
  border-color: var(--navy);
}

.ato-fcount {
  margin-left: auto;
  font-size: 11px;
  color: var(--muted);
  white-space: nowrap;
}

/* 可排序表头 */
th.ato-sort {
  cursor: pointer;
  user-select: none;
}

th.ato-sort:hover {
  filter: brightness(0.95);
}

.ato-arrow {
  font-style: normal;
  font-size: 10px;
  margin-left: 3px;
  opacity: 0.3;
}

.ato-arrow.on {
  opacity: 1;
  color: var(--navy);
}

.ato-empty {
  min-height: 200px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--muted);
}

/* ---------- 双表布局：左固定块 + 右滚动矩阵 ---------- */
.ato-scroll {
  max-height: calc(100vh - 220px);
  overflow: auto;
  border-radius: 0 0 6px 6px;
}

.ato-grid {
  display: flex;
  align-items: flex-start;
  width: max-content;
  min-width: 100%;
}

/* 左侧固定列：整个块 sticky，块内普通表格，列间不存在吸附缝隙 */
.ato-left {
  position: sticky;
  left: 0;
  z-index: 6;
  flex: none;
  background: var(--card);
  box-shadow: 1px 0 0 var(--line2);
}

.ato-tbl {
  border-collapse: separate;
  border-spacing: 0;
  table-layout: fixed;
  font-size: 12px;
}

.ato-tbl th,
.ato-tbl td {
  border-right: 1px solid var(--line2);
  border-bottom: 1px solid var(--line2);
  text-align: center;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  padding: 0 4px;
}

/* 行高严格一致，保证左右两表逐行对齐 */
.ato-tbl tbody tr {
  height: 30px;
}

/* 左表表头：单行撑满 4 层表头的高度 */
.ato-left thead tr {
  height: 104px;
}

.ato-left thead th {
  position: sticky;
  top: 0;
  z-index: 7;
  background: var(--soft);
  color: var(--ink);
  font-weight: 600;
  text-align: left;
  padding-left: 8px;
  vertical-align: middle;
}

.ato-left td {
  background: var(--card);
}

.ato-advisor {
  font-weight: 600;
  text-align: left;
  padding-left: 8px;
}

.ato-mono {
  font-family: var(--mono);
  font-size: 11px;
}

/* 右侧矩阵表头：4 层，每层 26px */
.ato-main thead tr {
  height: 26px;
}

.ato-main thead th {
  position: sticky;
  z-index: 3;
  color: var(--ink);
  font-weight: 600;
}

.ato-main thead tr:nth-child(1) th.ato-l1 {
  top: 0;
  background: #5B9BD5;
  color: #fff;
  font-size: 12px;
}

.ato-main thead tr:nth-child(2) th.ato-l2 {
  top: 26px;
  background: #D6E4F0;
  color: #2C4A6E;
  font-size: 12px;
}

.ato-main thead tr:nth-child(3) th.ato-code {
  top: 52px;
  background: #EDF2F8;
  font-family: var(--mono);
  font-size: 11px;
}

.ato-main thead tr:nth-child(4) th.ato-name {
  top: 78px;
  background: var(--soft);
  font-weight: 500;
  font-size: 11px;
}

.ato-main thead th.ato-agg {
  background: #F5EFD8;
}

/* 数据单元格：等宽小字号，62px 列宽可完整显示 */
.ato-cell {
  font-family: var(--mono);
  font-size: 11px;
  color: var(--ink);
}

.ato-cell.ato-agg {
  font-weight: 600;
}

/* 左右两表联动悬停 */
.ato-tbl tbody tr.ato-hover td {
  background-color: #F8F4E9;
}
</style>
