<template>
  <div class="max-w-6xl">
    <div class="flex items-center justify-between mb-6">
      <div>
        <h2 class="text-xl font-bold text-ink">系统管理</h2>
        <p class="text-sm text-ink-muted mt-1">管理后台用户与基础权限</p>
      </div>
      <BaseButton variant="primary" size="md" :icon="Plus" @click="openCreate">新增用户</BaseButton>
    </div>

    <div class="bg-panel border border-line rounded shadow-card">
      <div v-if="loading" class="px-5 py-16 text-center text-ink-faint text-sm">加载中...</div>
      <BaseTable v-else :columns="columns" :rows="users" :frozen-count="0">
        <template #actions="{ row }">
          <div class="flex items-center justify-end gap-3 text-xs">
            <button class="text-ink-muted hover:text-accent transition-colors" @click="openEdit(row)">编辑</button>
            <button class="text-ink-muted hover:text-accent transition-colors" @click="openPassword(row)">重置密码</button>
            <button
              class="text-ink-muted hover:text-danger transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
              :disabled="row.id === auth.user?.id"
              @click="confirmDelete(row)"
            >
              删除
            </button>
          </div>
        </template>
      </BaseTable>
    </div>

    <BaseModal :show="formShow" :title="formMode === 'create' ? '新增用户' : '编辑用户'" @close="formShow = false">
      <div class="space-y-4">
        <BaseInput v-model="form.username" label="用户名" placeholder="用户名" />
        <BaseInput v-model="form.email" label="邮箱" placeholder="邮箱" />
        <BaseInput v-model="form.first_name" label="名" placeholder="名" />
        <BaseInput v-model="form.last_name" label="姓" placeholder="姓" />
        <BaseInput v-if="formMode === 'create'" v-model="form.password" label="密码" type="password" placeholder="密码" />
        <label class="flex items-center gap-2 text-sm text-ink">
          <input v-model="form.is_active" type="checkbox" class="w-4 h-4 accent-accent" />
          启用账号
        </label>
        <label class="flex items-center gap-2 text-sm text-ink">
          <input v-model="form.is_staff" type="checkbox" class="w-4 h-4 accent-accent" />
          Staff 权限
        </label>
        <label class="flex items-center gap-2 text-sm text-ink">
          <input v-model="form.is_superuser" type="checkbox" class="w-4 h-4 accent-accent" />
          超级管理员
        </label>
      </div>
      <template #footer>
        <BaseButton variant="ghost" size="md" @click="formShow = false">取消</BaseButton>
        <BaseButton variant="primary" size="md" :disabled="saving" @click="saveUser">
          {{ saving ? '保存中...' : '保存' }}
        </BaseButton>
      </template>
    </BaseModal>

    <BaseModal :show="passwordShow" title="重置密码" @close="passwordShow = false">
      <div class="space-y-4">
        <p class="text-sm text-ink-muted">用户：{{ selectedUser?.username }}</p>
        <BaseInput v-model="newPassword" label="新密码" type="password" placeholder="新密码" />
      </div>
      <template #footer>
        <BaseButton variant="ghost" size="md" @click="passwordShow = false">取消</BaseButton>
        <BaseButton variant="primary" size="md" :disabled="savingPassword" @click="savePassword">
          {{ savingPassword ? '保存中...' : '保存' }}
        </BaseButton>
      </template>
    </BaseModal>

    <BaseModal :show="deleteShow" title="确认删除" @close="deleteShow = false">
      <p class="text-sm text-ink">确定删除用户「{{ selectedUser?.username }}」吗？此操作不可撤销。</p>
      <template #footer>
        <BaseButton variant="ghost" size="md" @click="deleteShow = false">取消</BaseButton>
        <BaseButton variant="danger" size="md" :disabled="deleting" @click="deleteUser">
          {{ deleting ? '删除中...' : '删除' }}
        </BaseButton>
      </template>
    </BaseModal>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { Plus } from 'lucide-vue-next'
import BaseButton from '../components/ui/BaseButton.vue'
import BaseInput from '../components/ui/BaseInput.vue'
import BaseModal from '../components/ui/BaseModal.vue'
import BaseTable from '../components/ui/BaseTable.vue'
import client from '../api/client'
import { useAuthStore } from '../stores/auth'
import { useToast } from '../components/ui/toast'

const auth = useAuthStore()
const toast = useToast()

const users = ref([])
const loading = ref(false)
const formShow = ref(false)
const formMode = ref('create')
const form = ref(defaultForm())
const saving = ref(false)
const selectedUser = ref(null)
const passwordShow = ref(false)
const newPassword = ref('')
const savingPassword = ref(false)
const deleteShow = ref(false)
const deleting = ref(false)

const columns = computed(() => [
  { key: 'id', label: 'ID', sortable: true, mono: true },
  { key: 'username', label: '用户名', sortable: true },
  { key: 'email', label: '邮箱' },
  { key: 'is_active', label: '状态', valueMap: { true: '启用', false: '停用' } },
  { key: 'is_staff', label: 'Staff', valueMap: { true: '是', false: '否' } },
  { key: 'is_superuser', label: '超级管理员', valueMap: { true: '是', false: '否' } },
  { key: 'last_login', label: '最后登录', type: 'datetime' },
  { key: 'date_joined', label: '创建时间', type: 'datetime' },
])

function defaultForm() {
  return {
    username: '',
    email: '',
    first_name: '',
    last_name: '',
    password: '',
    is_active: true,
    is_staff: false,
    is_superuser: false,
  }
}

async function fetchUsers() {
  loading.value = true
  try {
    const { data } = await client.get('/auth/users/')
    users.value = data.results || data
  } catch (e) {
    toast.error(e.response?.data?.detail || '加载用户失败')
  } finally {
    loading.value = false
  }
}

function openCreate() {
  formMode.value = 'create'
  form.value = defaultForm()
  selectedUser.value = null
  formShow.value = true
}

function openEdit(user) {
  formMode.value = 'edit'
  selectedUser.value = user
  form.value = {
    username: user.username || '',
    email: user.email || '',
    first_name: user.first_name || '',
    last_name: user.last_name || '',
    is_active: !!user.is_active,
    is_staff: !!user.is_staff,
    is_superuser: !!user.is_superuser,
  }
  formShow.value = true
}

async function saveUser() {
  saving.value = true
  try {
    if (formMode.value === 'create') {
      await client.post('/auth/users/', form.value)
      toast.success('用户已创建')
    } else {
      await client.patch(`/auth/users/${selectedUser.value.id}/`, form.value)
      toast.success('用户已更新')
    }
    formShow.value = false
    await fetchUsers()
    if (selectedUser.value?.id === auth.user?.id) await auth.fetchMe()
  } catch (e) {
    toast.error(e.response?.data?.detail || '保存用户失败')
  } finally {
    saving.value = false
  }
}

function openPassword(user) {
  selectedUser.value = user
  newPassword.value = ''
  passwordShow.value = true
}

async function savePassword() {
  if (!newPassword.value) {
    toast.error('请输入新密码')
    return
  }
  savingPassword.value = true
  try {
    await client.post(`/auth/users/${selectedUser.value.id}/set-password/`, { password: newPassword.value })
    toast.success('密码已重置')
    passwordShow.value = false
  } catch (e) {
    toast.error(e.response?.data?.detail || '重置密码失败')
  } finally {
    savingPassword.value = false
  }
}

function confirmDelete(user) {
  selectedUser.value = user
  deleteShow.value = true
}

async function deleteUser() {
  deleting.value = true
  try {
    await client.delete(`/auth/users/${selectedUser.value.id}/`)
    toast.success('用户已删除')
    deleteShow.value = false
    await fetchUsers()
  } catch (e) {
    toast.error(e.response?.data?.detail || '删除用户失败')
  } finally {
    deleting.value = false
  }
}

onMounted(fetchUsers)
</script>
