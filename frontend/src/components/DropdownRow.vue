<script setup lang="ts">
/** Label above the control, control fills width (Rule 8.11). The control is a
 * styled SelectMenu (custom listbox) rather than a native <select>. */
import SelectMenu from '@/components/SelectMenu.vue'

const props = withDefaults(
  defineProps<{
    label: string
    modelValue: string
    options: { value: string; label: string; disabled?: boolean }[]
    placeholder?: string
    disabled?: boolean
  }>(),
  { placeholder: 'Select…', disabled: false },
)
const emit = defineEmits<{ 'update:modelValue': [value: string] }>()
</script>

<template>
  <div class="dropdown-row">
    <span class="dropdown-label">{{ props.label }}</span>
    <SelectMenu
      :model-value="props.modelValue"
      :options="props.options"
      :placeholder="props.placeholder"
      :disabled="props.disabled"
      @update:model-value="emit('update:modelValue', $event)"
    />
  </div>
</template>

<style scoped>
.dropdown-row {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.dropdown-label {
  font-size: 14px;
  font-weight: 500;
  color: var(--color-charcoal);
}
</style>
