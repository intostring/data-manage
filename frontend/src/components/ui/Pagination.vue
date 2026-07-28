<template>
  <div class="flex items-center justify-between gap-4 text-sm flex-wrap">
    <div class="flex items-center gap-3">
      <span class="text-ink-muted">
        共 <span class="text-ink font-medium">{{ total }}</span> 条
      </span>
      <label class="flex items-center gap-1.5 text-ink-muted">
        每页
        <select
          :value="pageSize"
          class="px-1.5 py-1 border border-line rounded bg-panelLight text-ink focus:border-accent focus:outline-none cursor-pointer"
          @change="onPageSizeChange($event.target.value)"
        >
          <option v-for="s in sizeOptions" :key="s" :value="s">{{ s }} 条</option>
        </select>
      </label>
    </div>
    <div class="flex items-center gap-1">
      <button
        class="px-2 py-1 rounded border border-line text-ink-muted hover:bg-canvasDark disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
        :disabled="page <= 1"
        @click="go(page - 1)"
      >
        上一页
      </button>
      <template v-for="(p, idx) in pages" :key="idx">
        <span
          v-if="p === '...'"
          class="px-1 text-ink-faint select-none"
        >...</span>
        <button
          v-else
          class="min-w-[28px] px-2 py-1 rounded text-center transition-colors"
          :class="p === page
            ? 'bg-accent text-white'
            : 'border border-line text-ink-muted hover:bg-canvasDark'"
          @click="go(p)"
        >
          {{ p }}
        </button>
      </template>
      <button
        class="px-2 py-1 rounded border border-line text-ink-muted hover:bg-canvasDark disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
        :disabled="page >= totalPages"
        @click="go(page + 1)"
      >
        下一页
      </button>
    </div>
    <div class="flex items-center gap-2 text-ink-muted">
      <span>前往</span>
      <input
        v-model="jumpInput"
        type="number"
        min="1"
        :max="totalPages"
        class="w-14 px-2 py-1 border border-line rounded bg-panelLight text-ink focus:border-accent focus:outline-none text-center"
        @keyup.enter="onJump"
      />
      <span>页</span>
      <button
        class="px-3 py-1 rounded border border-line text-ink-muted hover:bg-canvasDark transition-colors"
        @click="onJump"
      >
        go
      </button>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'

const props = defineProps({
  total: { type: Number, default: 0 },
  page: { type: Number, default: 1 },
  pageSize: { type: Number, default: 20 },
  // 可选的每页条数
  sizeOptions: { type: Array, default: () => [10, 20, 30, 50] },
})
const emit = defineEmits(['change', 'size-change'])

const totalPages = computed(() => Math.max(1, Math.ceil(props.total / props.pageSize)))

// 生成带省略号的页码序列：如 1 2 3 ... 9 10
const pages = computed(() => {
  const tp = totalPages.value
  const cur = props.page
  const arr = []

  // 总页数较少时，全部展示
  if (tp <= 7) {
    for (let i = 1; i <= tp; i++) arr.push(i)
    return arr
  }

  // 始终展示前 2 页
  arr.push(1, 2)

  // 当前页附近
  const left = Math.max(3, cur - 1)
  const right = Math.min(tp - 2, cur + 1)

  if (left > 3) arr.push('...')
  for (let i = left; i <= right; i++) arr.push(i)
  if (right < tp - 2) arr.push('...')

  // 始终展示后 2 页
  arr.push(tp - 1, tp)

  return arr
})

const jumpInput = ref('')

// 页码变化时清空跳转输入
watch(() => props.page, () => { jumpInput.value = '' })

function go(p) {
  if (p < 1 || p > totalPages.value || p === props.page) return
  emit('change', p)
}

function onJump() {
  const p = parseInt(jumpInput.value, 10)
  if (Number.isNaN(p)) return
  go(p)
  jumpInput.value = ''
}

function onPageSizeChange(val) {
  emit('size-change', Number(val))
}
</script>
