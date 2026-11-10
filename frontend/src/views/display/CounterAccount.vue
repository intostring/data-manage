<template>
  <div class="d-anim w-full">
    <div class="d-card">
      <div class="d-card-h">
        <div>
          <span class="d-card-t">柜台账户</span>
          <span class="d-card-x" style="margin-left:10px">mom_fund_status 每日快照 · 只读（{{ rows.length }} 个账户）</span>
        </div>
        <div style="display:flex;gap:8px;align-items:center">
          <input v-model="date" type="date" class="d-ipt" style="font-size:12px;padding:5px 8px;width:140px" :max="latestDate" @change="load" />
          <div ref="comboRef" style="position:relative;width:260px">
            <input
              v-model="accountSearch"
              name="counter_account_search"
              autocomplete="off"
              class="d-ipt"
              style="width:100%;font-size:12px;padding:5px 10px"
              placeholder="按客户名称筛选账户…"
              @focus="showAccountDropdown = true"
              @input="accountHoverIdx = -1"
              @keydown.down.prevent="hoverNextAccount"
              @keydown.up.prevent="hoverPrevAccount"
              @keydown.enter.prevent="confirmHoverAccount"
              @keydown.esc="showAccountDropdown = false"
            />
            <div v-if="showAccountDropdown && accountOptions.length" class="d-combo-list">
              <div
                class="d-combo-it ca-combo-it"
                :class="{ on: !customer }"
                @mousedown.prevent="pickFund(null)"
              >
                <span class="ca-cust">全部账户</span>
              </div>
              <div
                v-for="(f, i) in accountOptions"
                :key="f.short"
                class="d-combo-it ca-combo-it"
                :class="{ on: accountHoverIdx === i || customer === f.short }"
                :title="`${f.full}${f.count > 1 ? ` · 共 ${f.count} 个账户` : ''}`"
                @mousedown.prevent="pickFund(f)"
                @mouseenter="accountHoverIdx = i"
              >
                <span class="ca-cust">{{ f.short }}</span>
              </div>
            </div>
          </div>
          <input v-model="search" class="d-ipt" style="font-size:12px;padding:5px 10px;width:160px" placeholder="搜索账户 / 客户 / 公司" />
        </div>
      </div>
      <div class="d-card-b">
        <div v-if="loading" style="display:flex;align-items:center;justify-content:center;height:200px">
          <span class="d-muted">加载中…</span>
        </div>
        <div v-else-if="error" style="display:flex;align-items:center;justify-content:center;height:200px">
          <span style="color:var(--up)">{{ error }}</span>
        </div>
        <div v-else-if="!filteredRows.length" style="display:flex;align-items:center;justify-content:center;height:200px">
          <span class="d-muted">{{ date }} 无数据（非交易日或账户未同步）</span>
        </div>
        <div v-else class="ca-scroll">
          <table class="d-table">
            <thead>
              <tr>
                <th>交易日期</th>
                <th>期货公司</th>
                <th>保证金账户</th>
                <th>期货账户</th>
                <th>客户名称</th>
                <th>上日结存</th>
                <th>客户权益</th>
                <th>出入金</th>
                <th>货币资金</th>
                <th>当日盈亏</th>
                <th>权利金总额</th>
                <th>手续费</th>
                <th>冻结</th>
                <th>结存</th>
                <th>占用保证金</th>
                <th>浮动盈亏</th>
                <th>可用资金</th>
                <th>风险度</th>
                <th>追加保证金</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="r in filteredRows" :key="r.margin_account">
                <td class="d-mono">{{ r.trade_date }}</td>
                <td style="text-align:left">{{ r.broker_name || '—' }}</td>
                <td class="d-mono">{{ r.margin_account || '—' }}</td>
                <td class="d-mono">{{ r.futures_account || '—' }}</td>
                <td class="d-muted" style="text-align:left;max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" :title="r.customer_name">{{ shortName(r.customer_name) || '—' }}</td>
                <td class="d-mono">{{ fmtMoney(r.prev_balance) }}</td>
                <td class="d-mono" style="font-weight:600">{{ fmtMoney(r.customer_equity) }}</td>
                <td class="d-mono" :class="pnlColor(r.deposit_withdraw)">{{ fmtMoney(r.deposit_withdraw) }}</td>
                <td class="d-mono">{{ fmtMoney(r.currency_funds) }}</td>
                <td class="d-mono" :class="pnlColor(r.day_pl)">{{ fmtMoney(r.day_pl) }}</td>
                <td class="d-mono">{{ fmtMoney(r.total_premium) }}</td>
                <td class="d-mono">{{ fmtMoney(r.fee) }}</td>
                <td class="d-mono">{{ fmtMoney(r.frozen) }}</td>
                <td class="d-mono">{{ fmtMoney(r.balance) }}</td>
                <td class="d-mono">{{ fmtMoney(r.margin_occupied) }}</td>
                <td class="d-mono" :class="pnlColor(r.floating_pl)">{{ fmtMoney(r.floating_pl) }}</td>
                <td class="d-mono">{{ fmtMoney(r.available) }}</td>
                <td class="d-mono" :class="riskColor(r.risk_degree)">{{ fmtPct(r.risk_degree) }}</td>
                <td class="d-mono">{{ fmtMoney(r.margin_call) }}</td>
              </tr>
            </tbody>
            <tfoot v-if="filteredRows.length">
              <tr class="ca-total">
                <td colspan="5">合计（{{ filteredRows.length }} 个账户）</td>
                <td class="d-mono">{{ fmtMoney(totals.prev_balance) }}</td>
                <td class="d-mono">{{ fmtMoney(totals.customer_equity) }}</td>
                <td class="d-mono" :class="pnlColor(totals.deposit_withdraw)">{{ fmtMoney(totals.deposit_withdraw) }}</td>
                <td class="d-mono">{{ fmtMoney(totals.currency_funds) }}</td>
                <td class="d-mono" :class="pnlColor(totals.day_pl)">{{ fmtMoney(totals.day_pl) }}</td>
                <td class="d-mono">{{ fmtMoney(totals.total_premium) }}</td>
                <td class="d-mono">{{ fmtMoney(totals.fee) }}</td>
                <td class="d-mono">{{ fmtMoney(totals.frozen) }}</td>
                <td class="d-mono">{{ fmtMoney(totals.balance) }}</td>
                <td class="d-mono">{{ fmtMoney(totals.margin_occupied) }}</td>
                <td class="d-mono" :class="pnlColor(totals.floating_pl)">{{ fmtMoney(totals.floating_pl) }}</td>
                <td class="d-mono">{{ fmtMoney(totals.available) }}</td>
                <td class="d-mono">{{ fmtPct(totals.risk_degree) }}</td>
                <td class="d-mono">{{ fmtMoney(totals.margin_call) }}</td>
              </tr>
            </tfoot>
          </table>
        </div>
        <div class="d-muted" style="font-size:11px;margin-top:8px">
          数据来源：mom_fund_status（每日同步，当前最新 {{ latestDate || '—' }}）；金额单位为元（万/亿缩写），风险度为百分比；本页面只读。
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import client from '../../api/client'

const rows = ref([])
const accounts = ref([])
const loading = ref(false)
const error = ref('')
const date = ref('')
const customer = ref('')
const search = ref('')
const latestDate = ref('')

// 账户下拉：按客户名称（基金简称）筛选
const accountSearch = ref('')
const showAccountDropdown = ref(false)
const accountHoverIdx = ref(-1)
const comboRef = ref(null)

// 按简称去重为基金选项：同一基金在各期货公司的账户合并为一项
const fundOptions = computed(() => {
  const map = new Map()
  for (const a of accounts.value) {
    const short = shortName(a.customer_name) || '—'
    if (!map.has(short)) {
      map.set(short, { short, full: a.customer_name || '', count: 0 })
    }
    map.get(short).count += 1
  }
  return [...map.values()]
})

const accountOptions = computed(() => {
  const kw = accountSearch.value.trim().toLowerCase()
  if (!kw) return fundOptions.value
  return fundOptions.value.filter(
    (f) => f.short.toLowerCase().includes(kw) || f.full.toLowerCase().includes(kw),
  )
})

// 客户名称简称：去掉管理人前缀（首个「公司」前，含其后的连字符）与「私募证券投资基金」等后缀
function shortName(name) {
  if (!name) return ''
  let s = name
  const idx = s.indexOf('公司')
  if (idx >= 0) s = s.slice(idx + 2)
  s = s.replace(/^[-—－]+/, '')
  s = s.replace(/(私募证券投资基金|私募基金|证券投资基金)$/, '')
  return s || name
}

function hoverNextAccount() {
  showAccountDropdown.value = true
  accountHoverIdx.value = Math.min(accountHoverIdx.value + 1, accountOptions.value.length - 1)
}
function hoverPrevAccount() {
  accountHoverIdx.value = Math.max(accountHoverIdx.value - 1, -1)
}
function confirmHoverAccount() {
  if (accountHoverIdx.value >= 0 && accountHoverIdx.value < accountOptions.value.length) {
    pickFund(accountOptions.value[accountHoverIdx.value])
  } else {
    showAccountDropdown.value = false
  }
}

function pickFund(f) {
  customer.value = f ? f.short : ''
  accountSearch.value = f ? f.short : ''
  showAccountDropdown.value = false
  accountHoverIdx.value = -1
  load()
}

// 数据刷新后同步输入框显示为已选基金简称
watch(customer, (v) => {
  if (v && accountSearch.value !== v) accountSearch.value = v
})

function onDocPointerDown(e) {
  if (comboRef.value && !comboRef.value.contains(e.target)) {
    showAccountDropdown.value = false
  }
}

const filteredRows = computed(() => {
  const kw = search.value.trim().toLowerCase()
  if (!kw) return rows.value
  return rows.value.filter(
    (r) =>
      (r.margin_account || '').toLowerCase().includes(kw) ||
      (r.futures_account || '').toLowerCase().includes(kw) ||
      (r.customer_name || '').toLowerCase().includes(kw) ||
      (r.broker_name || '').toLowerCase().includes(kw)
  )
})

// 合计行：金额列求和；风险度 = Σ占用保证金 / Σ客户权益
const SUM_KEYS = [
  'prev_balance', 'customer_equity', 'deposit_withdraw', 'currency_funds', 'day_pl',
  'total_premium', 'fee', 'frozen', 'balance', 'margin_occupied', 'floating_pl',
  'available', 'margin_call',
]
const totals = computed(() => {
  const t = Object.fromEntries(SUM_KEYS.map((k) => [k, 0]))
  for (const r of filteredRows.value) {
    for (const k of SUM_KEYS) {
      if (r[k] != null) t[k] += Number(r[k])
    }
  }
  t.risk_degree = t.customer_equity > 0 ? (t.margin_occupied / t.customer_equity) * 100 : null
  return t
})

async function load() {
  loading.value = true
  error.value = ''
  try {
    const params = {}
    if (date.value) params.date = date.value
    if (customer.value) params.customer = customer.value
    const { data } = await client.get('/tables/product-ops/counter-account/', { params })
    rows.value = data.rows || []
    accounts.value = data.accounts || []
    latestDate.value = data.latest_date || ''
    if (!date.value) date.value = data.trade_date || ''
  } catch (e) {
    error.value = e.response?.data?.detail || '加载失败'
  } finally {
    loading.value = false
  }
}

let searchTimer = null
watch(search, () => {
  clearTimeout(searchTimer)
}, { flush: 'sync' })

function fmtMoney(v) {
  if (v == null || v === '') return '—'
  const n = Number(v)
  if (Math.abs(n) >= 100000000) return `${(n / 100000000).toFixed(2)}亿`
  if (Math.abs(n) >= 10000) return `${(n / 10000).toFixed(2)}万`
  return n.toLocaleString('zh-CN', { maximumFractionDigits: 2 })
}
function fmtPct(v) {
  if (v == null || v === '') return '—'
  return Number(v).toFixed(2) + '%'
}
function pnlColor(v) {
  if (v == null || v === 0) return ''
  return v > 0 ? 'd-up' : 'd-dn'
}
function riskColor(v) {
  if (v == null) return ''
  if (v >= 95) return 'd-dn'
  if (v >= 85) return ''
  return 'd-up'
}

onMounted(() => {
  load()
  document.addEventListener('pointerdown', onDocPointerDown)
})
onUnmounted(() => {
  document.removeEventListener('pointerdown', onDocPointerDown)
})
</script>

<style scoped>
/* 账户组合框选项：仅显示客户名称 */
.ca-combo-it {
  justify-content: flex-start;
}
.ca-cust {
  font-size: 12px;
  max-width: 230px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ca-scroll {
  overflow-x: auto;
}
.ca-scroll .d-table th {
  padding: 6px 6px;
  text-align: center;
  white-space: normal;
  word-break: break-word;
}
.ca-scroll .d-table td {
  padding: 6px 6px;
  font-size: 12px;
  text-align: center;
  word-break: break-word;
}

/* 合计行 */
.ca-total td {
  position: sticky;
  bottom: 0;
  background: var(--soft);
  border-top: 2px solid var(--line);
  font-weight: 600;
  white-space: nowrap;
}
</style>
