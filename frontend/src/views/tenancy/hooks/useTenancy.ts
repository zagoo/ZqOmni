/** M02 business hooks: list/load state for tenants, resources, bindings,
 * projects, members (logic out of templates per ARCHITECTURE building
 * principles). */
import { ref } from 'vue'
import { useToast } from '@/composables/useToast'
import {
  m02GetTenant,
  m02ListProjectMembers,
  m02ListProjects,
  m02ListResourceBindings,
  m02ListResources,
  m02ListTenants,
  type BindingOut,
  type MemberOut,
  type ProjectOut,
  type ResourceOut,
  type TenantOut,
} from '@/views/tenancy/api'

export function useTenantList() {
  const toast = useToast()
  const items = ref<TenantOut[]>([])
  const total = ref<number | null>(null)
  const loading = ref(false)
  const q = ref('')
  const statuses = ref<string[]>(['active', 'suspended'])

  async function load() {
    loading.value = true
    try {
      const { data } = await m02ListTenants({
        query: { q: q.value || null, status: statuses.value, page_size: 100 },
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

export function useTenantDetail(tenantId: string) {
  const toast = useToast()
  const tenant = ref<TenantOut | null>(null)
  const etag = ref<string | null>(null)
  const loading = ref(false)

  async function load() {
    loading.value = true
    try {
      const result = await m02GetTenant({ path: { tenant_id: tenantId }, throwOnError: true })
      tenant.value = result.data.data ?? null
      etag.value = (result.headers as Record<string, string>)['etag'] ?? null
    } catch (e) {
      toast.apiError(e)
    } finally {
      loading.value = false
    }
  }
  return { tenant, etag, loading, load }
}

export function useResourceList() {
  const toast = useToast()
  const items = ref<ResourceOut[]>([])
  const loading = ref(false)
  const filters = ref<{ resource_class?: string; form?: string; status?: string; q?: string }>({})

  async function load() {
    loading.value = true
    try {
      const { data } = await m02ListResources({
        query: { ...filters.value, page_size: 100 },
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

export function useBindingList(tenantId: string) {
  const toast = useToast()
  const items = ref<BindingOut[]>([])
  const loading = ref(false)

  async function load() {
    loading.value = true
    try {
      const { data } = await m02ListResourceBindings({
        path: { tenant_id: tenantId },
        query: { page_size: 100 },
        throwOnError: true,
      })
      items.value = data.data?.items ?? []
    } catch (e) {
      toast.apiError(e)
    } finally {
      loading.value = false
    }
  }
  return { items, loading, load }
}

export function useProjectList(tenantId: () => string | null) {
  const toast = useToast()
  const items = ref<ProjectOut[]>([])
  const loading = ref(false)

  async function load() {
    const tid = tenantId()
    if (!tid) return
    loading.value = true
    try {
      const { data } = await m02ListProjects({
        path: { tenant_id: tid },
        query: { page_size: 100 },
        throwOnError: true,
      })
      items.value = data.data?.items ?? []
    } catch (e) {
      toast.apiError(e)
    } finally {
      loading.value = false
    }
  }
  return { items, loading, load }
}

export function useMemberList(projectId: string) {
  const toast = useToast()
  const items = ref<MemberOut[]>([])
  const loading = ref(false)

  async function load() {
    loading.value = true
    try {
      const { data } = await m02ListProjectMembers({
        path: { project_id: projectId },
        query: { page_size: 200 },
        throwOnError: true,
      })
      items.value = data.data?.items ?? []
    } catch (e) {
      toast.apiError(e)
    } finally {
      loading.value = false
    }
  }
  return { items, loading, load }
}

export const PERSONA_TEMPLATE_OPTIONS = [
  'persona.data_collection_lead',
  'persona.robotics_data_engineer',
  'persona.annotator',
  'persona.annotation_qa_lead',
  'persona.simulation_engineer',
  'persona.model_engineer',
  'persona.evaluation_lead',
  'persona.governance_approver',
  'persona.program_manager',
]
