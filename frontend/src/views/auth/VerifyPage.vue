<script setup lang="ts">
/** M01 UI page 2 — Code verification, route /login/verify (FDD §2.1.2):
 * 8 digit boxes, paste support, auto-submit on 8th digit, resend cooldown,
 * 10-minute expiry countdown, uniform anti-enumeration error. */
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useLoginFlow } from '@/views/auth/hooks/useLoginFlow'

const router = useRouter()
const flow = useLoginFlow()

const digits = ref<string[]>(Array(8).fill(''))
const boxes = ref<HTMLInputElement[]>([])

onMounted(() => {
  if (!flow.normalizedEmail.value) router.replace('/login')
  boxes.value[0]?.focus()
})

const expiryLabel = computed(() => {
  const s = flow.codeExpiresIn.value
  if (s <= 0) return null
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`
})

function onInput(index: number, event: Event) {
  const input = event.target as HTMLInputElement
  const value = input.value.replace(/\D/g, '')
  if (value.length > 1) {
    paste(value, index)
    return
  }
  digits.value[index] = value
  input.value = value
  if (value && index < 7) boxes.value[index + 1]?.focus()
}

function onKeydown(index: number, event: KeyboardEvent) {
  if (event.key === 'Backspace' && !digits.value[index] && index > 0) {
    boxes.value[index - 1]?.focus()
  }
}

function onPaste(event: ClipboardEvent) {
  event.preventDefault()
  paste(event.clipboardData?.getData('text') ?? '', 0)
}

function paste(raw: string, from: number) {
  const cleaned = raw.replace(/\s+/g, '').replace(/\D/g, '').slice(0, 8 - from)
  for (let i = 0; i < cleaned.length; i++) digits.value[from + i] = cleaned[i] ?? ''
  const next = Math.min(from + cleaned.length, 7)
  boxes.value[next]?.focus()
}

watch(
  digits,
  async (value) => {
    const joined = value.join('')
    if (joined.length === 8 && /^[0-9]{8}$/.test(joined) && !flow.submitting.value) {
      flow.code.value = joined
      const ok = await flow.verifyCode()
      if (!ok) {
        digits.value = Array(8).fill('')
        boxes.value[0]?.focus()
      }
    }
  },
  { deep: true },
)

async function resend() {
  if (flow.resendCooldown.value > 0) return
  await flow.requestCode()
}
</script>

<template>
  <div class="login-hero">
    <div class="login-card">
      <h1 class="login-title">Enter your code</h1>
      <p class="login-subtitle">
        If this email is registered, a login code has been sent. It expires in 10 minutes.
      </p>
      <div class="email-row">
        <span class="email-value">{{ flow.normalizedEmail.value }}</span>
        <router-link class="change-link" to="/login">Change</router-link>
      </div>

      <div class="code-boxes" :class="{ locked: flow.submitting.value }" @paste="onPaste">
        <input
          v-for="(_, i) in digits"
          :key="i"
          :ref="(el) => { if (el) boxes[i] = el as HTMLInputElement }"
          class="code-box"
          type="text"
          inputmode="numeric"
          maxlength="8"
          :value="digits[i]"
          :disabled="flow.submitting.value || flow.retryAfter.value > 0"
          @input="onInput(i, $event)"
          @keydown="onKeydown(i, $event)"
        />
      </div>
      <p v-if="flow.codeError.value" class="field-error code-error">{{ flow.codeError.value }}</p>
      <p v-if="expiryLabel" class="text-caption expiry-hint">Code expires in {{ expiryLabel }}</p>

      <button
        class="btn btn-secondary resend-btn"
        type="button"
        :disabled="flow.resendCooldown.value > 0 || flow.submitting.value"
        @click="resend"
      >
        <span v-if="flow.resendCooldown.value > 0">Resend code ({{ flow.resendCooldown.value }}s)</span>
        <span v-else>Resend code</span>
      </button>
    </div>
  </div>
</template>

<style scoped>
.login-hero {
  min-height: 100vh;
  background: var(--color-brand-navy);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--space-xl);
}
.login-card {
  width: min(440px, 100%);
  background: var(--color-canvas);
  border: 1px solid var(--color-hairline);
  border-radius: var(--rounded-lg);
  box-shadow: var(--shadow-mockup);
  padding: var(--space-xxl);
}
.login-title {
  font-size: 28px;
  font-weight: 600;
  letter-spacing: -0.5px;
}
.login-subtitle {
  font-size: 14px;
  color: var(--color-steel);
  margin: var(--space-xs) 0 var(--space-lg);
  line-height: 1.5;
}
.email-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: var(--color-surface);
  border-radius: var(--rounded-md);
  padding: var(--space-sm) var(--space-md);
  margin-bottom: var(--space-lg);
}
.email-value {
  font-size: 14px;
  font-weight: 500;
  color: var(--color-charcoal);
  overflow: hidden;
  text-overflow: ellipsis;
}
.change-link {
  font-size: 14px;
  font-weight: 500;
  flex: none;
}
.code-boxes {
  display: flex;
  gap: 6px;
  justify-content: space-between;
}
.code-box {
  width: 42px;
  height: 52px;
  text-align: center;
  font-size: 22px;
  font-weight: 600;
  font-family: var(--font-sans);
  color: var(--color-ink);
  border: 1px solid var(--color-hairline-strong);
  border-radius: var(--rounded-md);
  outline: none;
}
.code-box:focus {
  border: 2px solid var(--color-primary);
}
.code-boxes.locked .code-box {
  background: var(--color-surface);
}
.code-error {
  margin-top: var(--space-sm);
}
.expiry-hint {
  margin-top: var(--space-xs);
}
.resend-btn {
  width: 100%;
  justify-content: center;
  margin-top: var(--space-lg);
}
</style>
