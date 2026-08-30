<template>
  <div class="overflow-auto max-h-[70vh]" @click="closeFilterPopup">
    <table class="w-full text-sm border-collapse">
      <thead>
        <tr class="bg-canvasDark border-b border-line">
          <th
            v-for="(col, idx) in columns"
            :key="col.key"
            class="text-left font-semibold text-ink-muted px-3 py-2.5 whitespace-nowrap select-none align-top border-b border-line sticky top-0 bg-canvasDark"
            :class="[
              isFrozen(idx) ? 'z-30' : 'z-20',
              isFrozen(idx) && idx === frozenCount - 1 ? 'shadow-[2px_0_4px_-2px_rgba(0,0,0,0.15)]' : '',
            ]"
            :style="cellStyle(col, idx)"
          >
            <div class="flex items-center gap-1 relative">
              <span
                :class="col.sortable ? 'cursor-pointer hover:text-ink' : ''"
                :title="col.labelTitle || undefined"
                @click="col.sortable && toggleSort(col.key)"
              >
                {{ col.label }}
                <span v-if="col.sortable && sortKey === col.key" class="text-accent">
                  {{ sortOrder === 'asc' ? '↑' : '↓' }}
                </span>
              </span>
              <!-- 筛选图标按钮 -->
              <button
                v-if="col.filterable"
                class="relative flex items-center justify-center w-4 h-4 rounded hover:bg-panelLight transition-colors"
                :class="isFilterActive(col.key) ? 'text-accent' : 'text-ink-faint'"
                @click.stop="toggleFilterPopup(col.key)"
                :title="isFilterActive(col.key) ? '筛选: ' + filterSummary(col.key) : '筛选'"
              >
                <svg class="w-3 h-3" viewBox="0 0 16 16" fill="currentColor">
                  <path d="M1.5 1.5h13a.5.5 0 0 1 .4.8L10 8v6.5a.5.5 0 0 1-.7.45L7 14V8L1.1 2.3a.5.5 0 0 1 .4-.8z"/>
                </svg>
                <!-- 激活指示点 -->
                <span v-if="isFilterActive(col.key)" class="absolute -top-0.5 -right-0.5 w-1.5 h-1.5 rounded-full bg-accent"></span>
              </button>
              <!-- 筛选弹窗 -->
              <div
                v-if="filterPopupKey === col.key"
                class="absolute top-full left-0 mt-1 z-50 bg-panel border border-line rounded-lg shadow-xl p-3 min-w-[220px]"
                @click.stop
              >
                <select
                  v-model="filterDraft.op"
                  class="w-full mb-2 px-2 py-1 text-xs border border-line rounded bg-panelLight text-ink focus:border-accent focus:outline-none"
                >
                  <option v-for="opt in operatorOptions(col)" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
                </select>
                <input
                  v-if="!isNullOperator(filterDraft.op)"
                  v-model="filterDraft.value"
                  :type="inputTypeForFilter(col)"
                  :placeholder="col.label"
                  class="w-full mb-2 px-2 py-1 text-xs border border-line rounded bg-panelLight text-ink focus:border-accent focus:outline-none placeholder:text-ink-faint"
                  @keydown.enter="applyFilter(col.key)"
                />
                <div class="flex items-center gap-2">
                  <button
                    class="flex-1 px-2 py-1 text-xs bg-accent text-white rounded hover:opacity-90 transition-opacity"
                    @click="applyFilter(col.key)"
                  >应用</button>
                  <button
                    v-if="isFilterActive(col.key)"
                    class="px-2 py-1 text-xs border border-line text-ink-muted rounded hover:bg-canvasDark transition-colors"
                    @click="clearFilterPopup(col.key)"
                  >清除</button>
                </div>
              </div>
            </div>
          </th>
          <th v-if="$slots.actions" class="text-right font-semibold text-ink-muted px-3 py-2.5 border-b border-line sticky top-0 bg-canvasDark z-20">
            操作
          </th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="(row, idx) in rows"
          :key="row.id ?? idx"
          class="border-b border-line transition-colors"
          :class="idx % 2 === 1 ? 'bg-canvas/40 hover:bg-canvasDark' : 'bg-panel hover:bg-canvasDark'"
        >
          <td
            v-for="(col, cIdx) in columns"
            :key="col.key"
            class="px-3 py-2 text-ink whitespace-nowrap"
            :class="[
              col.mono ? 'font-mono text-xs' : '',
              isFrozen(cIdx) ? 'sticky z-10 ' + (idx % 2 === 1 ? 'bg-canvas' : 'bg-panel') : '',
              isFrozen(cIdx) && cIdx === frozenCount - 1 ? 'shadow-[2px_0_4px_-2px_rgba(0,0,0,0.15)]' : '',
            ]"
            :style="cellStyle(col, cIdx)"
          >
            <span
              v-if="col.expandable && hasExpandableContent(row[col.key])"
              class="inline-flex min-w-0 items-center gap-1 cursor-pointer text-accent hover:underline"
              @click="openDetail(col.label, row[col.key])"
            >
              <span
                class="truncate inline-block align-bottom"
                :style="{ maxWidth: col.previewWidth || col.width || '120px' }"
              >
                {{ formatCell(row[col.key], col) }}
              </span>
              <span class="text-ink-faint">…</span>
            </span>
            <span
              v-else-if="col.truncate"
              class="block overflow-hidden text-ellipsis whitespace-nowrap"
              :style="{ maxWidth: col.previewWidth || col.width || '120px' }"
              :title="formatCell(row[col.key], col)"
            >
              {{ formatCell(row[col.key], col) }}
            </span>
            <template v-else>{{ formatCell(row[col.key], col) }}</template>
          </td>
          <td v-if="$slots.actions" class="px-3 py-2 text-right whitespace-nowrap">
            <slot name="actions" :row="row" />
          </td>
        </tr>
        <tr v-if="!rows.length">
          <td :colspan="columns.length + ($slots.actions ? 1 : 0)" class="px-3 py-12 text-center text-ink-faint">
            暂无数据
          </td>
        </tr>
      </tbody>
    </table>
  </div>

  <!-- 长文本详情弹窗 -->
  <BaseModal :show="detailShow" :title="detailTitle" @close="detailShow = false">
    <pre class="text-sm text-ink whitespace-pre-wrap break-all bg-canvas border border-line rounded p-3 max-h-[60vh] overflow-auto font-mono">{{ detailContent }}</pre>
    <template #footer>
      <BaseButton variant="ghost" size="md" @click="detailShow = false">关闭</BaseButton>
      <BaseButton variant="secondary" size="md" @click="copyDetail">复制</BaseButton>
    </template>
  </BaseModal>
</template>

<script setup>
import { ref } from 'vue'
import BaseModal from './BaseModal.vue'
import BaseButton from './BaseButton.vue'

const props = defineProps({
  columns: { type: Array, required: true },
  rows: { type: Array, default: () => [] },
  sortKey: { type: String, default: '' },
  sortOrder: { type: String, default: 'asc' },
  // 筛选状态：{ colKey: { op, value } }
  filterValues: { type: Object, default: () => ({}) },
  showFilters: { type: Boolean, default: true },
  frozenCount: { type: Number, default: 1 },
})
const emit = defineEmits(['sort', 'filter', 'clear-filter'])

// 冻结列
function isFrozen(idx) {
  return idx < props.frozenCount
}
const frozenOffsets = []
function getFrozenOffset(idx) {
  if (frozenOffsets[idx] !== undefined) return frozenOffsets[idx] + 'px'
  let offset = 0
  for (let i = 0; i < idx; i++) offset += 120
  frozenOffsets[idx] = offset
  return offset + 'px'
}

function cellStyle(col, idx) {
  const style = {}
  if (isFrozen(idx)) style.left = getFrozenOffset(idx)
  if (col.width) {
    style.width = col.width
    style.minWidth = col.width
    style.maxWidth = col.width
  }
  return style
}

// 排序
function toggleSort(key) {
  let newKey = key
  let newOrder = 'asc'
  if (props.sortKey === key) {
    if (props.sortOrder === 'asc') {
      newOrder = 'desc'
    } else {
      newKey = ''
      newOrder = 'asc'
    }
  }
  emit('sort', { key: newKey, order: newOrder })
}

// ==================== Navicat 风格筛选 ====================

// 操作符选项
const ALL_OPERATORS = [
  { value: 'contains', label: '包含' },
  { value: 'not_contains', label: '不包含' },
  { value: 'eq', label: '等于' },
  { value: 'ne', label: '不等于' },
  { value: 'gt', label: '大于' },
  { value: 'lt', label: '小于' },
  { value: 'gte', label: '大于等于' },
  { value: 'lte', label: '小于等于' },
  { value: 'empty', label: '为空' },
  { value: 'not_empty', label: '不为空' },
]

const STR_OPERATORS = [
  { value: 'contains', label: '包含' },
  { value: 'not_contains', label: '不包含' },
  { value: 'eq', label: '等于' },
  { value: 'ne', label: '不等于' },
  { value: 'empty', label: '为空' },
  { value: 'not_empty', label: '不为空' },
]

function operatorOptions(col) {
  if (col.type === 'int' || col.type === 'float') return ALL_OPERATORS
  if (col.type === 'date' || col.type === 'datetime') return ALL_OPERATORS
  return STR_OPERATORS
}

function isNullOperator(op) {
  return op === 'empty' || op === 'not_empty'
}

function inputTypeForFilter(col) {
  if (col.type === 'date' || col.type === 'datetime') return 'date'
  if (col.type === 'int' || col.type === 'float') return 'text'
  return 'text'
}

// 筛选弹窗状态
const filterPopupKey = ref('')
const filterDraft = ref({ op: 'contains', value: '' })

function toggleFilterPopup(colKey) {
  if (filterPopupKey.value === colKey) {
    filterPopupKey.value = ''
    return
  }
  filterPopupKey.value = colKey
  const existing = props.filterValues[colKey]
  if (existing) {
    filterDraft.value = { op: existing.op || 'contains', value: existing.value || '' }
  } else {
    // 根据列类型设置默认操作符
    const col = props.columns.find((c) => c.key === colKey)
    const defaultOp = (col && (col.type === 'int' || col.type === 'float' || col.type === 'date' || col.type === 'datetime')) ? 'eq' : 'contains'
    filterDraft.value = { op: defaultOp, value: '' }
  }
}

function closeFilterPopup() {
  filterPopupKey.value = ''
}

function applyFilter(colKey) {
  const draft = filterDraft.value
  if (isNullOperator(draft.op)) {
    emit('filter', { key: colKey, value: { op: draft.op, value: '' } })
  } else if (draft.value) {
    emit('filter', { key: colKey, value: { op: draft.op, value: draft.value } })
  }
  filterPopupKey.value = ''
}

function clearFilterPopup(colKey) {
  emit('clear-filter', colKey)
  filterPopupKey.value = ''
}

function isFilterActive(colKey) {
  const f = props.filterValues[colKey]
  return f && (f.value || isNullOperator(f.op))
}

function filterSummary(colKey) {
  const f = props.filterValues[colKey]
  if (!f) return ''
  const opLabel = [...ALL_OPERATORS].find((o) => o.value === f.op)?.label || f.op
  return `${opLabel} ${f.value || ''}`
}

// ==================== 格式化与详情弹窗 ====================

function formatCell(value, col) {
  if (value === null || value === undefined || value === '') return ''
  if (col.valueMap && Object.prototype.hasOwnProperty.call(col.valueMap, String(value))) {
    return col.valueMap[String(value)]
  }
  if (typeof value === 'object') {
    try {
      return JSON.stringify(value)
    } catch (e) {
      return String(value)
    }
  }
  const n = Number(value)
  if (col.format === 'integer') {
    return isNaN(n) ? value : Math.round(n)
  }
  if (col.format === 'decimal2') {
    return isNaN(n) ? value : n.toFixed(2)
  }
  if (col.format === 'decimal4') {
    return isNaN(n) ? value : n.toFixed(4)
  }
  if (col.format === 'percent2') {
    return isNaN(n) ? value : `${Math.round(n * 100)}%`
  }
  if (col.format === 'percent1') {
    return isNaN(n) ? value : `${(n * 100).toFixed(1)}%`
  }
  if (col.type === 'date') {
    // 日期类型只显示 YYYY-MM-DD
    const d = new Date(value)
    if (isNaN(d)) return value
    const y = d.getFullYear()
    const m = String(d.getMonth() + 1).padStart(2, '0')
    const day = String(d.getDate()).padStart(2, '0')
    return `${y}-${m}-${day}`
  }
  if (col.type === 'datetime') {
    const d = new Date(value)
    if (isNaN(d)) return value
    return d.toLocaleString('zh-CN', { hour12: false })
  }
  if (typeof value === 'boolean') return value ? '是' : '否'
  return value
}

const detailShow = ref(false)
const detailTitle = ref('')
const detailContent = ref('')

function hasExpandableContent(value) {
  if (value === null || value === undefined || value === '') return false
  if (typeof value === 'object') return true
  return String(value).length > 30
}

function openDetail(label, value) {
  detailTitle.value = `${label} - 详情`
  let content = value
  if (typeof value === 'object') {
    content = JSON.stringify(value, null, 2)
  } else if (typeof value === 'string') {
    const trimmed = value.trim()
    if (trimmed.startsWith('{') || trimmed.startsWith('[')) {
      try {
        content = JSON.stringify(JSON.parse(trimmed), null, 2)
      } catch (e) {
        // 非合法 JSON，保持原样
      }
    }
  }
  detailContent.value = content
  detailShow.value = true
}

async function copyDetail() {
  try {
    await navigator.clipboard.writeText(detailContent.value)
  } catch (e) {
    // 剪贴板不可用时静默失败
  }
}
</script>
