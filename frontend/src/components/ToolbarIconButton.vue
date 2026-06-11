<script setup lang="ts">
import AppIcon from '@/components/AppIcon.vue'

const props = defineProps<{ icon: string; label: string }>()
const emit = defineEmits<{ click: [] }>()
</script>

<template>
  <button class="toolbar-icon-btn" type="button" :title="props.label" @click="emit('click')">
    <AppIcon :name="props.icon" :size="16" />
  </button>
</template>

<style scoped>
.toolbar-icon-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  border: none;
  border-radius: var(--rounded-sm);
  background: transparent;
  color: var(--color-slate);
  cursor: pointer;
}
.toolbar-icon-btn:active {
  background: var(--color-surface);
  color: var(--color-ink);
}
</style>
