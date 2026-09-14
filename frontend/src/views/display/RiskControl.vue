<template>
  <div class="max-w-6xl">
    <div class="mb-5">
      <h2 class="text-lg font-semibold text-ink">风险控制</h2>
      <p class="text-sm text-ink-muted mt-1">回撤、敞口、保证金率与预警事件跟踪</p>
    </div>
    <div class="bg-panel border border-line rounded shadow-card px-6 py-16 text-center">
      <ShieldCheck :size="36" :stroke-width="1.5" class="mx-auto text-ink-faint" />
      <p class="mt-3 text-sm font-medium text-ink-muted">页面建设中</p>
      <p class="mt-1 text-xs text-ink-faint">布局与数据接入后续提供</p>
    </div>
  </div>
</template>

<script setup>
import { ShieldCheck } from 'lucide-vue-next'
</script>
