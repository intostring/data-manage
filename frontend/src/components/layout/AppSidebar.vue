<template>
  <aside class="w-56 shrink-0 bg-sidebar flex flex-col">
    <div class="px-4 py-3 border-b border-white/10">
      <h1 class="text-sm font-bold text-white tracking-tight">数据管理平台</h1>
      <p class="text-xs text-sidebar-muted mt-0.5">Data Console</p>
    </div>

    <nav class="flex-1 overflow-y-auto py-2">
      <div class="px-2 mb-1">
        <router-link
          to="/"
          class="flex items-center gap-2 px-2.5 py-1.5 rounded text-sm transition-colors"
          :class="isActive('dashboard') ? 'bg-sidebar-active text-white font-medium' : 'text-sidebar-text hover:bg-sidebar-hover hover:text-white'"
        >
          <LayoutDashboard :size="15" :stroke-width="1.75" />
          概览
        </router-link>
        <router-link
          to="/upload"
          class="flex items-center gap-2 px-2.5 py-1.5 rounded text-sm transition-colors"
          :class="isActive('upload') ? 'bg-sidebar-active text-white font-medium' : 'text-sidebar-text hover:bg-sidebar-hover hover:text-white'"
        >
          <Upload :size="15" :stroke-width="1.75" />
          上传数据
        </router-link>
      </div>

      <!-- MOM 数据 -->
      <div class="px-2 mt-3">
        <button
          class="w-full flex items-center gap-2 px-2.5 py-1.5 rounded text-sm transition-colors text-sidebar-text hover:bg-sidebar-hover hover:text-white"
          @click="momOpen = !momOpen"
        >
          <ChevronDown v-if="momOpen" :size="14" :stroke-width="2" class="text-sidebar-muted" />
          <ChevronRight v-else :size="14" :stroke-width="2" class="text-sidebar-muted" />
          <span class="font-medium">MOM数据</span>
          <span class="ml-auto text-xs text-sidebar-muted">{{ tables.momTables.length }}</span>
        </button>
        <div v-show="momOpen" class="mt-0.5 space-y-0.5">
          <router-link
            v-for="t in tables.momTables"
            :key="t.key"
            :to="`/table/existing/${t.key}`"
            class="flex items-center gap-2 pl-8 pr-2.5 py-1 rounded text-sm transition-colors"
            :class="isTableActive('existing', t.key) ? 'bg-sidebar-active text-white font-medium' : 'text-sidebar-text hover:bg-sidebar-hover hover:text-white'"
          >
            <Table2 :size="13" :stroke-width="1.75" class="text-sidebar-muted" />
            <span class="truncate">{{ t.label }}</span>
          </router-link>
        </div>
      </div>

      <!-- FOF 数据 -->
      <div class="px-2 mt-3">
        <button
          class="w-full flex items-center gap-2 px-2.5 py-1.5 rounded text-sm transition-colors text-sidebar-text hover:bg-sidebar-hover hover:text-white"
          @click="fofOpen = !fofOpen"
        >
          <ChevronDown v-if="fofOpen" :size="14" :stroke-width="2" class="text-sidebar-muted" />
          <ChevronRight v-else :size="14" :stroke-width="2" class="text-sidebar-muted" />
          <span class="font-medium">FOF数据</span>
          <span class="ml-auto text-xs text-sidebar-muted">{{ tables.fofTables.length }}</span>
        </button>
        <div v-show="fofOpen" class="mt-0.5 space-y-0.5">
          <router-link
            v-for="t in tables.fofTables"
            :key="t.key"
            :to="`/table/existing/${t.key}`"
            class="flex items-center gap-2 pl-8 pr-2.5 py-1 rounded text-sm transition-colors"
            :class="isTableActive('existing', t.key) ? 'bg-sidebar-active text-white font-medium' : 'text-sidebar-text hover:bg-sidebar-hover hover:text-white'"
          >
            <Table2 :size="13" :stroke-width="1.75" class="text-sidebar-muted" />
            <span class="truncate">{{ t.label }}</span>
          </router-link>
        </div>
      </div>

      <div class="px-2 mt-3">
        <p class="px-2.5 mb-1 text-xs font-medium text-sidebar-muted uppercase tracking-wider">动态表</p>
        <router-link
          v-for="t in tables.dynamicTables"
          :key="t.key"
          :to="`/table/dynamic/${t.key}`"
          class="flex items-center gap-2 px-2.5 py-1 rounded text-sm transition-colors"
          :class="isTableActive('dynamic', t.key) ? 'bg-sidebar-active text-white font-medium' : 'text-sidebar-text hover:bg-sidebar-hover hover:text-white'"
        >
          <Table2 :size="13" :stroke-width="1.75" class="text-sidebar-muted" />
          <span class="truncate">{{ t.label }}</span>
        </router-link>
        <p v-if="!tables.dynamicTables.length" class="px-2.5 py-1 text-xs text-sidebar-muted">暂无</p>
      </div>
    </nav>

    <div class="px-2 py-2 border-t border-white/10">
      <div class="flex items-center gap-2 px-2.5 py-1 text-xs text-sidebar-muted">
        <span class="w-1.5 h-1.5 rounded-full bg-success"></span>
        已连接
      </div>
    </div>
  </aside>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { LayoutDashboard, Upload, Table2, ChevronDown, ChevronRight } from 'lucide-vue-next'
import { useTablesStore } from '../../stores/tables'

const route = useRoute()
const tables = useTablesStore()

// 分组展开状态：默认展开，命中其中某张表时自动展开
const momOpen = ref(true)
const fofOpen = ref(true)

watch(
  () => route.path,
  (p) => {
    if (p.includes('/table/existing/')) {
      // 根据当前表所属分组自动展开
      const key = p.split('/').pop()
      const t = tables.existingTables.find((e) => e.key === key)
      if (t) {
        if (t.group === 'fof') fofOpen.value = true
        else momOpen.value = true
      }
    }
  },
  { immediate: true },
)

function isActive(name) {
  return route.name === name
}
function isTableActive(kind, key) {
  return route.params.key === key && (route.name === 'existing-table' || route.name === 'dynamic-table') && route.path.includes(kind)
}
</script>
