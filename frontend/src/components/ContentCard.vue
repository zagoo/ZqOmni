<script setup lang="ts">
/** Card grid unit (Rule 8.8): tinted ~32px square icon top-left, title,
 * description. Tints come from the DESIGN.md pastel palette. */
import AppIcon from '@/components/AppIcon.vue'

const props = withDefaults(
  defineProps<{
    icon: string
    title: string
    description?: string
    tint?: 'peach' | 'rose' | 'mint' | 'lavender' | 'sky' | 'yellow' | 'gray'
  }>(),
  { description: '', tint: 'lavender' },
)
const emit = defineEmits<{ click: [] }>()
</script>

<template>
  <button class="content-card" type="button" @click="emit('click')">
    <span class="card-icon" :class="`tint-${props.tint}`">
      <AppIcon :name="props.icon" :size="20" />
    </span>
    <span class="card-title">{{ props.title }}</span>
    <span v-if="props.description" class="card-description">{{ props.description }}</span>
    <slot />
  </button>
</template>

<style scoped>
.content-card {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: var(--space-xs);
  background: var(--color-canvas);
  border: 1px solid var(--color-hairline);
  border-radius: var(--rounded-lg);
  padding: var(--space-xl);
  cursor: pointer;
  text-align: left;
  font-family: var(--font-sans);
}
.content-card:active {
  box-shadow: var(--shadow-subtle);
}
.card-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: var(--rounded-md);
  color: var(--color-charcoal);
}
.tint-peach { background: var(--color-tint-peach); }
.tint-rose { background: var(--color-tint-rose); }
.tint-mint { background: var(--color-tint-mint); }
.tint-lavender { background: var(--color-tint-lavender); }
.tint-sky { background: var(--color-tint-sky); }
.tint-yellow { background: var(--color-tint-yellow); }
.tint-gray { background: var(--color-tint-gray); }
.card-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--color-ink);
}
.card-description {
  font-size: 14px;
  color: var(--color-steel);
  line-height: 1.5;
}
</style>
