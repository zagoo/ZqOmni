<script setup lang="ts">
/** Label above the control, control fills width (Rule 8.11). */
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

function onChange(event: Event) {
  emit('update:modelValue', (event.target as HTMLSelectElement).value)
}
</script>

<template>
  <div class="dropdown-row">
    <span class="dropdown-label">{{ props.label }}</span>
    <select
      class="select-input"
      :value="props.modelValue"
      :disabled="props.disabled"
      @change="onChange"
    >
      <option value="" disabled>{{ props.placeholder }}</option>
      <option
        v-for="option in props.options"
        :key="option.value"
        :value="option.value"
        :disabled="option.disabled"
      >
        {{ option.label }}
      </option>
    </select>
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
