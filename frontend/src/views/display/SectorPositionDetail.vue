<template>
  <div class="max-w-6xl mx-auto">
    <div class="mb-5">
      <h2 class="text-lg font-semibold text-ink">板块持仓明细</h2>
      <p class="text-sm text-ink-muted mt-1">板块 / 品种 / 合约三级持仓结构，点击行首图标展开或合并</p>
    </div>

    <section class="d-card">
      <div class="d-card-h">
        <div>
          <span class="d-card-t">持仓明细</span>
          <span class="d-card-x" style="margin-left:10px">截至 {{ treeData.trade_date || '—' }} · 按保证金占用降序</span>
        </div>
        <div class="spd-tools">
          <button class="spd-btn" @click="expandAllTree">全部展开</button>
          <button class="spd-btn" @click="collapseAllTree">全部合并</button>
        </div>
      </div>
      <div class="d-card-b">
        <div v-if="treeLoading" class="spd-empty">加载中...</div>
        <div v-else-if="treeError" class="spd-empty">{{ treeError }}</div>
        <div v-else class="spd-table-wrap">
          <table class="d-table spd-table">
            <thead>
              <tr>
                <th class="spd-name-col">板块 / 品种 / 合约</th>
                <th>买数量</th>
                <th>卖数量</th>
                <th>净头寸</th>
                <th>买保证金</th>
                <th>卖保证金</th>
                <th>总保证金</th>
                <th>净保证金</th>
                <th>保证金占比</th>
                <th>买持仓市值</th>
                <th>卖持仓市值</th>
                <th>净持仓市值</th>
                <th>净市值日变化</th>
                <th>净市值日变化%</th>
                <th>净市值周变化</th>
                <th>净市值周变化%</th>
                <th>近10天波动率</th>
                <th>近20天波动率</th>
                <th>近60天波动率</th>
                <th>风险度近10天</th>
                <th>风险度近20天</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="row in treeFlatRows"
                :key="row.key"
                :class="`spd-lv${row.level}`"
                @click="toggleTreeNode(row)"
              >
                <td class="spd-name-col">
                  <span :style="{ marginLeft: `${row.depth * 18}px` }" class="spd-name-inner">
                    <i v-if="row.children.length" class="spd-caret" :class="{ open: row.expanded }">▸</i>
                    <i v-else class="spd-caret spd-caret-leaf"></i>
                    {{ row.name }}
                    <span v-if="row.level < 3" class="spd-cnt">({{ row.children.length }})</span>
                  </span>
                </td>
                <td class="d-mono">{{ fmtInt(row.buy_num) }}</td>
                <td class="d-mono">{{ fmtInt(row.sell_num) }}</td>
                <td class="d-mono" :class="negCls(row.net_num)">{{ fmtInt(row.net_num) }}</td>
                <td class="d-mono">{{ fmtMoney(row.buy_margin) }}</td>
                <td class="d-mono">{{ fmtMoney(row.sell_margin) }}</td>
                <td class="d-mono">{{ fmtMoney(row.total_margin) }}</td>
                <td class="d-mono" :class="negCls(row.net_margin)">{{ fmtMoney(row.net_margin) }}</td>
                <td class="d-mono">{{ fmtRatioPct(row.margin_ratio) }}</td>
                <td class="d-mono">{{ fmtMoney(row.buy_market_value) }}</td>
                <td class="d-mono">{{ fmtMoney(row.sell_market_value) }}</td>
                <td class="d-mono" :class="negCls(row.net_market_value)">{{ fmtMoney(row.net_market_value) }}</td>
                <td class="d-mono" :class="negCls(row.net_mv_chg_1d)">{{ fmtMoney(row.net_mv_chg_1d) }}</td>
                <td class="d-mono" :class="negCls(row.net_mv_chr_1d)">{{ fmtPct(row.net_mv_chr_1d) }}</td>
                <td class="d-mono" :class="negCls(row.net_mv_chg_1w)">{{ fmtMoney(row.net_mv_chg_1w) }}</td>
                <td class="d-mono" :class="negCls(row.net_mv_chr_1w)">{{ fmtPct(row.net_mv_chr_1w) }}</td>
                <td class="d-mono">{{ fmtPct(row.hv_10d) }}</td>
                <td class="d-mono">{{ fmtPct(row.hv_20d) }}</td>
                <td class="d-mono">{{ fmtPct(row.hv_60d) }}</td>
                <td class="d-mono">{{ fmtPct(row.risk_degree_10d) }}</td>
                <td class="d-mono">{{ fmtPct(row.risk_degree_20d) }}</td>
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

const treeLoading = ref(false)
const treeError = ref('')
const treeData = ref({})
const expandedKeys = ref(new Set())

// 深度优先拍平树，仅保留祖先均已展开的节点
const treeFlatRows = computed(() => {
  const flat = []
  const walk = (rows, depth) => {
    for (const node of rows) {
      const key = `${node.level}-${node.code}`
      const expanded = expandedKeys.value.has(key)
      flat.push({ ...node, key, depth, expanded })
      if (expanded && node.children && node.children.length) walk(node.children, depth + 1)
    }
  }
  walk(treeData.value.rows || [], 0)
  return flat
})

function toggleTreeNode(row) {
  if (!row.children || !row.children.length) return
  const keys = new Set(expandedKeys.value)
  if (keys.has(row.key)) keys.delete(row.key)
  else keys.add(row.key)
  expandedKeys.value = keys
}

function collectKeys(rows, acc) {
  for (const node of rows || []) {
    if (node.children && node.children.length) {
      acc.add(`${node.level}-${node.code}`)
      collectKeys(node.children, acc)
    }
  }
  return acc
}

function expandAllTree() {
  expandedKeys.value = collectKeys(treeData.value.rows || [], new Set())
}

function collapseAllTree() {
  expandedKeys.value = new Set()
}

function fmtInt(value) {
  if (value == null || value === '') return '—'
  return Number(value).toLocaleString('zh-CN', { maximumFractionDigits: 0 })
}

function fmtMoney(value) {
  if (value == null || value === '') return '—'
  const n = Number(value)
  if (Math.abs(n) >= 100000000) return `${(n / 100000000).toFixed(2)}亿`
  if (Math.abs(n) >= 10000) return `${(n / 10000).toFixed(2)}万`
  return n.toLocaleString('zh-CN', { maximumFractionDigits: 2 })
}

// 已是百分比值，直接附加百分号
function fmtPct(value) {
  if (value == null || value === '') return '—'
  return `${Number(value).toFixed(2)}%`
}

// 0-1 比例，乘 100 转百分比
function fmtRatioPct(value) {
  if (value == null || value === '') return '—'
  return `${(Number(value) * 100).toFixed(2)}%`
}

function negCls(value) {
  return Number(value) < 0 ? 'spd-neg' : ''
}

async function fetchDetailTree() {
  treeLoading.value = true
  treeError.value = ''
  try {
    const { data } = await client.get('/tables/sector/bk-detail-tree/')
    treeData.value = data || {}
  } catch (e) {
    console.error('获取板块持仓明细失败', e)
    treeError.value = '获取板块持仓明细失败'
    treeData.value = {}
  } finally {
    treeLoading.value = false
  }
}

onMounted(fetchDetailTree)
</script>

<style scoped>
.spd-empty {
  min-height: 200px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--muted);
}

.spd-tools {
  display: flex;
  gap: 8px;
}

.spd-btn {
  border: 1px solid var(--line);
  background: var(--card);
  color: var(--ink);
  font-size: 12px;
  padding: 4px 10px;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.spd-btn:hover {
  border-color: #4472C4;
  color: #4472C4;
}

.spd-table-wrap {
  max-height: calc(100vh - 260px);
  min-height: 320px;
  overflow: auto;
  border: 1px solid var(--line);
  border-radius: 4px;
}

.spd-table thead th {
  position: sticky;
  top: 0;
  z-index: 3;
  background: var(--soft);
}

.spd-table th,
.spd-table td {
  text-align: right;
  white-space: nowrap;
}

.spd-table th.spd-name-col,
.spd-table td.spd-name-col {
  text-align: left;
  position: sticky;
  left: 0;
  z-index: 2;
  background: var(--card);
  box-shadow: 1px 0 0 var(--line);
}

.spd-table thead th.spd-name-col {
  z-index: 4;
  background: var(--soft);
}

.spd-table tbody tr {
  cursor: pointer;
}

.spd-lv1 td {
  font-weight: 600;
  background: #F5F1E6;
}

.spd-lv2 td.spd-name-col {
  font-weight: 500;
}

.spd-name-inner {
  display: inline-flex;
  align-items: center;
  gap: 5px;
}

.spd-caret {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 14px;
  height: 14px;
  font-size: 11px;
  color: var(--muted);
  transition: transform 0.15s ease;
  font-style: normal;
  flex: 0 0 auto;
}

.spd-caret.open {
  transform: rotate(90deg);
}

.spd-caret-leaf {
  visibility: hidden;
}

.spd-cnt {
  color: var(--muted);
  font-size: 11px;
  font-family: var(--mono);
}

.spd-neg {
  color: #C5504B;
}
</style>
