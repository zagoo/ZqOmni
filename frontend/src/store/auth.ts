/**
 * Auth store (setup-store pattern) — manages the short-lived access token and
 * coordinates the non-disruptive refresh flow (ARCHITECTURE §2.6).
 *
 * Dual-token model: the access JWT lives only in memory here; the long-lived
 * opaque session token rides an httpOnly cookie set by the backend and is
 * never readable from JS. Interceptors are mounted on the generated client
 * instance (src/api/generated/client.gen.ts) — the SSOT transport.
 */
import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import type { AxiosError, InternalAxiosRequestConfig } from 'axios'
import { client } from '@/api/generated/client.gen'
import {
  m01CurrentSession,
  m01Logout,
  m01RefreshAccessToken,
  m01SwitchActiveTenant,
} from '@/api/generated/sdk.gen'
import type { CurrentSessionResponse } from '@/api/generated/types.gen'

const REFRESH_PATH = '/api/v1/auth/sessions/refresh'

export const useAuthStore = defineStore('auth', () => {
  const accessToken = ref<string | null>(null)
  const current = ref<CurrentSessionResponse | null>(null)
  const loading = ref(false)

  const isAuthenticated = computed(() => accessToken.value !== null)
  const activeTenantId = computed(() => current.value?.active_tenant_id ?? null)
  const allowedKeys = computed(
    () => new Set(current.value?.permission_summary?.allowed_keys ?? []),
  )
  const user = computed(() => current.value?.user ?? null)
  const tenants = computed(() => current.value?.tenants ?? [])

  function can(key: string): boolean {
    return allowedKeys.value.has(key)
  }

  function setAccessToken(token: string | null) {
    accessToken.value = token
  }

  // --- Silent refresh (single-flight) ---
  let refreshing: Promise<boolean> | null = null

  async function tryRefresh(): Promise<boolean> {
    refreshing ??= (async () => {
      try {
        const { data } = await m01RefreshAccessToken({ throwOnError: false })
        if (data?.data?.access_token) {
          accessToken.value = data.data.access_token
          return true
        }
        return false
      } catch {
        return false
      } finally {
        refreshing = null
      }
    })()
    return refreshing
  }

  async function loadCurrentSession(): Promise<boolean> {
    const result = await m01CurrentSession()
    if (result.data?.data) {
      current.value = result.data.data
      return true
    }
    return false
  }

  async function switchTenant(tenantId: string) {
    await m01SwitchActiveTenant({ body: { tenant_id: tenantId }, throwOnError: true })
    await loadCurrentSession()
  }

  async function logout() {
    try {
      await m01Logout()
    } finally {
      accessToken.value = null
      current.value = null
    }
  }

  /** Restore a session on hard reload via the refresh cookie. */
  async function bootstrap(): Promise<boolean> {
    if (accessToken.value) return true
    loading.value = true
    try {
      if (!(await tryRefresh())) return false
      return await loadCurrentSession()
    } finally {
      loading.value = false
    }
  }

  // --- Interceptors on the generated client (mounted once) ---
  let mounted = false
  function mountInterceptors(onSessionLost: () => void) {
    if (mounted) return
    mounted = true

    client.instance.interceptors.request.use((config: InternalAxiosRequestConfig) => {
      if (accessToken.value && !config.headers.Authorization) {
        config.headers.Authorization = `Bearer ${accessToken.value}`
      }
      return config
    })

    client.instance.interceptors.response.use(
      (response) => response,
      async (error: AxiosError) => {
        const config = error.config as
          | (InternalAxiosRequestConfig & { _retried?: boolean })
          | undefined
        const status = error.response?.status
        const isRefreshCall = config?.url?.includes(REFRESH_PATH)
        // Silent, seamless refresh on access-token expiry — a raw 401 must
        // never surface to the UI (Rule 5.11).
        if (status === 401 && config && !config._retried && !isRefreshCall) {
          if (await tryRefresh()) {
            config._retried = true
            config.headers.Authorization = `Bearer ${accessToken.value}`
            return client.instance.request(config)
          }
          accessToken.value = null
          current.value = null
          onSessionLost()
        }
        return Promise.reject(error)
      },
    )
  }

  return {
    accessToken,
    current,
    loading,
    isAuthenticated,
    activeTenantId,
    user,
    tenants,
    can,
    setAccessToken,
    loadCurrentSession,
    switchTenant,
    logout,
    bootstrap,
    mountInterceptors,
  }
})
