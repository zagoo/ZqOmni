<script setup lang="ts">
/** Label fills the row, switch right-aligned (Rule 8.11). */
const props = withDefaults(
  defineProps<{ label: string; modelValue: boolean; disabled?: boolean }>(),
  { disabled: false },
)
const emit = defineEmits<{ 'update:modelValue': [value: boolean] }>()
</script>

<template>
  <label class="toggle-row" :class="{ disabled: props.disabled }">
    <span class="toggle-label">{{ props.label }}</span>
    <button
      class="switch"
      :class="{ on: props.modelValue }"
      type="button"
      role="switch"
      :aria-checked="props.modelValue"
      :disabled="props.disabled"
      @click="emit('update:modelValue', !props.modelValue)"
    >
      <span class="knob" />
    </button>
  </label>
</template>

<style scoped>
.toggle-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-sm);
}
.toggle-row.disabled {
  opacity: 0.5;
}
.toggle-label {
  flex: 1;
  font-size: 14px;
  color: var(--color-charcoal);
}
.switch {
  flex: none;
  width: 36px;
  height: 20px;
  border-radius: var(--rounded-full);
  border: none;
  background: var(--color-hairline-strong);
  position: relative;
  cursor: pointer;
  transition: background-color 150ms ease;
}
.switch.on {
  background: var(--color-primary);
}
.knob {
  position: absolute;
  top: 2px;
  left: 2px;
  width: 16px;
  height: 16px;
  border-radius: var(--rounded-full);
  background: #fff;
  transition: transform 150ms ease;
}
.switch.on .knob {
  transform: translateX(16px);
}
</style>
