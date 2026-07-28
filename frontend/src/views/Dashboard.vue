<template>
  <div class="max-w-6xl">
    <div class="mb-6">
      <h2 class="text-xl font-bold text-ink">概览</h2>
      <p class="text-sm text-ink-muted mt-1">管理你的全部数据表</p>
    </div>

    <!-- 统计卡片 -->
    <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
      <div class="bg-panel border border-line rounded p-5 shadow-card">
        <p class="text-xs text-ink-muted uppercase tracking-wider mb-2">已有表</p>
        <p class="text-3xl font-bold text-ink">{{ tables.existingTables.length }}</p>
      </div>
      <div class="bg-panel border border-line rounded p-5 shadow-card">
        <p class="text-xs text-ink-muted uppercase tracking-wider mb-2">动态表</p>
        <p class="text-3xl font-bold text-ink">{{ tables.dynamicTables.length }}</p>
      </div>
      <div class="bg-panel border border-line rounded p-5 shadow-card">
        <p class="text-xs text-ink-muted uppercase tracking-wider mb-2">总数据量</p>
        <p class="text-3xl font-bold text-ink">{{ formatNumber(totalAllRows) }}</p>
      </div>
      <div class="bg-panel border border-line rounded p-5 shadow-card">
        <p class="text-xs text-ink-muted uppercase tracking-wider mb-2">最近更新</p>
        <p class="text-sm font-medium text-ink mt-1.5">{{ latestUpdate || '—' }}</p>
      </div>
    </div>

    <!-- 已有表清单 -->
    <div class="bg-panel border border-line rounded shadow-card mb-6">
      <div class="px-5 py-4 border-b border-line flex items-center justify-between">
        <h3 class="font-semibold text-ink">已有业务表</h3>
        <BaseButton variant="secondary" size="sm" :icon="RefreshCw" :disabled="tables.loading" @click="tables.fetchAll()">
          刷新
        </BaseButton>
      </div>
      <BaseTable :columns="existingColumns" :rows="existingTablesWithPath">
        <template #actions="{ row }">
          <button
            class="text-xs text-accent hover:underline"
            @click="$router.push(`/table/existing/${row.key}`)"
          >
            查看
          </button>
        </template>
      </BaseTable>
    </div>

    <!-- 动态表清单 -->
    <div class="bg-panel border border-line rounded shadow-card">
      <div class="px-5 py-4 border-b border-line flex items-center justify-between">
        <h3 class="font-semibold text-ink">动态上传表</h3>
        <BaseButton variant="primary" size="sm" :icon="Upload" @click="$router.push('/upload')">
          上传新表
        </BaseButton>
      </div>
      <BaseTable
        v-if="tables.dynamicTables.length"
        :columns="dynamicColumns"
        :rows="dynamicTablesWithPath"
      >
        <template #actions="{ row }">
          <button
            class="text-xs text-accent hover:underline"
            @click="$router.push(`/table/dynamic/${row.key}`)"
          >
            查看
          </button>
        </template>
      </BaseTable>
      <div v-else class="px-5 py-12 text-center text-ink-faint text-sm">
        暂无动态表，点击右上角「上传新表」开始
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Upload, RefreshCw } from 'lucide-vue-next'
import BaseTable from '../components/ui/BaseTable.vue'
import BaseButton from '../components/ui/BaseButton.vue'
import { useTablesStore } from '../stores/tables'

const tables = useTablesStore()

// 已有表行数据：补上 _path 供跳转用（BaseTable 不需要）
const existingTablesWithPath = computed(() => tables.existingTables)
const dynamicTablesWithPath = computed(() => tables.dynamicTables)

// 总数据量 = 已有表行数 + 动态表行数
const totalAllRows = computed(() =>
  tables.all.reduce((sum, t) => sum + (t.row_count || 0), 0)
)

// 最近更新时间：所有表中 updated_at 的最大值
const latestUpdate = computed(() => {
  const times = tables.all
    .map((t) => t.updated_at)
    .filter(Boolean)
    .sort()
  if (!times.length) return ''
  return formatDateTime(times[times.length - 1])
})

function formatNumber(n) {
  if (n >= 10000) return (n / 10000).toFixed(1) + ' 万'
  return String(n)
}

function formatDateTime(v) {
  const d = new Date(v)
  if (isNaN(d)) return String(v)
  return d.toLocaleString('zh-CN', { hour12: false })
}

const existingColumns = [
  { key: 'label', label: '表名' },
  { key: 'row_count', label: '数据量', format: 'integer' },
  { key: 'updated_at', label: '最新更新', type: 'datetime' },
  { key: 'key', label: '标识', mono: true },
]

const dynamicColumns = [
  { key: 'label', label: '表名' },
  { key: 'row_count', label: '数据量', format: 'integer' },
  { key: 'updated_at', label: '最新更新', type: 'datetime' },
  { key: 'created_at', label: '创建时间', type: 'datetime' },
]
</script>
