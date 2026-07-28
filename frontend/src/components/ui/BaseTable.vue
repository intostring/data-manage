<template>
  <div class="overflow-x-auto">
    <table class="w-full text-sm">
      <thead>
        <tr class="border-b border-line">
          <th
            v-for="col in columns"
            :key="col.key"
            class="text-left font-medium text-ink-muted px-3 py-2.5 whitespace-nowrap select-none"
            :class="col.sortable ? 'cursor-pointer hover:text-ink' : ''"
            @click="col.sortable && toggleSort(col.key)"
          >
            <span class="inline-flex items-center gap-1">
              {{ col.label }}
              <span v-if="col.sortable && sortKey === col.key" class="text-accent">
                {{ sortOrder === 'asc' ? '↑' : '↓' }}
              </span>
            </span>
          </th>
          <th v-if="$slots.actions" class="text-right font-medium text-ink-muted px-3 py-2.5">
            操作
          </th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="(row, idx) in rows"
          :key="row.id ?? idx"
          class="border-b border-line last:border-0 hover:bg-canvas transition-colors"
        >
          <td
            v-for="col in columns"
            :key="col.key"
            class="px-3 py-2.5 text-ink"
            :class="col.mono ? 'font-mono text-xs' : ''"
          >
            {{ formatCell(row[col.key], col) }}
          </td>
          <td v-if="$slots.actions" class="px-3 py-2.5 text-right whitespace-nowrap">
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
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  columns: { type: Array, required: true }, // [{ key, label, sortable, mono, type }]
  rows: { type: Array, default: () => [] },
})

const emit = defineEmits(['sort'])

const sortKey = ref('')
const sortOrder = ref('asc')

function toggleSort(key) {
  if (sortKey.value === key) {
    sortOrder.value = sortOrder.value === 'asc' ? 'desc' : 'asc'
  } else {
    sortKey.value = key
    sortOrder.value = 'asc'
  }
  emit('sort', { key: sortKey.value, order: sortOrder.value })
}

function formatCell(value, col) {
  if (value === null || value === undefined) return ''
  if (col.type === 'datetime' || col.type === 'date') {
    const d = new Date(value)
    if (isNaN(d)) return value
    return d.toLocaleString('zh-CN', { hour12: false })
  }
  if (typeof value === 'boolean') return value ? '是' : '否'
  return value
}
</script>
