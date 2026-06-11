<script setup lang="ts">
/** M01 UI page 1 — Sign-in email step, route /login (FDD §2.1.2). */
import { useRouter } from 'vue-router'
import logoIcon from '@/assets/logo_icon.svg'
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
      <div class="login-brand">
        <img class="login-logo" :src="logoIcon" alt="ZqOmni logo" />
        <h1 class="login-title">ZqOmni</h1>
      </div>
      <p class="login-subtitle">
        Physical AI Data &amp; Compute Infrastructure Platform
      </p>
      <form class="login-form" @submit.prevent="submit">
        <div class="field">
          <input
            id="email"
            aria-label="Email"
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
/* Robot-fleet hero image over the brand navy. The image must stay untinted
   (no overlay/filter — the robots are to remain pixel-identical), so blending
   happens in the base color only: the image's own edge tone (#7985a2) fused
   into the brand navy, which lands on the image's corner color (~#384661). */
.login-hero {
  min-height: 100vh;
  background-color: color-mix(in srgb, var(--color-brand-navy) 60%, #7985a2);
  background-image: url('../../assets/bg.png');
  background-size: cover;
  background-position: center;
  background-repeat: no-repeat;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--space-xl);
}
.login-card {
  width: min(420px, 100%);
  background: var(--color-canvas);
  border: 1px solid rgba(255, 255, 255, 0.7);
  border-radius: var(--rounded-lg);
  /* Edge depth against the bright hero: light-catching rim on the top edge,
     tight contact shadow, then deep navy-toned ambient falloff. */
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.9),
    0 1px 2px rgba(10, 21, 48, 0.16),
    0 12px 28px -8px rgba(10, 21, 48, 0.28),
    0 32px 64px -16px rgba(10, 21, 48, 0.34);
  padding: var(--space-xxl);
  display: flex;
  flex-direction: column;
}
@supports ((backdrop-filter: blur(1px)) or (-webkit-backdrop-filter: blur(1px))) {
  .login-card {
    background: rgba(255, 255, 255, 0.8);
    -webkit-backdrop-filter: blur(18px) saturate(150%);
    backdrop-filter: blur(18px) saturate(150%);
  }
}
.login-brand {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  margin-bottom: var(--space-lg);
}
.login-logo {
  width: 40px;
  height: 40px;
  flex: none;
  display: block;
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
