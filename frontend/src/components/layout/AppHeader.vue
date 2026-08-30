<template>
  <header class="h-14 shrink-0 bg-panel border-b border-line flex items-center justify-between px-6">
    <div class="flex items-center gap-2 text-sm">
      <span class="text-ink-faint">数据管理</span>
      <span class="text-ink-faint">/</span>
      <span class="text-ink font-medium">{{ currentTitle }}</span>
    </div>

    <div class="flex items-center gap-3">
      <button
        class="p-1.5 rounded text-ink-muted hover:bg-canvasDark transition-colors"
        title="刷新表列表"
        @click="tables.fetchAll()"
      >
        <RefreshCw :size="16" :stroke-width="1.75" />
      </button>

      <div class="relative" ref="menuRef">
        <button
          class="flex items-center gap-2 px-2.5 py-1.5 rounded text-sm text-ink-muted hover:bg-canvasDark transition-colors"
          @click="menuOpen = !menuOpen"
        >
          <span class="w-6 h-6 rounded-full bg-accent text-white text-xs font-medium flex items-center justify-center">
            {{ initials }}
          </span>
          <span class="text-ink">{{ auth.user?.username || '用户' }}</span>
        </button>
        <div
          v-if="menuOpen"
          class="absolute right-0 top-full mt-1 w-40 bg-panel border border-line rounded shadow-pop py-1 z-20"
        >
          <button
            class="w-full text-left px-3 py-2 text-sm text-ink-muted hover:bg-canvasDark transition-colors flex items-center gap-2"
            @click="onLogout"
          >
            <LogOut :size="14" :stroke-width="1.75" />
            退出登录
          </button>
        </div>
      </div>
    </div>
  </header>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { RefreshCw, LogOut } from 'lucide-vue-next'
import { useAuthStore } from '../../stores/auth'
import { useTablesStore } from '../../stores/tables'
import { useToast } from '../ui/toast'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const tables = useTablesStore()
const toast = useToast()

const menuOpen = ref(false)
const menuRef = ref(null)

const currentTitle = computed(() => {
  if (route.name === 'dashboard') return '概览'
  if (route.name === 'upload') return '上传数据'
  if (route.name === 'system-users') return '系统管理'
  if (route.params.key) return route.params.key
  return '数据管理平台'
})

const initials = computed(() => {
  const name = auth.user?.username || ''
  return name.slice(0, 1).toUpperCase()
})

function onOutside(e) {
  if (menuRef.value && !menuRef.value.contains(e.target)) menuOpen.value = false
}
onMounted(() => document.addEventListener('click', onOutside))
onUnmounted(() => document.removeEventListener('click', onOutside))

async function onLogout() {
  await auth.logout()
  toast.info('已退出登录')
  router.push('/login')
}
</script>
