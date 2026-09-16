<template>
  <div class="max-w-6xl mx-auto">
    <div class="mb-5">
      <h2 class="text-lg font-semibold text-ink">板块持仓概览</h2>
      <p class="text-sm text-ink-muted mt-1">板块 / 品种 / 合约三级持仓结构，点击行首图标展开或合并</p>
    </div>

    <section class="d-card">
      <div class="d-card-h">
        <div>
          <span class="d-card-t">持仓概览</span>
          <span class="d-card-x" style="margin-left:10px">持仓 {{ data.trade_date || '—' }} · 市场 {{ data.market_date || '—' }}</span>
        </div>
        <div class="spo-tools">
          <button class="spo-btn" @click="expandAllTree">全部展开</button>
          <button class="spo-btn" @click="collapseAllTree">全部合并</button>
        </div>
      </div>
      <div class="d-card-b">
        <div v-if="loading" class="spo-empty">加载中...</div>
        <div v-else-if="error" class="spo-empty">{{ error }}</div>
        <div v-else class="spo-wrap">
          <table class="d-table spo-table">
            <thead>
              <tr>
                <th class="spo-name-col">板块 / 品种 / 合约</th>
                <th>代码</th>
                <th>净持仓市值</th>
                <th>净市值变化1天</th>
                <th>净市值变化1周</th>
                <th>波动率</th>
                <th>波动率分位数</th>
                <th>全市场持仓量</th>
                <th>持仓量占比</th>
                <th>持仓量分位数</th>
                <th>全市场成交量</th>
                <th>成交量占比</th>
                <th>成交量分位数</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="row in treeFlatRows"
                :key="row.key"
                :class="`spo-lv${row.level}`"
                @click="toggleTreeNode(row)"
              >
                <td class="spo-name-col">
                  <span :style="{ marginLeft: `${row.depth * 18}px` }" class="spo-name-inner">
                    <i v-if="row.children.length" class="spo-caret" :class="{ open: row.expanded }">▸</i>
                    <i v-else class="spo-caret spo-caret-leaf"></i>
                    {{ row.name }}
                    <span v-if="row.level < 3" class="spo-cnt">({{ row.children.length }})</span>
                  </span>
                </td>
                <td class="d-mono spo-code">{{ row.code }}</td>
                <td class="d-mono" :class="negCls(row.net_market_value)">{{ fmtMoney(row.net_market_value) }}</td>
                <td class="d-mono" :class="negCls(row.net_mv_chg_1d)">{{ fmtMoney(row.net_mv_chg_1d) }}</td>
                <td class="d-mono" :class="negCls(row.net_mv_chg_1w)">{{ fmtMoney(row.net_mv_chg_1w) }}</td>
                <td class="d-mono">{{ fmtPct(row.volatility) }}</td>
                <td class="d-mono">{{ fmtPctl(row.vol_pctl) }}</td>
                <td class="d-mono">{{ fmtInt(row.total_oi) }}</td>
                <td class="d-mono">{{ fmtPctl(row.oi_share) }}</td>
                <td class="d-mono">{{ fmtPctl(row.oi_pctl) }}</td>
                <td class="d-mono">{{ fmtInt(row.total_volume) }}</td>
                <td class="d-mono">{{ fmtPctl(row.volume_share) }}</td>
                <td class="d-mono">{{ fmtPctl(row.volume_pctl) }}</td>
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
  walk(data.value.rows || [], 0)
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
  expandedKeys.value = collectKeys(data.value.rows || [], new Set())
}

function collapseAllTree() {
  expandedKeys.value = new Set()
}

function fmtMoney(value) {
  if (value == null || value === '') return '—'
  const n = Number(value)
  if (Math.abs(n) >= 100000000) return `${(n / 100000000).toFixed(2)}亿`
  if (Math.abs(n) >= 10000) return `${(n / 10000).toFixed(2)}万`
  return n.toLocaleString('zh-CN', { maximumFractionDigits: 2 })
}

function fmtInt(value) {
  if (value == null || value === '') return '—'
  return Number(value).toLocaleString('zh-CN', { maximumFractionDigits: 0 })
}

// 已是百分比值，直接附加百分号（波动率）
function fmtPct(value) {
  if (value == null || value === '') return '—'
  return `${Number(value).toFixed(2)}%`
}

// 0-1 分位/占比，乘 100 转百分位
function fmtPctl(value) {
  if (value == null || value === '') return '—'
  return `${(Number(value) * 100).toFixed(1)}%`
}

function negCls(value) {
  return Number(value) < 0 ? 'spo-neg' : ''
}

async function fetchOverview() {
  loading.value = true
  error.value = ''
  try {
    const { data: res } = await client.get('/tables/sector/position-overview/')
    data.value = res || {}
  } catch (e) {
    console.error('获取板块持仓概览失败', e)
    error.value = '获取板块持仓概览失败'
    data.value = {}
  } finally {
    loading.value = false
  }
}

onMounted(fetchOverview)
</script>

<style scoped>
.spo-empty {
  min-height: 200px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--muted);
}

.spo-tools {
  display: flex;
  gap: 8px;
}

.spo-btn {
  border: 1px solid var(--line);
  background: var(--card);
  color: var(--ink);
  font-size: 12px;
  padding: 4px 10px;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.spo-btn:hover {
  border-color: #4472C4;
  color: #4472C4;
}

.spo-wrap {
  max-height: calc(100vh - 260px);
  min-height: 320px;
  overflow: auto;
  border: 1px solid var(--line);
  border-radius: 4px;
}

.spo-table thead th {
  position: sticky;
  top: 0;
  z-index: 3;
  background: var(--soft);
  white-space: nowrap;
}

.spo-table th,
.spo-table td {
  text-align: right;
  white-space: nowrap;
  padding: 8px 12px;
}

.spo-table th.spo-name-col,
.spo-table td.spo-name-col {
  text-align: left;
  position: sticky;
  left: 0;
  z-index: 2;
  background: var(--card);
  box-shadow: 1px 0 0 var(--line);
}

.spo-table thead th.spo-name-col {
  z-index: 4;
  background: var(--soft);
}

.spo-table th:nth-child(2),
.spo-table td:nth-child(2) {
  text-align: left;
}

.spo-table tbody tr {
  cursor: pointer;
}

.spo-lv1 td {
  font-weight: 600;
  background: #F5F1E6;
}

.spo-lv1 td.spo-name-col {
  background: #F5F1E6;
}

.spo-lv2 td.spo-name-col {
  font-weight: 500;
}

.spo-name-inner {
  display: inline-flex;
  align-items: center;
  gap: 5px;
}

.spo-caret {
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

.spo-caret.open {
  transform: rotate(90deg);
}

.spo-caret-leaf {
  visibility: hidden;
}

.spo-cnt {
  color: var(--muted);
  font-size: 11px;
  font-family: var(--mono);
}

.spo-code {
  color: var(--muted);
}

.spo-neg {
  color: #C5504B;
}
</style>
