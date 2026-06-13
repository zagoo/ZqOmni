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
    <div class="login-hero-bg login-hero-bg--a" aria-hidden="true"></div>
    <div class="login-hero-bg login-hero-bg--b" aria-hidden="true"></div>
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
/* Robot-fleet hero: two images cross-fading over the brand navy. The images
   must stay untinted (no overlay/filter — the robots are to remain
   pixel-identical), so blending happens in the base color only: the image's
   own edge tone (#7985a2) fused into the brand navy, which lands on the
   image's corner color (~#384661). The backgrounds are stacked as layers so
   the lower one (bg.png) stays fully opaque while the upper one (bg2.png)
   fades in/out — a true cross-fade with no brightness dip.
   Cycle (14s): bg.png held 5s → 2s fade → bg2.png held 5s → 2s fade back. */
.login-hero {
  position: relative;
  overflow: hidden;
  min-height: 100vh;
  background-color: color-mix(in srgb, var(--color-brand-navy) 60%, #7985a2);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--space-xl);
}
.login-hero-bg {
  position: absolute;
  inset: 0;
  z-index: 0;
  background-size: cover;
  background-position: center;
  background-repeat: no-repeat;
}
.login-hero-bg--a {
  background-image: url('../../assets/bg.png');
}
.login-hero-bg--b {
  background-image: url('../../assets/bg2.png');
  opacity: 0;
  animation: login-hero-crossfade 14s ease-in-out infinite;
}
@keyframes login-hero-crossfade {
  0%, 35.714% { opacity: 0; }   /* bg.png shown (0–5s) */
  50%, 85.714% { opacity: 1; }  /* fade to bg2.png (5–7s), hold (7–12s) */
  100% { opacity: 0; }          /* fade back to bg.png (12–14s) */
}
@media (prefers-reduced-motion: reduce) {
  .login-hero-bg--b { animation: none; }
}
.login-card {
  position: relative;
  z-index: 1;
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
