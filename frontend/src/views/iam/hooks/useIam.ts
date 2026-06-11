/** M03 business hooks. */
import { ref } from 'vue'
import { useToast } from '@/composables/useToast'
import { useAuthStore } from '@/store/auth'
import {
  m03ListPermissions,
  m03ListPlatformRoles,
  m03ListRoleBindings,
  m03ListTenantRoles,
  m03ListUsers,
  type PermissionOut,
  type RoleBindingOut,
  type RoleOut,
  type UserOut,
} from '@/views/iam/api'

export function useUserList() {
  const toast = useToast()
  const items = ref<UserOut[]>([])
  const total = ref<number | null>(null)
  const loading = ref(false)
  const q = ref('')
  const statuses = ref<string[]>([])

  async function load() {
    loading.value = true
    try {
      const { data } = await m03ListUsers({
        query: {
          q: q.value || null,
          status: statuses.value.length ? statuses.value : null,
          page_size: 200,
        },
        throwOnError: true,
      })
      items.value = data.data?.items ?? []
      total.value = data.data?.total_size ?? null
    } catch (e) {
      toast.apiError(e)
    } finally {
      loading.value = false
    }
  }
  return { items, total, loading, q, statuses, load }
}

export function usePermissionCatalog() {
  const toast = useToast()
  const items = ref<PermissionOut[]>([])
  const loading = ref(false)
  const domain = ref('')
  const q = ref('')

  async function load() {
    loading.value = true
    try {
      const { data } = await m03ListPermissions({
        query: { domain: domain.value || null, q: q.value || null, page_size: 500 },
        throwOnError: true,
      })
      items.value = data.data?.items ?? []
    } catch (e) {
      toast.apiError(e)
    } finally {
      loading.value = false
    }
  }
  return { items, loading, domain, q, load }
}

/** Roles for the current surface: platform route lists platform-scoped roles,
 * tenant route lists built-ins + the active tenant's custom roles. */
export function useRoleList(scope: 'platform' | 'tenant') {
  const toast = useToast()
  const auth = useAuthStore()
  const items = ref<RoleOut[]>([])
  const loading = ref(false)

  async function load() {
    loading.value = true
    try {
      if (scope === 'tenant' && auth.activeTenantId) {
        const { data } = await m03ListTenantRoles({
          path: { tenant_id: auth.activeTenantId },
          query: { page_size: 200 },
          throwOnError: true,
        })
        items.value = data.data?.items ?? []
      } else {
        const { data } = await m03ListPlatformRoles({
          query: { page_size: 200 },
          throwOnError: true,
        })
        items.value = data.data?.items ?? []
      }
    } catch (e) {
      toast.apiError(e)
    } finally {
      loading.value = false
    }
  }
  return { items, loading, load }
}

export function useBindingListQuery() {
  const toast = useToast()
  const items = ref<RoleBindingOut[]>([])
  const loading = ref(false)
  const filters = ref<{ user_id?: string; role_id?: string; scope_type?: string }>({})

  async function load() {
    loading.value = true
    try {
      const { data } = await m03ListRoleBindings({
        query: { ...filters.value, page_size: 200 },
        throwOnError: true,
      })
      items.value = data.data?.items ?? []
    } catch (e) {
      toast.apiError(e)
    } finally {
      loading.value = false
    }
  }
  return { items, loading, filters, load }
}

export const BUILTIN_ROLE_OPTIONS = [
  { value: 'builtin:platform_admin', label: 'Platform Administrator (platform)' },
  { value: 'builtin:tenant_admin', label: 'Tenant Administrator (tenant)' },
  { value: 'builtin:ops_engineer', label: 'Operations Engineer (platform)' },
  { value: 'builtin:rd_engineer', label: 'R&D Engineer (tenant or project)' },
]
