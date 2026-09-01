<template>
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="show" class="fixed inset-0 z-50 flex items-start justify-center pt-20 px-4">
        <div class="absolute inset-0 bg-slate-900/35" @click="onClose" />
        <div class="relative w-full max-w-lg bg-panel rounded shadow-pop border border-line">
          <div class="flex items-center justify-between px-5 py-4 border-b border-line">
            <h3 class="text-base font-semibold text-ink">{{ title }}</h3>
            <button class="text-ink-faint hover:text-ink transition-colors" @click="onClose">
              <X :size="18" :stroke-width="1.75" />
            </button>
          </div>
          <div class="px-5 py-4 max-h-[60vh] overflow-y-auto">
            <slot />
          </div>
          <div v-if="$slots.footer" class="flex items-center justify-end gap-2 px-5 py-3 border-t border-line bg-panelLight rounded-b">
            <slot name="footer" />
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { X } from 'lucide-vue-next'

defineProps({
  show: { type: Boolean, default: false },
  title: { type: String, default: '' },
})
const emit = defineEmits(['close'])
function onClose() {
  emit('close')
}
</script>

<style scoped>
.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.15s ease;
}
.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}
</style>
