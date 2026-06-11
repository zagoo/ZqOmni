/** Global toast queue + unified ApiResponse error extraction (Rule 5.12:
 * code != 0 is a domain error; never inspect HTTP status alone). */
import { ref } from 'vue'
import { AxiosError } from 'axios'

export interface Toast {
  id: number
  kind: 'success' | 'error' | 'info'
  message: string
}

const toasts = ref<Toast[]>([])
let nextId = 1

function push(kind: Toast['kind'], message: string, ttlMs = 4200) {
  const id = nextId++
  toasts.value.push({ id, kind, message })
  setTimeout(() => {
    toasts.value = toasts.value.filter((t) => t.id !== id)
  }, ttlMs)
}

interface EnvelopeError {
  code?: number
  message?: string
  data?: { error_code?: string; details?: unknown[] }
}

/** Extracts the domain error from an ApiResponse envelope carried by an
 * AxiosError; falls back to a network-failure message. */
export function describeApiError(error: unknown): { message: string; errorCode: string | null } {
  if (error instanceof AxiosError) {
    const envelope = error.response?.data as EnvelopeError | undefined
    if (envelope && typeof envelope.code === 'number' && envelope.code !== 0) {
      return {
        message: envelope.message || 'Request failed.',
        errorCode: envelope.data?.error_code ?? null,
      }
    }
    if (!error.response) {
      return { message: 'Network error. Check your connection and retry.', errorCode: null }
    }
  }
  return { message: 'Something went wrong.', errorCode: null }
}

export function useToast() {
  return {
    toasts,
    success: (m: string) => push('success', m),
    error: (m: string) => push('error', m),
    info: (m: string) => push('info', m),
    apiError: (e: unknown) => push('error', describeApiError(e).message),
  }
}
