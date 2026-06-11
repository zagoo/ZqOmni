<script setup lang="ts">
/** Primary-nav row (Rule 8.5): icon + label; parents expand INLINE; selected
 * state is a soft rounded fill — never a side border. */
import { useRoute, useRouter } from 'vue-router'
import AppIcon from '@/components/AppIcon.vue'

const props = withDefaults(
  defineProps<{
    icon: string
    label: string
    to?: string
    expandable?: boolean
    expanded?: boolean
    indent?: boolean
  }>(),
  { to: undefined, expandable: false, expanded: false, indent: false },
)
const emit = defineEmits<{ toggle: []; select: [] }>()

const route = useRoute()
const router = useRouter()

function onClick() {
  if (props.expandable) {
    emit('toggle')
  } else if (props.to) {
    router.push(props.to)
  } else {
    emit('select')
  }
}
</script>

<template>
  <button
    class="nav-item"
    :class="{ selected: props.to && route.path === props.to, indent: props.indent }"
    type="button"
    @click="onClick"
  >
    <AppIcon :name="props.icon" :size="16" class="nav-item-icon" />
    <span class="nav-item-label">{{ props.label }}</span>
    <AppIcon
      v-if="props.expandable"
      :name="props.expanded ? 'chevron-down' : 'chevron-right'"
      :size="16"
      class="nav-item-chevron"
    />
  </button>
</template>

<style scoped>
.nav-item {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  border: none;
  background: transparent;
  font-family: var(--font-sans);
  font-size: 14px;
  font-weight: 500;
  color: var(--color-slate);
  padding: 6px 10px;
  border-radius: var(--rounded-sm);
  cursor: pointer;
  text-align: left;
}
.nav-item:active {
  background: var(--color-hairline-soft);
}
.nav-item.selected {
  background: var(--color-tint-gray);
  color: var(--color-ink);
}
.nav-item.indent {
  padding-left: 32px;
}
.nav-item-icon {
  flex: none;
  color: var(--color-steel);
}
.nav-item.selected .nav-item-icon {
  color: var(--color-ink);
}
.nav-item-label {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.nav-item-chevron {
  flex: none;
  color: var(--color-stone);
}
</style>
