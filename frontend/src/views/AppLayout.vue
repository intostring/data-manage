<template>
  <div class="flex h-screen bg-canvas">
    <AppSidebar />
    <div class="flex-1 flex flex-col min-w-0">
      <AppHeader />
      <main class="flex-1 overflow-y-auto p-6">
        <router-view />
      </main>
    </div>
    <ToastContainer />
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import AppSidebar from '../components/layout/AppSidebar.vue'
import AppHeader from '../components/layout/AppHeader.vue'
import ToastContainer from '../components/ui/ToastContainer.vue'
import { useAuthStore } from '../stores/auth'
import { useTablesStore } from '../stores/tables'

const auth = useAuthStore()
const tables = useTablesStore()

onMounted(async () => {
  if (auth.isAuthenticated && !auth.user) {
    await auth.fetchMe()
  }
  await tables.fetchAll()
})
</script>
