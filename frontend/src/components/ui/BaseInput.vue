<template>
  <label class="block">
    <span v-if="label" class="label-base">{{ label }}</span>
    <textarea
      v-if="type === 'textarea'"
      :value="modelValue"
      :placeholder="placeholder"
      :rows="rows"
      class="input-base resize-none"
      @input="$emit('update:modelValue', $event.target.value)"
    />
    <input
      v-else
      :type="type"
      :value="modelValue"
      :placeholder="placeholder"
      :step="step"
      class="input-base"
      @input="$emit('update:modelValue', $event.target.value)"
    />
  </label>
</template>

<script setup>
defineProps({
  modelValue: { type: [String, Number], default: '' },
  label: { type: String, default: '' },
  placeholder: { type: String, default: '' },
  type: { type: String, default: 'text' },
  rows: { type: Number, default: 3 },
  step: { type: String, default: '' },
})
defineEmits(['update:modelValue'])
</script>
