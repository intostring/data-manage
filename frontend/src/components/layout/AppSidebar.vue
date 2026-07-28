<template>
  <aside class="w-60 shrink-0 bg-panel border-r border-line flex flex-col">
    <div class="px-5 py-4 border-b border-line">
      <h1 class="text-base font-bold text-ink tracking-tight">数据管理平台</h1>
      <p class="text-xs text-ink-faint mt-0.5">Data Console</p>
    </div>

    <nav class="flex-1 overflow-y-auto py-3">
      <div class="px-3 mb-1">
        <router-link
          to="/"
          class="flex items-center gap-2 px-2.5 py-2 rounded text-sm transition-colors"
          :class="isActive('dashboard') ? 'bg-canvas text-ink font-medium' : 'text-ink-muted hover:bg-canvas hover:text-ink'"
        >
          <LayoutDashboard :size="16" :stroke-width="1.75" />
          概览
        </router-link>
        <router-link
          to="/upload"
          class="flex items-center gap-2 px-2.5 py-2 rounded text-sm transition-colors"
          :class="isActive('upload') ? 'bg-canvas text-ink font-medium' : 'text-ink-muted hover:bg-canvas hover:text-ink'"
        >
          <Upload :size="16" :stroke-width="1.75" />
          上传数据
        </router-link>
      </div>

      <div class="px-3 mt-4">
        <p class="px-2.5 mb-1.5 text-xs font-medium text-ink-faint uppercase tracking-wider">已有表</p>
        <router-link
          v-for="t in tables.existingTables"
          :key="t.key"
          :to="`/table/existing/${t.key}`"
          class="flex items-center gap-2 px-2.5 py-1.5 rounded text-sm transition-colors"
          :class="isTableActive('existing', t.key) ? 'bg-canvas text-ink font-medium' : 'text-ink-muted hover:bg-canvas hover:text-ink'"
        >
          <Table2 :size="14" :stroke-width="1.75" class="text-ink-faint" />
          <span class="truncate">{{ t.label }}</span>
        </router-link>
      </div>

      <div class="px-3 mt-4">
        <p class="px-2.5 mb-1.5 text-xs font-medium text-ink-faint uppercase tracking-wider">动态表</p>
        <router-link
          v-for="t in tables.dynamicTables"
          :key="t.key"
          :to="`/table/dynamic/${t.key}`"
          class="flex items-center gap-2 px-2.5 py-1.5 rounded text-sm transition-colors"
          :class="isTableActive('dynamic', t.key) ? 'bg-canvas text-ink font-medium' : 'text-ink-muted hover:bg-canvas hover:text-ink'"
        >
          <Table2 :size="14" :stroke-width="1.75" class="text-ink-faint" />
          <span class="truncate">{{ t.label }}</span>
        </router-link>
        <p v-if="!tables.dynamicTables.length" class="px-2.5 py-1 text-xs text-ink-faint">暂无</p>
      </div>
    </nav>

    <div class="px-3 py-3 border-t border-line">
      <div class="flex items-center gap-2 px-2.5 py-1.5 text-xs text-ink-faint">
        <span class="w-1.5 h-1.5 rounded-full bg-success"></span>
        已连接
      </div>
    </div>
  </aside>
</template>

<script setup>
import { useRoute } from 'vue-router'
import { LayoutDashboard, Upload, Table2 } from 'lucide-vue-next'
import { useTablesStore } from '../../stores/tables'

const route = useRoute()
const tables = useTablesStore()

function isActive(name) {
  return route.name === name
}
function isTableActive(kind, key) {
  return route.params.key === key && (route.name === 'existing-table' || route.name === 'dynamic-table') && route.path.includes(kind)
}
</script>
