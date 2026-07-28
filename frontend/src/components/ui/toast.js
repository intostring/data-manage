import { reactive } from 'vue'

const toasts = reactive([])
let seq = 0

function push(message, type = 'info', duration = 3000) {
  const id = ++seq
  toasts.push({ id, message, type })
  if (duration > 0) {
    setTimeout(() => remove(id), duration)
  }
  return id
}

function remove(id) {
  const idx = toasts.findIndex((t) => t.id === id)
  if (idx >= 0) toasts.splice(idx, 1)
}

export function useToast() {
  return {
    toasts,
    success: (msg, d) => push(msg, 'success', d),
    error: (msg, d) => push(msg, 'error', d ?? 4000),
    info: (msg, d) => push(msg, 'info', d),
    warning: (msg, d) => push(msg, 'warning', d ?? 4000),
    remove,
  }
}
