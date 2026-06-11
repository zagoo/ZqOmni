/** M01 login flow logic (FDD §2.1.2 UI pages 1-2): email step, code step,
 * resend cooldown, code-expiry countdown, anti-enumeration messaging. */
import { computed, onBeforeUnmount, ref } from 'vue'
import { useRouter } from 'vue-router'
import { AxiosError } from 'axios'
import { describeApiError } from '@/composables/useToast'
import { useAuthStore } from '@/store/auth'
import { m01CreateSession, m01RequestLoginCode } from '@/views/auth/api'

const EMAIL_KEY = 'zq.login.email'
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

export function useLoginFlow() {
  const router = useRouter()
  const auth = useAuthStore()

  const email = ref(sessionStorage.getItem(EMAIL_KEY) ?? localStorage.getItem(EMAIL_KEY) ?? '')
  const emailError = ref('')
  const code = ref('')
  const codeError = ref('')
  const submitting = ref(false)
  const resendCooldown = ref(0)
  const codeExpiresIn = ref(0)
  const retryAfter = ref(0)

  let timer: ReturnType<typeof setInterval> | null = null
  function startTimers() {
    timer ??= setInterval(() => {
      if (resendCooldown.value > 0) resendCooldown.value--
      if (codeExpiresIn.value > 0) codeExpiresIn.value--
      if (retryAfter.value > 0) retryAfter.value--
    }, 1000)
  }
  onBeforeUnmount(() => {
    if (timer) clearInterval(timer)
  })

  const normalizedEmail = computed(() => email.value.trim().toLowerCase().normalize('NFC'))

  function validateEmail(): boolean {
    if (!EMAIL_RE.test(normalizedEmail.value) || normalizedEmail.value.length > 254) {
      emailError.value = 'Enter a valid email address.'
      return false
    }
    emailError.value = ''
    return true
  }

  async function requestCode(): Promise<boolean> {
    if (!validateEmail() || submitting.value) return false
    submitting.value = true
    try {
      const { data } = await m01RequestLoginCode({
        body: { email: normalizedEmail.value },
        throwOnError: true,
      })
      sessionStorage.setItem(EMAIL_KEY, normalizedEmail.value)
      localStorage.setItem(EMAIL_KEY, normalizedEmail.value)
      resendCooldown.value = data.data?.resend_available_in_s ?? 60
      codeExpiresIn.value = 600
      startTimers()
      return true
    } catch (e) {
      const { errorCode, message } = describeApiError(e)
      if (errorCode === 'E_RATE_LIMITED' && e instanceof AxiosError) {
        retryAfter.value = Number(e.response?.headers['retry-after'] ?? 60)
        startTimers()
      }
      emailError.value =
        errorCode === 'E_VALIDATION' ? 'Enter a valid email address.' : message
      return false
    } finally {
      submitting.value = false
    }
  }

  async function verifyCode(): Promise<boolean> {
    if (!/^[0-9]{8}$/.test(code.value)) {
      codeError.value = 'Enter the 8-digit code from your email.'
      return false
    }
    if (submitting.value) return false
    submitting.value = true
    try {
      const { data } = await m01CreateSession({
        body: { email: normalizedEmail.value, code: code.value },
        throwOnError: true,
      })
      const payload = data.data
      if (!payload) return false
      auth.setAccessToken(payload.access_token)
      await auth.loadCurrentSession()
      router.push(payload.tenant_selection_required ? '/account/session' : '/')
      return true
    } catch (e) {
      const { errorCode } = describeApiError(e)
      code.value = ''
      if (errorCode === 'E_RATE_LIMITED' && e instanceof AxiosError) {
        retryAfter.value = Number(e.response?.headers['retry-after'] ?? 60)
        startTimers()
        codeError.value = `Too many attempts. Try again in ${retryAfter.value}s.`
      } else {
        // One uniform message regardless of cause (anti-enumeration, FDD).
        codeError.value = 'This code is invalid or has expired. Request a new code.'
      }
      return false
    } finally {
      submitting.value = false
    }
  }

  return {
    email,
    emailError,
    code,
    codeError,
    submitting,
    resendCooldown,
    codeExpiresIn,
    retryAfter,
    normalizedEmail,
    validateEmail,
    requestCode,
    verifyCode,
  }
}
