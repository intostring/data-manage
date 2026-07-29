<template>
  <div class="overflow-auto max-h-[70vh]">
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
            :style="isFrozen(idx) ? { left: getFrozenOffset(idx) } : {}"
          >
            <div
              :class="col.sortable ? 'cursor-pointer hover:text-ink inline-flex items-center gap-1' : 'inline-flex items-center gap-1'"
              @click="col.sortable && toggleSort(col.key)"
            >
              {{ col.label }}
              <span v-if="col.sortable && sortKey === col.key" class="text-accent">
                {{ sortOrder === 'asc' ? '↑' : '↓' }}
              </span>
              <!-- 该列有筛选值时显示小圆点指示 -->
              <span v-if="col.filterable && filterValues[col.key]" class="w-1.5 h-1.5 rounded-full bg-accent inline-block"></span>
            </div>
            <!-- 筛选输入框 -->
            <div v-if="col.filterable && showFilters" class="mt-1.5 relative">
              <input
                :value="filterValues[col.key] || ''"
                :placeholder="col.label"
                class="w-40 max-w-full text-xs px-2 py-1 pr-5 border border-line rounded bg-panelLight focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent/30 text-ink placeholder:text-ink-faint"
                @input="onFilterInput(col.key, $event.target.value)"
                @keydown.esc="clearFilter(col.key)"
              />
              <!-- 清空按钮 -->
              <button
                v-if="filterValues[col.key]"
                class="absolute right-1 top-1/2 -translate-y-1/2 w-4 h-4 flex items-center justify-center text-ink-faint hover:text-danger text-xs leading-none"
                title="清空"
                @click="clearFilter(col.key)"
              >×</button>
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
            class="px-3 py-2 text-ink"
            :class="[
              col.mono ? 'font-mono text-xs' : '',
              isFrozen(cIdx) ? 'sticky z-10 ' + (idx % 2 === 1 ? 'bg-canvas' : 'bg-panel') : '',
              isFrozen(cIdx) && cIdx === frozenCount - 1 ? 'shadow-[2px_0_4px_-2px_rgba(0,0,0,0.15)]' : '',
            ]"
            :style="isFrozen(cIdx) ? { left: getFrozenOffset(cIdx) } : {}"
          >
            <span
              v-if="col.expandable && hasExpandableContent(row[col.key])"
              class="inline-flex items-center gap-1 cursor-pointer text-accent hover:underline"
              @click="openDetail(col.label, row[col.key])"
            >
              <span class="truncate inline-block max-w-[120px] align-bottom">{{ formatCell(row[col.key], col) }}</span>
              <span class="text-ink-faint">…</span>
            </span>
            <template v-else>
              {{ formatCell(row[col.key], col) }}
            </template>
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
  columns: { type: Array, required: true }, // [{ key, label, sortable, filterable, mono, type, format, expandable }]
  rows: { type: Array, default: () => [] },
  // 排序状态受控：由父组件传入，排序由后端处理
  sortKey: { type: String, default: '' },
  sortOrder: { type: String, default: 'asc' },
  // 筛选值：{ colKey: value }
  filterValues: { type: Object, default: () => ({}) },
  // 是否显示筛选输入框（由父组件控制）
  showFilters: { type: Boolean, default: true },
  // 冻结前 N 列（水平滚动时保持可见），默认冻结第 1 列
  frozenCount: { type: Number, default: 1 },
})
const emit = defineEmits(['sort', 'filter', 'clear-filter'])

// 判断指定列索引是否被冻结
function isFrozen(idx) {
  return idx < props.frozenCount
}

// 计算冻结列的 left 偏移量（需与实际列宽匹配）
// 由于列宽不固定，这里用估算值：每列约 120px
const frozenOffsets = []
function getFrozenOffset(idx) {
  if (frozenOffsets[idx] !== undefined) return frozenOffsets[idx] + 'px'
  let offset = 0
  for (let i = 0; i < idx; i++) {
    offset += 120
  }
  frozenOffsets[idx] = offset
  return offset + 'px'
}

function toggleSort(key) {
  // 通知父组件切换排序，由父组件决定新状态并传回 sortKey/sortOrder
  let newKey = key
  let newOrder = 'asc'
  if (props.sortKey === key) {
    if (props.sortOrder === 'asc') {
      newOrder = 'desc'
    } else {
      // 已是降序，清除排序
      newKey = ''
      newOrder = 'asc'
    }
  }
  emit('sort', { key: newKey, order: newOrder })
}

let filterTimers = {}
function onFilterInput(key, value) {
  clearTimeout(filterTimers[key])
  filterTimers[key] = setTimeout(() => {
    emit('filter', { key, value })
  }, 400)
}

function clearFilter(key) {
  emit('clear-filter', key)
}

function formatCell(value, col) {
  if (value === null || value === undefined || value === '') return ''
  const n = Number(value)
  if (col.format === 'integer') {
    return isNaN(n) ? value : Math.round(n)
  }
  if (col.format === 'decimal2') {
    return isNaN(n) ? value : n.toFixed(2)
  }
  if (col.type === 'datetime' || col.type === 'date') {
    const d = new Date(value)
    if (isNaN(d)) return value
    return d.toLocaleString('zh-CN', { hour12: false })
  }
  if (typeof value === 'boolean') return value ? '是' : '否'
  return value
}

// 长文本/JSON 详情弹窗
const detailShow = ref(false)
const detailTitle = ref('')
const detailContent = ref('')

// 判断该单元格是否需要"截断+点击展开"
function hasExpandableContent(value) {
  if (value === null || value === undefined || value === '') return false
  return String(value).length > 30
}

function openDetail(label, value) {
  detailTitle.value = `${label} - 详情`
  // 尝试格式化 JSON，失败则原样展示
  let content = value
  if (typeof value === 'string') {
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
