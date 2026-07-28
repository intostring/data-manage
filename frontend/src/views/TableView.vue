<template>
  <div>
    <!-- 顶部工具栏 -->
    <div class="flex items-center justify-between mb-5">
      <div>
        <h2 class="text-xl font-bold text-ink">{{ tableKey }}</h2>
        <p class="text-sm text-ink-muted mt-1">
          {{ kind === 'existing' ? '已有业务表' : '动态上传表' }}
          <span v-if="total > 0" class="ml-2">· {{ total }} 条</span>
        </p>
      </div>
      <div class="flex items-center gap-2">
        <BaseInput v-model="search" placeholder="搜索…" type="text" class="!w-48" />
        <BaseButton variant="secondary" size="md" :icon="RefreshCw" :disabled="loading" @click="fetchData">
          刷新
        </BaseButton>
        <BaseButton variant="primary" size="md" :icon="Plus" @click="openCreate">
          新增
        </BaseButton>
      </div>
    </div>

    <!-- 数据表格 -->
    <div class="bg-panel border border-line rounded">
      <div v-if="loading" class="px-5 py-16 text-center text-ink-faint text-sm">加载中…</div>
      <BaseTable v-else :columns="columns" :rows="rows" @sort="onSort">
        <template #actions="{ row }">
          <div class="flex items-center justify-end gap-3 text-xs">
            <button class="text-ink-muted hover:text-accent transition-colors" @click="openEdit(row)">编辑</button>
            <button class="text-ink-muted hover:text-danger transition-colors" @click="confirmDelete(row)">删除</button>
          </div>
        </template>
      </BaseTable>
    </div>

    <!-- 分页 -->
    <div class="mt-4" v-if="total > pageSize">
      <Pagination :total="total" :page="page" :page-size="pageSize" @change="onPageChange" />
    </div>

    <!-- 新增/编辑模态框 -->
    <BaseModal :show="formShow" :title="formMode === 'create' ? '新增记录' : '编辑记录'" @close="formShow = false">
      <div class="space-y-4">
        <BaseInput
          v-for="col in editableColumns"
          :key="col.key"
          v-model="form[col.key]"
          :label="col.label"
          :type="inputType(col)"
          :placeholder="col.label"
        />
      </div>
      <template #footer>
        <BaseButton variant="ghost" size="md" @click="formShow = false">取消</BaseButton>
        <BaseButton variant="primary" size="md" :disabled="saving" @click="saveRecord">
          {{ saving ? '保存中…' : '保存' }}
        </BaseButton>
      </template>
    </BaseModal>

    <!-- 删除确认 -->
    <BaseModal :show="deleteShow" title="确认删除" @close="deleteShow = false">
      <p class="text-sm text-ink">确定删除这条记录吗？此操作不可撤销。</p>
      <template #footer>
        <BaseButton variant="ghost" size="md" @click="deleteShow = false">取消</BaseButton>
        <BaseButton variant="danger" size="md" :disabled="deleting" @click="doDelete">
          {{ deleting ? '删除中…' : '删除' }}
        </BaseButton>
      </template>
    </BaseModal>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { RefreshCw, Plus } from 'lucide-vue-next'
import BaseTable from '../components/ui/BaseTable.vue'
import BaseButton from '../components/ui/BaseButton.vue'
import BaseInput from '../components/ui/BaseInput.vue'
import BaseModal from '../components/ui/BaseModal.vue'
import Pagination from '../components/ui/Pagination.vue'
import client from '../api/client'
import { useToast } from '../components/ui/toast'

const route = useRoute()
const toast = useToast()

const kind = computed(() => (route.name === 'existing-table' ? 'existing' : 'dynamic'))
const tableKey = computed(() => route.params.key)

const rows = ref([])
const columns = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const search = ref('')
const loading = ref(false)

// 表单状态
const formShow = ref(false)
const formMode = ref('create')
const form = ref({})
const editingId = ref(null)
const saving = ref(false)

// 删除状态
const deleteShow = ref(false)
const deletingRow = ref(null)
const deleting = ref(false)

let searchTimer = null

const editableColumns = computed(() => columns.value.filter((c) => c.key !== 'id'))

function inputType(col) {
  if (col.type === 'int') return 'number'
  if (col.type === 'float') return 'number'
  if (col.type === 'datetime' || col.type === 'date') return 'text'
  if (col.type === 'bool') return 'text'
  return 'text'
}

function buildColumnsFromData(sample, colsMeta) {
  if (colsMeta) {
    return [
      { key: 'id', label: 'ID', mono: true, sortable: true },
      ...colsMeta.map((c) => ({
        key: c.name,
        label: c.name,
        type: c.type,
        sortable: true,
        mono: c.type === 'int' || c.type === 'float',
      })),
    ]
  }
  if (!sample) return []
  const keys = Object.keys(sample).filter((k) => k !== 'id')
  return [
    { key: 'id', label: 'ID', mono: true, sortable: true },
    ...keys.map((k) => {
      const v = sample[k]
      let type = 'str'
      if (typeof v === 'number') type = Number.isInteger(v) ? 'int' : 'float'
      else if (v && /\d{4}-\d{2}-\d{2}/.test(String(v))) type = 'datetime'
      return { key: k, label: k, type, sortable: true, mono: type === 'int' || type === 'float' }
    }),
  ]
}

async function fetchData() {
  loading.value = true
  try {
    if (kind.value === 'existing') {
      const { data } = await client.get(`/tables/${tableKey.value}/`, {
        params: { page: page.value, page_size: pageSize.value, search: search.value || undefined },
      })
      const list = data.results || data
      rows.value = list
      total.value = data.count ?? list.length
      if (!columns.value.length && list.length) {
        columns.value = buildColumnsFromData(list[0], null)
      }
    } else {
      const { data } = await client.get(`/dynamic/${tableKey.value}/`, {
        params: { page: page.value, page_size: pageSize.value, search: search.value || undefined },
      })
      rows.value = data.results || []
      total.value = data.count || 0
      columns.value = buildColumnsFromData(data.results?.[0], data.columns)
    }
  } catch (e) {
    toast.error(e.response?.data?.detail || '加载失败')
    rows.value = []
  } finally {
    loading.value = false
  }
}

function onPageChange(p) {
  page.value = p
  fetchData()
}

function onSort() {
  // 排序交由前端展示（已有表可通过 ordering 参数传后端，此处简化）
}

watch(search, () => {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    page.value = 1
    fetchData()
  }, 350)
})

watch(tableKey, () => {
  columns.value = []
  rows.value = []
  page.value = 1
  search.value = ''
  fetchData()
})

function openCreate() {
  formMode.value = 'create'
  form.value = {}
  editableColumns.value.forEach((c) => (form.value[c.key] = ''))
  editingId.value = null
  formShow.value = true
}

function openEdit(row) {
  formMode.value = 'edit'
  form.value = { ...row }
  editingId.value = row.id
  formShow.value = true
}

async function saveRecord() {
  saving.value = true
  try {
    const payload = { ...form.value }
    delete payload.id
    if (kind.value === 'existing') {
      if (formMode.value === 'create') {
        await client.post(`/tables/${tableKey.value}/`, payload)
      } else {
        await client.patch(`/tables/${tableKey.value}/${editingId.value}/`, payload)
      }
    } else {
      // 动态表暂不支持单行编辑，提示用 CSV 重传
      toast.info('动态表请通过重新上传 CSV 修改数据')
      formShow.value = false
      return
    }
    toast.success(formMode.value === 'create' ? '已新增' : '已更新')
    formShow.value = false
    fetchData()
  } catch (e) {
    toast.error(e.response?.data?.detail || '保存失败')
  } finally {
    saving.value = false
  }
}

function confirmDelete(row) {
  deletingRow.value = row
  deleteShow.value = true
}

async function doDelete() {
  if (!deletingRow.value) return
  deleting.value = true
  try {
    if (kind.value === 'existing') {
      await client.delete(`/tables/${tableKey.value}/${deletingRow.value.id}/`)
      toast.success('已删除')
    } else {
      toast.info('动态表暂不支持单行删除')
    }
    deleteShow.value = false
    fetchData()
  } catch (e) {
    toast.error(e.response?.data?.detail || '删除失败')
  } finally {
    deleting.value = false
  }
}

onMounted(fetchData)
</script>
