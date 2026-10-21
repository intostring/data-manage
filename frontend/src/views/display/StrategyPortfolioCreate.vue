<template>
  <div class="d-anim max-w-4xl mx-auto">
    <!-- ① 基本信息 -->
    <div class="d-card" style="margin-bottom:14px">
      <div class="d-card-h">
        <div>
          <span class="d-card-t">{{ isEdit ? '编辑组合' : '创建组合' }}</span>
          <span class="d-card-x" style="margin-left:10px">命名并选择配置模型，成分保存后可随时调整</span>
        </div>
        <router-link class="d-btn" to="/display/strategy/portfolio">返回我的组合</router-link>
      </div>
      <div class="d-card-b">
        <div class="spc-form">
          <div class="spc-field">
            <label>组合名称 <i>*</i></label>
            <input v-model="recordName" name="portfolio_name" class="d-ipt" style="width:100%" placeholder="例如：CTA 稳健增强组合" />
          </div>
          <div class="spc-field">
            <label>备注</label>
            <input v-model="recordNote" name="portfolio_note" class="d-ipt" style="width:100%" placeholder="可选：投资思路、目标等" />
          </div>
        </div>

        <div class="sp-model">
          <span class="sp-model-label">配置模型</span>
          <div class="d-seg">
            <button
              v-for="m in MODEL_OPTIONS"
              :key="m.value"
              class="d-seg-btn"
              :class="{ on: model === m.value }"
              @click="switchModel(m.value)"
            >{{ m.label }}</button>
          </div>
          <span class="d-muted" style="font-size:11px">{{ MODEL_HINTS[model] }}</span>
        </div>
      </div>
    </div>

    <!-- ② 成分选择 -->
    <div class="d-card" style="margin-bottom:14px">
      <div class="d-card-h">
        <div>
          <span class="d-card-t">选择成分投顾</span>
          <span class="d-card-x" style="margin-left:10px">已选 {{ selected.length }} / 20 个</span>
        </div>
      </div>
      <div class="d-card-b">
        <div style="position:relative">
          <input
            v-model="searchText"
            name="advisor_search"
            autocomplete="off"
            class="d-ipt"
            style="width:100%"
            placeholder="输入投顾名称、代码或ID搜索并添加…"
            @input="onSearch"
            @focus="showDropdown = true"
            @keydown.down.prevent="hoverIdx = Math.min(hoverIdx + 1, results.length - 1)"
            @keydown.up.prevent="hoverIdx = Math.max(hoverIdx - 1, 0)"
            @keydown.enter.prevent="addHover"
            @blur="showDropdown = false"
          />
          <div v-if="showDropdown && results.length" class="d-combo-list">
            <div
              v-for="(a, i) in results"
              :key="a.pid"
              class="d-combo-it"
              :class="hoverIdx === i ? 'on' : ''"
              @mousedown.prevent="addAdvisor(a)"
              @mouseenter="hoverIdx = i"
            >
              <span style="font-size:12.5px">{{ a.account_name || a.product_name }}</span>
              <span class="d-muted d-mono" style="font-size:10px;margin-left:6px">{{ a.account_code || a.product_name }}</span>
              <span v-if="a.account_count > 1" class="d-pill info" style="margin-left:6px;font-size:10px">合并{{ a.account_count }}账户</span>
              <span v-if="isSelected(a.pid)" class="d-pill info" style="margin-left:auto;font-size:10px">已添加</span>
            </div>
          </div>
        </div>

        <div v-if="selected.length" class="spc-scroll">
          <table class="d-table">
            <thead>
              <tr>
                <th style="text-align:left">投顾名称</th>
                <th style="text-align:left">代码</th>
                <th style="width:130px">权重(%)</th>
                <th style="width:60px"></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in selected" :key="item.pid">
                <td>
                  {{ item.account_name || item.product_name }}
                  <span v-if="item.account_count > 1" class="d-pill info" style="font-size:10px;margin-left:6px">合并{{ item.account_count }}账户</span>
                </td>
                <td class="d-mono d-muted">{{ item.account_code || item.product_name }}</td>
                <td>
                  <input
                    v-if="model === 'custom'"
                    v-model.number="item.weight"
                    name="advisor_weight"
                    type="number"
                    min="0"
                    step="0.5"
                    class="d-ipt d-mono"
                    style="width:90px;padding:3px 8px;font-size:12px;text-align:right"
                  />
                  <span v-else class="d-muted" style="font-size:12px">保存后按模型自动计算</span>
                </td>
                <td>
                  <button class="spc-del" @click="removeAdvisor(item.pid)">✕</button>
                </td>
              </tr>
            </tbody>
          </table>
          <div v-if="model === 'custom'" class="d-muted d-mono" style="font-size:11px;margin-top:8px;text-align:right">
            权重合计 {{ weightSum.toFixed(2) }}%
            <span v-if="Math.abs(weightSum - 100) > 0.01">（计算时自动归一化）</span>
          </div>
        </div>
        <div v-else style="display:flex;align-items:center;justify-content:center;height:120px">
          <span class="d-muted">尚未选择投顾，请从上方搜索添加（至少 1 个）</span>
        </div>
      </div>
    </div>

    <!-- ③ 提交 -->
    <div class="d-card">
      <div class="d-card-b" style="display:flex;align-items:center;justify-content:space-between">
        <span v-if="error" style="color:var(--up);font-size:12px">{{ error }}</span>
        <span v-else class="d-muted" style="font-size:12px">
          {{ isEdit ? '保存后将更新该组合' : '保存后可在「我的组合」中查看分析' }}
        </span>
        <div style="display:flex;gap:8px">
          <router-link class="d-btn" to="/display/strategy/portfolio">取消</router-link>
          <button class="d-btn d-btn-pri" :disabled="!canSave || saving" @click="save">
            {{ saving ? '保存中…' : (isEdit ? '保存修改' : '创建组合') }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import client from '../../api/client'
import { useAuthStore } from '../../stores/auth'

const MODEL_OPTIONS = [
  { value: 'equal', label: '等权' },
  { value: 'fund', label: '整体运作' },
  { value: 'rp', label: '风险平价' },
  { value: 'mv', label: '均值方差' },
  { value: 'custom', label: '自定义' },
]
const MODEL_HINTS = {
  equal: '各成分等比例分配',
  fund: '组合视作单一投顾：后上线投顾的投入按组合入金并入，无权重概念',
  rp: '等风险贡献（ERC）：低波动投顾自动获得更高权重',
  mv: '最大夏普切点组合：基于历史收益与协方差优化',
  custom: '手动输入各成分权重（自动归一化）',
}

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const isEdit = computed(() => !!route.query.id)
const recordId = ref(null)
const recordName = ref('')
const recordNote = ref('')
const model = ref('equal')
const saving = ref(false)
const error = ref('')

const allAdvisors = ref([])
const searchText = ref('')
const results = ref([])
const showDropdown = ref(false)
const hoverIdx = ref(-1)
const selected = ref([])

let searchTimer = null

const weightSum = computed(() =>
  selected.value.reduce((s, it) => s + (Number(it.weight) || 0), 0)
)
const canSave = computed(() => recordName.value.trim() && selected.value.length > 0)

function isSelected(pid) {
  return selected.value.some((it) => it.pid === pid)
}

function onSearch() {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    const q = searchText.value.trim().toLowerCase()
    if (!q) {
      results.value = allAdvisors.value.slice(0, 20)
    } else {
      results.value = allAdvisors.value
        .filter((a) =>
          [String(a.pid), a.product_name || '', a.account_name || '', a.account_code || '']
            .some((f) => f.toLowerCase().includes(q))
        )
        .slice(0, 20)
    }
    hoverIdx.value = -1
  }, 150)
}

function addAdvisor(a) {
  if (isSelected(a.pid) || selected.value.length >= 20) return
  selected.value.push({
    pid: a.pid,
    product_name: a.product_name,
    account_name: a.account_name,
    account_code: a.account_code || a.product_name,
    account_count: a.account_count || 1,
    weight: 0,
  })
  if (model.value === 'custom') equalWeights()
  searchText.value = ''
  showDropdown.value = false
}

function addHover() {
  const a = results.value[hoverIdx.value >= 0 ? hoverIdx.value : 0]
  if (a) addAdvisor(a)
}

function removeAdvisor(pid) {
  selected.value = selected.value.filter((it) => it.pid !== pid)
  if (selected.value.length && model.value === 'custom') equalWeights()
}

function equalWeights() {
  const w = 100 / selected.value.length
  selected.value.forEach((it) => { it.weight = Math.round(w * 100) / 100 })
}

function switchModel(m) {
  model.value = m
  if (m === 'custom') equalWeights()
}

async function save() {
  if (!canSave.value) return
  if (!auth.isAuthenticated) {
    error.value = '请先登录，组合将保存到你的账号下'
    setTimeout(() => router.push('/login?redirect=' + encodeURIComponent(route.fullPath)), 900)
    return
  }
  saving.value = true
  error.value = ''
  try {
    const { data } = await client.post('/tables/strategy/portfolios/', {
      id: recordId.value || undefined,
      name: recordName.value.trim(),
      note: recordNote.value.trim(),
      pids: selected.value.map((it) => it.pid),
      weight_model: model.value,
      weights: model.value === 'custom'
        ? selected.value.map((it) => Number(it.weight) || 0)
        : [],
    })
    router.push(`/display/strategy/portfolio/detail/${data.id}`)
  } catch (e) {
    console.error('保存组合失败', e)
    if (e.response?.status === 401) {
      error.value = '登录已过期，请重新登录'
      setTimeout(() => router.push('/login?redirect=' + encodeURIComponent(route.fullPath)), 900)
      return
    }
    error.value = e.response?.data?.detail || '保存组合失败'
  } finally {
    saving.value = false
  }
}

onMounted(async () => {
  try {
    const { data } = await client.get('/tables/advisor/performance/?merge=1')
    allAdvisors.value = data || []
  } catch (e) {
    console.error('获取投顾列表失败', e)
  }
  // 编辑模式：回填已有组合（组内任意 pid 均映射到合并条目）
  if (route.query.id) {
    try {
      const { data: r } = await client.get(`/tables/strategy/portfolios/${route.query.id}/`)
      recordId.value = r.id
      recordName.value = r.name
      recordNote.value = r.note || ''
      model.value = r.weight_model || 'equal'
      const byPid = new Map()
      allAdvisors.value.forEach((a) => (a.pids || [a.pid]).forEach((p) => byPid.set(p, a)))
      r.pids.forEach((pid, i) => {
        const a = byPid.get(pid)
        selected.value.push({
          pid: a ? a.pid : pid,
          product_name: a?.product_name || String(pid),
          account_name: a?.account_name || null,
          account_code: a?.account_code || a?.product_name || String(pid),
          account_count: a?.account_count || 1,
          weight: Number(r.weights?.[i]) || 0,
        })
      })
      // 去重：旧组合可能同时含同组多个 pid
      const seen = new Set()
      selected.value = selected.value.filter((it) => {
        if (seen.has(it.pid)) return false
        seen.add(it.pid)
        return true
      })
      if (model.value !== 'custom' && !r.weights?.length) equalWeights()
    } catch (e) {
      console.error('加载组合失败', e)
      error.value = '组合不存在或已被删除'
    }
  }
})
</script>

<style scoped>
.spc-form {
  display: grid;
  grid-template-columns: 1fr 1.4fr;
  gap: 12px;
}

.spc-field label {
  display: block;
  font-size: 12px;
  color: var(--muted);
  margin-bottom: 5px;
}

.spc-field label i {
  color: var(--up, #B03A2E);
  font-style: normal;
}

.spc-scroll {
  overflow-x: auto;
}

.spc-del {
  border: none;
  background: none;
  color: var(--muted);
  cursor: pointer;
  font-size: 13px;
  padding: 2px 6px;
  border-radius: 3px;
}

.spc-del:hover {
  color: var(--up, #B03A2E);
  background: #FAEFEA;
}

.sp-model {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 14px;
}

.sp-model-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--muted);
}

@media (max-width: 900px) {
  .spc-form {
    grid-template-columns: 1fr;
  }
}
</style>
