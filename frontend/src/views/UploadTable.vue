<template>
  <div class="max-w-3xl">
    <div class="mb-6">
      <h2 class="text-xl font-bold text-ink">上传数据</h2>
      <p class="text-sm text-ink-muted mt-1">上传 CSV 文件，自动建表并导入数据</p>
    </div>

    <div class="bg-panel border border-line rounded p-6 space-y-5">
      <!-- 拖拽区 -->
      <div
        class="border-2 border-dashed border-line rounded p-8 text-center transition-colors cursor-pointer"
        :class="dragOver ? 'border-accent bg-accent-soft/30' : 'hover:border-ink-faint'"
        @dragover.prevent="dragOver = true"
        @dragleave.prevent="dragOver = false"
        @drop.prevent="onDrop"
        @click="fileInput?.click()"
      >
        <input ref="fileInput" type="file" accept=".csv" class="hidden" @change="onFileChange" />
        <FileSpreadsheet :size="32" :stroke-width="1.5" class="mx-auto text-ink-faint mb-3" />
        <p class="text-sm text-ink" v-if="!file">拖拽 CSV 文件到此处，或点击选择</p>
        <p class="text-sm text-ink font-medium" v-else>{{ file.name }} ({{ formatSize(file.size) }})</p>
        <p class="text-xs text-ink-faint mt-1">支持 UTF-8 编码 CSV</p>
      </div>

      <!-- 表信息 -->
      <div v-if="file" class="grid grid-cols-2 gap-4">
        <BaseInput v-model="form.key" label="表标识（URL 用）" placeholder="my_data" />
        <BaseInput v-model="form.label" label="显示名称" placeholder="我的数据表" />
      </div>

      <!-- 预览 -->
      <div v-if="preview.length" class="border border-line rounded">
        <div class="px-4 py-2.5 border-b border-line text-xs text-ink-muted">
          预览前 {{ preview.length }} 行 · 共检测到 {{ previewColumns.length }} 列
        </div>
        <BaseTable :columns="previewColumns" :rows="preview" />
      </div>

      <!-- 操作 -->
      <div class="flex justify-end gap-2 pt-2" v-if="file">
        <BaseButton variant="ghost" @click="reset">取消</BaseButton>
        <BaseButton variant="primary" :disabled="uploading" @click="onUpload">
          {{ uploading ? '上传中…' : '上传并建表' }}
        </BaseButton>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { FileSpreadsheet } from 'lucide-vue-next'
import BaseTable from '../components/ui/BaseTable.vue'
import BaseButton from '../components/ui/BaseButton.vue'
import BaseInput from '../components/ui/BaseInput.vue'
import client from '../api/client'
import { useToast } from '../components/ui/toast'
import { useTablesStore } from '../stores/tables'

const router = useRouter()
const toast = useToast()
const tables = useTablesStore()

const fileInput = ref(null)
const file = ref(null)
const dragOver = ref(false)
const preview = ref([])
const previewColumns = ref([])
const uploading = ref(false)
const form = reactive({ key: '', label: '' })

function onFileChange(e) {
  const f = e.target.files?.[0]
  if (f) loadFile(f)
}

function onDrop(e) {
  dragOver.value = false
  const f = e.dataTransfer.files?.[0]
  if (f) loadFile(f)
}

function loadFile(f) {
  if (!f.name.toLowerCase().endsWith('.csv')) {
    toast.error('请上传 CSV 文件')
    return
  }
  file.value = f
  // 自动填充 key
  const base = f.name.replace(/\.csv$/i, '').replace(/[^a-zA-Z0-9_]/g, '_').toLowerCase()
  form.key = base.slice(0, 60)
  form.label = base
  parsePreview(f)
}

function parsePreview(f) {
  const reader = new FileReader()
  reader.onload = (e) => {
    const text = e.target.result
    const lines = text.split(/\r?\n/).filter((l) => l.trim())
    if (!lines.length) return
    const header = parseCsvLine(lines[0])
    previewColumns.value = header.map((h) => ({ key: h, label: h }))
    preview.value = lines.slice(1, 6).map((line) => {
      const vals = parseCsvLine(line)
      const obj = {}
      header.forEach((h, i) => (obj[h] = vals[i] ?? ''))
      return obj
    })
  }
  reader.readAsText(f, 'utf-8-sig')
}

function parseCsvLine(line) {
  // 简易 CSV 解析（不处理含逗号的引号字段）
  return line.split(',').map((s) => s.trim().replace(/^"|"$/g, ''))
}

function formatSize(bytes) {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / 1024 / 1024).toFixed(1) + ' MB'
}

function reset() {
  file.value = null
  preview.value = []
  previewColumns.value = []
  form.key = ''
  form.label = ''
  if (fileInput.value) fileInput.value.value = ''
}

async function onUpload() {
  if (!file.value || !form.key) {
    toast.error('请选择文件并填写表标识')
    return
  }
  uploading.value = true
  try {
    const fd = new FormData()
    fd.append('file', file.value)
    fd.append('key', form.key)
    fd.append('label', form.label)
    const { data } = await client.post('/dynamic/', fd)
    toast.success(`已建表「${data.label}」，导入 ${data.imported_rows} 条`)
    await tables.fetchAll()
    router.push(`/table/dynamic/${data.key}`)
  } catch (e) {
    toast.error(e.response?.data?.detail || '上传失败')
  } finally {
    uploading.value = false
  }
}
</script>
