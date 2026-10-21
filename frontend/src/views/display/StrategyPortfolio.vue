<template>
  <div class="d-anim max-w-6xl mx-auto">
    <div class="d-card">
      <div class="d-card-h">
        <div>
          <span class="d-card-t">我的组合</span>
          <span class="d-card-x" style="margin-left:10px">已保存 {{ records.length }} 个 · 点击卡片查看组合分析</span>
        </div>
        <router-link class="d-btn d-btn-pri" to="/display/strategy/portfolio/create">+ 创建组合</router-link>
      </div>
      <div class="d-card-b">
        <div v-if="!auth.isAuthenticated" class="sp-login-tip">
          <span class="d-muted" style="font-size:12.5px">登录后可创建并管理自己的组合（当前仅显示公共组合）</span>
          <router-link class="d-btn d-btn-pri" to="/login?redirect=/display/strategy/portfolio">去登录</router-link>
        </div>
        <div v-if="loading" style="display:flex;align-items:center;justify-content:center;height:160px">
          <span class="d-muted">加载中…</span>
        </div>
        <div v-else-if="!records.length" class="sp-empty">
          <p class="sp-empty-t">还没有组合</p>
          <p class="d-muted" style="font-size:12px;margin-bottom:14px">选择投顾、配置权重模型，构建你的第一个策略组合</p>
          <router-link class="d-btn d-btn-pri" to="/display/strategy/portfolio/create">+ 创建组合</router-link>
        </div>
        <div v-else class="sp-rec-grid">
          <div
            v-for="r in records"
            :key="r.id"
            class="sp-rec"
            @click="goDetail(r)"
          >
            <div class="sp-rec-head">
              <b class="sp-rec-name" :title="r.name">{{ r.name }}</b>
              <span style="display:flex;gap:4px;flex-shrink:0">
                <span v-if="!r.owner_id" class="d-pill gray" style="font-size:10px">公共</span>
                <span class="d-pill info" style="font-size:10px">{{ r.weight_model_label }}</span>
              </span>
            </div>
            <div v-if="r.note" class="d-muted sp-rec-note" :title="r.note">{{ r.note }}</div>
            <div class="d-muted" style="font-size:11px;margin-top:6px">
              {{ r.pids.length }} 个成分 · {{ r.owner_name ? '创建者 ' + r.owner_name : '公共组合' }} · 更新于 {{ fmtTime(r.updated_at) }}
            </div>
            <div class="sp-rec-foot">
              <span class="sp-rec-link" @click.stop="goDetail(r)">查看分析</span>
              <template v-if="r.is_mine || auth.isSuperuser">
                <span class="sp-rec-link" @click.stop="goEdit(r)">编辑</span>
                <span class="sp-rec-link danger" @click.stop="deleteRecord(r)">删除</span>
              </template>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import client from '../../api/client'
import { useAuthStore } from '../../stores/auth'

const router = useRouter()
const auth = useAuthStore()
const records = ref([])
const loading = ref(false)

const mineCount = computed(() => records.value.filter((r) => r.is_mine).length)

async function fetchRecords() {
  loading.value = true
  try {
    const { data } = await client.get('/tables/strategy/portfolios/')
    records.value = data || []
  } catch (e) {
    console.error('获取组合列表失败', e)
  } finally {
    loading.value = false
  }
}

function goDetail(r) {
  router.push(`/display/strategy/portfolio/detail/${r.id}`)
}

function goEdit(r) {
  router.push(`/display/strategy/portfolio/create?id=${r.id}`)
}

async function deleteRecord(r) {
  try {
    await client.delete(`/tables/strategy/portfolios/${r.id}/`)
    await fetchRecords()
  } catch (e) {
    console.error('删除组合失败', e)
  }
}

function fmtTime(t) {
  if (!t) return '—'
  return String(t).replace('T', ' ').slice(0, 16)
}

onMounted(() => {
  if (auth.isAuthenticated && !auth.user) auth.fetchMe().catch(() => {})
  fetchRecords()
})
</script>

<style scoped>
.sp-login-tip {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 14px;
  margin-bottom: 12px;
  border: 1px dashed #C9A268;
  border-radius: 6px;
  background: #F5EDE0;
}

.sp-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 280px;
}

.sp-empty-t {
  font-size: 15px;
  font-weight: 600;
  margin-bottom: 6px;
}

.sp-rec-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 12px;
}

.sp-rec {
  border: 1px solid var(--line, #E5E0D2);
  border-radius: 6px;
  padding: 12px 14px;
  cursor: pointer;
  transition: all 0.15s ease;
  background: var(--card, #FFFDF8);
}

.sp-rec:hover {
  border-color: #C9A268;
  box-shadow: 0 1px 4px rgba(156, 107, 47, 0.10);
}

.sp-rec-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
}

.sp-rec-name {
  font-size: 13.5px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.sp-rec-note {
  font-size: 11px;
  margin-top: 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.sp-rec-foot {
  display: flex;
  gap: 12px;
  margin-top: 10px;
  padding-top: 8px;
  border-top: 1px dashed var(--line, #E5E0D2);
}

.sp-rec-link {
  font-size: 11px;
  color: #9C6B2F;
  cursor: pointer;
}

.sp-rec-link:hover {
  text-decoration: underline;
}

.sp-rec-link.danger {
  color: #B03A2E;
}
</style>
