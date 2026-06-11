<script setup lang="ts">
/** Collapsible labeled section for the right configuration panel (Rule 8.11). */
import { ref } from 'vue'
import AppIcon from '@/components/AppIcon.vue'

const props = withDefaults(defineProps<{ title: string; defaultOpen?: boolean }>(), {
  defaultOpen: true,
})
const open = ref(props.defaultOpen)
</script>

<template>
  <section class="settings-section">
    <button class="section-header" type="button" @click="open = !open">
      <span class="section-title">{{ props.title }}</span>
      <AppIcon :name="open ? 'chevron-down' : 'chevron-right'" :size="16" />
    </button>
    <div v-show="open" class="section-body">
      <slot />
    </div>
  </section>
</template>

<style scoped>
.settings-section {
  border-bottom: 1px solid var(--color-hairline-soft);
  padding: var(--space-sm) 0;
}
.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  border: none;
  background: transparent;
  cursor: pointer;
  padding: 6px 0;
  color: var(--color-stone);
}
.section-title {
  font-family: var(--font-sans);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 1px;
  text-transform: uppercase;
  color: var(--color-stone);
}
.section-body {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
  padding: var(--space-xs) 0;
}
</style>
