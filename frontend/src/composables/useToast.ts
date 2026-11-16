import { ref } from 'vue'

export type ToastKind = 'info' | 'error'

interface ToastItem {
  id: number
  text: string
}

const toasts = ref<ToastItem[]>([])
let nextId = 1

export function useToast() {
  function push(text: string, ms = 4000) {
    const id = nextId++
    toasts.value.push({ id, text })
    setTimeout(() => {
      toasts.value = toasts.value.filter((t) => t.id !== id)
    }, ms)
  }

  function remove(id: number) {
    toasts.value = toasts.value.filter((t) => t.id !== id)
  }

  return { toasts, push, remove }
}
