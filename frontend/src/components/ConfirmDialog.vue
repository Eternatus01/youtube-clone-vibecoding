<script setup lang="ts">
import { onBeforeUnmount, onMounted } from 'vue'

const props = defineProps<{
  open: boolean
  title: string
  message: string
  confirmText?: string
  cancelText?: string
}>()

const emit = defineEmits<{
  confirm: []
  cancel: []
}>()

function onKeydown(e: KeyboardEvent) {
  if (!props.open) return
  if (e.key === 'Escape') emit('cancel')
}

onMounted(() => document.addEventListener('keydown', onKeydown))
onBeforeUnmount(() => document.removeEventListener('keydown', onKeydown))
</script>

<template>
  <Teleport to="body">
    <div
      v-if="open"
      class="dialog-overlay"
      role="dialog"
      aria-modal="true"
      :aria-label="title"
      @click.self="emit('cancel')"
    >
      <div class="dialog-box">
        <h3>{{ title }}</h3>
        <p>{{ message }}</p>
        <div class="dialog-actions">
          <button class="btn" type="button" @click="emit('cancel')">
            {{ cancelText ?? 'Отмена' }}
          </button>
          <button class="btn btn-confirm" type="button" @click="emit('confirm')">
            {{ confirmText ?? 'Удалить' }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.btn-confirm {
  background: var(--danger);
  color: #fff;
}

.btn-confirm:hover {
  background: var(--danger);
  opacity: 0.9;
}
</style>
