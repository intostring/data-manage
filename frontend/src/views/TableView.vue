<template>
  <div>
    <!-- 顶部工具栏 -->
    <div class="flex items-center justify-between mb-5">
      <div>
        <h2 class="text-xl font-bold text-ink">{{ tableLabel || tableKey }}</h2>
        <p class="text-sm text-ink-muted mt-1">
          {{ kind === 'existing' ? '已有业务表' : '动态上传表' }}
          <span v-if="total > 0" class="ml-2">· {{ total }} 条</span>
        </p>
      </div>
      <div class="flex items-center gap-2">
        <BaseInput v-model="search" placeholder="搜索…" type="text" class="!w-48" />
        <BaseButton variant="secondary" size="md" :icon="RefreshCw" :disabled="loading" @click="fetchData">
          刷新
        </BaseButton>
        <BaseButton variant="secondary" size="md" :icon="Download" :disabled="exporting" @click="exportExcel">
          {{ exporting ? '导出中…' : '导出' }}
        </BaseButton>
        <BaseButton variant="secondary" size="md" :icon="Upload" :disabled="importing" @click="triggerImport">
          {{ importing ? '导入中…' : '导入' }}
        </BaseButton>
        <BaseButton variant="ghost" size="md" :icon="FileSpreadsheet" @click="downloadTemplate">
          模板
        </BaseButton>
        <input
          ref="importInput"
          type="file"
          accept=".xlsx,.xls"
          class="hidden"
          @change="onImportFileChange"
        />
        <BaseButton v-if="kind === 'existing'" variant="primary" size="md" :icon="Plus" @click="openCreate">
          新增
        </BaseButton>
      </div>
    </div>

    <!-- 筛选状态条 -->
    <div v-if="hasActiveFilters" class="mb-3 flex items-center gap-2 text-xs text-ink-muted">
      <span>当前筛选：</span>
      <span
        v-for="(val, key) in activeFilterDisplay"
        :key="key"
        class="inline-flex items-center gap-1 px-2 py-0.5 bg-panelLight border border-line rounded"
      >
        {{ filterLabel(key) }}: {{ val }}
        <button class="text-ink-faint hover:text-danger" @click="clearFilter(key)">×</button>
      </span>
      <button class="text-accent hover:underline" @click="clearAllFilters">清除全部</button>
    </div>

    <!-- 数据表格 -->
    <div class="bg-panel border border-line rounded shadow-card">
      <div v-if="loading" class="px-5 py-16 text-center text-ink-faint text-sm">加载中…</div>
      <BaseTable
        v-else
        :columns="columns"
        :rows="rows"
        :sort-key="sortKey"
        :sort-order="sortOrder"
        :filter-values="filterValues"
        @sort="onSort"
        @filter="onFilter"
        @clear-filter="clearFilter"
      >
        <template v-if="kind === 'existing'" #actions="{ row }">
          <div class="flex items-center justify-end gap-3 text-xs">
            <button class="text-ink-muted hover:text-accent transition-colors" @click="openEdit(row)">编辑</button>
            <button class="text-ink-muted hover:text-danger transition-colors" @click="confirmDelete(row)">删除</button>
          </div>
        </template>
      </BaseTable>
    </div>

    <!-- 分页 -->
    <div class="mt-4" v-if="total > 0">
      <Pagination :total="total" :page="page" :page-size="pageSize" @change="onPageChange" @size-change="onPageSizeChange" />
    </div>

    <!-- 新增/编辑模态框 -->
    <BaseModal :show="formShow" :title="formMode === 'create' ? '新增记录' : '编辑记录'" @close="formShow = false">
      <div class="space-y-4">
        <div v-for="col in editableColumns" :key="col.key" class="space-y-1">
          <label v-if="col.options" class="block text-sm text-ink-muted">{{ col.label }}</label>
          <select
            v-if="col.options"
            v-model="form[col.key]"
            class="w-full px-3 py-2 border border-line rounded bg-panelLight text-ink focus:border-accent focus:outline-none"
          >
            <option v-for="opt in col.options" :key="opt.value" :value="opt.value">
              {{ opt.label }}
            </option>
          </select>
          <BaseInput
            v-else
            v-model="form[col.key]"
            :label="col.label"
            :type="inputType(col)"
            :placeholder="col.label"
          />
        </div>
        <!-- 日期字段使用日期控件 -->
        <div v-for="col in dateColumns" :key="col.key" class="space-y-1">
          <label class="block text-sm text-ink-muted">{{ col.label }}</label>
          <input
            v-model="form[col.key]"
            type="date"
            class="w-full px-3 py-2 border border-line rounded bg-panelLight text-ink focus:border-accent focus:outline-none"
          />
        </div>
      </div>
      <template #footer>
        <BaseButton variant="ghost" size="md" @click="formShow = false">取消</BaseButton>
        <BaseButton variant="primary" size="md" :disabled="saving" @click="saveRecord">
          {{ saving ? '保存中…' : '保存' }}
        </BaseButton>
      </template>
    </BaseModal>

    <!-- 删除确认 -->
    <BaseModal :show="deleteShow" title="确认删除" @close="deleteShow = false">
      <p class="text-sm text-ink">确定删除这条记录吗？此操作不可撤销。</p>
      <template #footer>
        <BaseButton variant="ghost" size="md" @click="deleteShow = false">取消</BaseButton>
        <BaseButton variant="danger" size="md" :disabled="deleting" @click="doDelete">
          {{ deleting ? '删除中…' : '删除' }}
        </BaseButton>
      </template>
    </BaseModal>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { RefreshCw, Plus, Download, Upload, FileSpreadsheet } from 'lucide-vue-next'
import BaseTable from '../components/ui/BaseTable.vue'
import BaseButton from '../components/ui/BaseButton.vue'
import BaseInput from '../components/ui/BaseInput.vue'
import BaseModal from '../components/ui/BaseModal.vue'
import Pagination from '../components/ui/Pagination.vue'
import client from '../api/client'
import { useToast } from '../components/ui/toast'

const route = useRoute()
const toast = useToast()

const kind = computed(() => (route.name === 'existing-table' ? 'existing' : 'dynamic'))
const tableKey = computed(() => route.params.key)

// 导入/导出状态
const exporting = ref(false)
const importing = ref(false)
const importInput = ref(null)

const rows = ref([])
const columns = ref([])
const tableLabel = ref('')
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const search = ref('')
const loading = ref(false)

// 排序状态
const sortKey = ref('')
const sortOrder = ref('asc')

// 筛选状态：{ colKey: { op, value } }
const filterValues = ref({})

// 表单状态
const formShow = ref(false)
const formMode = ref('create')
const form = ref({})
const editingId = ref(null)
const saving = ref(false)

// 删除状态
const deleteShow = ref(false)
const deletingRow = ref(null)
const deleting = ref(false)

let searchTimer = null

const editableColumns = computed(() => columns.value.filter((c) => c.key !== 'id' && c.type !== 'date' && c.type !== 'datetime'))
const dateColumns = computed(() => columns.value.filter((c) => c.type === 'date' || c.type === 'datetime'))
const primaryKey = computed(() => columns.value.find((c) => c.primary_key)?.key || 'id')

const OP_LABELS = {
  eq: '等于', ne: '不等于', contains: '包含', not_contains: '不包含',
  gt: '大于', lt: '小于', gte: '大于等于', lte: '小于等于',
  empty: '为空', not_empty: '不为空',
}

const hasActiveFilters = computed(() => {
  return Object.values(filterValues.value).some((f) => f && (f.value || f.op === 'empty' || f.op === 'not_empty'))
})
const activeFilterDisplay = computed(() => {
  const out = {}
  for (const [k, f] of Object.entries(filterValues.value)) {
    if (f && (f.value || f.op === 'empty' || f.op === 'not_empty')) {
      out[k] = `${OP_LABELS[f.op] || f.op} ${f.value || ''}`
    }
  }
  return out
})

function filterLabel(key) {
  const col = columns.value.find((c) => c.key === key)
  return col ? col.label : key
}

function inputType(col) {
  if (col.type === 'int') return 'number'
  if (col.type === 'float') return 'number'
  if (col.type === 'datetime' || col.type === 'date') return 'text'
  if (col.type === 'bool') return 'text'
  return 'text'
}

// 需要按整数显示的金额类字段（DecimalField 原带小数，这里四舍五入为整数）
const INTEGER_FIELDS = new Set([
  'cum_investment',    // 总投资金额
  'mk_bf',             // 初始市值
  'distribution_26',   // 26年分红
  'distribution_bf',   // 历史分红
  'redeem_mv',         // 赎回市值
  'new_add',           // 当日新增规模
])

// 需要显示 2 位小数的比率类字段
const DECIMAL2_FIELDS = new Set([
  'stop_loss_rate',    // 止损线
  'max_pos_rate',      // 最大保证金比例
  'perf_fee',          // 业绩报酬比例
  'share_chg',         // 份额变动
])

// 需要显示 4 位小数的字段（如基金净值）
const DECIMAL4_FIELDS = new Set([
  'unit_nav',          // 单位净值
  'accum_nav',         // 累计净值
  'adjust_nav',        // 复权净值
  'price',             // 变动价格
])

// 各表自定义可见字段与顺序（按字段 name 指定，只显示列出的字段并按此顺序排列）
// 未配置的表默认显示全部字段
const TABLE_FIELD_CONFIG = {
  mom_account_record: [
    'account_id',          // 投顾ID
    'account_name',        // 投顾名称
    'product_name',        // 所属产品
    'create_time',         // 创建时间
    'status',              // 状态
    'cum_investment',      // 总投资金额
    'stop_loss_rate',      // 止损线
    'max_pos_rate',        // 最大保证金比例
    'mk_bf',               // 初始市值
    'is_stop',             // 是否停止
    'account_tag',         // 投顾的类型
    'perf_fee',            // 业绩报酬比例
    'distribution_26',     // 26年分红
    'distribution_bf',     // 历史分红
    'redeem_mv',           // 赎回市值
    'new_add',             // 当日新增规模
    'tips',                // 说明
    'invest_cate',         // 投顾类型
    'invest_logic',        // 投资逻辑
  ],
}

// 将后端字段元信息 [{name, label, type}] 转为 BaseTable 所需的 columns 配置
function buildColumns(colsMeta, tableKey) {
  if (!colsMeta || !colsMeta.length) return []
  // 如果该表配置了可见字段，按配置顺序过滤
  const fieldOrder = TABLE_FIELD_CONFIG[tableKey]
  let meta = colsMeta
  if (fieldOrder) {
    const metaMap = new Map(colsMeta.map((c) => [c.name, c]))
    meta = fieldOrder.map((name) => metaMap.get(name)).filter(Boolean)
  }
  return meta.map((c) => {
    const labelParts = tableKey === 'perf_risk_indicators'
      ? { label: c.label || c.name, hint: '' }
      : splitLabelHint(c.label || c.name)
    const isNumeric = c.type === 'int' || c.type === 'float'
    // 长文本字段（如 raw_json）或指定字段（如 tips）截断显示，点击弹窗查看详情
    const EXPANDABLE_STR_FIELDS = new Set(['tips', 'raw_json'])
    // 实际是日期但存为 CharField 的字段，统一视为日期类型
    const DATE_STR_FIELDS = new Set([
      'create_time',       // 账户记录-创建时间
      'create_date',       // 投顾信息-创建日期
      'trading_day',       // 交易日期
      'crawl_time',        // 爬取时间
      'last_edit_date',    // 最后编辑日期
      'start_date',        // 成立日期
      'open_date',         // 开仓日期
    ])
    let colType = c.type
    if (DATE_STR_FIELDS.has(c.name)) colType = 'date'
    const isMomStopField = tableKey === 'mom_account_record' && c.name === 'is_stop'
    const isMomAccountTagField = tableKey === 'mom_account_record' && c.name === 'account_tag'
    const isRiskPercentField = tableKey === 'perf_risk_indicators'
      && (
        c.name.startsWith('annual_yield_')
        || c.name.startsWith('annual_volatility_')
        || c.name.startsWith('max_drawdown_')
      )
    return {
      key: c.name,
      label: labelParts.label,
      labelTitle: labelParts.hint,
      type: colType,
      sortable: true,
      filterable: true,
      mono: isNumeric,
      width: c.name === 'raw_json' ? '96px' : undefined,
      previewWidth: c.name === 'raw_json' ? '72px' : undefined,
      valueMap: isMomStopField
        ? { 0: '启用', 1: '停止' }
        : (isMomAccountTagField
          ? { 1: '外部投顾', 2: '内部投顾', 3: '外部代持', 4: '内部持仓' }
          : undefined),
      options: isMomStopField
        ? [
          { label: '启用', value: 0 },
          { label: '停止', value: 1 },
        ]
        : (isMomAccountTagField
          ? [
            { label: '外部投顾', value: 1 },
            { label: '内部投顾', value: 2 },
            { label: '外部代持', value: 3 },
            { label: '内部持仓', value: 4 },
          ]
          : undefined),
      format: INTEGER_FIELDS.has(c.name)
        ? 'integer'
        : (isRiskPercentField
          ? 'percent1'
          : (['max_pos_rate', 'perf_fee'].includes(c.name)
          ? 'percent2'
          : (DECIMAL2_FIELDS.has(c.name)
          ? 'decimal2'
          : (DECIMAL4_FIELDS.has(c.name) ? 'decimal4' : undefined)))),
      expandable: c.type === 'text' || EXPANDABLE_STR_FIELDS.has(c.name),
      truncate: c.name === 'raw_json',
    }
  })
}

function splitLabelHint(label) {
  const fullMatch = String(label).match(/^(.+?)[（(]([^）)]*)[）)]$/)
  if (fullMatch) {
    return {
      label: fullMatch[1].trim(),
      hint: fullMatch[2].trim(),
    }
  }

  const openIndex = Math.max(String(label).lastIndexOf('（'), String(label).lastIndexOf('('))
  if (openIndex > 0) {
    return {
      label: String(label).slice(0, openIndex).trim(),
      hint: String(label).slice(openIndex + 1).trim(),
    }
  }

  return { label, hint: '' }
}

async function fetchColumns() {
  try {
    if (kind.value === 'existing') {
      const { data } = await client.get(`/tables/${tableKey.value}/columns/`)
      tableLabel.value = data.label
      columns.value = buildColumns(data.columns, tableKey.value)
    } else {
      // 动态表：先请求数据接口获取 columns（label=name，CSV 表头由用户定义）
      const { data } = await client.get(`/dynamic/${tableKey.value}/`, {
        params: { page: 1, page_size: 1 },
      })
      tableLabel.value = ''
      // 动态表 columns 已带 name/type，补 label=name
      const cols = (data.columns || []).map((c) => ({ ...c, label: c.label || c.name }))
      columns.value = buildColumns(cols, tableKey.value)
    }
  } catch (e) {
    toast.error(e.response?.data?.detail || '获取字段信息失败')
  }
}

async function fetchData() {
  loading.value = true
  try {
    const ordering = sortKey.value
      ? (sortOrder.value === 'desc' ? `-${sortKey.value}` : sortKey.value)
      : undefined

    // 构建筛选参数：filter.<col>.<op>=value
    const filterParams = {}
    for (const [k, f] of Object.entries(filterValues.value)) {
      if (!f) continue
      if (f.op === 'empty' || f.op === 'not_empty') {
        filterParams[`filter.${k}.${f.op}`] = '1'
      } else if (f.value) {
        filterParams[`filter.${k}.${f.op}`] = f.value
      }
    }

    if (kind.value === 'existing') {
      const { data } = await client.get(`/tables/${tableKey.value}/`, {
        params: {
          page: page.value,
          page_size: pageSize.value,
          search: search.value || undefined,
          ordering,
          ...filterParams,
        },
      })
      const list = data.results || data
      rows.value = list
      total.value = data.count ?? list.length
    } else {
      const { data } = await client.get(`/dynamic/${tableKey.value}/`, {
        params: {
          page: page.value,
          page_size: pageSize.value,
          search: search.value || undefined,
          ordering,
          ...filterParams,
        },
      })
      rows.value = data.results || []
      total.value = data.count || 0
    }
  } catch (e) {
    toast.error(e.response?.data?.detail || '加载失败')
    rows.value = []
  } finally {
    loading.value = false
  }
}

function onPageChange(p) {
  page.value = p
  fetchData()
}

function onPageSizeChange(size) {
  pageSize.value = size
  page.value = 1
  fetchData()
}

function onSort({ key, order }) {
  sortKey.value = key
  sortOrder.value = order
  page.value = 1
  fetchData()
}

function onFilter({ key, value }) {
  filterValues.value = { ...filterValues.value, [key]: value }
  page.value = 1
  fetchData()
}

function clearFilter(key) {
  const next = { ...filterValues.value }
  delete next[key]
  filterValues.value = next
  page.value = 1
  fetchData()
}

function clearAllFilters() {
  filterValues.value = {}
  page.value = 1
  fetchData()
}

watch(search, () => {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    page.value = 1
    fetchData()
  }, 350)
})

watch(tableKey, () => {
  columns.value = []
  rows.value = []
  page.value = 1
  search.value = ''
  sortKey.value = ''
  sortOrder.value = 'asc'
  filterValues.value = {}
  fetchColumns().then(() => fetchData())
})

function openCreate() {
  formMode.value = 'create'
  form.value = {}
  editableColumns.value.forEach((c) => (form.value[c.key] = c.options ? c.options[0].value : ''))
  editingId.value = null
  formShow.value = true
}

function openEdit(row) {
  formMode.value = 'edit'
  form.value = { ...row }
  editingId.value = row[primaryKey.value]
  formShow.value = true
}

async function saveRecord() {
  saving.value = true
  try {
    const payload = { ...form.value }
    delete payload.id
    if (kind.value === 'existing') {
      if (formMode.value === 'create') {
        await client.post(`/tables/${tableKey.value}/`, payload)
      } else {
        await client.patch(`/tables/${tableKey.value}/${encodeURIComponent(editingId.value)}/`, payload)
      }
    } else {
      toast.info('动态表请通过重新上传 CSV 修改数据')
      formShow.value = false
      return
    }
    toast.success(formMode.value === 'create' ? '已新增' : '已更新')
    formShow.value = false
    fetchData()
  } catch (e) {
    toast.error(e.response?.data?.detail || '保存失败')
  } finally {
    saving.value = false
  }
}

function confirmDelete(row) {
  deletingRow.value = row
  deleteShow.value = true
}

async function doDelete() {
  if (!deletingRow.value) return
  deleting.value = true
  try {
    if (kind.value === 'existing') {
      await client.delete(`/tables/${tableKey.value}/${encodeURIComponent(deletingRow.value[primaryKey.value])}/`)
      toast.success('已删除')
    } else {
      toast.info('动态表暂不支持单行删除')
    }
    deleteShow.value = false
    fetchData()
  } catch (e) {
    toast.error(e.response?.data?.detail || '删除失败')
  } finally {
    deleting.value = false
  }
}

onMounted(async () => {
  await fetchColumns()
  await fetchData()
})

// ==================== 导入 / 导出 ====================

function buildExportParams() {
  const params = {}
  if (search.value) params.search = search.value
  const ordering = sortKey.value
    ? (sortOrder.value === 'desc' ? `-${sortKey.value}` : sortKey.value)
    : undefined
  if (ordering) params.ordering = ordering

  for (const [k, f] of Object.entries(filterValues.value)) {
    if (!f) continue
    if (f.op === 'empty' || f.op === 'not_empty') {
      params[`filter.${k}.${f.op}`] = '1'
    } else if (f.value) {
      params[`filter.${k}.${f.op}`] = f.value
    }
  }
  return params
}

async function exportExcel() {
  if (exporting.value) return
  exporting.value = true
  try {
    const url = kind.value === 'existing'
      ? `/tables/${tableKey.value}/export/`
      : `/dynamic/${tableKey.value}/export/`
    const resp = await client.get(url, {
      params: buildExportParams(),
      responseType: 'blob',
    })
    // 优先用响应头里的文件名，否则用 表名_时间戳.xlsx
    let filename = `${tableLabel.value || tableKey.value}_${new Date().toISOString().slice(0, 19).replace(/[:T]/g, '')}.xlsx`
    const disp = resp.headers['content-disposition']
    if (disp) {
      const m = /filename\*=UTF-8''([^;]+)/i.exec(disp)
      if (m && m[1]) filename = decodeURIComponent(m[1])
    }
    const blob = new Blob([resp.data], {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    })
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = filename
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(link.href)
    toast.success('导出成功')
  } catch (e) {
    toast.error(e.response?.data?.detail || '导出失败')
  } finally {
    exporting.value = false
  }
}

function triggerImport() {
  // 重置 value 以便相同文件可再次触发 change
  importInput.value.value = ''
  importInput.value.click()
}

async function onImportFileChange(e) {
  const file = e.target.files && e.target.files[0]
  if (!file) return
  if (importing.value) return
  importing.value = true
  try {
    const fd = new FormData()
    fd.append('file', file)
    const url = kind.value === 'existing'
      ? `/tables/${tableKey.value}/import/`
      : `/dynamic/${tableKey.value}/import/`
    const { data } = await client.post(url, fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 120000,
    })
    const errs = data.errors || []
    const created = data.created ?? 0
    const updated = data.updated ?? 0
    const skipped = data.skipped ?? 0
    const imported = data.imported ?? 0
    const parts = []
    if (created) parts.push(`新增 ${created}`)
    if (updated) parts.push(`更新 ${updated}`)
    if (skipped) parts.push(`跳过 ${skipped}`)
    if (imported) parts.push(`导入 ${imported}`)
    const summary = parts.join('，') || '无变化'
    if (errs.length) {
      toast.warning(`${summary}，${errs.length} 行有错误`)
    } else {
      toast.success(summary)
    }
    fetchData()
  } catch (err) {
    const detail = err.response?.data?.detail
    const errs = err.response?.data?.errors || []
    if (errs.length) {
      toast.error(`${detail || '导入失败'}（${errs.length} 行错误）`)
    } else {
      toast.error(detail || '导入失败')
    }
  } finally {
    importing.value = false
  }
}

async function downloadTemplate() {
  try {
    const url = kind.value === 'existing'
      ? `/tables/${tableKey.value}/template/`
      : `/dynamic/${tableKey.value}/template/`
    const resp = await client.get(url, { responseType: 'blob' })
    let filename = `${tableLabel.value || tableKey.value}_导入模板.xlsx`
    const disp = resp.headers['content-disposition']
    if (disp) {
      const m = /filename\*=UTF-8''([^;]+)/i.exec(disp)
      if (m && m[1]) filename = decodeURIComponent(m[1])
    }
    const blob = new Blob([resp.data], {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    })
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = filename
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(link.href)
    toast.success('模板已下载')
  } catch (e) {
    toast.error(e.response?.data?.detail || '下载模板失败')
  }
}
</script>
