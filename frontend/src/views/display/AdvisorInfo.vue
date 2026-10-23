<template>
  <div class="d-anim w-full">
    <div class="d-card">
      <div class="d-card-h">
        <div>
          <span class="d-card-t">投顾信息</span>
          <span class="d-card-x" style="margin-left:10px">产品运维 · 投顾台账维护（共 {{ total }} 条）</span>
        </div>
        <div style="display:flex;gap:8px;align-items:center">
          <input v-model="search" class="d-ipt" style="font-size:12px;padding:5px 10px;width:180px" placeholder="搜索姓名 / 账户 / 产品" />
          <template v-if="canEdit">
            <button class="d-btn" @click="downloadTemplate">下载模板</button>
            <button class="d-btn" @click="pickImport">导入</button>
            <input ref="importInput" type="file" accept=".xlsx" style="display:none" @change="onImportChange" />
            <button class="d-btn" @click="exportRows">导出</button>
            <button class="d-btn" @click="openCreate">新增投顾</button>
          </template>
        </div>
      </div>
      <div class="d-card-b">
        <div v-if="!auth.isAuthenticated" class="ai-login-tip">
          未登录仅可查看，<router-link :to="`/login?redirect=${encodeURIComponent($route.fullPath)}`">去登录</router-link> 后可维护数据
        </div>

        <div v-if="importResult" class="ai-import-result" :class="{ 'ai-import-err': importResult.hasError }">
          <span>导入完成：新增 {{ importResult.created }} 条 · 更新 {{ importResult.updated }} 条 · 跳过 {{ importResult.skipped }} 条</span>
          <div v-for="e in importResult.errors" :key="e" style="margin-top:2px">{{ e }}</div>
          <a class="ai-modal-x" style="font-size:14px" @click="importResult = null">×</a>
        </div>

        <div v-if="loading" style="display:flex;align-items:center;justify-content:center;height:200px">
          <span class="d-muted">加载中…</span>
        </div>
        <div v-else-if="error" style="display:flex;align-items:center;justify-content:center;height:200px">
          <span style="color:var(--up)">{{ error }}</span>
        </div>
        <div v-else class="ai-scroll">
          <table class="d-table">
            <thead>
              <tr>
                <th>姓名</th>
                <th>操作账户</th>
                <th>创建日期</th>
                <th>所属产品</th>
                <th>投资金额</th>
                <th>最大保证金使用(%)</th>
                <th>预警线</th>
                <th>止损线</th>
                <th>追保风险线</th>
                <th>强平风险线</th>
                <th>分红率(%)</th>
                <th>能否交易期权</th>
                <th>交易期权类型</th>
                <th>运行状态</th>
                <th>暂停日期</th>
                <th>清盘总盈亏</th>
                <th>投资标签</th>
                <th>投资逻辑</th>
                <th>备注</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="!rows.length && !loading">
                <td :colspan="20" style="text-align:center;color:var(--muted);padding:32px 0">
                  暂无数据，点击右上角「新增投顾」录入
                </td>
              </tr>
              <tr v-for="r in rows" :key="r.id">
                <td style="font-weight:600">{{ r.name }}</td>
                <td class="d-mono">{{ r.account_code || '—' }}</td>
                <td class="d-mono">{{ r.create_date || '—' }}</td>
                <td>{{ r.product || '—' }}</td>
                <td class="d-mono">{{ fmtMoney(r.invest_amount) }}</td>
                <td class="d-mono">{{ fmtRatioPct(r.max_margin_usage) }}</td>
                <td class="d-mono">{{ fmtNum(r.warning_line) }}</td>
                <td class="d-mono">{{ fmtNum(r.stop_loss_line) }}</td>
                <td class="d-mono">{{ fmtNum(r.margin_call_risk) }}</td>
                <td class="d-mono">{{ fmtNum(r.force_close_risk) }}</td>
                <td class="d-mono">{{ fmtRatioPct(r.dividend_rate) }}</td>
                <td>{{ r.can_trade_option ? '✓ 能' : '—' }}</td>
                <td>{{ r.option_trade_type || '—' }}</td>
                <td><span class="ai-status" :class="statusCls(r.run_status)">{{ r.run_status || '—' }}</span></td>
                <td class="d-mono">{{ r.suspend_date || '—' }}</td>
                <td class="d-mono" :class="pnlColor(r.liquidation_pnl)">{{ fmtMoney(r.liquidation_pnl) }}</td>
                <td>{{ r.invest_tag || '—' }}</td>
                <td class="d-muted">{{ r.invest_logic || '—' }}</td>
                <td
                  class="d-muted ai-remark"
                  :class="{ on: expandedRemark === r.id }"
                  :title="r.remark ? '点击展开/收起' : ''"
                  @click="toggleRemark(r)"
                >{{ r.remark || '—' }}</td>
                <td style="white-space:nowrap">
                  <a class="ai-op" @click="openEdit(r)">编辑</a>
                  <a class="ai-op ai-op-del" @click="remove(r)">删除</a>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- 分页 -->
        <div v-if="total" class="ai-pager">
          <div class="ai-page-size">
            <span>共 {{ total }} 条</span>
            <span>每页</span>
            <select v-model.number="pageSize" @change="changePage(1)">
              <option :value="10">10 条</option>
              <option :value="20">20 条</option>
              <option :value="50">50 条</option>
              <option :value="100">100 条</option>
            </select>
          </div>
          <div class="ai-page-actions">
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
          <div class="ai-page-jump">
            <span>前往</span>
            <input v-model="jumpPage" name="jump_page" type="number" min="1" :max="totalPages" @keydown.enter="goToPage" />
            <span>页</span>
            <button type="button" @click="goToPage">go</button>
          </div>
        </div>
      </div>
    </div>

    <!-- 新增 / 编辑弹窗 -->
    <div v-if="showModal" class="ai-mask" @click.self="closeModal">
      <div class="ai-modal">
        <div class="ai-modal-h">
          <span>{{ form.id ? '编辑投顾' : '新增投顾' }}</span>
          <a class="ai-modal-x" @click="closeModal">×</a>
        </div>
        <div class="ai-modal-b">
          <div class="ai-form">
            <label class="ai-fld"><span>姓名<i>*</i></span><input v-model.trim="form.name" class="d-ipt" placeholder="投顾姓名" /></label>
            <label class="ai-fld"><span>操作账户</span><input v-model.trim="form.account_code" class="d-ipt" placeholder="如 YL009、260416_JH" /></label>
            <label class="ai-fld"><span>创建日期</span><input v-model="form.create_date" type="date" class="d-ipt" /></label>
            <label class="ai-fld"><span>所属产品</span><input v-model.trim="form.product" class="d-ipt" placeholder="所属产品" /></label>
            <label class="ai-fld"><span>投资金额（万元）</span><input v-model.number="form.invest_amount" type="number" class="d-ipt" placeholder="投资金额" /></label>
            <label class="ai-fld"><span>最大保证金使用（%）</span><input v-model.number="form.max_margin_usage" type="number" class="d-ipt" placeholder="如 30" /></label>
            <label class="ai-fld"><span>预警线</span><input v-model.number="form.warning_line" type="number" class="d-ipt" placeholder="如 0.85" /></label>
            <label class="ai-fld"><span>止损线</span><input v-model.number="form.stop_loss_line" type="number" class="d-ipt" placeholder="如 0.80" /></label>
            <label class="ai-fld"><span>追保风险线</span><input v-model.number="form.margin_call_risk" type="number" class="d-ipt" placeholder="如 1.5" /></label>
            <label class="ai-fld"><span>强平风险线</span><input v-model.number="form.force_close_risk" type="number" class="d-ipt" placeholder="如 1.8" /></label>
            <label class="ai-fld"><span>分红率（%）</span><input v-model.number="form.dividend_rate" type="number" class="d-ipt" placeholder="如 20（存为 0.2）" /></label>
            <label class="ai-fld">
              <span>能否交易期权</span>
              <select v-model="form.can_trade_option" class="d-ipt">
                <option :value="true">能</option>
                <option :value="false">否</option>
              </select>
            </label>
            <label class="ai-fld"><span>交易期权类型</span><input v-model.trim="form.option_trade_type" class="d-ipt" placeholder="如 买方 / 卖方 / 买卖双向" /></label>
            <label class="ai-fld">
              <span>运行状态</span>
              <select v-model="form.run_status" class="d-ipt">
                <option v-for="s in runStatuses" :key="s" :value="s">{{ s }}</option>
              </select>
            </label>
            <label class="ai-fld"><span>暂停日期</span><input v-model="form.suspend_date" type="date" class="d-ipt" /></label>
            <label class="ai-fld"><span>清盘总盈亏（万元）</span><input v-model.number="form.liquidation_pnl" type="number" class="d-ipt" placeholder="清盘总盈亏" /></label>
            <label class="ai-fld"><span>投资标签</span><input v-model.trim="form.invest_tag" class="d-ipt" placeholder="如 趋势 CTA / 期权卖方" /></label>
            <label class="ai-fld ai-fld-wide"><span>投资逻辑</span><input v-model.trim="form.invest_logic" class="d-ipt" placeholder="投资逻辑" /></label>
            <label class="ai-fld ai-fld-wide"><span>备注</span><input v-model.trim="form.remark" class="d-ipt" placeholder="备注" /></label>
          </div>
          <div v-if="formError" class="ai-form-err">{{ formError }}</div>
        </div>
        <div class="ai-modal-f">
          <button class="d-btn" @click="closeModal">取消</button>
          <button class="d-btn ai-btn-save" @click="save" :disabled="saving">{{ saving ? '保存中…' : '保存' }}</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import client from '../../api/client'
import { useAuthStore } from '../../stores/auth'

const auth = useAuthStore()
const router = useRouter()

// 未登录时引导登录（保留回跳）
function requireLogin() {
  if (auth.isAuthenticated) return true
  router.push(`/login?redirect=${encodeURIComponent(window.location.pathname)}`)
  return false
}

const rows = ref([])
const loading = ref(false)
const error = ref('')
const search = ref('')

// 分页（服务端分页）
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const jumpPage = ref('')
const totalPages = computed(() => Math.max(Math.ceil(total.value / pageSize.value), 1))
const pageNumbers = computed(() => {
  const t = totalPages.value
  const current = page.value
  const start = Math.max(1, Math.min(current - 2, t - 4))
  const end = Math.min(t, start + 4)
  return Array.from({ length: end - start + 1 }, (_, i) => start + i)
})

const showModal = ref(false)
const saving = ref(false)
const formError = ref('')
const importInput = ref(null)
const importResult = ref(null)
const importing = ref(false)
const emptyForm = () => ({
  id: null,
  name: '',
  account_code: '',
  invest_amount: null,
  max_margin_usage: null,
  warning_line: null,
  stop_loss_line: null,
  margin_call_risk: null,
  force_close_risk: null,
  dividend_rate: null,
  can_trade_option: false,
  option_trade_type: '',
  product: '',
  run_status: '运行中',
  suspend_date: null,
  create_date: null,
  liquidation_pnl: null,
  invest_tag: '',
  invest_logic: '',
  remark: '',
})
const form = ref(emptyForm())

const canEdit = computed(() => auth.isAuthenticated)

const runStatuses = ['运行中', '已暂停', '已清盘']

// 备注列：点击展开/收起全文（同时只展开一条）
const expandedRemark = ref(null)
function toggleRemark(r) {
  expandedRemark.value = expandedRemark.value === r.id ? null : r.id
}
function statusCls(s) {
  if (s === '运行中') return 'ai-status-run'
  if (s === '已暂停') return 'ai-status-pause'
  if (s === '已清盘') return 'ai-status-close'
  return ''
}

const filteredRows = computed(() => rows.value)

async function load() {
  loading.value = true
  error.value = ''
  try {
    const { data } = await client.get('/tables/product-ops/advisor-info/', {
      params: {
        page: page.value,
        page_size: pageSize.value,
        ...(search.value.trim() ? { search: search.value.trim() } : {}),
      },
    })
    rows.value = data.rows || []
    total.value = data.total || 0
  } catch (e) {
    error.value = e.response?.data?.detail || '加载失败'
  } finally {
    loading.value = false
  }
}

function changePage(p) {
  const target = Math.min(Math.max(p, 1), totalPages.value)
  if (target === page.value) return
  page.value = target
  load()
}

function goToPage() {
  const p = Number(jumpPage.value)
  if (!p || p < 1 || p > totalPages.value) return
  jumpPage.value = ''
  changePage(p)
}

// 搜索变化：防抖后回到第 1 页重查
let searchTimer = null
watch(search, () => {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    page.value = 1
    load()
  }, 300)
})

function openCreate() {
  if (!requireLogin()) return
  form.value = emptyForm()
  formError.value = ''
  showModal.value = true
}

function openEdit(r) {
  if (!requireLogin()) return
  form.value = {
    ...r,
    // 百分比形态进表单（库中为小数）
    max_margin_usage: r.max_margin_usage == null ? null : Number(r.max_margin_usage) * 100,
    dividend_rate: r.dividend_rate == null ? null : Number(r.dividend_rate) * 100,
  }
  formError.value = ''
  showModal.value = true
}

function closeModal() {
  showModal.value = false
}

async function save() {
  if (!form.value.name) {
    formError.value = '姓名不能为空'
    return
  }
  saving.value = true
  formError.value = ''
  try {
    const payload = { ...form.value }
    delete payload.updated_at
    // 表单百分比 → 库中小数
    payload.max_margin_usage = pctToRatio(form.value.max_margin_usage)
    payload.dividend_rate = pctToRatio(form.value.dividend_rate)
    if (payload.id) {
      await client.put(`/tables/product-ops/advisor-info/${payload.id}/`, payload)
    } else {
      await client.post('/tables/product-ops/advisor-info/', payload)
    }
    showModal.value = false
    await load()
  } catch (e) {
    formError.value = e.response?.data?.detail || '保存失败'
  } finally {
    saving.value = false
  }
}

async function remove(r) {
  if (!requireLogin()) return
  if (!window.confirm(`确认删除投顾「${r.name}」？`)) return
  try {
    await client.delete(`/tables/product-ops/advisor-info/${r.id}/`)
    await load()
  } catch (e) {
    window.alert(e.response?.data?.detail || '删除失败')
  }
}

// ---------- 模板 / 导入 / 导出 ----------

function _saveBlob(resp, fallbackName) {
  const cd = resp.headers?.['content-disposition'] || ''
  const m = cd.match(/filename\*=UTF-8''([^;]+)/)
  const name = m ? decodeURIComponent(m[1]) : fallbackName
  const url = URL.createObjectURL(new Blob([resp.data]))
  const a = document.createElement('a')
  a.href = url
  a.download = name
  a.click()
  URL.revokeObjectURL(url)
}

async function downloadTemplate() {
  try {
    const resp = await client.get('/tables/mom_advisor_info/template/', { responseType: 'blob' })
    _saveBlob(resp, '投顾信息_导入模板.xlsx')
  } catch (e) {
    window.alert(e.response?.data?.detail || '模板下载失败')
  }
}

async function exportRows() {
  try {
    const resp = await client.get('/tables/mom_advisor_info/export/', {
      responseType: 'blob',
      params: search.value.trim() ? { search: search.value.trim() } : {},
    })
    _saveBlob(resp, '投顾信息.xlsx')
  } catch (e) {
    window.alert(e.response?.data?.detail || '导出失败')
  }
}

function pickImport() {
  importInput.value?.click()
}

async function onImportChange(e) {
  const file = e.target.files?.[0]
  e.target.value = ''
  if (!file) return
  importing.value = true
  importResult.value = null
  try {
    const fd = new FormData()
    fd.append('file', file)
    const { data } = await client.post('/tables/mom_advisor_info/import/', fd)
    importResult.value = {
      created: data.created,
      updated: data.updated,
      skipped: data.skipped,
      errors: data.errors || [],
      hasError: !!(data.errors && data.errors.length),
    }
    await load()
  } catch (err) {
    const detail = err.response?.data?.detail
    importResult.value = {
      created: 0,
      updated: 0,
      skipped: 0,
      errors: [typeof detail === 'string' ? detail : '导入失败'],
      hasError: true,
    }
  } finally {
    importing.value = false
  }
}

function fmtMoney(v) {
  if (v == null || v === '') return '—'
  return Number(v).toLocaleString('zh-CN', { maximumFractionDigits: 2 })
}
function fmtNum(v) {
  if (v == null || v === '') return '—'
  return Number(v).toLocaleString('zh-CN', { maximumFractionDigits: 4 })
}
// 库中小数形态 → 百分比显示（0.2 → 20.00%）
function fmtRatioPct(v) {
  if (v == null || v === '') return '—'
  return (Number(v) * 100).toFixed(2) + '%'
}
// 表单百分比 → 库中小数（30 → 0.3）
function pctToRatio(v) {
  const n = Number(v)
  if (v === null || v === '' || v === undefined || Number.isNaN(n)) return null
  return n / 100
}
function fmtPctField(v) {
  if (v == null || v === '') return '—'
  return Number(v).toFixed(2) + '%'
}
function pnlColor(v) {
  if (v == null) return ''
  return v >= 0 ? 'd-up' : 'd-dn'
}

onMounted(load)
</script>

<style scoped>
.ai-login-tip {
  font-size: 12px;
  color: var(--muted);
  background: var(--soft);
  border: 1px solid var(--line);
  border-radius: 4px;
  padding: 6px 12px;
  margin-bottom: 10px;
}
.ai-login-tip a {
  color: #9C6B2F;
  text-decoration: underline dotted;
}
.ai-import-result {
  position: relative;
  font-size: 12px;
  background: #EDF5EF;
  border: 1px solid #BCD9C9;
  border-radius: 4px;
  padding: 8px 30px 8px 12px;
  margin-bottom: 10px;
  color: #1F5C40;
}
.ai-import-result.ai-import-err {
  background: #F9EDEB;
  border-color: #E2B4AE;
  color: #7A2E26;
}
.ai-import-result .ai-modal-x {
  position: absolute;
  top: 6px;
  right: 10px;
  color: inherit;
}
.ai-scroll {
  overflow-x: auto;
}

/* 等宽列：fixed 布局均分列宽，内容居中、自动换行 */
.ai-scroll .d-table {
  table-layout: fixed;
}
.ai-scroll .d-table th {
  padding: 6px 4px;
  text-align: center;
  white-space: normal;
  word-break: break-word;
}
.ai-scroll .d-table td {
  padding: 6px 4px;
  font-size: 12px;
  text-align: center;
  word-break: break-word;
}

/* 分页 */
.ai-pager {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
  margin-top: 12px;
  font-size: 12px;
  color: var(--muted);
}
.ai-page-size {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.ai-page-size select {
  border: 1px solid var(--line);
  border-radius: 4px;
  background: transparent;
  font-size: 12px;
  padding: 2px 4px;
  color: inherit;
}
.ai-page-actions {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}
.ai-page-actions button {
  min-width: 26px;
  height: 24px;
  padding: 0 7px;
  border: 1px solid var(--line);
  border-radius: 4px;
  background: transparent;
  font-size: 12px;
  color: inherit;
  cursor: pointer;
}
.ai-page-actions button:hover:not(:disabled) {
  border-color: #9C6B2F;
  color: #9C6B2F;
}
.ai-page-actions button.on {
  background: #9C6B2F;
  border-color: #9C6B2F;
  color: #FDFCF8;
}
.ai-page-actions button:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
.ai-page-jump {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.ai-page-jump input {
  width: 52px;
  border: 1px solid var(--line);
  border-radius: 4px;
  background: transparent;
  font-size: 12px;
  padding: 3px 6px;
  color: inherit;
}
.ai-page-jump button {
  height: 24px;
  padding: 0 10px;
  border: 1px solid var(--line);
  border-radius: 4px;
  background: transparent;
  font-size: 12px;
  color: inherit;
  cursor: pointer;
}
.ai-page-jump button:hover {
  border-color: #9C6B2F;
  color: #9C6B2F;
}
/* 备注列：超宽省略，点击展开全文 */
.ai-remark {
  max-width: 220px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  cursor: pointer;
}
.ai-remark.on {
  white-space: normal;
  overflow: visible;
  background: #F8F4E9;
}

.ai-status {
  display: inline-block;
  font-size: 11px;
  padding: 1px 8px;
  border-radius: 3px;
  border: 1px solid transparent;
}
.ai-status-run {
  color: #1F5C40;
  background: #EDF5EF;
  border-color: #BCD9C9;
}
.ai-status-pause {
  color: #8A6D1C;
  background: #F7F1DF;
  border-color: #E3D6A8;
}
.ai-status-close {
  color: #7A2E26;
  background: #F9EDEB;
  border-color: #E2B4AE;
}
.ai-op {
  color: #9C6B2F;
  cursor: pointer;
  font-size: 12px;
  margin-right: 8px;
  text-decoration: underline dotted rgba(156, 107, 47, 0.6);
  text-underline-offset: 3px;
}
.ai-op:hover {
  color: #B03A2E;
}
.ai-op-del {
  color: #B03A2E;
  text-decoration-color: rgba(176, 58, 46, 0.6);
}

.ai-mask {
  position: fixed;
  inset: 0;
  background: rgba(32, 40, 58, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
}
.ai-modal {
  width: 680px;
  max-width: calc(100vw - 40px);
  max-height: calc(100vh - 60px);
  background: #FDFCF8;
  border: 1px solid var(--line);
  border-radius: 8px;
  box-shadow: 0 12px 40px rgba(32, 40, 58, 0.25);
  display: flex;
  flex-direction: column;
}
.ai-modal-h {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 18px;
  border-bottom: 1px solid var(--line);
  font-family: var(--serif);
  font-weight: 600;
  font-size: 15px;
}
.ai-modal-x {
  cursor: pointer;
  font-size: 18px;
  color: var(--muted);
  line-height: 1;
}
.ai-modal-x:hover {
  color: #B03A2E;
}
.ai-modal-b {
  padding: 16px 18px;
  overflow-y: auto;
}
.ai-modal-f {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding: 12px 18px;
  border-top: 1px solid var(--line);
}
.ai-btn-save {
  background: #9C6B2F;
  border-color: #9C6B2F;
  color: #FDFCF8;
}
.ai-btn-save:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.ai-form {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px 16px;
}
.ai-fld {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 12px;
}
.ai-fld > span {
  color: var(--muted);
}
.ai-fld > span i {
  color: #B03A2E;
  font-style: normal;
  margin-left: 2px;
}
.ai-fld-wide {
  grid-column: 1 / -1;
}
.ai-form-err {
  color: #B03A2E;
  font-size: 12px;
  margin-top: 10px;
}
</style>
