<script setup lang="ts">
/** M01 UI page 1 — Sign-in email step, route /login (FDD §2.1.2). */
import { useRouter } from 'vue-router'
import { useLoginFlow } from '@/views/auth/hooks/useLoginFlow'

const router = useRouter()
const flow = useLoginFlow()

async function submit() {
  if (await flow.requestCode()) router.push('/login/verify')
}
</script>

<template>
  <div class="login-hero">
    <div class="login-card">
      <span class="login-logo">Z</span>
      <h1 class="login-title">Sign in to ZqOmni</h1>
      <p class="login-subtitle">
        Physical AI Data &amp; Compute Infrastructure Platform
      </p>
      <form class="login-form" @submit.prevent="submit">
        <div class="field">
          <label class="field-label" for="email">Work email</label>
          <input
            id="email"
            v-model="flow.email.value"
            class="text-input"
            type="email"
            placeholder="name@company.com"
            autocomplete="email"
            maxlength="254"
            required
            @blur="flow.email.value && flow.validateEmail()"
          />
          <span v-if="flow.emailError.value" class="field-error">{{ flow.emailError.value }}</span>
        </div>
        <button
          class="btn btn-primary login-submit"
          type="submit"
          :disabled="flow.submitting.value || flow.retryAfter.value > 0"
        >
          <span v-if="flow.retryAfter.value > 0">Too many requests. Try again in {{ flow.retryAfter.value }}s</span>
          <span v-else-if="flow.submitting.value">Sending…</span>
          <span v-else>Send code</span>
        </button>
      </form>
      <p class="login-footnote">
        Access requires a pre-registered corporate email. A one-time code will be sent if the
        email is registered.
      </p>
    </div>
  </div>
</template>

<style scoped>
/* Deep navy hero band with centered card (DESIGN.md signature). */
.login-hero {
  min-height: 100vh;
  background: var(--color-brand-navy);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--space-xl);
}
.login-card {
  width: min(420px, 100%);
  background: var(--color-canvas);
  border: 1px solid var(--color-hairline);
  border-radius: var(--rounded-lg);
  box-shadow: var(--shadow-mockup);
  padding: var(--space-xxl);
  display: flex;
  flex-direction: column;
}
.login-logo {
  width: 40px;
  height: 40px;
  border-radius: var(--rounded-md);
  background: var(--color-primary);
  color: var(--color-on-primary);
  font-size: 20px;
  font-weight: 600;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  margin-bottom: var(--space-lg);
}
.login-title {
  font-size: 28px;
  font-weight: 600;
  line-height: 1.25;
  letter-spacing: -0.5px;
  color: var(--color-ink);
}
.login-subtitle {
  font-size: 14px;
  color: var(--color-steel);
  margin: var(--space-xs) 0 var(--space-xl);
}
.login-form {
  display: flex;
  flex-direction: column;
}
.login-submit {
  width: 100%;
  justify-content: center;
}
.login-footnote {
  font-size: 13px;
  color: var(--color-steel);
  margin-top: var(--space-lg);
  line-height: 1.4;
}
</style>
