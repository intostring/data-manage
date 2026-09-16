<template>
  <div class="vals-page">
    <div class="vals-head">
      <h2>品种投顾多空</h2>
      <p>每个单元格为投顾数量，括号内为量化投顾数量</p>
    </div>

    <section class="d-card">
      <div class="d-card-b">
        <div v-if="loading" class="vals-empty">加载中...</div>
        <div v-else-if="error" class="vals-empty">{{ error }}</div>
        <div v-else class="vals-wrap">
          <table class="vals-table">
            <thead>
              <tr>
                <th class="vals-name">品种名称</th>
                <th v-for="col in columns" :key="col.key">{{ col.label }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in rows" :key="row.variety">
                <td class="vals-name">{{ row.variety }}</td>
                <td v-for="col in columns" :key="col.key">
                  <span
                    class="vals-cell"
                    :class="col.tone"
                    :style="cellStyle(row.metrics[col.key], col)"
                    @click="openAdvisorModal(row, col)"
                  >
                    {{ formatCell(row.metrics[col.key]) }}
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </section>

    <div v-if="modal.show" class="vals-modal-mask" @click.self="closeAdvisorModal">
      <div class="vals-modal">
        <div class="vals-modal-h">
          <div>
            <b>{{ modal.variety }} · {{ modal.label }}</b>
            <span>{{ modal.advisors.length }} 位投顾，其中量化 {{ modal.quantCount }} 位</span>
          </div>
          <button type="button" @click="closeAdvisorModal">×</button>
        </div>
        <div class="vals-modal-b">
          <div v-if="modal.advisors.length" class="vals-advisor-list">
            <div v-for="advisor in modal.advisors" :key="advisor.name || advisor.account_code || advisor.pid" class="vals-advisor">
              <span>{{ advisor.name || advisor.account_code || advisor.pid }}</span>
              <em>{{ advisor.account_code || advisor.pid }}</em>
              <i v-if="advisor.is_quant">量化</i>
            </div>
          </div>
          <div v-else class="vals-modal-empty">暂无投顾</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import client from '../../api/client'

const loading = ref(false)
const error = ref('')
const data = ref({})
const modal = ref({
  show: false,
  variety: '',
  label: '',
  advisors: [],
  quantCount: 0,
})

const columns = [
  { key: 'net_long', label: '净多头投顾', tone: 'long' },
  { key: 'net_short', label: '净空头投顾', tone: 'short' },
  { key: 'add_long', label: '加多投顾', tone: 'long' },
  { key: 'reduce_long', label: '减多投顾', tone: 'short' },
  { key: 'long_to_short', label: '多翻空投顾', tone: 'short' },
  { key: 'add_short', label: '加空投顾', tone: 'short' },
  { key: 'reduce_short', label: '减空投顾', tone: 'long' },
  { key: 'short_to_long', label: '空翻多投顾', tone: 'long' },
]

const rows = computed(() => data.value.rows || [])
const maxByColumn = computed(() => {
  const result = {}
  for (const col of columns) {
    result[col.key] = Math.max(...rows.value.map((row) => Number(row.metrics?.[col.key]?.count || 0)), 1)
  }
  return result
})
function formatCell(metric) {
  const count = Number(metric?.count || 0)
  const quant = Number(metric?.quant_count || 0)
  return quant > 0 ? `${count}（${quant}）` : `${count}`
}

function cellStyle(metric, col) {
  const count = Number(metric?.count || 0)
  const max = maxByColumn.value[col.key] || 1
  const alpha = count ? 0.08 + Math.min(count / max, 1) * 0.32 : 0.04
  const color = col.tone === 'long' ? '176, 58, 46' : '23, 113, 75'
  return { backgroundColor: `rgba(${color}, ${alpha})` }
}

function openAdvisorModal(row, col) {
  const metric = row.metrics?.[col.key]
  if (!metric || !Number(metric.count || 0)) return
  const advisors = [...(metric.advisors || [])].sort((a, b) => {
    if (a.is_quant !== b.is_quant) return a.is_quant ? -1 : 1
    return String(a.name || '').localeCompare(String(b.name || ''), 'zh-CN')
  })
  modal.value = {
    show: true,
    variety: row.variety,
    label: col.label,
    advisors,
    quantCount: Number(metric.quant_count || 0),
  }
}

function closeAdvisorModal() {
  modal.value = {
    show: false,
    variety: '',
    label: '',
    advisors: [],
    quantCount: 0,
  }
}

async function fetchRows() {
  loading.value = true
  error.value = ''
  try {
    const { data: res } = await client.get('/tables/position/variety-advisor-long-short/')
    data.value = res || {}
  } catch (e) {
    console.error('获取品种投顾多空失败', e)
    error.value = '获取品种投顾多空失败'
    data.value = {}
  } finally {
    loading.value = false
  }
}

onMounted(fetchRows)
</script>

<style scoped>
.vals-page {
  max-width: 1280px;
  margin: 0 auto;
}

.vals-head {
  margin-bottom: 14px;
}

.vals-head h2 {
  font-family: var(--serif);
  color: var(--ink);
  font-size: 21px;
  font-weight: 600;
  letter-spacing: 0.02em;
}

.vals-head p {
  margin-top: 4px;
  color: var(--muted);
  font-size: 13px;
}

.vals-empty {
  min-height: 240px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--muted);
}

.vals-wrap {
  max-height: calc(100vh - 260px);
  overflow: auto;
  border: 1px solid var(--line);
  background: var(--card);
}

.vals-table {
  width: 100%;
  min-width: 960px;
  table-layout: fixed;
  border-collapse: separate;
  border-spacing: 0;
  background: var(--card);
}

.vals-table th {
  position: sticky;
  top: 0;
  z-index: 3;
  height: 36px;
  padding: 0 10px;
  background: var(--card);
  box-shadow: 0 1px 0 var(--line), 0 8px 10px rgba(245, 242, 234, 0.96);
  color: var(--muted);
  font-size: 10.5px;
  font-weight: 500;
  letter-spacing: 0.08em;
  text-align: center;
  white-space: nowrap;
}

.vals-table td {
  height: 31px;
  padding: 3px 5px;
  border-bottom: 1px solid var(--line2);
  color: var(--ink);
  font-size: 12px;
  text-align: center;
}

.vals-table tbody tr:hover td {
  background: #F8F4E9;
}

.vals-table .vals-name {
  position: sticky;
  left: 0;
  z-index: 2;
  width: 112px;
  min-width: 112px;
  max-width: 112px;
  text-align: left;
}

.vals-table th:not(.vals-name),
.vals-table td:not(.vals-name) {
  width: calc((100% - 112px) / 8);
  min-width: 98px;
}

.vals-table th.vals-name {
  z-index: 4;
  background: var(--card);
}

.vals-table td.vals-name {
  padding-left: 12px;
  background: var(--card);
  font-weight: 500;
  white-space: nowrap;
}

.vals-table tbody tr:hover td.vals-name {
  background: #F8F4E9;
}

.vals-cell {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 23px;
  border: 1px solid rgba(229, 224, 210, 0.65);
  border-radius: 4px;
  font-family: var(--mono);
  font-weight: 600;
  color: var(--ink);
  cursor: pointer;
  transition: border-color 0.12s ease, box-shadow 0.12s ease, color 0.12s ease;
}

.vals-cell:hover {
  border-color: #C9C2AE;
  box-shadow: 0 2px 8px rgba(32, 40, 58, 0.08);
  color: var(--brass);
}

.vals-cell.long {
  color: var(--up);
}

.vals-cell.short {
  color: var(--dn);
}

.vals-modal-mask {
  position: fixed;
  inset: 0;
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(16, 28, 42, 0.34);
  padding: 24px;
}

.vals-modal {
  width: min(560px, 92vw);
  max-height: min(680px, 86vh);
  display: flex;
  flex-direction: column;
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: 6px;
  box-shadow: 0 18px 48px rgba(17, 32, 48, 0.22);
  overflow: hidden;
}

.vals-modal-h {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 18px;
  padding: 15px 18px;
  border-bottom: 1px solid var(--line);
}

.vals-modal-h b {
  display: block;
  color: var(--ink);
  font-size: 15px;
}

.vals-modal-h span {
  display: block;
  margin-top: 4px;
  color: var(--muted);
  font-size: 12px;
}

.vals-modal-h button {
  width: 26px;
  height: 26px;
  border: 1px solid var(--line);
  border-radius: 4px;
  background: var(--card);
  color: var(--muted);
  font-size: 18px;
  line-height: 1;
  cursor: pointer;
}

.vals-modal-b {
  overflow: auto;
  padding: 12px 18px 18px;
}

.vals-advisor-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(210px, 1fr));
  gap: 8px;
}

.vals-advisor {
  min-width: 0;
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  gap: 5px 8px;
  padding: 8px 10px;
  background: #FBF9F3;
  border: 1px solid var(--line);
  border-radius: 5px;
}

.vals-advisor span {
  min-width: 0;
  color: var(--ink);
  font-size: 13px;
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.vals-advisor em {
  color: var(--muted);
  font-family: var(--mono);
  font-size: 11px;
  font-style: normal;
}

.vals-advisor i {
  justify-self: start;
  grid-column: 1 / span 2;
  padding: 1px 7px;
  background: #EEF3F8;
  border: 1px solid #BFCFDF;
  border-radius: 9px;
  color: var(--info);
  font-size: 11px;
  font-style: normal;
}

.vals-modal-empty {
  padding: 36px 12px;
  color: var(--muted);
  text-align: center;
}
</style>
