<template>
  <div class="d-anim max-w-6xl mx-auto">
    <!-- 筛选块 -->
    <div class="d-card" style="margin-bottom:14px">
      <div class="d-card-b" style="padding:12px 16px">
        <div class="al-filter-row">
          <span class="al-filter-label">投资逻辑</span>
          <button
            v-for="opt in LOGIC_OPTIONS"
            :key="opt.value"
            class="al-pill"
            :class="{ on: logicFilter === opt.value }"
            @click="logicFilter = opt.value"
          >{{ opt.label }}</button>
          <span class="al-filter-label" style="margin-left:22px">运行状态</span>
          <button
            v-for="opt in STATUS_OPTIONS"
            :key="opt.value"
            class="al-pill"
            :class="{ on: statusFilter === opt.value }"
            @click="statusFilter = opt.value"
          >{{ opt.label }}</button>
          <span class="al-filter-label" style="margin-left:22px">合并同名投顾</span>
          <button
            class="al-pill"
            :class="{ on: mergeMode }"
            @click="toggleMerge"
          >{{ mergeMode ? '已合并' : '未合并' }}</button>
        </div>
        <div class="al-filter-row" style="margin-top:10px">
          <span class="al-filter-label">投资品种</span>
          <button
            v-for="opt in CATE_OPTIONS"
            :key="opt.key"
            class="al-pill"
            :class="{ on: cateFilter === opt.key }"
            @click="cateFilter = opt.key"
          >{{ opt.label }}</button>
        </div>
      </div>
    </div>

    <div class="d-card">
      <div class="d-card-h">
        <div>
          <span class="d-card-t">投顾列表</span>
          <span class="d-card-x" style="margin-left:10px">
            筛选后 {{ sortedRows.length }} / {{ rows.length }} 个投顾 · 点击列头排序 · 点击行查看业绩详情
          </span>
        </div>
        <input v-model="search" name="advisor_search" class="d-ipt" style="width:200px;font-size:12px;padding:4px 8px" placeholder="搜索投顾名称/代码…" />
      </div>
      <div class="d-card-b">
        <div v-if="loading" style="display:flex;align-items:center;justify-content:center;height:300px">
          <span class="d-muted">加载中…</span>
        </div>
        <div v-else-if="error" style="display:flex;align-items:center;justify-content:center;height:300px">
          <span style="color:var(--up)">{{ error }}</span>
        </div>
        <template v-else>
          <div class="al-scroll">
            <table class="d-table">
              <thead>
                <tr>
                  <th v-for="col in columns" :key="col.key" :style="{ textAlign: col.align }">
                    <span
                      v-if="col.sortable"
                      class="al-sort"
                      :class="{ on: sortKey === col.key }"
                      @click="toggleSort(col.key)"
                    >
                      {{ col.label }}
                      <i class="al-arrow">{{ sortArrow(col.key) }}</i>
                    </span>
                    <template v-else>{{ col.label }}</template>
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="row in pagedRows"
                  :key="row.pid"
                  class="al-row"
                  @click="goDetail(row)"
                >
                  <td style="text-align:left">
                    <span class="al-name" :class="{ 'al-stopped': row.is_stop === 1 }">{{ row.account_name }}</span>
                    <span v-if="row.merged" class="al-merge-tag" :title="row.account_codes.join('、')">
                      {{ row.account_count }} 账号
                    </span>
                    <span v-else class="al-code d-mono">{{ row.account_code }}</span>
                    <span v-if="row.is_stop === 1" class="al-stop-tag">终止</span>
                  </td>
                  <td class="d-mono">{{ fmtMoney(row.cum_investment) }}</td>
                  <td class="d-mono">{{ row.avg_position == null ? '—' : row.avg_position.toFixed(2) + '%' }}</td>
                  <td class="d-mono" :class="pctClass(row.total_return)">{{ fmtPct(row.total_return) }}</td>
                  <td class="d-mono" :class="pctClass(row.annual_yield)">{{ fmtPct(row.annual_yield) }}</td>
                  <td class="d-mono">{{ fmtNum(row.sharpe_ratio) }}</td>
                  <td class="d-mono">{{ fmtNum(row.calmar_ratio) }}</td>
                  <td class="d-mono">{{ fmtPct(row.annual_volatility) }}</td>
                  <td class="d-mono d-dn">{{ fmtPct(row.max_drawdown) }}</td>
                </tr>
                <tr v-if="!sortedRows.length">
                  <td :colspan="columns.length" style="text-align:center;color:var(--muted);padding:32px 0">
                    没有匹配的投顾
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <!-- 分页 -->
          <div v-if="sortedRows.length" class="al-pager">
            <div class="al-page-size">
              <span>共 {{ sortedRows.length }} 条</span>
              <span>每页</span>
              <select v-model.number="pageSize" name="page_size" @change="page = 1">
                <option :value="10">10 条</option>
                <option :value="20">20 条</option>
                <option :value="50">50 条</option>
                <option :value="100">100 条</option>
              </select>
            </div>
            <div class="al-page-actions">
              <button type="button" :disabled="page === 1" @click="page = 1">首页</button>
              <button type="button" :disabled="page === 1" @click="page -= 1">上一页</button>
              <button
                v-for="p in pageNumbers"
                :key="p"
                type="button"
                :class="{ on: page === p }"
                @click="page = p"
              >{{ p }}</button>
              <button type="button" :disabled="page === totalPages" @click="page += 1">下一页</button>
              <button type="button" :disabled="page === totalPages" @click="page = totalPages">尾页</button>
            </div>
            <div class="al-page-jump">
              <span>前往</span>
              <input v-model="jumpPage" name="jump_page" type="number" min="1" :max="totalPages" @keydown.enter="goToPage" />
              <span>页</span>
              <button type="button" @click="goToPage">go</button>
            </div>
          </div>
          <div class="d-muted" style="font-size:11px;margin-top:10px">
            口径说明：总收益为成立以来收益；平均仓位为成立以来保证金占用率（Σ保证金 / 结算权益 的日均值）；
            年化收益/夏普/卡玛/年化波动/最大回撤取成立以来口径（合并模式下指标由 rh_funds 市值+出入金份额法净值推导，夏普无风险利率取 1.5%）。
          </div>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import client from '../../api/client'

const router = useRouter()
const rows = ref([])
const loading = ref(false)
const error = ref('')
const search = ref('')
const logicFilter = ref('')
const statusFilter = ref('running')
const cateFilter = ref('all')
const mergeMode = ref(true)
const sortKey = ref('cum_investment')
const sortDir = ref('desc')

const LOGIC_OPTIONS = [
  { value: '', label: '全部' },
  { value: '主观', label: '主观' },
  { value: '量化', label: '量化' },
]

const STATUS_OPTIONS = [
  { value: 'running', label: '运行中' },
  { value: 'stopped', label: '已终止' },
  { value: '', label: '全部' },
]

// 投资品种筛选：基于 invest_cate 包含匹配（覆盖具体品种归入大类）
const CATE_OPTIONS = [
  { key: 'all', label: '全部' },
  { key: '全品种', label: '全品种', re: /全品种|全板块/ },
  { key: '农产品', label: '农产品', re: /农产品|棉花|白糖|花生|豆一|豆二|玉米|淀粉|生鲜|软商品|生猪|鸡蛋|苹果|红枣/ },
  { key: '化工', label: '化工', re: /化工|能化|纯碱|玻璃|尿素|乙二醇|橡胶|沥青|碳酸锂|甲醇|PTA|苯乙烯/ },
  { key: '黑色', label: '黑色', re: /黑色/ },
  { key: '有色', label: '有色', re: /有色/ },
  { key: '贵金属', label: '贵金属', re: /贵金属|黄金|白银/ },
  { key: '宏观', label: '宏观', re: /宏观/ },
  { key: '国债', label: '国债', re: /国债/ },
  { key: 'other', label: '其他' },
]

const columns = [
  { key: 'account_name', label: '投顾名称', align: 'left' },
  { key: 'cum_investment', label: '投资金额', align: 'right', sortable: true },
  { key: 'avg_position', label: '平均仓位', align: 'right', sortable: true },
  { key: 'total_return', label: '总收益', align: 'right', sortable: true },
  { key: 'annual_yield', label: '年化收益', align: 'right', sortable: true },
  { key: 'sharpe_ratio', label: '夏普比率', align: 'right', sortable: true },
  { key: 'calmar_ratio', label: '卡玛比率', align: 'right', sortable: true },
  { key: 'annual_volatility', label: '年化波动', align: 'right', sortable: true },
  { key: 'max_drawdown', label: '最大回撤', align: 'right', sortable: true },
]

const sortedRows = computed(() => {
  let list = rows.value
  // 运行状态：默认只看运行中，可选已终止或全部
  if (statusFilter.value === 'running') {
    list = list.filter((r) => r.is_stop !== 1)
  } else if (statusFilter.value === 'stopped') {
    list = list.filter((r) => r.is_stop === 1)
  }
  if (logicFilter.value) {
    list = list.filter((r) => r.invest_logic === logicFilter.value)
  }
  if (cateFilter.value !== 'all') {
    if (cateFilter.value === 'other') {
      // 其他：invest_cate 非空且不匹配任何已定义大类
      list = list.filter((r) => {
        const v = r.invest_cate || ''
        if (!v) return false
        return !CATE_OPTIONS.some((o) => o.re && o.re.test(v))
      })
    } else {
      const opt = CATE_OPTIONS.find((o) => o.key === cateFilter.value)
      if (opt?.re) {
        list = list.filter((r) => opt.re.test(r.invest_cate || ''))
      }
    }
  }
  const q = search.value.trim().toLowerCase()
  if (q) {
    list = list.filter((r) =>
      [r.account_name || '', r.account_code || ''].some((f) => f.toLowerCase().includes(q))
    )
  }
  const key = sortKey.value
  const dir = sortDir.value === 'asc' ? 1 : -1
  return [...list].sort((a, b) => {
    const va = a[key], vb = b[key]
    if (va == null) return 1
    if (vb == null) return -1
    return (va - vb) * dir
  })
})

function toggleSort(key) {
  if (sortKey.value === key) {
    sortDir.value = sortDir.value === 'asc' ? 'desc' : 'asc'
  } else {
    sortKey.value = key
    sortDir.value = key === 'max_drawdown' ? 'asc' : 'desc'
  }
}

// 分页（前端分页：数据一次拉取，筛选/排序后分页展示）
const page = ref(1)
const pageSize = ref(20)
const jumpPage = ref('')
const totalPages = computed(() => Math.max(Math.ceil(sortedRows.value.length / pageSize.value), 1))
const pagedRows = computed(() => {
  const start = (page.value - 1) * pageSize.value
  return sortedRows.value.slice(start, start + pageSize.value)
})
const pageNumbers = computed(() => {
  const t = totalPages.value
  const current = page.value
  const start = Math.max(1, Math.min(current - 2, t - 4))
  const end = Math.min(t, start + 4)
  return Array.from({ length: end - start + 1 }, (_, i) => start + i)
})
function goToPage() {
  const p = Number(jumpPage.value)
  if (!p || p < 1 || p > totalPages.value) return
  jumpPage.value = ''
  page.value = p
}

// 筛选/搜索/排序/合并模式变化后回到第 1 页；页码越界自动收缩
watch(sortedRows, () => { page.value = 1 })
watch(totalPages, (t) => { if (page.value > t) page.value = t })

function sortArrow(key) {
  if (sortKey.value !== key) return '⇅'
  return sortDir.value === 'asc' ? '↑' : '↓'
}

function goDetail(row) {
  // 合并行跳转合并详情（?merged=1），单账号正常跳转
  if (row.merged) {
    router.push(`/display/advisor/detail/${row.pid}?merged=1`)
    return
  }
  router.push(`/display/advisor/detail/${row.pid}`)
}

function toggleMerge() {
  mergeMode.value = !mergeMode.value
  fetchList()
}

async function fetchList() {
  loading.value = true
  try {
    const { data } = await client.get('/tables/advisor/performance-list/', {
      params: mergeMode.value ? { merge: 1 } : {},
    })
    rows.value = data || []
  } catch (e) {
    console.error('获取投顾列表失败', e)
    error.value = '获取投顾列表失败'
  } finally {
    loading.value = false
  }
}

function fmtPct(v) {
  if (v == null) return '—'
  return (v >= 0 ? '+' : '') + Number(v).toFixed(2) + '%'
}
function fmtNum(v) {
  if (v == null) return '—'
  return Number(v).toFixed(2)
}
function pctClass(v) {
  if (v == null) return ''
  return v >= 0 ? 'd-up' : 'd-dn'
}
function fmtMoney(v) {
  if (v == null || v === '') return '—'
  const n = Number(v)
  if (Math.abs(n) >= 100000000) return `${(n / 100000000).toFixed(2)}亿`
  if (Math.abs(n) >= 10000) return `${(n / 10000).toFixed(0)}万`
  return n.toLocaleString('zh-CN', { maximumFractionDigits: 0 })
}

onMounted(fetchList)
</script>

<style scoped>
.al-filter-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
}

.al-filter-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--muted);
  margin-right: 8px;
  flex-shrink: 0;
}

.al-pill {
  border: 1px solid var(--line, #E5E0D2);
  background: var(--card, #FFFDF8);
  color: var(--muted);
  font-size: 12px;
  padding: 4px 14px;
  border-radius: 999px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.al-pill:hover {
  border-color: #C9A268;
  color: #9C6B2F;
}

.al-pill.on {
  background: #9C6B2F;
  border-color: #9C6B2F;
  color: #FFFDF8;
  font-weight: 500;
}

.al-scroll {
  overflow-x: auto;
}

.al-sort {
  cursor: pointer;
  user-select: none;
}

.al-sort:hover {
  color: #9C6B2F;
}

.al-sort.on {
  color: #9C6B2F;
  font-weight: 600;
}

.al-arrow {
  font-style: normal;
  font-size: 10px;
  margin-left: 2px;
  opacity: 0.7;
}

.al-row {
  cursor: pointer;
}

.al-row:hover td {
  background: #FBF6EC;
}

.al-name {
  font-size: 13px;
}

.al-name.al-stopped {
  color: var(--muted);
}

.al-stop-tag {
  display: inline-block;
  font-size: 10px;
  line-height: 1;
  padding: 3px 7px;
  margin-left: 6px;
  border-radius: 3px;
  color: #8F8A79;
  background: #EFECE3;
  border: 1px solid #E0DCCF;
}

.al-merge-tag {
  display: inline-block;
  font-size: 10px;
  line-height: 1;
  padding: 3px 7px;
  margin-left: 6px;
  border-radius: 3px;
  color: #9C6B2F;
  background: #F5EDE0;
  border: 1px solid #E4D5BC;
  cursor: help;
}

.al-code {
  font-size: 10.5px;
  color: var(--muted);
  margin-left: 8px;
}

/* 分页条 */
.al-pager {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
  gap: 12px;
  margin-top: 12px;
  color: var(--muted);
  font-size: 12px;
}

.al-page-size,
.al-page-jump {
  display: flex;
  align-items: center;
  gap: 8px;
}

.al-page-jump { justify-content: flex-end; }

.al-page-size select,
.al-page-jump input {
  height: 30px;
  border: 1px solid var(--line, #E5E0D2);
  border-radius: 7px;
  background: var(--card, #FFFDF8);
  color: var(--ink);
  font-size: 12px;
}

.al-page-size select { padding: 0 24px 0 10px; }

.al-page-jump input {
  width: 60px;
  padding: 0 8px;
  text-align: center;
}

.al-page-actions {
  display: flex;
  align-items: center;
  gap: 6px;
}

.al-page-actions button,
.al-page-jump button {
  min-width: 30px;
  height: 30px;
  padding: 0 9px;
  border: 1px solid var(--line, #E5E0D2);
  border-radius: 7px;
  background: var(--card, #FFFDF8);
  color: var(--muted);
  font-size: 12px;
  cursor: pointer;
}

.al-page-actions button:hover:not(:disabled),
.al-page-jump button:hover {
  border-color: #C9A268;
  color: #9C6B2F;
}

.al-page-actions button.on {
  border-color: #9C6B2F;
  background: #9C6B2F;
  color: #FFFDF8;
}

.al-page-actions button:disabled {
  cursor: not-allowed;
  opacity: 0.45;
}

@media (max-width: 900px) {
  .al-pager { grid-template-columns: 1fr; }
  .al-page-actions,
  .al-page-jump { justify-content: flex-start; }
}
</style>
