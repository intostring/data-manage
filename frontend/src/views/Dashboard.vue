<template>
  <div class="max-w-5xl">
    <div class="mb-6">
      <h2 class="text-xl font-bold text-ink">概览</h2>
      <p class="text-sm text-ink-muted mt-1">管理你的全部数据表</p>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
      <div class="bg-panel border border-line rounded p-5">
        <p class="text-xs text-ink-muted uppercase tracking-wider mb-2">已有表</p>
        <p class="text-3xl font-bold text-ink">{{ tables.existingTables.length }}</p>
      </div>
      <div class="bg-panel border border-line rounded p-5">
        <p class="text-xs text-ink-muted uppercase tracking-wider mb-2">动态表</p>
        <p class="text-3xl font-bold text-ink">{{ tables.dynamicTables.length }}</p>
      </div>
      <div class="bg-panel border border-line rounded p-5">
        <p class="text-xs text-ink-muted uppercase tracking-wider mb-2">动态表总行数</p>
        <p class="text-3xl font-bold text-ink">{{ totalRows }}</p>
      </div>
    </div>

    <div class="bg-panel border border-line rounded">
      <div class="px-5 py-4 border-b border-line flex items-center justify-between">
        <h3 class="font-semibold text-ink">最近动态表</h3>
        <BaseButton variant="secondary" size="sm" :icon="Upload" @click="$router.push('/upload')">
          上传新表
        </BaseButton>
      </div>
      <BaseTable
        v-if="tables.dynamicTables.length"
        :columns="dynColumns"
        :rows="tables.dynamicTables"
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
import { Upload } from 'lucide-vue-next'
import BaseTable from '../components/ui/BaseTable.vue'
import BaseButton from '../components/ui/BaseButton.vue'
import { useTablesStore } from '../stores/tables'

const tables = useTablesStore()

const totalRows = computed(() =>
  tables.dynamicTables.reduce((sum, t) => sum + (t.row_count || 0), 0)
)

const dynColumns = [
  { key: 'label', label: '表名' },
  { key: 'key', label: '标识', mono: true },
  { key: 'row_count', label: '行数' },
  { key: 'created_at', label: '创建时间', type: 'datetime' },
]
</script>
