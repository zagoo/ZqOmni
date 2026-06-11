<script setup lang="ts">
import { useToast } from '@/composables/useToast'

const { toasts } = useToast()
</script>

<template>
  <Teleport to="body">
    <div class="toast-host" aria-live="polite">
      <div v-for="toast in toasts" :key="toast.id" class="toast" :class="`toast-${toast.kind}`">
        {{ toast.message }}
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.toast-host {
  position: fixed;
  bottom: var(--space-lg);
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  flex-direction: column;
  gap: var(--space-xs);
  z-index: 80;
  align-items: center;
}
.toast {
  background: var(--color-ink-deep);
  color: var(--color-on-dark);
  border-radius: var(--rounded-md);
  padding: 10px 18px;
  font-size: 14px;
  font-weight: 500;
  box-shadow: var(--shadow-modal);
  max-width: 70vw;
}
.toast-error {
  background: var(--color-error);
}
.toast-success {
  background: var(--color-ink-deep);
}
.toast-info {
  background: var(--color-brand-navy);
}
</style>
