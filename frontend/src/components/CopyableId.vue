<script setup lang="ts">
/** Read-only identifier with a one-click copy affordance. Surfaces opaque
 * ULIDs (tnt-…, prj-…) that the API returns but detail pages would otherwise
 * never render, so operators can paste them where a scope id is required. */
import { ref } from 'vue'
import AppIcon from '@/components/AppIcon.vue'
import { useToast } from '@/composables/useToast'

const props = defineProps<{ value: string; label?: string }>()
const toast = useToast()
const copied = ref(false)
let resetTimer: ReturnType<typeof setTimeout> | undefined

async function copy() {
  try {
    await navigator.clipboard.writeText(props.value)
    copied.value = true
    toast.success(`${props.label ?? 'ID'} copied to clipboard.`)
    clearTimeout(resetTimer)
    resetTimer = setTimeout(() => (copied.value = false), 1400)
  } catch {
    toast.error('Could not copy. Select the id and copy it manually.')
  }
}
</script>

<template>
  <span class="copyable-id">
    <span v-if="props.label" class="copyable-id__label">{{ props.label }}</span>
    <code class="copyable-id__value">{{ props.value }}</code>
    <button
      class="copyable-id__btn"
      type="button"
      :title="`Copy ${props.label ?? 'id'}`"
      @click="copy"
    >
      <AppIcon :name="copied ? 'check-circle' : 'clipboard'" :size="16" />
    </button>
  </span>
</template>

<style scoped>
.copyable-id {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}
.copyable-id__label {
  font-size: 12px;
  font-weight: 500;
  color: var(--color-steel);
}
.copyable-id__value {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 12.5px;
  color: var(--color-charcoal);
  background: var(--color-surface);
  border: 1px solid var(--color-hairline);
  border-radius: var(--rounded-sm);
  padding: 2px 8px;
  user-select: all;
}
.copyable-id__btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  height: 26px;
  border: none;
  border-radius: var(--rounded-sm);
  background: transparent;
  color: var(--color-slate);
  cursor: pointer;
}
.copyable-id__btn:active {
  background: var(--color-surface);
  color: var(--color-ink);
}
</style>
