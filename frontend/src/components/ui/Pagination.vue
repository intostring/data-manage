<template>
  <div class="flex items-center justify-between gap-4 text-sm">
    <span class="text-ink-muted">
      共 <span class="text-ink font-medium">{{ total }}</span> 条
    </span>
    <div class="flex items-center gap-1">
      <button
        class="px-2 py-1 rounded border border-line text-ink-muted hover:bg-canvas disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
        :disabled="page <= 1"
        @click="go(page - 1)"
      >
        上一页
      </button>
      <button
        v-for="p in pages"
        :key="p"
        class="min-w-[28px] px-2 py-1 rounded text-center transition-colors"
        :class="p === page
          ? 'bg-accent text-white'
          : 'border border-line text-ink-muted hover:bg-canvas'"
        @click="go(p)"
      >
        {{ p }}
      </button>
      <button
        class="px-2 py-1 rounded border border-line text-ink-muted hover:bg-canvas disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
        :disabled="page >= totalPages"
        @click="go(page + 1)"
      >
        下一页
      </button>
    </div>
    <span class="text-ink-faint text-xs">第 {{ page }} / {{ totalPages || 1 }} 页</span>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  total: { type: Number, default: 0 },
  page: { type: Number, default: 1 },
  pageSize: { type: Number, default: 20 },
})
const emit = defineEmits('change')

const totalPages = computed(() => Math.max(1, Math.ceil(props.total / props.pageSize)))

const pages = computed(() => {
  const tp = totalPages.value
  const cur = props.page
  const arr = []
  let start = Math.max(1, cur - 2)
  let end = Math.min(tp, start + 4)
  start = Math.max(1, end - 4)
  for (let i = start; i <= end; i++) arr.push(i)
  return arr
})

function go(p) {
  if (p < 1 || p > totalPages.value || p === props.page) return
  emit('change', p)
}
</script>
