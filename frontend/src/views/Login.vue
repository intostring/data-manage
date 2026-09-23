<template>
  <div class="lg-page">
    <!-- 背景层：网格 + 光晕 -->
    <div class="lg-bg">
      <div class="lg-grid"></div>
      <div class="lg-glow lg-glow-a"></div>
      <div class="lg-glow lg-glow-b"></div>
    </div>

    <div class="lg-shell">
      <!-- 左侧品牌视觉区 -->
      <aside class="lg-brand">
        <div class="lg-brand-top lg-rise" style="--d:.05s">
          <div class="lg-logo">
            <CandlestickChart :size="22" :stroke-width="1.8" />
          </div>
          <span class="lg-brand-name">YL·MOM</span>
        </div>

        <div class="lg-brand-mid">
          <h1 class="lg-title lg-rise" style="--d:.15s">
            数据管理平台
            <span class="lg-title-accent">MOM 分析</span>
          </h1>
          <p class="lg-sub lg-rise" style="--d:.25s">
            投顾业绩 · 持仓分析 · 板块风险，全景数据一屏尽览
          </p>

          <!-- 动态收益曲线 -->
          <div class="lg-chart lg-rise" style="--d:.35s">
            <svg viewBox="0 0 480 160" preserveAspectRatio="none" class="lg-chart-svg">
              <defs>
                <linearGradient id="lgArea" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stop-color="#4da3ff" stop-opacity="0.35" />
                  <stop offset="100%" stop-color="#4da3ff" stop-opacity="0" />
                </linearGradient>
              </defs>
              <path class="lg-area" :d="areaPath" fill="url(#lgArea)" />
              <path class="lg-line" :d="linePath" fill="none" stroke="#4da3ff" stroke-width="2" stroke-linecap="round" />
              <circle v-if="lastPoint" class="lg-dot" :cx="lastPoint[0]" :cy="lastPoint[1]" r="3.5" fill="#4da3ff" />
            </svg>
            <div class="lg-chart-meta">
              <span>组合净值走势</span>
              <span class="lg-up">+12.36%</span>
            </div>
          </div>
        </div>

        <div class="lg-brand-bottom lg-rise" style="--d:.45s">
          <div class="lg-stat" v-for="s in stats" :key="s.k">
            <div class="lg-stat-v">{{ s.v }}</div>
            <div class="lg-stat-k">{{ s.k }}</div>
          </div>
        </div>
      </aside>

      <!-- 右侧登录表单 -->
      <main class="lg-panel">
        <form @submit.prevent="onSubmit" class="lg-card lg-rise" style="--d:.2s">
          <div class="lg-card-head">
            <h2>欢迎回来</h2>
            <p>请使用管理员分配的账号登录</p>
          </div>

          <label class="lg-field">
            <span class="lg-field-label">用户名</span>
            <div class="lg-field-box" :class="{ 'lg-field-focus': focusField === 'u' }">
              <User :size="15" class="lg-field-icon" />
              <input
                v-model="form.username"
                type="text"
                placeholder="请输入用户名"
                autocomplete="username"
                @focus="focusField = 'u'"
                @blur="focusField = ''"
              />
            </div>
          </label>

          <label class="lg-field">
            <span class="lg-field-label">密码</span>
            <div class="lg-field-box" :class="{ 'lg-field-focus': focusField === 'p' }">
              <Lock :size="15" class="lg-field-icon" />
              <input
                v-model="form.password"
                :type="showPwd ? 'text' : 'password'"
                placeholder="请输入密码"
                autocomplete="current-password"
                @focus="focusField = 'p'"
                @blur="focusField = ''"
              />
              <button type="button" class="lg-eye" @click="showPwd = !showPwd" tabindex="-1">
                <Eye v-if="!showPwd" :size="15" />
                <EyeOff v-else :size="15" />
              </button>
            </div>
          </label>

          <p v-if="error" class="lg-error">
            <CircleAlert :size="14" />
            {{ error }}
          </p>

          <button type="submit" class="lg-btn" :disabled="loading">
            <span v-if="!loading">登 录</span>
            <span v-else class="lg-btn-loading">
              <LoaderCircle :size="15" class="lg-spin" /> 登录中…
            </span>
          </button>

          <p class="lg-foot">账号由系统管理员维护 · 数据每日收盘后更新</p>
        </form>
      </main>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  CandlestickChart, User, Lock, Eye, EyeOff, CircleAlert, LoaderCircle,
} from 'lucide-vue-next'
import { useAuthStore } from '../stores/auth'
import { useToast } from '../components/ui/toast'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const toast = useToast()

const form = reactive({ username: '', password: '' })
const loading = ref(false)
const error = ref('')
const focusField = ref('')
const showPwd = ref(false)

const stats = [
  { k: '在管投顾', v: '30+' },
  { k: '覆盖品种', v: '60+' },
  { k: '跟踪板块', v: '19' },
]

// 生成一条向上的折线（装饰用）
const points = (() => {
  const raw = [38, 42, 40, 47, 45, 52, 50, 58, 55, 63, 60, 68, 66, 74, 71, 80, 78, 86, 84, 92]
  const w = 480, h = 160, pad = 6
  const max = Math.max(...raw), min = Math.min(...raw)
  return raw.map((v, i) => [
    pad + (i / (raw.length - 1)) * (w - pad * 2),
    h - pad - ((v - min) / (max - min)) * (h - pad * 2),
  ])
})()

const linePath = computed(() =>
  points.map((p, i) => `${i === 0 ? 'M' : 'L'}${p[0].toFixed(1)},${p[1].toFixed(1)}`).join(' ')
)
const areaPath = computed(() => `${linePath.value} L${points[points.length - 1][0]},160 L${points[0][0]},160 Z`)
const lastPoint = computed(() => points[points.length - 1])

async function onSubmit() {
  error.value = ''
  loading.value = true
  try {
    await auth.login(form.username, form.password)
    toast.success('登录成功')
    const redirect = route.query.redirect || '/display/overview'
    router.push(redirect)
  } catch (e) {
    error.value = e.response?.data?.detail || '登录失败，请检查账号密码'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.lg-page {
  min-height: 100vh;
  background: #0a0f1a;
  color: #e6edf7;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  position: relative;
  overflow: hidden;
}

/* ---------- 背景 ---------- */
.lg-bg { position: absolute; inset: 0; pointer-events: none; }
.lg-grid {
  position: absolute; inset: 0;
  background-image:
    linear-gradient(rgba(120, 160, 255, 0.05) 1px, transparent 1px),
    linear-gradient(90deg, rgba(120, 160, 255, 0.05) 1px, transparent 1px);
  background-size: 44px 44px;
  mask-image: radial-gradient(ellipse 90% 80% at 30% 40%, #000 30%, transparent 75%);
}
.lg-glow { position: absolute; border-radius: 50%; filter: blur(90px); }
.lg-glow-a {
  width: 520px; height: 520px; left: -140px; top: -120px;
  background: radial-gradient(circle, rgba(59, 130, 246, 0.22), transparent 65%);
  animation: lgDrift 14s ease-in-out infinite alternate;
}
.lg-glow-b {
  width: 420px; height: 420px; right: -100px; bottom: -140px;
  background: radial-gradient(circle, rgba(38, 198, 166, 0.14), transparent 65%);
  animation: lgDrift 18s ease-in-out infinite alternate-reverse;
}
@keyframes lgDrift {
  from { transform: translate(0, 0) scale(1); }
  to { transform: translate(40px, 30px) scale(1.08); }
}

/* ---------- 布局 ---------- */
.lg-shell {
  position: relative;
  width: 100%;
  max-width: 980px;
  display: grid;
  grid-template-columns: 1.15fr 1fr;
  border: 1px solid rgba(120, 160, 255, 0.14);
  border-radius: 18px;
  overflow: hidden;
  background: rgba(13, 20, 36, 0.72);
  backdrop-filter: blur(14px);
  box-shadow: 0 24px 80px rgba(0, 0, 0, 0.5), 0 0 0 1px rgba(255, 255, 255, 0.02) inset;
}
@media (max-width: 860px) {
  .lg-shell { grid-template-columns: 1fr; }
  .lg-brand { display: none; }
}

/* ---------- 入场动画 ---------- */
.lg-rise {
  opacity: 0;
  transform: translateY(14px);
  animation: lgRise 0.7s cubic-bezier(0.22, 1, 0.36, 1) forwards;
  animation-delay: var(--d, 0s);
}
@keyframes lgRise {
  to { opacity: 1; transform: translateY(0); }
}

/* ---------- 左侧品牌区 ---------- */
.lg-brand {
  padding: 44px 44px 36px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  border-right: 1px solid rgba(120, 160, 255, 0.1);
  background: linear-gradient(160deg, rgba(59, 130, 246, 0.07), transparent 55%);
}
.lg-brand-top { display: flex; align-items: center; gap: 10px; }
.lg-logo {
  width: 38px; height: 38px;
  display: grid; place-items: center;
  border-radius: 10px;
  color: #7db8ff;
  background: linear-gradient(145deg, rgba(77, 163, 255, 0.22), rgba(77, 163, 255, 0.06));
  border: 1px solid rgba(125, 184, 255, 0.35);
  box-shadow: 0 0 18px rgba(77, 163, 255, 0.25);
}
.lg-brand-name {
  font-size: 13px; font-weight: 600; letter-spacing: 0.18em;
  color: #9db8dd;
}

.lg-title {
  font-size: 34px;
  font-weight: 700;
  line-height: 1.25;
  letter-spacing: 0.02em;
  margin: 0;
}
.lg-title-accent {
  display: block;
  background: linear-gradient(92deg, #7db8ff, #4da3ff 55%, #26c6a6);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}
.lg-sub {
  margin: 12px 0 0;
  font-size: 13.5px;
  color: #8fa3c4;
  letter-spacing: 0.02em;
}

.lg-chart {
  margin-top: 28px;
  border: 1px solid rgba(120, 160, 255, 0.14);
  border-radius: 12px;
  background: rgba(9, 14, 26, 0.55);
  padding: 14px 16px 10px;
}
.lg-chart-svg { width: 100%; height: 130px; display: block; }
.lg-line {
  stroke-dasharray: 1200;
  stroke-dashoffset: 1200;
  animation: lgDraw 2.2s ease-out 0.5s forwards;
  filter: drop-shadow(0 0 6px rgba(77, 163, 255, 0.5));
}
.lg-area { opacity: 0; animation: lgFade 1.2s ease 1.4s forwards; }
.lg-dot {
  opacity: 0;
  animation: lgFade 0.5s ease 2.4s forwards, lgPulse 2.4s ease-in-out 2.6s infinite;
}
@keyframes lgDraw { to { stroke-dashoffset: 0; } }
@keyframes lgFade { to { opacity: 1; } }
@keyframes lgPulse {
  0%, 100% { r: 3.5; opacity: 1; }
  50% { r: 5.5; opacity: 0.6; }
}
.lg-chart-meta {
  display: flex; justify-content: space-between;
  font-size: 11.5px; color: #7788a8;
  padding-top: 8px;
  border-top: 1px dashed rgba(120, 160, 255, 0.14);
}
.lg-up { color: #26c6a6; font-weight: 600; font-variant-numeric: tabular-nums; }

.lg-brand-bottom { display: flex; gap: 28px; }
.lg-stat-v { font-size: 20px; font-weight: 700; font-variant-numeric: tabular-nums; }
.lg-stat-k { font-size: 11.5px; color: #7788a8; margin-top: 2px; }

/* ---------- 右侧表单 ---------- */
.lg-panel {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 48px 44px;
}
.lg-card { width: 100%; max-width: 320px; }
.lg-card-head h2 { font-size: 22px; font-weight: 700; margin: 0; }
.lg-card-head p { font-size: 12.5px; color: #7788a8; margin: 6px 0 26px; }

.lg-field { display: block; margin-bottom: 16px; }
.lg-field-label {
  display: block;
  font-size: 12px;
  color: #9db8dd;
  margin-bottom: 7px;
  letter-spacing: 0.04em;
}
.lg-field-box {
  display: flex; align-items: center; gap: 9px;
  height: 42px;
  padding: 0 12px;
  border-radius: 10px;
  border: 1px solid rgba(120, 160, 255, 0.18);
  background: rgba(9, 14, 26, 0.6);
  transition: border-color 0.2s, box-shadow 0.2s;
}
.lg-field-focus {
  border-color: #4da3ff;
  box-shadow: 0 0 0 3px rgba(77, 163, 255, 0.16);
}
.lg-field-icon { color: #5f7396; flex: none; }
.lg-field-box input {
  flex: 1;
  background: transparent;
  border: none;
  outline: none;
  color: #e6edf7;
  font-size: 14px;
}
.lg-field-box input::placeholder { color: #4d5f7d; }
.lg-eye {
  background: none; border: none; cursor: pointer;
  color: #5f7396; display: grid; place-items: center; padding: 2px;
}
.lg-eye:hover { color: #9db8dd; }

.lg-error {
  display: flex; align-items: center; gap: 6px;
  font-size: 12.5px;
  color: #ff7a7a;
  background: rgba(255, 90, 90, 0.08);
  border: 1px solid rgba(255, 90, 90, 0.25);
  border-radius: 8px;
  padding: 8px 10px;
  margin: 0 0 14px;
}

.lg-btn {
  width: 100%;
  height: 44px;
  border: none;
  border-radius: 10px;
  cursor: pointer;
  font-size: 14.5px;
  font-weight: 600;
  letter-spacing: 0.3em;
  color: #06111f;
  background: linear-gradient(92deg, #7db8ff, #4da3ff 60%, #3b8ef2);
  box-shadow: 0 8px 24px rgba(59, 130, 246, 0.35);
  transition: transform 0.15s, box-shadow 0.2s, filter 0.2s;
}
.lg-btn:hover:not(:disabled) {
  filter: brightness(1.08);
  box-shadow: 0 10px 30px rgba(59, 130, 246, 0.5);
  transform: translateY(-1px);
}
.lg-btn:active:not(:disabled) { transform: translateY(0); }
.lg-btn:disabled { opacity: 0.65; cursor: not-allowed; letter-spacing: 0.1em; }
.lg-btn-loading { display: inline-flex; align-items: center; gap: 8px; }
.lg-spin { animation: lgSpin 0.9s linear infinite; }
@keyframes lgSpin { to { transform: rotate(360deg); } }

.lg-foot {
  margin: 22px 0 0;
  text-align: center;
  font-size: 11.5px;
  color: #55677f;
}
</style>
