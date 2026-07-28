<template>
  <Teleport to="body">
    <div class="fixed top-4 right-4 z-[100] flex flex-col gap-2 pointer-events-none">
      <TransitionGroup name="toast">
        <div
          v-for="t in toasts"
          :key="t.id"
          class="pointer-events-auto flex items-center gap-2 px-4 py-2.5 rounded shadow-pop border bg-panel text-sm min-w-[240px]"
          :class="borderClass(t.type)"
        >
          <component :is="iconFor(t.type)" :size="16" :stroke-width="1.75" />
          <span class="text-ink">{{ t.message }}</span>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>

<script setup>
import { CheckCircle2, AlertCircle, Info } from 'lucide-vue-next'
import { useToast } from './toast'

const { toasts } = useToast()

function iconFor(type) {
  return { success: CheckCircle2, error: AlertCircle, info: Info }[type] || Info
}
function borderClass(type) {
  return {
    success: 'border-line text-success',
    error: 'border-line text-danger',
    info: 'border-line text-ink-muted',
  }[type]
}
</script>

<style scoped>
.toast-enter-active,
.toast-leave-active {
  transition: all 0.2s ease;
}
.toast-enter-from {
  opacity: 0;
  transform: translateX(20px);
}
.toast-leave-to {
  opacity: 0;
  transform: translateX(20px);
}
</style>
