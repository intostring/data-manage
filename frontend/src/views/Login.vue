<template>
  <div class="min-h-screen bg-canvas flex items-center justify-center px-4">
    <div class="w-full max-w-sm">
      <div class="mb-6">
        <h1 class="text-xl font-semibold text-ink tracking-tight">数据管理平台</h1>
        <p class="text-sm text-ink-muted mt-1">请输入账号信息</p>
      </div>

      <form @submit.prevent="onSubmit" class="bg-panel border border-line rounded p-5 shadow-card space-y-4">
        <BaseInput
          v-model="form.username"
          label="用户名"
          placeholder="admin"
          autocomplete="username"
        />
        <BaseInput
          v-model="form.password"
          label="密码"
          type="password"
          placeholder="••••••••"
          autocomplete="current-password"
        />

        <p v-if="error" class="text-sm text-danger">{{ error }}</p>

        <BaseButton type="submit" block :disabled="loading">
          {{ loading ? '登录中…' : '登录' }}
        </BaseButton>
      </form>

      <p class="text-xs text-ink-faint mt-4">账号由系统管理员维护</p>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import BaseInput from '../components/ui/BaseInput.vue'
import BaseButton from '../components/ui/BaseButton.vue'
import { useAuthStore } from '../stores/auth'
import { useToast } from '../components/ui/toast'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const toast = useToast()

const form = reactive({ username: '', password: '' })
const loading = ref(false)
const error = ref('')

async function onSubmit() {
  error.value = ''
  loading.value = true
  try {
    await auth.login(form.username, form.password)
    toast.success('登录成功')
    const redirect = route.query.redirect || '/display/overview'
    router.push(redirect)
  } catch (e) {
    const msg = e.response?.data?.detail || '登录失败，请检查账号密码'
    error.value = msg
  } finally {
    loading.value = false
  }
}
</script>
