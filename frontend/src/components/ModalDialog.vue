<script setup lang="ts">
/** Modal surface (DESIGN.md modal elevation; 12px card radius). Used by
 * create/confirm dialogs across the tenancy and IAM modules. */
import AppIcon from '@/components/AppIcon.vue'

const props = withDefaults(defineProps<{ title: string; open: boolean; wide?: boolean }>(), {
  wide: false,
})
const emit = defineEmits<{ close: [] }>()
</script>

<template>
  <Teleport to="body">
    <div v-if="props.open" class="modal-backdrop" @click.self="emit('close')">
      <div class="modal" :class="{ wide: props.wide }" role="dialog" :aria-label="props.title">
        <header class="modal-header">
          <h3 class="text-h5">{{ props.title }}</h3>
          <button class="modal-close" type="button" aria-label="Close" @click="emit('close')">
            <AppIcon name="x" :size="16" />
          </button>
        </header>
        <div class="modal-body">
          <slot />
        </div>
        <footer v-if="$slots.footer" class="modal-footer">
          <slot name="footer" />
        </footer>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(15, 15, 15, 0.35);
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding: 9vh var(--space-md) var(--space-md);
  z-index: 60;
}
.modal {
  width: min(480px, 100%);
  background: var(--color-canvas);
  border: 1px solid var(--color-hairline);
  border-radius: var(--rounded-lg);
  box-shadow: var(--shadow-modal);
  max-height: 82vh;
  display: flex;
  flex-direction: column;
}
.modal.wide {
  width: min(680px, 100%);
}
.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-lg) var(--space-xl) var(--space-sm);
}
.modal-close {
  border: none;
  background: transparent;
  color: var(--color-steel);
  cursor: pointer;
  width: 28px;
  height: 28px;
  border-radius: var(--rounded-sm);
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
.modal-close:active {
  background: var(--color-surface);
}
.modal-body {
  padding: var(--space-sm) var(--space-xl);
  overflow-y: auto;
}
.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-sm);
  padding: var(--space-md) var(--space-xl) var(--space-lg);
  border-top: 1px solid var(--color-hairline-soft);
}
</style>
