<script setup lang="ts">
/** Right-aligned segmented pill for in-content mode toggles (Rule 8.7).
 * Pill geometry is allowed here (pill tabs), per DESIGN.md. */
const props = defineProps<{
  modelValue: string
  options: { value: string; label: string }[]
}>()
const emit = defineEmits<{ 'update:modelValue': [value: string] }>()
</script>

<template>
  <div class="segmented" role="tablist">
    <button
      v-for="option in props.options"
      :key="option.value"
      type="button"
      role="tab"
      class="segment"
      :class="{ active: option.value === props.modelValue }"
      :aria-selected="option.value === props.modelValue"
      @click="emit('update:modelValue', option.value)"
    >
      {{ option.label }}
    </button>
  </div>
</template>

<style scoped>
.segmented {
  display: inline-flex;
  gap: 4px;
  background: var(--color-surface);
  border: 1px solid var(--color-hairline);
  border-radius: var(--rounded-full);
  padding: 3px;
}
.segment {
  border: none;
  background: transparent;
  font-family: var(--font-sans);
  font-size: 14px;
  font-weight: 500;
  color: var(--color-steel);
  border-radius: var(--rounded-full);
  padding: 5px 14px;
  cursor: pointer;
}
.segment.active {
  background: var(--color-ink-deep);
  color: var(--color-on-dark);
}
</style>
