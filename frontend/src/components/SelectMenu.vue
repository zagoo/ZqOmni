<script setup lang="ts">
/**
 * Custom listbox dropdown — replaces the native <select> so the option popup
 * can be styled (native <option> lists are not styleable across browsers).
 *
 * Visual contract:
 *  - Trigger matches the .select-input field exactly (44px, hairline-strong
 *    border, 8px radius) so it sits seamlessly where a text input would.
 *  - Popup is teleported to <body> and fixed-positioned from the trigger's
 *    rect, so it never clips inside overflow:auto modals/panels and always
 *    aligns to the field's width and edge. Flips above when space is tight.
 *  - Options are borderless; the option font matches the field automatically
 *    and long labels ellipsize to fit; hover/active paints a transparent
 *    light-blue fill.
 *
 * Drop-in for native <select>: same v-model + { value, label, disabled }
 * options, plus restored keyboard operability (Up/Down/Enter/Esc).
 */
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import AppIcon from '@/components/AppIcon.vue'

interface SelectOption {
  value: string
  label: string
  disabled?: boolean
}

const props = withDefaults(
  defineProps<{
    modelValue: string
    options: SelectOption[]
    placeholder?: string
    disabled?: boolean
  }>(),
  { placeholder: 'Select…', disabled: false },
)
const emit = defineEmits<{ 'update:modelValue': [value: string] }>()

const open = ref(false)
const activeIndex = ref(-1)
const triggerEl = ref<HTMLButtonElement | null>(null)
const popupEl = ref<HTMLElement | null>(null)

const selected = computed(() => props.options.find((o) => o.value === props.modelValue))

interface Coords {
  left: number
  width: number
  top: number
  bottom: number
  maxHeight: number
  dropUp: boolean
}
const coords = ref<Coords>({ left: 0, width: 0, top: 0, bottom: 0, maxHeight: 300, dropUp: false })

const popupStyle = computed<Record<string, string>>(() => {
  const c = coords.value
  const style: Record<string, string> = {
    left: `${c.left}px`,
    width: `${c.width}px`,
    maxHeight: `${c.maxHeight}px`,
  }
  if (c.dropUp) style.bottom = `${c.bottom}px`
  else style.top = `${c.top}px`
  return style
})

function reposition() {
  const el = triggerEl.value
  if (!el) return
  const r = el.getBoundingClientRect()
  const gap = 4
  const vh = window.innerHeight
  const spaceBelow = vh - r.bottom - gap
  const spaceAbove = r.top - gap
  const dropUp = spaceBelow < 200 && spaceAbove > spaceBelow
  coords.value = {
    left: r.left,
    width: r.width,
    top: r.bottom + gap,
    bottom: vh - (r.top - gap),
    maxHeight: Math.max(140, Math.min(300, dropUp ? spaceAbove : spaceBelow)),
    dropUp,
  }
}

function openMenu() {
  if (props.disabled) return
  activeIndex.value = props.options.findIndex((o) => o.value === props.modelValue && !o.disabled)
  open.value = true
}
function closeMenu() {
  open.value = false
  activeIndex.value = -1
}
function toggle() {
  if (open.value) closeMenu()
  else openMenu()
}
function choose(opt: SelectOption) {
  if (opt.disabled) return
  emit('update:modelValue', opt.value)
  closeMenu()
  triggerEl.value?.focus()
}
function hover(i: number) {
  if (!props.options[i]?.disabled) activeIndex.value = i
}

function moveActive(dir: 1 | -1) {
  const n = props.options.length
  if (!n) return
  let i = activeIndex.value
  for (let step = 0; step < n; step++) {
    i = (i + dir + n) % n
    if (!props.options[i].disabled) {
      activeIndex.value = i
      break
    }
  }
  nextTick(() => {
    popupEl.value?.querySelector('.is-active')?.scrollIntoView({ block: 'nearest' })
  })
}

function onKeydown(e: KeyboardEvent) {
  if (props.disabled) return
  if (!open.value) {
    if (['ArrowDown', 'ArrowUp', 'Enter', ' '].includes(e.key)) {
      e.preventDefault()
      openMenu()
    }
    return
  }
  if (e.key === 'Escape' || e.key === 'Tab') {
    if (e.key === 'Escape') e.preventDefault()
    closeMenu()
  } else if (e.key === 'Enter' || e.key === ' ') {
    e.preventDefault()
    const opt = props.options[activeIndex.value]
    if (opt) choose(opt)
  } else if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
    e.preventDefault()
    moveActive(e.key === 'ArrowDown' ? 1 : -1)
  }
}

// Outside-click + scroll/resize tracking, active only while open.
function onDocPointerDown(e: MouseEvent) {
  const target = e.target as Node
  if (triggerEl.value?.contains(target) || popupEl.value?.contains(target)) return
  closeMenu()
}
let detach: (() => void) | null = null
watch(open, async (isOpen) => {
  if (isOpen) {
    await nextTick()
    reposition()
    document.addEventListener('mousedown', onDocPointerDown, true)
    window.addEventListener('scroll', reposition, true)
    window.addEventListener('resize', reposition)
    detach = () => {
      document.removeEventListener('mousedown', onDocPointerDown, true)
      window.removeEventListener('scroll', reposition, true)
      window.removeEventListener('resize', reposition)
    }
  } else {
    detach?.()
    detach = null
  }
})
onBeforeUnmount(() => detach?.())
</script>

<template>
  <div class="select-menu">
    <button
      ref="triggerEl"
      type="button"
      class="select-trigger"
      :class="{ open, 'is-placeholder': !selected, 'is-disabled': props.disabled }"
      :disabled="props.disabled"
      aria-haspopup="listbox"
      :aria-expanded="open"
      @click="toggle"
      @keydown="onKeydown"
    >
      <span class="select-value">{{ selected ? selected.label : props.placeholder }}</span>
      <AppIcon name="chevron-down" :size="16" class="select-caret" :class="{ flip: open }" />
    </button>

    <Teleport to="body">
      <div
        v-if="open"
        ref="popupEl"
        class="select-popup"
        :style="popupStyle"
        role="listbox"
      >
        <button
          v-for="(opt, i) in props.options"
          :key="opt.value"
          type="button"
          class="select-option"
          :class="{
            'is-active': i === activeIndex,
            'is-selected': opt.value === props.modelValue,
            'is-disabled': opt.disabled,
          }"
          role="option"
          :aria-selected="opt.value === props.modelValue"
          :disabled="opt.disabled"
          :title="opt.label"
          @mousemove="hover(i)"
          @click="choose(opt)"
        >
          <span class="option-label">{{ opt.label }}</span>
          <AppIcon
            v-if="opt.value === props.modelValue"
            name="check"
            :size="16"
            class="option-check"
          />
        </button>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.select-menu {
  width: 100%;
}

/* Trigger mirrors .select-input (assets/styles.css) so it drops in seamlessly */
.select-trigger {
  display: flex;
  align-items: center;
  gap: var(--space-xs);
  width: 100%;
  height: 44px;
  font-family: var(--font-sans);
  font-size: 16px;
  color: var(--color-ink);
  background: var(--color-canvas);
  border: 1px solid var(--color-hairline-strong);
  border-radius: var(--rounded-md);
  padding: var(--space-sm) var(--space-md);
  cursor: pointer;
  text-align: left;
  transition: border-color 150ms ease;
}
.select-trigger:hover:not(.is-disabled) {
  border-color: var(--color-stone);
}
.select-trigger.open,
.select-trigger:focus-visible {
  outline: none;
  border: 2px solid var(--color-primary);
  /* keep text from shifting when the border grows by 1px (matches .select-input:focus) */
  padding: calc(var(--space-sm) - 1px) calc(var(--space-md) - 1px);
}
.select-trigger.is-disabled {
  background: var(--color-surface);
  color: var(--color-muted);
  cursor: not-allowed;
}
.select-value {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.select-trigger.is-placeholder .select-value {
  color: var(--color-steel);
}
.select-caret {
  flex: none;
  color: var(--color-steel);
  transition: transform 150ms ease;
}
.select-caret.flip {
  transform: rotate(180deg);
}

/* Popup — fixed + teleported; width/edge come from the trigger's rect */
.select-popup {
  position: fixed;
  z-index: 1000;
  display: flex;
  flex-direction: column;
  gap: 1px;
  background: var(--color-canvas);
  border: 1px solid var(--color-hairline);
  border-radius: var(--rounded-md);
  box-shadow: var(--shadow-modal);
  padding: var(--space-xxs);
  overflow-y: auto;
  animation: select-pop 120ms ease;
}
@keyframes select-pop {
  from {
    opacity: 0;
    transform: translateY(-2px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* Options — borderless; font matches the field; label ellipsizes to fit */
.select-option {
  display: flex;
  align-items: center;
  gap: var(--space-xs);
  width: 100%;
  border: none;
  background: transparent;
  font-family: var(--font-sans);
  font-size: 16px;
  color: var(--color-ink);
  text-align: left;
  padding: 9px var(--space-sm);
  border-radius: var(--rounded-sm);
  cursor: pointer;
  transition: background-color 120ms ease, color 120ms ease;
}
.option-label {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.option-check {
  flex: none;
  color: var(--color-link-blue);
}
/* Transparent light-blue fill on mouse-over / keyboard-active */
.select-option:hover:not(.is-disabled),
.select-option.is-active:not(.is-disabled) {
  background: rgba(0, 117, 222, 0.1);
  color: var(--color-link-blue-pressed);
}
.select-option.is-selected {
  font-weight: 600;
  color: var(--color-link-blue);
}
.select-option.is-selected:hover:not(.is-disabled),
.select-option.is-selected.is-active:not(.is-disabled) {
  background: rgba(0, 117, 222, 0.14);
}
.select-option.is-disabled {
  color: var(--color-muted);
  cursor: not-allowed;
}
</style>
