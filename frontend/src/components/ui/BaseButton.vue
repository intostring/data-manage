<template>
  <button :class="classes" :disabled="disabled" :type="type" @click="$emit('click', $event)">
    <component :is="icon" v-if="icon" :size="15" :stroke-width="1.75" class="shrink-0" />
    <slot />
  </button>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  variant: { type: String, default: 'primary' }, // primary | secondary | danger | ghost
  size: { type: String, default: 'md' }, // sm | md
  icon: { type: [Object, Function], default: null },
  disabled: { type: Boolean, default: false },
  type: { type: String, default: 'button' },
  block: { type: Boolean, default: false },
})

defineEmits(['click'])

const variants = {
  primary: 'bg-accent text-white hover:bg-accent-hover border border-accent',
  secondary: 'bg-panel text-ink hover:bg-panelLight border border-line',
  danger: 'bg-danger text-white hover:bg-red-600 border border-danger',
  ghost: 'bg-transparent text-ink-muted hover:bg-panelLight border border-transparent',
}

const sizes = {
  sm: 'text-xs px-2.5 py-1.5 gap-1.5',
  md: 'text-sm px-3.5 py-2 gap-2',
}

const classes = computed(() => [
  'inline-flex items-center justify-center font-medium rounded transition-colors',
  'disabled:opacity-50 disabled:cursor-not-allowed',
  variants[props.variant],
  sizes[props.size],
  props.block ? 'w-full' : '',
])
</script>
